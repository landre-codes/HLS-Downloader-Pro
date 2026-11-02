"""Ciclo de vida completo da fila com um worker falso (sem rede)."""

from __future__ import annotations

from hlsdl.downloader import DownloadWorker
from hlsdl.model import DownloadModel
from hlsdl.queue import QueueManager
from hlsdl.status import Status
from tests.conftest import process_until


class FakeWorker(DownloadWorker):
    """Simula um download concluído instantaneamente."""

    def run(self) -> None:  # type: ignore[override]
        self.statusChanged.emit(Status.DOWNLOADING.value)
        self.progressChanged.emit(42.0, "1MiB/s", "2MiB")
        self._succeed("/caminho/inexistente/fake.mp4")


def test_full_queue_finishes(qapp):
    model = DownloadModel([])
    manager = QueueManager(model, outdir="out", concurrency=2, worker_factory=FakeWorker)
    manager.addText("https://a.com/1\nhttps://b.com/2\nhttps://c.com/3")
    assert model.rowCount() == 3

    manager.start()
    finished = process_until(
        qapp, lambda: all(i["status"] in Status and i["status"].is_final for i in manager.items),
        timeout=15,
    )
    assert finished
    assert all(i["status"] == Status.DONE for i in manager.items)
    # O modelo e o gerente devem concordar ao final.
    assert model.rowCount() == len(manager.items) == 3
    for row, item in enumerate(manager.items):
        assert model.data(model.index(row, 0), DownloadModel.URL) == item["url"]
        assert model.data(model.index(row, 0), DownloadModel.STATUS) == "done"


def test_stats_signal(qapp):
    model = DownloadModel([])
    manager = QueueManager(model, outdir="out", concurrency=1, worker_factory=FakeWorker)
    received = []
    manager.statsChanged.connect(lambda *a: received.append(a))
    manager.addText("https://a.com/1")
    manager.start()
    process_until(qapp, lambda: all(i["status"].is_final for i in manager.items), timeout=15)
    assert received  # houve atualizações de estatística
    assert received[-1][2] == 1  # 1 concluído


def test_shutdown_cancels_and_joins(qapp):
    model = DownloadModel([])
    manager = QueueManager(model, outdir="out", concurrency=1, worker_factory=FakeWorker)
    manager.addText("https://a.com/1")
    manager.start()
    process_until(qapp, lambda: all(i["status"].is_final for i in manager.items), timeout=15)
    manager.shutdown(timeout=3)
    assert manager._running == 0
