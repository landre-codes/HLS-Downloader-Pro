"""Testes do compressor: presets, filtros, streams e validação."""

from __future__ import annotations

import os

import pytest

from hlsdl.bridge import Bridge
from hlsdl.compress import (
    CompressionManager,
    CompressionSettings,
    build_args,
    build_filters,
    expected_dimensions,
    quality_max_for_codec,
    skip_reason,
    validate_output,
    video_args,
)
from hlsdl.downloader import DownloadWorker
from hlsdl.model import DownloadModel
from hlsdl.queue import QueueManager


def _probe(video=None, audios=None, subs=None, duration="10"):
    streams = [video or {"codec_type": "video", "codec_name": "h264"}]
    streams += audios or []
    streams += subs or []
    return {"streams": streams, "format": {"duration": duration}}


def test_quality_range_is_codec_specific():
    assert quality_max_for_codec("av1") == 63
    assert quality_max_for_codec("hevc") == 51
    av1 = " ".join(video_args("libsvtav1", "av1", 60, "balanced"))
    hevc = " ".join(video_args("libx265", "hevc", 60, "balanced"))
    assert "-crf 60" in av1
    assert "-crf 51" in hevc


def test_build_args_preserves_mkv_bitmap_subs_and_attachments():
    probe = _probe(
        audios=[{"codec_type": "audio", "codec_name": "dts", "channels": 6}],
        subs=[
            {"codec_type": "subtitle", "codec_name": "hdmv_pgs_subtitle"},
            {"codec_type": "subtitle", "codec_name": "subrip"},
        ],
    )
    settings = CompressionSettings(
        codec="hevc", container="mkv", subtitle_mode="all", audio_mode="auto"
    )
    cmd = build_args("in.mkv", "out.mkv", settings, "libx265", probe)
    joined = " ".join(cmd)
    assert "-map 0:s:0" in joined and "-map 0:s:1" in joined
    assert "-c:s copy" in joined
    assert "-map 0:t?" in joined
    assert "-c:a:0 copy" in joined  # DTS não deve virar AAC em MKV


def test_build_args_mp4_reencodes_unsafe_audio_with_channel_bitrate():
    probe = _probe(
        audios=[{"codec_type": "audio", "codec_name": "dts", "channels": 6}],
    )
    settings = CompressionSettings(codec="hevc", container="mp4", audio_mode="auto")
    cmd = build_args("in.mkv", "out.mp4", settings, "libx265", probe)
    joined = " ".join(cmd)
    assert "-c:a:0 aac" in joined
    assert "-b:a:0 320k" in joined


def test_build_args_applies_deinterlace_denoise_and_tonemap():
    probe = _probe(
        video={
            "codec_type": "video",
            "codec_name": "h264",
            "field_order": "tt",
            "color_transfer": "smpte2084",
            "color_primaries": "bt2020",
        }
    )
    settings = CompressionSettings(
        codec="hevc", container="mp4", deinterlace="auto", denoise="medium",
        hdr_tonemap=True, skip_hdr=False,
    )
    cmd = build_args("in.mp4", "out.mp4", settings, "libx265", probe)
    joined = " ".join(cmd)
    assert "yadif=deint=interlaced" in joined
    assert "hqdn3d=3:3:12:12" in joined
    assert "tonemap=hable" in joined
    assert "-color_trc bt709" in joined


def test_geometry_filters_and_expected_dimensions():
    video = {"codec_type": "video", "width": 1920, "height": 1080}
    settings = CompressionSettings(
        codec="hevc", crop="1280:720:100:50",
        scale_width=640, scale_height=360, rotate=90, fps=30,
    )
    chain = build_filters(settings, video)
    assert "crop=1280:720:100:50" in chain
    assert "scale=640:360:flags=lanczos" in chain
    assert "transpose=1" in chain
    assert "fps=30" in chain
    width, height = expected_dimensions(settings, video)
    assert (width, height) == (360, 640)


def test_hdr_tonemap_overrides_default_skip():
    probe = _probe(
        video={
            "codec_type": "video",
            "codec_name": "hevc",
            "color_transfer": "smpte2084",
        }
    )
    assert skip_reason(CompressionSettings(codec="h264"), probe) == "hdr"
    assert skip_reason(
        CompressionSettings(codec="h264", hdr_tonemap=True), probe
    ) == ""


def test_validate_output_detects_truncation_and_audio_loss(tmp_path):
    good = tmp_path / "good.mp4"
    good.write_bytes(b"x" * 100)
    source = _probe(
        audios=[{"codec_type": "audio", "codec_name": "aac"}], duration="100"
    )
    assert validate_output(source, _probe(
        audios=[{"codec_type": "audio", "codec_name": "aac"}], duration="100"
    ), str(good)) == ""
    assert validate_output(source, _probe(duration="40"), str(good)) == "duration"
    assert validate_output(source, _probe(duration="100"), str(good)) == "audio"
    assert validate_output(source, {"streams": []}, str(good)) == "no_video"


def test_download_compression_uses_part_and_does_not_reuse_stale_output(
    monkeypatch, tmp_path
):
    src = tmp_path / "a.mp4"
    src.write_bytes(b"orig" * 200)
    stale = tmp_path / "a_h264.mp4"
    stale.write_bytes(b"stale")

    w = DownloadWorker(
        "https://x.com/v", str(tmp_path), codec="h264",
        compress_level="strong", container="mp4",
    )
    monkeypatch.setattr("hlsdl.downloader.which", lambda name: "/usr/bin/ffmpeg")
    monkeypatch.setattr("hlsdl.downloader.probe_duration", lambda p: 10.0)
    monkeypatch.setattr(
        "hlsdl.downloader.probe_media",
        lambda p: _probe(
            audios=[{"codec_type": "audio", "codec_name": "aac"}], duration="10"
        ),
    )

    seen = {}

    def fake_run(cmd, duration=None, is_ffmpeg=False):
        seen["cmd"] = list(cmd)
        seen["tmp"] = cmd[-1]
        with open(cmd[-1], "wb") as fh:
            fh.write(b"compressed" * 8)
        return True, cmd[-1]

    monkeypatch.setattr(w, "_run_process", fake_run)
    out = w._maybe_compress(str(src))
    assert out is not None
    assert out.endswith("a_h264-2.mp4")
    assert os.path.exists(out) and os.path.getsize(out) == 80
    assert stale.read_bytes() == b"stale"
    assert src.exists()
    assert ".part." in os.path.basename(seen["tmp"])


def test_download_compression_rejects_invalid_output(monkeypatch, tmp_path):
    src = tmp_path / "a.mp4"
    src.write_bytes(b"orig" * 200)
    w = DownloadWorker(
        "https://x.com/v", str(tmp_path), codec="h264", container="mp4"
    )
    monkeypatch.setattr("hlsdl.downloader.which", lambda name: "/usr/bin/ffmpeg")
    monkeypatch.setattr("hlsdl.downloader.probe_duration", lambda p: 10.0)

    def fake_probe(path):
        if ".part." in path:
            return {"streams": [], "format": {"duration": "2"}}
        return _probe(
            audios=[{"codec_type": "audio", "codec_name": "aac"}], duration="10"
        )

    monkeypatch.setattr("hlsdl.downloader.probe_media", fake_probe)
    monkeypatch.setattr(
        w, "_run_process",
        lambda cmd, duration=None, is_ffmpeg=False: (
            open(cmd[-1], "wb").write(b"bad") and (True, cmd[-1])
        ),
    )
    assert w._maybe_compress(str(src)) == str(src)
    assert not any(p.name.endswith(".part.mp4") for p in tmp_path.iterdir())


def test_manager_resolves_encoder_per_job(monkeypatch):
    manager = CompressionManager.__new__(CompressionManager)
    manager.available = {"hevc_qsv", "libx264", "libx265"}
    manager._qsv_device = 0
    manager.qsv_devices = []
    monkeypatch.setattr("hlsdl.compress.probe_encoder", lambda *a, **k: True)
    assert manager._encoder_for_job(
        CompressionSettings(codec="hevc", encoder="qsv")
    ) == "hevc_qsv"
    assert manager._encoder_for_job(
        CompressionSettings(codec="h264", encoder="qsv")
    ) == "libx264"


def test_bridge_applies_preset_and_persists_new_choices(qapp, tmp_path, fake_deps):
    path = str(tmp_path / "s.ini")
    bridge = Bridge(
        QueueManager(DownloadModel([]), outdir="out"), "out",
        settings_path=path, deps=fake_deps,
    )
    bridge.compression.available = {"libx265", "libx264", "libsvtav1"}
    bridge.applyCompressionPreset("archive_hevc")
    assert bridge.compressionEncoder == "software"
    assert bridge.compressionCodec == "hevc"
    assert bridge.compressionContainer == "mkv"
    assert bridge.compressionQuality == 16
    assert bridge.compressionTenBit is True
    assert bridge.compressionPreset == "archive_hevc"
    bridge.setCompressionQuality(23)
    assert bridge.compressionPreset == "custom"
    bridge.setCompressionHdrTonemap(True)
    bridge.setCompressionDeinterlace("on")
    bridge.setCompressionDenoise("medium")
    bridge.setCompressionAudioMode("copy")
    bridge.setCompressionSubtitleMode("all")

    restored = Bridge(
        QueueManager(DownloadModel([]), outdir="out"), "out",
        settings_path=path, deps=fake_deps,
    )
    assert restored.compressionHdrTonemap is True
    assert restored.compressionDeinterlace == "on"
    assert restored.compressionDenoise == "medium"
    assert restored.compressionAudioMode == "copy"
    assert restored.compressionSubtitleMode == "all"
    assert restored.compressionQualityMax == 51


@pytest.mark.parametrize("key", ["fast_h264", "balanced_hevc", "quality_hevc",
                                 "archive_hevc", "av1_balanced"])
def test_presets_are_known(qapp, tmp_path, fake_deps, key):
    bridge = Bridge(
        QueueManager(DownloadModel([]), outdir="out"), "out",
        settings_path=str(tmp_path / f"{key}.ini"), deps=fake_deps,
    )
    bridge.compression.available = {"libx265", "libx264", "libsvtav1"}
    assert key in bridge.compressionPresets
    bridge.applyCompressionPreset(key)
    assert bridge.compressionEffectiveEncoder != ""


def test_bridge_min_bitrate_setting_persists(qapp, tmp_path, fake_deps):
    path = str(tmp_path / "min_bitrate.ini")
    bridge = Bridge(
        QueueManager(DownloadModel([]), outdir="out"), "out",
        settings_path=path, deps=fake_deps,
    )
    assert bridge.compressionMinBitrate == 0
    bridge.setCompressionMinBitrate(30)
    assert bridge.compressionMinBitrate == 30

    restored = Bridge(
        QueueManager(DownloadModel([]), outdir="out"), "out",
        settings_path=path, deps=fake_deps,
    )
    assert restored.compressionMinBitrate == 30
    restored.setCompressionMinBitrate(0)
    assert restored.compressionMinBitrate == 0
