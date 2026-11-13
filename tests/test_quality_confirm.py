"""Confirmação de queda extrema de bitrate antes de instalar a saída."""

from __future__ import annotations

import threading

from PySide6.QtCore import Qt

from hlsdl.bridge import Bridge
from hlsdl.cli import build_parser
from hlsdl.compress import (
    CompressionManager,
    CompressionModel,
    CompressionSettings,
    CompressionWorker,
    CompressStatus,
)
from hlsdl.model import DownloadModel
from hlsdl.queue import QueueManager
from tests.conftest import process_until


def _report() -> dict:
    return {
        "bitrate_before": 15_000_000,
        "bitrate_after": 450_000,
        "width_before": 1920,
        "height_before": 1080,
        "width_after": 1920,
        "height_after": 1080,
        "ssim": 0.93,
        "quality_warning": "bitrate_drop",
    }


class _FakeWorker:
    def __init__(self) -> None:
        self.decisions: list[bool] = []
        self.cancelled = False

    def respond_quality(self, allow: bool) -> None:
        self.decisions.append(allow)

    def cancel(self) -> None:
        self.cancelled = True


def _manager(tmp_path) -> CompressionManager:
    manager = CompressionManager(CompressionModel([]), defer_detection=True)
    for index in range(2):
        path = tmp_path / f"video{index}.mp4"
        path.write_bytes(b"x")
        manager.add_paths([str(path)])
    return manager


def test_worker_accepts_extreme_drop_when_user_confirms(qapp):
    worker = CompressionWorker(
        "video.mp4", CompressionSettings(), "libx265", quality_timeout=2.0,
    )
    seen: list[dict] = []
    worker.qualityConfirmation.connect(
        lambda report: (seen.append(report), worker.respond_quality(True))
    )
    assert worker._quality_drop_allowed(_report()) is True
    assert seen and seen[0]["name"] == "video.mp4"
    assert seen[0]["bitrate_after"] == 450_000


def test_worker_rejects_extreme_drop_when_user_discards(qapp):
    worker = CompressionWorker(
        "video.mp4", CompressionSettings(), "libx265", quality_timeout=2.0,
    )
    worker.qualityConfirmation.connect(lambda _report: worker.respond_quality(False))
    assert worker._quality_drop_allowed(_report()) is False


def test_worker_rejects_on_confirmation_timeout(qapp):
    worker = CompressionWorker(
        "video.mp4", CompressionSettings(), "libx265", quality_timeout=0.05,
    )
    assert worker._quality_drop_allowed(_report()) is False


def test_worker_cancel_releases_confirmation_wait(qapp):
    worker = CompressionWorker(
        "video.mp4", CompressionSettings(), "libx265", quality_timeout=5.0,
    )
    started = threading.Event()
    worker.qualityConfirmation.connect(
        lambda _report: started.set(), Qt.DirectConnection
    )
    result: list[bool] = []
    thread = threading.Thread(
        target=lambda: result.append(worker._quality_drop_allowed(_report()))
    )
    thread.start()
    assert started.wait(1.0)
    worker.cancel()
    thread.join(2.0)
    assert not thread.is_alive()
    assert result == [False]


def test_headless_default_is_safe_without_prompt(qapp):
    worker = CompressionWorker(
        "video.mp4", CompressionSettings(confirm_quality_drop=False), "libx265",
    )
    seen: list[dict] = []
    worker.qualityConfirmation.connect(seen.append)
    assert worker._quality_drop_allowed(_report()) is False
    assert seen == []


def test_headless_allow_flag_accepts(qapp):
    worker = CompressionWorker(
        "video.mp4",
        CompressionSettings(confirm_quality_drop=False, allow_quality_drop=True),
        "libx265",
    )
    assert worker._quality_drop_allowed(_report()) is True


def test_manager_queues_and_answers_quality_prompts(qapp, tmp_path):
    manager = _manager(tmp_path)
    first, second = manager.items
    worker1, worker2 = _FakeWorker(), _FakeWorker()
    manager._threads[first["id"]] = (object(), worker1, first)
    manager._threads[second["id"]] = (object(), worker2, second)

    manager._request_quality(first, _report())
    manager._request_quality(second, _report())
    assert manager.quality_prompt["id"] == first["id"]

    manager.respond_quality(True)
    assert worker1.decisions == [True]
    assert manager.quality_prompt["id"] == second["id"]

    manager.respond_quality(False)
    assert worker2.decisions == [False]
    assert manager.quality_prompt is None


def test_manager_cancel_clears_pending_prompt(qapp, tmp_path):
    manager = _manager(tmp_path)
    first = manager.items[0]
    worker = _FakeWorker()
    manager._threads[first["id"]] = (object(), worker, first)
    manager._request_quality(first, _report())
    assert manager.quality_prompt is not None

    manager.cancelAll()
    assert manager.quality_prompt is None
    assert worker.cancelled is True


def test_bridge_exposes_quality_prompt_and_response(qapp, tmp_path, fake_deps):
    model = DownloadModel([])
    bridge = Bridge(
        QueueManager(model, outdir="out"), "out",
        settings_path=str(tmp_path / "settings.ini"), deps=fake_deps,
        defer_detection=True,
    )
    path = tmp_path / "video.mp4"
    path.write_bytes(b"x")
    bridge.compression.add_paths([str(path)])
    item = bridge.compression.items[0]
    worker = _FakeWorker()
    bridge.compression._threads[item["id"]] = (object(), worker, item)

    bridge.compression._request_quality(item, _report())
    assert bridge.compressionQualityPrompt["id"] == item["id"]
    bridge.respondCompressionQuality(False)
    assert worker.decisions == [False]
    assert bridge.compressionQualityPrompt == {}

    bridge.compression._threads.clear()
    bridge.shutdown()


def test_cli_has_explicit_allow_quality_drop_flag():
    args = build_parser().parse_args(
        ["compress", "video.mp4", "--allow-quality-drop"]
    )
    assert args.allow_quality_drop is True

class _PromptWorker(CompressionWorker):
    """Worker sem ffmpeg: emite o pedido e espera a resposta do manager."""

    def run(self) -> None:
        report = _report()
        report.update({"size_before": 1000, "size_after": 100, "saving": 90.0})
        self.qualityReport.emit(report)
        self.qualityConfirmation.emit(report)
        allowed = self._quality_event.wait(3.0) and self._quality_decision is True
        if self._cancel:
            self.cancelled.emit()
        elif allowed:
            self.completed.emit("out.mp4", "", 1000, 100, "sha", "ok")
        else:
            self.skipped.emit("rejected")
        self.finished.emit()


def test_manager_prompt_crosses_worker_thread(qapp, tmp_path):
    class Manager(CompressionManager):
        def __init__(self, model):
            super().__init__(model, worker_factory=_PromptWorker,
                             defer_detection=True)
            self.available = {"libx265"}
            self._encoders_ready = True

    path = tmp_path / "video.mp4"
    path.write_bytes(b"x")
    manager = Manager(CompressionModel([]))
    manager.settings = CompressionSettings(
        encoder="software", codec="hevc", parallel=1,
    )
    manager.add_paths([str(path)])
    assert manager.start() is True
    assert process_until(qapp, lambda: manager.quality_prompt is not None)
    assert manager.quality_prompt["name"] == "video.mp4"

    manager.respond_quality(False)
    assert process_until(
        qapp, lambda: manager.items[0]["status"] == CompressStatus.SKIPPED
    )
    assert process_until(qapp, lambda: not manager._threads)

