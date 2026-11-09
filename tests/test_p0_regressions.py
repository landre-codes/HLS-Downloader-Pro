"""Regressões dos P0 da auditoria: threading, shutdown, settings e mídia."""

from __future__ import annotations

import os
import subprocess
import sys

from PySide6.QtCore import QThread

from hlsdl import deps
from hlsdl.bridge import Bridge
from hlsdl.compress import (
    CompressionManager,
    CompressionModel,
    CompressionSettings,
    CompressionWorker,
)
from hlsdl.downloader import DownloadWorker
from hlsdl.model import DownloadModel
from hlsdl.queue import QueueManager
from tests.conftest import process_until


class _ProgressWorker(DownloadWorker):
    def run(self) -> None:  # type: ignore[override]
        self.progressChanged.emit(42.0, "1MiB/s", "2MiB")
        self._succeed("/caminho/inexistente/fake.mp4")


def test_queue_callbacks_run_on_gui_thread(qapp):
    main_thread = QThread.currentThread()
    seen: list[tuple[str, bool]] = []
    model = DownloadModel([])
    manager = QueueManager(
        model, outdir="out", concurrency=1, worker_factory=_ProgressWorker
    )
    original = manager._on_progress

    def patched(item, pct, speed, size):
        seen.append(("progress", QThread.currentThread() is main_thread))
        return original(item, pct, speed, size)

    manager._on_progress = patched  # type: ignore[method-assign]
    manager.addText("https://x/1")
    manager.start()
    assert process_until(qapp, lambda: bool(seen), timeout=10)
    assert seen[0][1] is True, "callback de progresso saiu da thread da GUI"
    manager.shutdown(timeout=3)


class _CompressionProgressWorker(CompressionWorker):
    def run(self) -> None:  # type: ignore[override]
        self.progressChanged.emit(37.0, "1.2x")
        self.finished.emit()


def test_compression_callbacks_run_on_gui_thread(qapp, tmp_path):
    main_thread = QThread.currentThread()
    seen: list[tuple[str, bool]] = []
    src = tmp_path / "entrada.mp4"
    src.write_bytes(b"x")
    model = CompressionModel([])
    manager = CompressionManager(model, worker_factory=_CompressionProgressWorker)
    manager.available = {"libx265"}
    manager.settings = CompressionSettings(encoder="software", codec="hevc")
    original = manager._on_progress

    def patched(item, pct, speed):
        seen.append(("progress", QThread.currentThread() is main_thread))
        return original(item, pct, speed)

    manager._on_progress = patched  # type: ignore[method-assign]
    manager.add_paths([str(src)])
    manager.start()
    assert process_until(qapp, lambda: bool(seen), timeout=10)
    assert seen[0][1] is True, "callback de compressão saiu da thread da GUI"
    manager.shutdown(timeout=3)


def test_shutdown_with_stuck_worker_does_not_crash():
    """Um worker que ignora cancelamento não pode derrubar o processo."""
    script = r"""
import os, sys, time
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from hlsdl.downloader import DownloadWorker
from hlsdl.model import DownloadModel
from hlsdl.queue import QueueManager

class Slow(DownloadWorker):
    def run(self):
        time.sleep(30)

app = QApplication([])
manager = QueueManager(DownloadModel([]), outdir=os.getcwd(), concurrency=1,
                       worker_factory=Slow)
manager.addText("https://x/1")
manager.start()
time.sleep(0.3)
manager.shutdown(timeout=0.2)
app.quit()
print("OK", flush=True)
"""
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        timeout=40,
    )
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    assert "OK" in proc.stdout


def test_corrupt_settings_falls_back(qapp, tmp_path, fake_deps):
    settings = tmp_path / "settings.ini"
    settings.write_text(
        "[download]\n"
        "concurrency=abc\n"
        "limit_rate=xyz\n"
        "fragments=\n"
        "folder=\n"
        "[compress]\n"
        "quality=no\n"
        "parallel=??\n",
        encoding="utf-8",
    )
    default_out = tmp_path / "saida"
    bridge = Bridge(
        QueueManager(DownloadModel([]), outdir=str(default_out)),
        str(default_out),
        settings_path=str(settings),
        deps=fake_deps,
    )
    assert bridge.concurrency == 3
    assert bridge.limitRateMB == 0
    assert bridge.fragments == 1
    assert bridge.compressionQuality == 24
    assert bridge.compressionParallel == 1
    assert os.path.isabs(bridge.outputFolder)
    assert bridge.outputFolder == str(default_out.resolve())


def test_ffmpeg_install_uses_working_url_and_package_fallback(monkeypatch):
    assert deps.FFMPEG_WIN_ZIP.endswith("ffmpeg-release-essentials.zip")
    manager = deps.DependencyManager()
    monkeypatch.setattr(manager, "_install_ffmpeg_download", lambda: False)
    monkeypatch.setattr(deps, "_ffmpeg_package_command", lambda: ["pkg-install"])
    called = []
    monkeypatch.setattr(manager, "_run_install", lambda cmd: called.append(cmd) or True)
    assert manager._install_ffmpeg() is True
    assert called == [["pkg-install"]]


def test_mac_ffmpeg_url_comes_from_info_api(monkeypatch):
    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return (
                b'{"download": {"zip": {"url": '
                b'"https://evermeet.cx/ffmpeg/ffmpeg-9.0.2.zip"}}}'
            )

    monkeypatch.setattr(deps.urllib.request, "urlopen", lambda *a, **k: _Resp())
    assert deps.DependencyManager._mac_ffmpeg_url("ffmpeg") == (
        "https://evermeet.cx/ffmpeg/ffmpeg-9.0.2.zip"
    )


class _TitleProc:
    stdout = [
        "__HSLDL_TITLE__Meu vídeo (4K)\n",
        "[download] Destination: /tmp/vid_hash.mp4\n",
        "[download]  12.3% of 10.00MiB at 1.00MiB/s ETA 00:01\n",
        "/tmp/vid_hash.mp4\n",
    ]


def test_metadata_title_is_not_overwritten_by_filename():
    worker = DownloadWorker("https://x/v", "out")
    titles: list[str] = []
    worker.titleChanged.connect(titles.append)
    result = worker._consume_ytdlp_stdout(_TitleProc())
    assert result == "/tmp/vid_hash.mp4"
    assert titles == ["Meu vídeo (4K)"]
