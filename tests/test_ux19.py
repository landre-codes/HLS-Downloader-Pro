"""Regressões de UX/robustez da reauditoria R3 (pastas e feedback)."""

from __future__ import annotations

import threading
import time

from hlsdl.bridge import Bridge
from hlsdl.i18n import tr
from hlsdl.model import DownloadModel
from hlsdl.queue import QueueManager


def _bridge(tmp_path, fake_deps) -> Bridge:
    bridge = Bridge(
        QueueManager(DownloadModel([]), outdir="out"),
        "out",
        settings_path=str(tmp_path / "s.ini"),
        state_path=str(tmp_path / "queue.json"),
        deps=fake_deps,
        defer_detection=True,
    )
    bridge.setLanguage("pt")
    return bridge


def test_open_output_folder_delegates_to_directory_helper(qapp, tmp_path, fake_deps):
    bridge = _bridge(tmp_path, fake_deps)
    seen: list[str] = []
    bridge._open_directory = lambda folder: seen.append(folder) or True  # type: ignore[method-assign]
    bridge.openOutputFolder()
    assert seen == [bridge.outputFolder]
    bridge.shutdown()


def test_missing_directory_emits_actionable_message(qapp, tmp_path, fake_deps):
    bridge = _bridge(tmp_path, fake_deps)
    messages: list[str] = []
    bridge.notifyText.connect(messages.append)
    assert bridge._open_directory(str(tmp_path / "missing")) is False
    assert messages and messages[-1] == tr("pt", "folder_missing")
    bridge.shutdown()


def test_output_folder_rejects_unwritable_directory(qapp, tmp_path, fake_deps, monkeypatch):
    bridge = _bridge(tmp_path, fake_deps)
    target = tmp_path / "target"
    target.mkdir()
    before = bridge.outputFolder
    messages: list[str] = []
    bridge.notifyText.connect(messages.append)
    monkeypatch.setattr(
        "hlsdl.bridge_parts.settings.QFileDialog.getExistingDirectory",
        lambda *args, **kwargs: str(target),
    )
    monkeypatch.setattr("hlsdl.bridge_parts.settings.os.access", lambda *args: False)
    bridge.chooseOutputFolder()
    assert bridge.outputFolder == before
    assert messages and messages[-1] == tr("pt", "output_folder_readonly")
    bridge.shutdown()


def _wait_until(qapp, predicate, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        qapp.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_empty_compression_folder_emits_feedback(qapp, tmp_path, fake_deps, monkeypatch):
    bridge = _bridge(tmp_path, fake_deps)
    empty = tmp_path / "empty"
    empty.mkdir()
    messages: list[str] = []
    bridge.notifyText.connect(messages.append)
    monkeypatch.setattr(
        "hlsdl.bridge_parts.compression.QFileDialog.getExistingDirectory",
        lambda *args, **kwargs: str(empty),
    )
    bridge.addCompressionFolder()
    assert bridge.compressionScanBusy is True
    assert _wait_until(qapp, lambda: bool(messages))
    assert messages and messages[-1] == tr("pt", "compress_folder_empty")
    assert bridge.compressionScanBusy is False
    bridge.shutdown()


def test_compression_scan_can_be_cancelled(qapp, tmp_path, fake_deps, monkeypatch):
    bridge = _bridge(tmp_path, fake_deps)
    started = threading.Event()
    release = threading.Event()

    def fake_scan(paths, recursive=True, cancel=None):
        started.set()
        while not cancel.is_set() and not release.is_set():
            time.sleep(0.01)
        return {
            "files": [], "scanned": 0, "ignored": 0, "duplicates": 0,
            "errors": 0, "cancelled": cancel.is_set(),
        }

    monkeypatch.setattr(
        "hlsdl.bridge_parts.compression.scan_media_paths", fake_scan
    )
    monkeypatch.setattr(
        "hlsdl.bridge_parts.compression.QFileDialog.getExistingDirectory",
        lambda *args, **kwargs: str(tmp_path),
    )
    messages: list[str] = []
    bridge.notifyText.connect(messages.append)
    bridge.addCompressionFolder()
    assert started.wait(2.0)
    assert _wait_until(qapp, lambda: bridge.compressionScanBusy)
    bridge.cancelCompressionScan()
    assert _wait_until(qapp, lambda: not bridge.compressionScanBusy)
    assert messages and messages[-1] == tr("pt", "compress_scan_cancelled")
    release.set()
    bridge.shutdown()


def test_compression_folder_scan_reports_counts(qapp, tmp_path, fake_deps, monkeypatch):
    bridge = _bridge(tmp_path, fake_deps)
    folder = tmp_path / "videos"
    folder.mkdir()
    (folder / "a.mp4").write_bytes(b"a")
    (folder / "b.txt").write_bytes(b"b")
    messages: list[str] = []
    bridge.notifyText.connect(messages.append)
    monkeypatch.setattr(
        "hlsdl.bridge_parts.compression.QFileDialog.getExistingDirectory",
        lambda *args, **kwargs: str(folder),
    )
    bridge.addCompressionFolder()
    assert _wait_until(qapp, lambda: bool(messages))
    assert "1" in messages[-1] and "adicionados" in messages[-1]
    assert "1" in messages[-1] and "ignorados" in messages[-1]
    assert bridge.compression.items[0]["name"] == "a.mp4"
    bridge.shutdown()
