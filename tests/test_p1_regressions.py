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


def test_ffmpeg_fallback_audio_respects_mode_and_headers(
    monkeypatch, tmp_path
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
    captured = {}

    def fake_run(cmd, duration=None, is_ffmpeg=False):
        captured["cmd"] = list(cmd)
        return _fake_ffmpeg_process(cmd, duration, is_ffmpeg)

    monkeypatch.setattr(worker, "_run_process", fake_run)
    ok, path = worker._run_ffmpeg("https://cdn/site/master.m3u8")
    assert ok and path.endswith(".mp3") and os.path.exists(path)
    cmd = captured["cmd"]
    assert "-vn" in cmd and "libmp3lame" in cmd
    assert "-referer" in cmd and "https://site/page" in cmd
    assert "-i" in cmd


def test_ffmpeg_fallback_video_only_removes_audio(
    monkeypatch, tmp_path
):
    worker = DownloadWorker(
        "https://site/page", str(tmp_path),
        format_mode="video_only", container="mkv",
    )
    monkeypatch.setattr("hlsdl.downloader.which", lambda name: "/usr/bin/ffmpeg")
    monkeypatch.setattr("hlsdl.downloader.probe_duration", lambda url: 10.0)
    captured = {}

    def fake_run(cmd, duration=None, is_ffmpeg=False):
        captured["cmd"] = list(cmd)
        return _fake_ffmpeg_process(cmd, duration, is_ffmpeg)

    monkeypatch.setattr(worker, "_run_process", fake_run)
    ok, path = worker._run_ffmpeg("https://cdn/site/master.m3u8")
    assert ok and path.endswith(".mkv")
    assert "-an" in captured["cmd"]


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
