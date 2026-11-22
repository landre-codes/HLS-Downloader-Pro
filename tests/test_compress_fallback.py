"""Fallback de encoders de hardware e diagnóstico de falhas de compressão."""

from __future__ import annotations

from pathlib import Path

from hlsdl.compress import CompressionSettings, CompressionWorker


def _probe() -> dict:
    return {
        "streams": [{
            "codec_type": "video",
            "codec_name": "h264",
            "width": 1920,
            "height": 1080,
            "pix_fmt": "yuv420p",
            "duration": "10",
        }],
        "format": {"duration": "10"},
    }


def _worker(
    tmp_path: Path,
    encoder: str = "hevc_qsv",
    fallback: str = "libx265",
) -> CompressionWorker:
    return CompressionWorker(
        str(tmp_path / "in.mp4"),
        CompressionSettings(codec="hevc", container="mp4"),
        encoder,
        fallback_encoder=fallback,
        journals_dir=str(tmp_path / "journals"),
    )


def _fake_build_args(calls: list[tuple[str, bool | None]]):
    def build(src, tmp, settings, encoder, probe, qsv_device=0, **kwargs):
        calls.append((encoder, kwargs.get("qsv_low_power")))
        return ["ffmpeg", "-c:v", encoder, tmp]

    return build


def test_qsv_attempts_low_power_then_software(tmp_path):
    worker = _worker(tmp_path)
    assert worker._encoder_attempts() == [
        ("hevc_qsv", None),
        ("hevc_qsv", False),
        ("libx265", None),
    ]


def test_nvenc_attempts_software_without_low_power(tmp_path):
    worker = _worker(tmp_path, "hevc_nvenc")
    assert worker._encoder_attempts() == [
        ("hevc_nvenc", None),
        ("libx265", None),
    ]


def test_software_encoder_has_no_fallback(tmp_path):
    worker = _worker(tmp_path, "libx265", fallback="")
    assert worker._encoder_attempts() == [("libx265", None)]


def test_hardware_init_failure_markers(tmp_path):
    worker = _worker(tmp_path)
    assert worker._hardware_init_failure(
        "hevc_qsv", "Low power mode is unsupported | Current resolution is unsupported"
    )
    assert worker._hardware_init_failure(
        "hevc_nvenc", "Error while opening encoder - maybe incorrect parameters"
    )
    assert not worker._hardware_init_failure(
        "hevc_qsv", "Invalid data found when processing input"
    )
    assert not worker._hardware_init_failure(
        "libx265", "Error while opening encoder"
    )


def test_fallback_runs_qsv_low_power_then_software(
    tmp_path, monkeypatch
):
    worker = _worker(tmp_path)
    temp = str(tmp_path / "out.mp4")
    calls: list[tuple[str, bool | None]] = []
    seen: list[tuple[str, str]] = []
    worker.fallbackUsed.connect(lambda encoder, reason: seen.append((encoder, reason)))
    monkeypatch.setattr(
        "hlsdl.compress.build_args", _fake_build_args(calls)
    )

    attempts = 0

    def fake_run(cmd, duration):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return 1, "Error while opening encoder | Low power mode is unsupported"
        Path(temp).write_bytes(b"encoded")
        return 0, ""

    monkeypatch.setattr(worker, "_run_ffmpeg", fake_run)
    encoder, rc, detail = worker._encode_with_fallback(_probe(), temp, 10.0)

    assert encoder == "libx265" and rc == 0 and detail == ""
    assert calls == [
        ("hevc_qsv", None),
        ("hevc_qsv", False),
        ("libx265", None),
    ]
    assert seen == [("libx265", "software")]
    assert worker.encoder == "libx265"


def test_low_power_retry_can_succeed_alone(tmp_path, monkeypatch):
    worker = _worker(tmp_path)
    temp = str(tmp_path / "out.mp4")
    calls: list[tuple[str, bool | None]] = []
    seen: list[tuple[str, str]] = []
    worker.fallbackUsed.connect(lambda encoder, reason: seen.append((encoder, reason)))
    monkeypatch.setattr(
        "hlsdl.compress.build_args", _fake_build_args(calls)
    )

    def fake_run(cmd, duration):
        if len(calls) == 1:
            return 1, "Current resolution is unsupported"
        Path(temp).write_bytes(b"encoded")
        return 0, ""

    monkeypatch.setattr(worker, "_run_ffmpeg", fake_run)
    encoder, rc, _detail = worker._encode_with_fallback(_probe(), temp, 10.0)

    assert encoder == "hevc_qsv" and rc == 0
    assert calls == [("hevc_qsv", None), ("hevc_qsv", False)]
    assert seen == [("hevc_qsv", "low_power")]


def test_non_init_failure_does_not_retry(tmp_path, monkeypatch):
    worker = _worker(tmp_path)
    calls: list[tuple[str, bool | None]] = []
    monkeypatch.setattr(
        "hlsdl.compress.build_args", _fake_build_args(calls)
    )
    monkeypatch.setattr(
        worker,
        "_run_ffmpeg",
        lambda cmd, duration: (1, "Invalid data found when processing input"),
    )

    encoder, rc, detail = worker._encode_with_fallback(
        _probe(), str(tmp_path / "out.mp4"), 10.0
    )

    assert encoder == "" and rc == 1 and "Invalid data" in detail
    assert calls == [("hevc_qsv", None)]


def test_cancel_stops_attempts(tmp_path, monkeypatch):
    worker = _worker(tmp_path)
    calls: list[tuple[str, bool | None]] = []
    monkeypatch.setattr(
        "hlsdl.compress.build_args", _fake_build_args(calls)
    )

    def fake_run(cmd, duration):
        worker._cancel = True
        return 1, "Error while opening encoder"

    monkeypatch.setattr(worker, "_run_ffmpeg", fake_run)
    encoder, _rc, _detail = worker._encode_with_fallback(
        _probe(), str(tmp_path / "out.mp4"), 10.0
    )

    assert encoder == ""
    assert calls == [("hevc_qsv", None)]


def test_command_for_log_redacts_src_out_and_url_secrets(tmp_path):
    worker = _worker(tmp_path)
    src = str(tmp_path / "in.mp4")
    temp = str(tmp_path / "out.mp4")
    cmd = [
        "ffmpeg", "-i", src,
        "-metadata", "comment=https://site/video?token=CANARY",
        temp,
    ]
    text = worker._command_for_log(cmd, src, temp)
    assert "<src>" in text and "<out>" in text
    assert src not in text and temp not in text
    assert "CANARY" not in text


def test_probe_summary_includes_resolution_codec_and_audio(tmp_path):
    summary = _worker(tmp_path)._probe_summary(_probe())
    assert "1920x1080" in summary
    assert "h264/yuv420p" in summary
    assert "audio=0" in summary
