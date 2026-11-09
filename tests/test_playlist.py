"""Testes do carregador de playlists (parsing, sem rede)."""

from __future__ import annotations

import json
import subprocess

from hlsdl.playlist import PlaylistLoader


def test_to_item_youtube_id_becomes_watch_url():
    item = PlaylistLoader._to_item({"id": "abc123", "title": "Video", "url": "abc123"}, 0)
    assert item["url"] == "https://www.youtube.com/watch?v=abc123"
    assert item["title"] == "Video"
    assert item["index"] == 1


def test_to_item_non_youtube_id_is_not_forced_to_youtube():
    item = PlaylistLoader._to_item(
        {"id": "abc", "title": "V", "url": "abc", "ie_key": "Vimeo"}, 0
    )
    assert item["url"] == ""


def test_to_item_full_url_and_thumb():
    entry = {
        "id": "x", "title": "T", "webpage_url": "https://site/v/1",
        "thumbnails": [{"url": "https://img/small.jpg"}, {"url": "https://img/big.jpg"}],
        "duration": 120,
    }
    item = PlaylistLoader._to_item(entry, 4)
    assert item["url"] == "https://site/v/1"
    assert item["thumb"] == "https://img/big.jpg"
    assert item["duration"] == 120
    assert item["index"] == 5


class _FakeProc:
    def __init__(self, stdout: str = "", returncode: int = 0, stderr: str = ""):
        self._out = stdout
        self._err = stderr
        self.returncode = returncode
        self.pid = 4242

    def communicate(self, timeout=None):
        return self._out, self._err

    def poll(self):
        return self.returncode


def test_loader_parses_entries(qapp, monkeypatch):
    payload = json.dumps({"entries": [
        {"id": "a", "title": "A", "url": "a"},
        {"id": "b", "title": "B", "url": "b"},
        None,  # entrada vazia deve ser ignorada
    ]})
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: _FakeProc(payload))
    loader = PlaylistLoader()
    loader._ytdlp_argv = lambda: ["yt-dlp"]
    got: list = []
    loader.loaded.connect(got.append)

    loader._run(["yt-dlp"], "https://site/playlist", 10, "")

    assert got and len(got[0]) == 2
    assert [i["title"] for i in got[0]] == ["A", "B"]


def test_loader_reports_failure_on_error(qapp, monkeypatch):
    monkeypatch.setattr(
        subprocess, "Popen", lambda *a, **k: _FakeProc("", 1, "ERROR: nope")
    )
    loader = PlaylistLoader()
    loader._ytdlp_argv = lambda: ["yt-dlp"]
    errors: list = []
    loader.failed.connect(errors.append)

    loader._run(["yt-dlp"], "https://site/bad", 10, "")

    assert errors and "nope" in errors[0]
