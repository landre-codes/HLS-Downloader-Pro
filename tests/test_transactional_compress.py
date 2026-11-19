"""Transactional compression and startup/retry safety tests."""

from __future__ import annotations

import os
import subprocess

import pytest

from hlsdl.compress import (
    CompressionManager,
    CompressionModel,
    CompressionSettings,
    CompressionWorker,
    validate_output_quality,
)
from hlsdl.integrity import read_completion, reserved_paths, verify_completion
from hlsdl.services.procutils import popen_kwargs, which


def _probe(audio_channels: int = 2, width: int = 320, height: int = 240,
           pix_fmt: str = "yuv420p", duration: str = "10") -> dict:
    streams = [
        {"codec_type": "video", "codec_name": "h264", "width": width,
         "height": height, "pix_fmt": pix_fmt, "duration": duration},
    ]
    if audio_channels:
        streams.append({
            "codec_type": "audio", "codec_name": "aac",
            "channels": audio_channels, "duration": duration,
        })
    return {"streams": streams, "format": {"duration": duration}}


def test_start_without_detection_keeps_items_waiting(tmp_path):
    source = tmp_path / "video.mp4"
    source.write_bytes(b"x")
    manager = CompressionManager(CompressionModel([]), defer_detection=True)
    manager.add_paths([str(source)])
    assert manager.start() is False
    assert manager.items[0]["status"].value == "waiting"
    assert manager.last_error == "detecting"


def test_shutdown_joins_qsv_detection_thread(qapp):
    import threading

    manager = CompressionManager(CompressionModel([]), defer_detection=True)
    started = threading.Event()

    def worker():
        started.set()
        while not manager._closing:
            threading.Event().wait(0.01)

    thread = threading.Thread(target=worker, daemon=True)
    manager._qsv_thread = thread
    thread.start()
    assert started.wait(1)
    manager.shutdown(timeout=2)
    assert not thread.is_alive()


def test_retry_refuses_while_previous_thread_is_alive(tmp_path):
    source = tmp_path / "video.mp4"
    source.write_bytes(b"x")
    manager = CompressionManager(CompressionModel([]), defer_detection=True)
    manager.add_paths([str(source)])
    item = manager.items[0]
    item["status"] = manager.items[0]["status"].__class__.ERROR
    manager._threads[item["id"]] = (object(), object(), item)
    assert manager.retryItem(0) is False
    manager._threads.clear()
    assert manager.retryItem(0) is True
    assert item["status"].value == "waiting"


def test_deep_validation_rejects_audio_channel_loss(tmp_path):
    output = tmp_path / "out.mp4"
    output.write_bytes(b"x" * 100)
    settings = CompressionSettings(codec="hevc", container="mp4",
                                   audio_mode="auto")
    reason = validate_output_quality(
        _probe(audio_channels=6), _probe(audio_channels=2),
        str(output), settings,
    )
    assert reason == "audio_channels"


def test_deep_validation_rejects_resolution_change(tmp_path):
    output = tmp_path / "out.mp4"
    output.write_bytes(b"x" * 100)
    settings = CompressionSettings(codec="hevc", container="mp4")
    reason = validate_output_quality(
        _probe(width=1920, height=1080), _probe(width=1280, height=720),
        str(output), settings,
    )
    assert reason == "resolution"


def test_deep_validation_respects_subtitle_none_policy(tmp_path):
    output = tmp_path / "out.mp4"
    output.write_bytes(b"x" * 100)
    source = _probe()
    source["streams"].append({
        "codec_type": "subtitle", "codec_name": "subrip",
        "duration": "10",
    })
    settings = CompressionSettings(codec="hevc", container="mp4",
                                   subtitle_mode="none")
    assert validate_output_quality(
        source, _probe(), str(output), settings
    ) == ""
    with_subs = _probe()
    with_subs["streams"].append({
        "codec_type": "subtitle", "codec_name": "mov_text",
        "duration": "10",
    })
    assert validate_output_quality(
        source, with_subs, str(output), settings
    ) == "subtitles"


def test_deep_validation_requires_10bit_when_requested(tmp_path):
    output = tmp_path / "out.mp4"
    output.write_bytes(b"x" * 100)
    settings = CompressionSettings(codec="hevc", container="mp4",
                                   ten_bit=True)
    reason = validate_output_quality(
        _probe(pix_fmt="yuv420p10le"), _probe(pix_fmt="yuv420p"),
        str(output), settings,
    )
    assert reason == "bit_depth"


def _hdr_probe(*, with_mastering=True, with_light=True, max_average=400):
    probe = _probe(pix_fmt="yuv420p10le")
    video = probe["streams"][0]
    video.update({
        "codec_name": "hevc",
        "color_primaries": "bt2020",
        "color_transfer": "smpte2084",
        "color_space": "bt2020nc",
        "color_range": "tv",
    })
    side_data = []
    if with_mastering:
        side_data.append({
            "side_data_type": "Mastering display metadata",
            "green_x": "13250/50000", "green_y": "34500/50000",
            "blue_x": "7500/50000", "blue_y": "3000/50000",
            "red_x": "34000/50000", "red_y": "16000/50000",
            "white_point_x": "15635/50000", "white_point_y": "16450/50000",
            "min_luminance": "50/10000", "max_luminance": "10000000/10000",
        })
    if with_light:
        side_data.append({
            "side_data_type": "Content light level metadata",
            "max_content": 1000, "max_average": max_average,
        })
    video["side_data_list"] = side_data
    return probe


def test_deep_validation_preserves_hdr10_for_all_encoders(tmp_path):
    output = tmp_path / "out.mp4"
    output.write_bytes(b"x" * 100)
    settings = CompressionSettings(codec="hevc", container="mp4")
    good = _hdr_probe()
    assert validate_output_quality(
        _hdr_probe(), good, str(output), settings, encoder="hevc_qsv"
    ) == ""
    missing_light = _hdr_probe(with_light=False)
    assert validate_output_quality(
        _hdr_probe(), missing_light, str(output), settings, encoder="hevc_nvenc"
    ) == "hdr_metadata:content_light_missing"
    changed_light = _hdr_probe(max_average=200)
    assert validate_output_quality(
        _hdr_probe(), changed_light, str(output), settings, encoder="hevc_amf"
    ) == "hdr_metadata:content_light_max_average_mismatch"
    missing_mastering = _hdr_probe(with_mastering=False)
    assert validate_output_quality(
        _hdr_probe(), missing_mastering, str(output), settings, encoder="libx265"
    ) == "hdr_metadata:mastering_missing"


@pytest.mark.skipif(
    which("ffmpeg") is None or which("ffprobe") is None,
    reason="ffmpeg/ffprobe indisponíveis",
)
def test_real_transactional_encode_preserves_original_and_backup(tmp_path):
    from hlsdl.compress import detect_encoders

    if "libx265" not in detect_encoders():
        pytest.skip("libx265 indisponível")
    ffmpeg = which("ffmpeg")
    source = tmp_path / "in.mp4"
    subprocess.run(
        [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=15",
         "-pix_fmt", "yuv420p", "-c:v", "libx264", str(source)],
        check=True, **popen_kwargs(),
    )
    settings = CompressionSettings(
        encoder="software", codec="hevc", container="mp4",
        quality=30, speed="fast", only_if_smaller=False,
        replace_original=True,
    )
    worker = CompressionWorker(
        str(source), settings, "libx265",
        job_id="test", journals_dir=str(tmp_path / "journals"),
    )
    events: list = []
    worker.completed.connect(
        lambda final, backup, before, after, sha, validation:
        events.append((final, backup, before, after, sha, validation))
    )
    worker.failed.connect(lambda err: events.append(("fail", err)))
    worker.run()

    assert events and events[0][0] != "fail", events
    final, backup, _before, after, digest, validation = events[0]
    assert os.path.exists(final)
    assert after > 0
    assert digest and len(digest) == 64
    assert validation == "ok"
    assert backup and os.path.exists(backup)
    assert not source.exists()
    record = read_completion(final)
    assert record is not None and record.original_backup == backup
    ok, reason = verify_completion(final)
    assert ok, reason
    assert final not in reserved_paths()
    assert not os.listdir(tmp_path / "journals")
