"""Testes do motor de compressão (argumentos, skip, fila e encode real)."""

from __future__ import annotations

import os
import subprocess
import threading

import pytest

from hlsdl import compress as compress_module
from hlsdl.bridge import Bridge
from hlsdl.compress import (
    SSIM_MIN,
    CompressionManager,
    CompressionModel,
    CompressionSettings,
    CompressionWorker,
    CompressStatus,
    analyze,
    build_args,
    build_quality_report,
    detect_encoders,
    detect_qsv_devices,
    estimate_saving,
    filter_hardware_encoders,
    is_integrated_gpu,
    make_item,
    output_path,
    pick_encoder,
    quality_max_for_encoder,
    reset_qsv_device_cache,
    resolve_encoder,
    resolve_qsv_device,
    scan_media_paths,
    skip_reason,
    validate_visual_quality_report,
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


def test_quality_report_flags_extreme_bitrate_drop():
    source = {
        "streams": [{
            "codec_type": "video", "codec_name": "h264",
            "width": 1920, "height": 1080, "avg_frame_rate": "30/1",
        }],
        "format": {"duration": "10", "bit_rate": "15000000"},
    }
    output = {
        "streams": [{
            "codec_type": "video", "codec_name": "hevc",
            "width": 1920, "height": 1080, "avg_frame_rate": "30/1",
        }],
        "format": {"duration": "10", "bit_rate": "450000"},
    }
    report = build_quality_report(
        source, output, CompressionSettings(), 18_750_000, 562_500, 10.0, 0.93
    )
    assert report["bitrate_before"] == 15_000_000
    assert report["bitrate_after"] == 450_000
    assert report["quality_warning"] == "bitrate_drop"
    assert report["size_before"] == 18_750_000
    assert report["size_after"] == 562_500
    assert report["saving"] == 97.0


def test_quality_report_flags_half_bitrate_drop():
    source = {
        "streams": [{
            "codec_type": "video", "codec_name": "h264",
            "width": 1920, "height": 1080, "avg_frame_rate": "30/1",
        }],
        "format": {"duration": "10", "bit_rate": "15000000"},
    }
    output = {
        "streams": [{
            "codec_type": "video", "codec_name": "hevc",
            "width": 1920, "height": 1080, "avg_frame_rate": "30/1",
        }],
        "format": {"duration": "10", "bit_rate": "7000000"},
    }
    report = build_quality_report(
        source, output, CompressionSettings(), 18_750_000, 8_750_000, 10.0, 0.93
    )
    assert report["quality_warning"] == "bitrate_drop"


def test_quality_report_allows_hardware_floor_margin():
    source = {
        "streams": [{
            "codec_type": "video", "codec_name": "h264",
            "width": 1920, "height": 1080, "avg_frame_rate": "30/1",
        }],
        "format": {"duration": "10", "bit_rate": "10000000"},
    }
    output = {
        "streams": [{
            "codec_type": "video", "codec_name": "hevc",
            "width": 1920, "height": 1080, "avg_frame_rate": "30/1",
        }],
        "format": {"duration": "10", "bit_rate": "4800000"},
    }
    report = build_quality_report(
        source, output, CompressionSettings(), 12_500_000, 6_000_000, 10.0,
        0.96, bitrate_floor=True,
    )
    assert report["quality_warning"] == ""

    output["format"]["bit_rate"] = "4000000"
    report = build_quality_report(
        source, output, CompressionSettings(), 12_500_000, 5_000_000, 10.0,
        0.93, bitrate_floor=True,
    )
    assert report["quality_warning"] == "bitrate_drop"


def test_quality_report_ignores_drop_when_ssim_high():
    source = {
        "streams": [{
            "codec_type": "video", "codec_name": "h264",
            "width": 1920, "height": 1080, "avg_frame_rate": "30/1",
        }],
        "format": {"duration": "10", "bit_rate": "15000000"},
    }
    output = {
        "streams": [{
            "codec_type": "video", "codec_name": "hevc",
            "width": 1920, "height": 1080, "avg_frame_rate": "30/1",
        }],
        "format": {"duration": "10", "bit_rate": "1600000"},
    }
    report = build_quality_report(
        source, output, CompressionSettings(), 18_750_000, 2_000_000, 10.0, 0.99
    )
    assert report["quality_warning"] == ""
    assert report["saving"] > 89


def test_quality_report_does_not_warn_when_scaled():
    source = {
        "streams": [{
            "codec_type": "video", "codec_name": "h264",
            "width": 1920, "height": 1080, "avg_frame_rate": "30/1",
        }],
        "format": {"duration": "10", "bit_rate": "15000000"},
    }
    output = {
        "streams": [{
            "codec_type": "video", "codec_name": "hevc",
            "width": 1280, "height": 720, "avg_frame_rate": "30/1",
        }],
        "format": {"duration": "10", "bit_rate": "450000"},
    }
    report = build_quality_report(
        source, output, CompressionSettings(scale_width=1280), 18_750_000,
        562_500, 10.0, 0.95,
    )
    assert report["quality_warning"] == ""


def test_visual_quality_report_rejects_below_ssim_min(monkeypatch):
    import hlsdl.compress as compress_module

    monkeypatch.setattr(
        compress_module, "sampled_ssim", lambda *args: SSIM_MIN - 0.01
    )
    probe = {
        "streams": [{
            "codec_type": "video", "codec_name": "h264",
            "width": 1920, "height": 1080, "field_order": "progressive",
        }],
        "format": {"duration": "10"},
    }
    reason, score = validate_visual_quality_report(
        "source.mp4", "output.mp4", CompressionSettings(), probe
    )
    assert reason == "quality"
    assert score is not None and score < SSIM_MIN


def test_estimate_saving_order():
    assert estimate_saving("av1", 24) > estimate_saving("hevc", 24)
    assert estimate_saving("hevc", 24) > estimate_saving("h264", 24)
    assert estimate_saving("hevc", 40) > estimate_saving("hevc", 20)


def test_hardware_encoders_follow_gpu_vendor(monkeypatch):
    names = {"hevc_nvenc", "hevc_amf", "hevc_qsv", "libx265"}
    monkeypatch.setattr(
        "hlsdl.compress.detect_gpus",
        lambda *args, **kwargs: [{"name": "Intel(R) Arc(TM) B580 Graphics"}],
    )
    assert filter_hardware_encoders(names) == {"hevc_qsv", "libx265"}
    monkeypatch.setattr(
        "hlsdl.compress.detect_gpus",
        lambda *args, **kwargs: [{"name": "NVIDIA GeForce RTX 4070"}],
    )
    assert filter_hardware_encoders(names) == {"hevc_nvenc", "libx265"}


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


def test_qsv_device_detection_is_cached(monkeypatch):
    calls: list[tuple] = []

    class Result:
        returncode = 0
        stdout = ""
        stderr = "Using device 00:02.0 (Intel(R) Arc(TM) B580 Graphics)"

    def fake_run(*args, **kwargs):
        calls.append(args)
        return Result()

    monkeypatch.setattr(compress_module, "which", lambda name: "ffmpeg")
    monkeypatch.setattr(compress_module.subprocess, "run", fake_run)
    reset_qsv_device_cache()
    try:
        first = detect_qsv_devices()
        assert first
        count = len(calls)
        second = detect_qsv_devices()
        assert second == first
        assert len(calls) == count
    finally:
        reset_qsv_device_cache()


def test_build_args_includes_qsv_device():
    probe = {
        "streams": [{"codec_type": "video", "codec_name": "h264"}],
        "format": {"duration": "1"},
    }
    cmd = build_args("in.mp4", "out.mp4", CompressionSettings(),
                     "hevc_qsv", probe, qsv_device=1)
    assert "-qsv_device" in cmd
    assert cmd[cmd.index("-qsv_device") + 1] == "1"


def test_build_args_qsv_low_power_override():
    probe = {
        "streams": [{"codec_type": "video", "codec_name": "h264"}],
        "format": {"duration": "1"},
    }
    settings = CompressionSettings()
    default = build_args("in.mp4", "out.mp4", settings, "hevc_qsv", probe)
    assert "-low_power" not in default

    disabled = build_args(
        "in.mp4", "out.mp4", settings, "hevc_qsv", probe,
        qsv_low_power=False,
    )
    assert disabled[disabled.index("-low_power") + 1] == "0"
    # É opção do encoder: precisa vir depois do -i, senão o ffmpeg a interpreta
    # como opção do demuxer e recusa o arquivo de entrada.
    assert disabled.index("-low_power") > disabled.index("-i")

    enabled = build_args(
        "in.mp4", "out.mp4", settings, "hevc_qsv", probe,
        qsv_low_power=True,
    )
    assert enabled[enabled.index("-low_power") + 1] == "1"

    # NVENC/AMF não têm a opção low_power do QSV.
    nvenc = build_args(
        "in.mp4", "out.mp4", settings, "hevc_nvenc", probe,
        qsv_low_power=False,
    )
    assert "-low_power" not in nvenc


def test_hardware_encoders_declare_pixel_format():
    for encoder in ("hevc_qsv", "hevc_nvenc", "hevc_amf"):
        args = video_args(encoder, "hevc", 24, "balanced")
        assert args[args.index("-pix_fmt") + 1] == "nv12"
        args = video_args(encoder, "hevc", 24, "balanced", ten_bit=True)
        assert args[args.index("-pix_fmt") + 1] == "p010le"
    assert "-pix_fmt" not in video_args("libx265", "hevc", 24, "balanced")


def test_build_args_adds_hardware_bitrate_floor():
    probe = {
        "streams": [{"codec_type": "video", "codec_name": "h264"}],
        "format": {"duration": "1", "bit_rate": "10000000"},
    }
    settings = CompressionSettings(min_bitrate_percent=50)
    cmd = build_args("in.mp4", "out.mp4", settings, "hevc_qsv", probe)
    assert cmd[cmd.index("-b:v") + 1] == "5000000"
    assert cmd[cmd.index("-maxrate") + 1] == "6250000"
    assert cmd[cmd.index("-bufsize") + 1] == "10000000"


def test_build_args_floor_falls_back_to_size_duration(tmp_path):
    src = tmp_path / "in.mp4"
    src.write_bytes(b"x" * 1_250_000)
    probe = {
        "streams": [{
            "codec_type": "video", "codec_name": "h264",
            "duration": "10",
        }],
        "format": {"duration": "10"},
    }
    settings = CompressionSettings(min_bitrate_percent=50)
    cmd = build_args(str(src), "out.mp4", settings, "hevc_qsv", probe)
    assert cmd[cmd.index("-b:v") + 1] == "500000"


def test_build_args_does_not_apply_floor_to_software():
    probe = {
        "streams": [{"codec_type": "video", "codec_name": "h264"}],
        "format": {"duration": "1", "bit_rate": "10000000"},
    }
    settings = CompressionSettings(min_bitrate_percent=50)
    cmd = build_args("in.mp4", "out.mp4", settings, "libx265", probe)
    assert "-b:v" not in cmd


def test_build_args_omits_invalid_color_metadata():
    probe = {
        "streams": [{
            "codec_type": "video", "codec_name": "h264",
            "color_primaries": "reserved", "color_transfer": "reserved",
            "color_space": "reserved", "color_range": "reserved",
        }],
        "format": {"duration": "1"},
    }
    settings = CompressionSettings(codec="hevc", skip_hdr=False)
    cmd = build_args("in.mp4", "out.mp4", settings, "hevc_qsv", probe)
    for option in ("-color_primaries", "-color_trc", "-colorspace", "-color_range"):
        assert option not in cmd


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
    b.setCompressionCodec("hevc")
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
    assert b2.compressionCodec == "hevc"
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
    # Mesmo critério de test_hdr_hardware.py: só roda no runner/estande com QSV
    # real, onde HLSDL_TEST_QSV=1 está definido. A lista de encoders do ffmpeg
    # sozinha não garante driver/sessão MFX disponíveis.
    if os.environ.get("HLSDL_TEST_QSV") != "1":
        pytest.skip("defina HLSDL_TEST_QSV=1 em máquina com QSV real")
    devices = detect_qsv_devices(force=True)
    if not devices:
        pytest.skip("nenhum dispositivo QSV disponível para uma sessão MFX")
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


@pytest.mark.skipif(
    which("ffmpeg") is None or which("ffprobe") is None
    or not {"libx264", "libx265"} <= detect_encoders(),
    reason="ffmpeg/ffprobe/libx264/libx265 indisponíveis",
)
def test_worker_accepts_high_ssim_even_with_bitrate_drop(qapp, tmp_path):
    ffmpeg = which("ffmpeg")
    src = tmp_path / "in.mp4"
    subprocess.run(
        [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc2=duration=2:size=320x240:rate=30",
         "-c:v", "libx264", "-preset", "ultrafast", "-b:v", "8000k",
         "-maxrate", "8000k", "-bufsize", "16000k", "-pix_fmt", "yuv420p",
         str(src)],
        check=True, **popen_kwargs(),
    )
    before = src.read_bytes()
    worker = CompressionWorker(
        str(src),
        CompressionSettings(
            encoder="software", codec="hevc", container="mp4",
            quality=24, speed="fast", only_if_smaller=True,
        ),
        "libx265", quality_timeout=5,
    )
    prompts: list[dict] = []
    skipped: list[str] = []
    completed: list[tuple] = []
    worker.qualityConfirmation.connect(
        lambda report: (prompts.append(report), worker.respond_quality(False))
    )
    worker.skipped.connect(skipped.append)
    worker.completed.connect(lambda *args: completed.append(args))
    worker.run()

    # SSIM alto: a queda de bitrate é eficiência do codec e não é tratada
    # como perda de qualidade.
    assert not prompts
    assert completed and not skipped
    assert src.read_bytes() == before
    assert not list(tmp_path.glob("*.part.*"))


def test_compression_signals_allow_large_file_sizes(qapp):
    worker = CompressionWorker("in.mp4", CompressionSettings(), "libx265")
    succeeded: list[tuple] = []
    completed: list[tuple] = []
    worker.succeeded.connect(lambda *args: succeeded.append(args))
    worker.completed.connect(lambda *args: completed.append(args))

    before = 2_861_413_343
    after = 1_333_666_239
    worker.succeeded.emit("out.mp4", "out.mp4", before, after)
    worker.completed.emit("out.mp4", "", before, after, "hash", "ok")

    assert succeeded and succeeded[0][2] == before
    assert succeeded[0][3] == after
    assert completed and completed[0][2] == before
    assert completed[0][3] == after


def _display_names(model: CompressionModel) -> list[str]:
    return [
        model.data(model.index(row, 0), model.NAME)
        for row in range(model.rowCount())
    ]


def test_compression_model_sorting_is_display_only():
    model = CompressionModel([])
    first = make_item(1, "b.mp4")
    first["name"] = "b.mp4"
    first["saving"] = 10.0
    second = make_item(2, "a.mp4")
    second["name"] = "a.mp4"
    second["saving"] = 90.0
    model.add(first)
    model.add(second)

    model.sortBy("name")
    # A ordem de agendamento (compartilhada com o manager) não muda.
    assert [item["name"] for item in model.items()] == ["b.mp4", "a.mp4"]
    assert _display_names(model) == ["a.mp4", "b.mp4"]
    assert model.data(model.index(0, 0), model.SOURCE_INDEX) == 1
    assert model.sortKey == "name" and model.sortAscending is True

    model.sortBy("name")
    assert [item["name"] for item in model.items()] == ["b.mp4", "a.mp4"]
    assert _display_names(model) == ["b.mp4", "a.mp4"]
    assert model.sortAscending is False

    model.sortBy("saving")
    assert [item["saving"] for item in model.items()] == [10.0, 90.0]
    assert [
        model.data(model.index(row, 0), model.SAVING)
        for row in range(model.rowCount())
    ] == [90.0, 10.0]
    assert model.sortKey == "saving" and model.sortAscending is False


def test_compression_status_sort_uses_workflow_rank():
    model = CompressionModel([])
    for index, status in enumerate((
        CompressStatus.WAITING,
        CompressStatus.DONE,
        CompressStatus.ANALYZING,
        CompressStatus.ERROR,
    )):
        item = make_item(index + 1, f"{index}.mp4")
        item["name"] = f"{index}.mp4"
        item["status"] = status
        model.add(item)

    model.sortBy("status")
    assert [model.data(model.index(row, 0), model.STATUS)
            for row in range(model.rowCount())] == [
        "analyzing", "waiting", "done", "error"
    ]


def test_compression_model_remove_and_add_use_source_order_after_sort():
    model = CompressionModel([])
    for index, name in enumerate(("b.mp4", "a.mp4", "c.mp4")):
        item = make_item(index + 1, name)
        item["name"] = name
        model.add(item)
    model.sortBy("name")
    assert _display_names(model) == ["a.mp4", "b.mp4", "c.mp4"]

    # remove_rows recebe índice de agendamento (b = 0), não a linha exibida.
    model.remove_rows([0])
    assert [item["name"] for item in model.items()] == ["a.mp4", "c.mp4"]
    assert _display_names(model) == ["a.mp4", "c.mp4"]

    added = make_item(4, "0.mp4")
    added["name"] = "0.mp4"
    model.add(added)
    assert [item["name"] for item in model.items()] == ["a.mp4", "c.mp4", "0.mp4"]
    assert _display_names(model) == ["0.mp4", "a.mp4", "c.mp4"]


def test_compression_sort_does_not_change_scheduler_pick(qapp):
    model = CompressionModel([])
    first = make_item(1, "b.mp4")
    second = make_item(2, "a.mp4")
    model.add(first)
    model.add(second)
    manager = CompressionManager(model, defer_detection=True)

    model.sortBy("name")
    assert _display_names(model) == ["a.mp4", "b.mp4"]
    # O scheduler continua pegando o primeiro waiting na ordem de inserção.
    assert manager._next_waiting() is first
    assert manager.items is model.items()


def test_scan_media_paths_counts_dedup_and_cancel(tmp_path):
    root = tmp_path / "videos"
    nested = root / "sub"
    nested.mkdir(parents=True)
    (root / "a.mp4").write_bytes(b"a")
    (root / "b.txt").write_bytes(b"b")
    (root / "c.hlsdl.json").write_bytes(b"{}")
    (nested / "d.mkv").write_bytes(b"d")

    result = scan_media_paths([str(root), str(root / "a.mp4")])
    assert {os.path.basename(path) for path in result["files"]} == {"a.mp4", "d.mkv"}
    assert result["scanned"] == 5
    assert result["ignored"] == 2
    assert result["duplicates"] == 1
    assert result["errors"] == 0
    assert result["cancelled"] is False

    cancel = threading.Event()
    cancel.set()
    stopped = scan_media_paths([str(root)], cancel=cancel)
    assert stopped["cancelled"] is True
    assert stopped["files"] == []


def test_scan_media_paths_caps_without_partial_add(tmp_path):
    for index in range(3):
        (tmp_path / f"{index}.mp4").write_bytes(b"x")
    result = scan_media_paths([str(tmp_path)], max_files=2)
    assert result["truncated"] is True
    assert result["files"] == []


def test_scan_media_paths_reports_walk_errors(tmp_path, monkeypatch):
    def failing_walk(*args, **kwargs):
        raise OSError("unidade indisponível")

    monkeypatch.setattr("hlsdl.compress.os.walk", failing_walk)
    result = scan_media_paths([str(tmp_path)])
    assert result["errors"] == 1
    assert result["files"] == []
    assert result["cancelled"] is False
    assert result["truncated"] is False


def test_av1_qsv_never_gets_vbr_floor_or_rf_above_51():
    assert quality_max_for_encoder("av1", "av1_qsv") == 51
    assert quality_max_for_encoder("av1", "libaom-av1") == 63
    args = video_args("av1_qsv", "av1", 63, "balanced",
                      target_bitrate=7_000_000)
    joined = " ".join(args)
    assert "-global_quality 51" in joined
    assert "-b:v" not in args
    assert "-maxrate" not in args
    assert "-bufsize" not in args


def test_add_scanned_deduplicates_existing_items(qapp, tmp_path):
    model = CompressionModel([])
    manager = CompressionManager(model, defer_detection=True)
    first = tmp_path / "a.mp4"
    second = tmp_path / "b.mp4"
    first.write_bytes(b"a")
    second.write_bytes(b"b")

    assert manager.add_scanned([str(first), str(first)]) == 1
    assert manager.add_scanned([str(first), str(second)]) == 1
    assert [os.path.basename(item["input"]) for item in model.items()] == [
        "a.mp4", "b.mp4"
    ]


def test_compression_row_actions_use_source_rows_after_sort(qapp):
    """Cancelar/remover usam o índice de agendamento, mesmo com tabela ordenada."""
    model = CompressionModel([])
    first = make_item(1, "b.mp4")
    second = make_item(2, "a.mp4")
    first["name"] = "b.mp4"
    second["name"] = "a.mp4"
    model.add(first)
    model.add(second)
    manager = CompressionManager(model, defer_detection=True)

    model.sortBy("name")
    assert _display_names(model) == ["a.mp4", "b.mp4"]
    manager.cancelItem(0)  # source 0 = b.mp4, não a linha exibida 0 = a.mp4
    assert first["status"] == CompressStatus.CANCELLED
    assert second["status"] == CompressStatus.WAITING
