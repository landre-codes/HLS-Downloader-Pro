"""Regressões dos P1/P2: estatísticas, fallback ffmpeg, GPU/ffprobe e playlist."""

from __future__ import annotations

import json
import os
import subprocess

from hlsdl import deps
from hlsdl.bridge import Bridge
from hlsdl.downloader import DownloadWorker
from hlsdl.model import DownloadModel
from hlsdl.playlist import PlaylistLoader
from hlsdl.queue import QueueManager
from hlsdl.status import Status


def test_stats_include_cancelled(qapp):
    model = DownloadModel([])
    manager = QueueManager(model, outdir="out")
    manager.addText("https://x/1")
    manager.items[0]["status"] = Status.CANCELLED
    received: list[tuple] = []
    manager.statsChanged.connect(lambda *args: received.append(args))
    manager._emit_stats()
    assert received
    assert received[-1][4] == 1  # cancelados
    assert received[-1][2] == 0  # concluídos


def _fake_ffmpeg_process(cmd, duration=None, is_ffmpeg=False):
    with open(cmd[-1], "wb") as handle:
        handle.write(b"out")
    return True, cmd[-1]


def _valid_probe() -> dict:
    return {
        "streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 320,
             "height": 240, "pix_fmt": "yuv420p", "duration": "10"},
            {"codec_type": "audio", "codec_name": "aac", "channels": 2,
             "duration": "10"},
        ],
        "format": {"duration": "10"},
    }


def test_ytdlp_never_retries_with_allow_unsafe_ext(monkeypatch, tmp_path):
    worker = DownloadWorker("https://site/file.php", str(tmp_path))
    monkeypatch.setattr(worker, "_ytdlp_argv", lambda: ["yt-dlp"])
    calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return False, "Unsupported URL: unusual file extension"

    monkeypatch.setattr(worker, "_run_process", fake_run)
    ok, message = worker._run_ytdlp("https://site/file.php")
    assert ok is False
    assert "unusual" in message
    assert len(calls) == 1
    assert all("allow-unsafe-ext" not in cmd for cmd in calls)


def test_allow_unsafe_ext_validation_rejects_disguised_content(monkeypatch, tmp_path):
    worker = DownloadWorker("https://site/page", str(tmp_path))
    html = tmp_path / "fake.mp4"
    html.write_bytes(b"<html><body>login</body></html>")
    assert worker._looks_like_non_video(str(html)) is True

    playlist = tmp_path / "playlist.mp4"
    playlist.write_bytes(b"#EXTM3U\n#EXT-X-VERSION:3\n")
    assert worker._looks_like_non_video(str(playlist)) is True

    unknown = tmp_path / "binary.mp4"
    unknown.write_bytes(b"MZ\x90\x00fake executable")
    monkeypatch.setattr("hlsdl.downloader.probe_media", lambda path: None)
    assert worker._looks_like_non_video(str(unknown)) is True

    video = tmp_path / "video.mp4"
    video.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"\x00" * 32)
    monkeypatch.setattr("hlsdl.downloader.probe_media", lambda path: _valid_probe())
    assert worker._looks_like_non_video(str(video)) is False


def test_ffmpeg_fallback_audio_respects_mode_and_headers(    monkeypatch, tmp_path
):
    worker = DownloadWorker(
        "https://site/page", str(tmp_path),
        format_mode="audio_only", container="mp3",
    )
    monkeypatch.setattr(
        "hlsdl.downloader.which",
        lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None,
    )
    monkeypatch.setattr("hlsdl.downloader.probe_duration", lambda url: 10.0)
    monkeypatch.setattr("hlsdl.downloader.probe_media", lambda path: _valid_probe())
    captured = {}

    def fake_run(cmd, duration=None, is_ffmpeg=False):
        captured["cmd"] = list(cmd)
        return _fake_ffmpeg_process(cmd, duration, is_ffmpeg)

    monkeypatch.setattr(worker, "_run_process", fake_run)
    ok, path = worker._run_ffmpeg("https://cdn/site/master.m3u8")
    assert ok and path.endswith(".mp3") and os.path.exists(path)
    cmd = captured["cmd"]
    assert "-vn" in cmd and "libmp3lame" in cmd
    # A página de origem (site) e o CDN (cdn.site) são origens diferentes:
    # a política não encaminha Referer entre origens.
    assert "-referer" not in cmd
    assert "https://site/page" not in cmd
    assert "-i" in cmd
    # -loglevel info is what keeps the stall watchdog fed with time= lines.
    assert "-loglevel" in cmd and "info" in cmd


def test_ffmpeg_same_origin_referer_is_sanitized(monkeypatch, tmp_path):
    worker = DownloadWorker(
        "https://cdn/site/page?token=CANARY_SECRET#frag", str(tmp_path),
        format_mode="audio_only", container="mp3",
    )
    monkeypatch.setattr("hlsdl.downloader.which", lambda name: "/usr/bin/ffmpeg")
    monkeypatch.setattr("hlsdl.downloader.probe_duration", lambda url: 10.0)
    monkeypatch.setattr("hlsdl.downloader.probe_media", lambda path: _valid_probe())
    captured = {}

    def fake_run(cmd, duration=None, is_ffmpeg=False):
        captured["cmd"] = list(cmd)
        return _fake_ffmpeg_process(cmd, duration, is_ffmpeg)

    monkeypatch.setattr(worker, "_run_process", fake_run)
    ok, _path = worker._run_ffmpeg("https://cdn/site/master.m3u8")
    assert ok
    cmd = captured["cmd"]
    assert "-referer" in cmd
    assert cmd[cmd.index("-referer") + 1] == "https://cdn/site/page"
    assert "CANARY_SECRET" not in " ".join(cmd)


def test_ffmpeg_fallback_video_only_removes_audio(    monkeypatch, tmp_path
):
    worker = DownloadWorker(
        "https://site/page", str(tmp_path),
        format_mode="video_only", container="mkv",
    )
    monkeypatch.setattr("hlsdl.downloader.which", lambda name: "/usr/bin/ffmpeg")
    monkeypatch.setattr("hlsdl.downloader.probe_duration", lambda url: 10.0)
    monkeypatch.setattr("hlsdl.downloader.probe_media", lambda path: _valid_probe())
    captured = {}

    def fake_run(cmd, duration=None, is_ffmpeg=False):
        captured["cmd"] = list(cmd)
        return _fake_ffmpeg_process(cmd, duration, is_ffmpeg)

    monkeypatch.setattr(worker, "_run_process", fake_run)
    ok, path = worker._run_ffmpeg("https://cdn/site/master.m3u8")
    assert ok and path.endswith(".mkv")
    assert "-an" in captured["cmd"]


def test_ffmpeg_fallback_avi_uses_mp3_audio(monkeypatch, tmp_path):
    worker = DownloadWorker(
        "https://site/page", str(tmp_path),
        format_mode="video_audio", container="avi",
    )
    monkeypatch.setattr("hlsdl.downloader.which", lambda name: "/usr/bin/ffmpeg")
    monkeypatch.setattr("hlsdl.downloader.probe_duration", lambda url: 10.0)
    monkeypatch.setattr("hlsdl.downloader.probe_media", lambda path: _valid_probe())
    captured = {}

    def fake_run(cmd, duration=None, is_ffmpeg=False):
        captured["cmd"] = list(cmd)
        if "libmp3lame" not in cmd:
            return False, "copy failed"
        return _fake_ffmpeg_process(cmd, duration, is_ffmpeg)

    monkeypatch.setattr(worker, "_run_process", fake_run)
    ok, path = worker._run_ffmpeg("https://cdn/site/master.m3u8")
    assert ok and path.endswith(".avi")
    assert "libmp3lame" in captured["cmd"]
    assert "aac" not in captured["cmd"]


def test_ffmpeg_detect_requires_ffprobe(monkeypatch):
    monkeypatch.setattr(
        deps.config,
        "find_binary",
        lambda name: "C:/tools/ffmpeg.exe" if name == "ffmpeg" else None,
    )
    manager = deps.DependencyManager()
    spec = next(s for s in deps.SPECS if s.key == "ffmpeg")
    status = manager.detect(spec)
    assert status.found is False


def test_compression_effective_encoder(qapp, tmp_path, fake_deps):
    bridge = Bridge(
        QueueManager(DownloadModel([]), outdir="out"),
        "out",
        settings_path=str(tmp_path / "s.ini"),
        deps=fake_deps,
    )
    bridge.compression.available = {"hevc_qsv", "libx265"}
    bridge.setCompressionEncoder("auto")
    assert bridge.compressionEffectiveEncoder == "hevc_qsv"
    bridge.setCompressionEncoder("software")
    assert bridge.compressionEffectiveEncoder == "libx265"


class _FakeProc:
    def __init__(self, stdout: str, stderr: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.pid = 4242

    def communicate(self, timeout=None):
        return self.stdout, self.stderr

    def poll(self):
        return self.returncode


def test_playlist_skips_non_youtube_id_without_url(qapp, monkeypatch):
    loader = PlaylistLoader()
    payload = json.dumps({"entries": [
        {"id": "vimeo-id", "title": "Vimeo", "url": "vimeo-id", "ie_key": "Vimeo"},
        {"id": "yt-id", "title": "YouTube", "url": "yt-id", "ie_key": "Youtube"},
    ]})
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: _FakeProc(payload))
    loader._ytdlp_argv = lambda: ["yt-dlp"]
    got: list = []
    loader.loaded.connect(got.append)
    loader._run(["yt-dlp"], "https://site/list", 10, "")
    assert got and len(got[0]) == 1
    assert got[0][0]["url"] == "https://www.youtube.com/watch?v=yt-id"
