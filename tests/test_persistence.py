"""Persistent queue snapshot tests."""

from __future__ import annotations

import json

from hlsdl import persistence
from hlsdl.bridge import Bridge
from hlsdl.model import DownloadModel
from hlsdl.queue import QueueManager


def test_persistence_roundtrip(tmp_path):
    path = tmp_path / "queue.json"
    persistence.save(
        str(path),
        [
            {"url": "https://a/1", "title": "A", "status": "waiting"},
            {"url": "https://b/2", "title": "B", "status": "done"},
        ],
        [{"input": str(tmp_path / "v.mp4")}],
    )
    data = persistence.load(str(path))
    assert [item["url"] for item in data["downloads"]] == ["https://a/1", "https://b/2"]
    assert data["compression"][0]["input"].endswith("v.mp4")


def test_invalid_persistence_file_is_ignored(tmp_path):
    path = tmp_path / "queue.json"
    path.write_text("{not json", encoding="utf-8")
    assert persistence.load(str(path)) == {"downloads": [], "compression": []}


def test_bridge_restores_non_done_items(qapp, tmp_path, fake_deps):
    state = tmp_path / "queue.json"
    state.write_text(
        json.dumps({
            "version": 1,
            "downloads": [
                {"url": "https://a/1", "title": "A", "status": "waiting"},
                {"url": "https://b/2", "title": "B", "status": "done"},
            ],
            "compression": [],
        }),
        encoding="utf-8",
    )
    bridge = Bridge(
        QueueManager(DownloadModel([]), outdir=str(tmp_path)),
        str(tmp_path),
        settings_path=str(tmp_path / "s.ini"),
        state_path=str(state),
        deps=fake_deps,
        defer_detection=True,
    )
    assert [item["url"] for item in bridge.manager.items] == ["https://a/1"]
    assert bridge.manager.items[0]["status"].value == "waiting"
