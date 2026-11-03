"""Testes do motor de compressão (argumentos, skip, fila e encode real)."""

from __future__ import annotations

import os
import subprocess

import pytest

from hlsdl.bridge import Bridge
from hlsdl.compress import (
    CompressionManager,
    CompressionModel,
    CompressionSettings,
    CompressionWorker,
    CompressStatus,
    analyze,
    build_args,
    detect_encoders,
    detect_qsv_devices,
    estimate_saving,
    is_integrated_gpu,
    output_path,
    pick_encoder,
    resolve_encoder,
    resolve_qsv_device,
    skip_reason,
    video_args,
)
from hlsdl.downloader import DownloadWorker  # noqa: F401  (garante import limpo)
from hlsdl.model import DownloadModel
from hlsdl.queue import QueueManager
from hlsdl.services.procutils import popen_kwargs, which


def test_video_args_per_encoder():
    qsv = " ".join(video_args("hevc_qsv", "hevc", 24, "balanced"))
    nvenc = " ".join(video_args("hevc_nvenc", "hevc", 24, "fast"))
    amf = " ".join(video_args("hevc_amf", "hevc", 23, "slow"))
    x265 = " ".join(video_args("libx265", "hevc", 26, "balanced"))
    x264 = " ".join(video_args("libx264", "h264", 22, "slower"))
    av1 = " ".join(video_args("libsvtav1", "av1", 30, "fast"))
    assert "hevc_qsv" in qsv and "global_quality 24" in qsv
    assert "hevc_nvenc" in nvenc and "-cq 24" in nvenc and "-gpu 0" in nvenc
    assert "hevc_amf" in amf and "qp_i 23" in amf
    assert "libx265" in x265 and "-crf 26" in x265
    assert "libx264" in x264 and "-preset slower" in x264
    assert "libsvtav1" in av1 and "-crf 30" in av1


def test_auto_prefers_discrete_gpu_encoders():
    settings = CompressionSettings(encoder="auto")
    all_names = {"hevc_qsv", "hevc_nvenc", "hevc_amf", "libx265"}
    assert resolve_encoder(settings, all_names) == "hevc_nvenc"
    no_nvenc = {"hevc_qsv", "hevc_amf", "libx265"}
    assert resolve_encoder(settings, no_nvenc) == "hevc_amf"
    only_qsv = {"hevc_qsv", "libx265"}
    assert resolve_encoder(settings, only_qsv) == "hevc_qsv"
    # Codec sem encoder de hardware cai para software.
    assert resolve_encoder(settings, {"libx264"}, codec="h264") == "libx264"


def test_estimate_saving_order():
    assert estimate_saving("av1", 24) > estimate_saving("hevc", 24)
    assert estimate_saving("hevc", 24) > estimate_saving("h264", 24)
    assert estimate_saving("hevc", 40) < estimate_saving("hevc", 20)


def test_x265_10bit_and_tuning():
    args = " ".join(video_args(
        "libx265", "hevc", 24, "slower",
        ten_bit=True, x265_tuning=True,
    ))
    assert "yuv420p10le" in args
    assert "aq-mode=3" in args
    assert "psy-rd=2.0" in args


def test_kvazaar_encoder_detection():
    assert pick_encoder("kvazaar", "hevc", {"libkvazaar"}) == "libkvazaar"
    assert pick_encoder("kvazaar", "h264", {"libkvazaar"}) == ""
    args = " ".join(video_args("libkvazaar", "hevc", 24, "fast"))
    assert "libkvazaar" in args and "-crf 24" in args


def test_resolve_qsv_device_prefers_arc():
    devices = [
        {"index": 0, "name": "Intel(R) UHD Graphics 770", "integrated": True},
        {"index": 1, "name": "Intel(R) Arc(TM) B580 Graphics", "integrated": False},
    ]
    assert resolve_qsv_device(-1, devices) == 1
    assert resolve_qsv_device(0, devices) == 0
    assert resolve_qsv_device(-1, []) == 0
    assert is_integrated_gpu("Intel(R) UHD Graphics 770") is True
    assert is_integrated_gpu("Intel(R) Arc(TM) B580 Graphics") is False
    assert is_integrated_gpu("NVIDIA GeForce RTX 4060") is False


def test_build_args_includes_qsv_device():
    probe = {
        "streams": [{"codec_type": "video", "codec_name": "h264"}],
        "format": {"duration": "1"},
    }
    cmd = build_args("in.mp4", "out.mp4", CompressionSettings(),
                     "hevc_qsv", probe, qsv_device=1)
    assert "-qsv_device" in cmd
    assert cmd[cmd.index("-qsv_device") + 1] == "1"


def test_build_args_preserves_hdr_metadata():
    probe = {
        "streams": [{
            "codec_type": "video", "codec_name": "h264",
            "color_primaries": "bt2020", "color_transfer": "smpte2084",
            "color_space": "bt2020nc", "color_range": "tv",
        }],
        "format": {"duration": "1"},
    }
    settings = CompressionSettings(skip_hdr=False)
    cmd = build_args("in.mp4", "out.mp4", settings, "libx265", probe)
    for option, value in (
        ("-color_primaries", "bt2020"),
        ("-color_trc", "smpte2084"),
        ("-colorspace", "bt2020nc"),
        ("-color_range", "tv"),
    ):
        assert option in cmd
        assert cmd[cmd.index(option) + 1] == value


def test_analyze_and_skip_rules():
    probe = {
        "streams": [
            {"codec_type": "video", "codec_name": "h264", "color_transfer": "bt709"},
            {"codec_type": "audio", "codec_name": "aac"},
        ],
        "format": {"duration": "10.5"},
    }
    videos, audios, subs, duration = analyze(probe)
    assert len(videos) == 1 and len(audios) == 1 and duration == 10.5
    assert skip_reason(CompressionSettings(), probe) == ""

    hevc = {"streams": [{"codec_type": "video", "codec_name": "hevc"}],
            "format": {"duration": "1"}}
    assert skip_reason(CompressionSettings(), hevc) == "already_codec"
    assert skip_reason(CompressionSettings(reencode_hevc=True), hevc) == ""

    hdr = {"streams": [{"codec_type": "video", "codec_name": "h264",
                        "color_transfer": "smpte2084"}],
           "format": {"duration": "1"}}
    assert skip_reason(CompressionSettings(), hdr) == "hdr"
    assert skip_reason(CompressionSettings(skip_hdr=False), hdr) == ""


def test_output_path_unique(tmp_path):
    src = tmp_path / "video.mkv"
    src.write_bytes(b"x")
    first = output_path(str(src), "hevc", "mp4")
    assert first.endswith("video_hevc.mp4")
    open(first, "wb").close()
    second = output_path(str(src), "hevc", "mp4")
    assert second.endswith("video_hevc-2.mp4")


def test_detect_encoders_returns_set():
    found = detect_encoders()
    assert isinstance(found, set)


def test_manager_add_paths_filters_videos(qapp, tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"x")
    (tmp_path / "b.txt").write_text("x", encoding="utf-8")
    model = CompressionModel([])
    manager = CompressionManager(model)
    added = manager.add_paths([str(tmp_path)], recursive=True)
    assert added == 1
    assert model.rowCount() == 1
    assert manager.items[0]["name"] == "a.mp4"


def test_bridge_persists_compression_settings(qapp, tmp_path, fake_deps):
    settings = str(tmp_path / "s.ini")
    b = Bridge(QueueManager(DownloadModel([]), outdir="out"), "out",
               settings_path=settings, deps=fake_deps)
    b.setCompressionEncoder("software")
    b.setCompressionCodec("h264")
    b.setCompressionContainer("mkv")
    b.setCompressionQuality(26)
    b.setCompressionParallel(2)
    b.setCompressionSpeed("slower")
    b.setCompressionOnlyIfSmaller(False)
    b.setCompressionQsvDevice(1)
    b.setCompressionTenBit(True)
    b.setCompressionX265Tuning(True)
    b2 = Bridge(QueueManager(DownloadModel([]), outdir="out"), "out",
                settings_path=settings, deps=fake_deps)
    assert b2.compressionEncoder == "software"
    assert b2.compressionCodec == "h264"
    assert b2.compressionContainer == "mkv"
    assert b2.compressionQuality == 26
    assert b2.compressionParallel == 2
    assert b2.compressionSpeed == "slower"
    assert b2.compressionOnlyIfSmaller is False
    assert b2.compressionQsvDevice == 1
    assert b2.compressionTenBit is True
    assert b2.compressionX265Tuning is True
    assert isinstance(b2.compressionEstimate, int)


@pytest.mark.skipif(
    which("ffmpeg") is None or which("ffprobe") is None
    or "libx265" not in detect_encoders(),
    reason="ffmpeg/ffprobe/libx265 indisponíveis",
)
def test_real_x265_encode(qapp, tmp_path):
    ffmpeg = which("ffmpeg")
    src = tmp_path / "in.mp4"
    subprocess.run(
        [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=15",
         "-pix_fmt", "yuv420p", "-c:v", "libx264", str(src)],
        check=True, **popen_kwargs(),
    )
    settings = CompressionSettings(
        encoder="software", quality=30, speed="fast",
        only_if_smaller=False, replace_original=False,
    )
    worker = CompressionWorker(str(src), settings, "libx265")
    events: list = []
    worker.succeeded.connect(
        lambda tmp, final, before, after: events.append((tmp, final, before, after))
    )
    worker.failed.connect(lambda err: events.append(("fail", err)))
    worker.run()

    assert events and events[0][0] != "fail", events
    tmp, final, before, after = events[0]
    assert os.path.exists(tmp) and after > 0 and before > 0
    os.replace(tmp, final)
    assert os.path.exists(final)


@pytest.mark.skipif(
    which("ffmpeg") is None or "hevc_qsv" not in detect_encoders(),
    reason="ffmpeg/QSV indisponível",
)
def test_real_qsv_encode_prefers_dedicated(qapp, tmp_path):
    devices = detect_qsv_devices()
    if not devices:
        pytest.skip("nenhum dispositivo QSV detectado")
    index = resolve_qsv_device(-1, devices)
    dedicated = [d for d in devices if not d["integrated"]]
    if dedicated:
        assert index == dedicated[0]["index"]

    ffmpeg = which("ffmpeg")
    src = tmp_path / "in.mp4"
    subprocess.run(
        [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=15",
         "-pix_fmt", "yuv420p", "-c:v", "libx264", str(src)],
        check=True, **popen_kwargs(),
    )
    settings = CompressionSettings(
        encoder="qsv", quality=30, speed="fast", qsv_device=-1,
        only_if_smaller=False, replace_original=False,
    )
    worker = CompressionWorker(str(src), settings, "hevc_qsv", qsv_device=index)
    events: list = []
    worker.succeeded.connect(
        lambda tmp, final, before, after: events.append((tmp, final, before, after))
    )
    worker.failed.connect(lambda err: events.append(("fail", err)))
    worker.run()

    assert events and events[0][0] != "fail", events
    tmp, final, _before, after = events[0]
    assert os.path.exists(tmp) and after > 0


@pytest.mark.skipif(
    which("ffmpeg") is None or which("ffprobe") is None
    or "libx265" not in detect_encoders(),
    reason="ffmpeg/ffprobe/libx265 indisponíveis",
)
def test_manager_queue_real_encode(qapp, tmp_path):
    from tests.conftest import process_until

    ffmpeg = which("ffmpeg")
    src = tmp_path / "in.mp4"
    subprocess.run(
        [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=15",
         "-pix_fmt", "yuv420p", "-c:v", "libx264", str(src)],
        check=True, **popen_kwargs(),
    )

    model = CompressionModel([])
    manager = CompressionManager(model)
    manager.settings = CompressionSettings(
        encoder="software", quality=32, speed="fast", parallel=1,
        only_if_smaller=False, replace_original=False,
    )
    manager.add_paths([str(src)])
    manager.start()

    assert process_until(
        qapp,
        lambda: all(i["status"].is_final for i in manager.items),
        timeout=90,
    )
    item = manager.items[0]
    assert item["status"] == CompressStatus.DONE, item
    assert item["output"] and os.path.exists(item["output"])
    manager.shutdown(timeout=5)
