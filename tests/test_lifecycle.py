"""Testes do helper comum de encerramento de QThreads."""

from __future__ import annotations

from hlsdl import lifecycle


class _FakeThread:
    def __init__(self, finish_on_quit: bool = True, finish_on_terminate: bool = True):
        self.finish_on_quit = finish_on_quit
        self.finish_on_terminate = finish_on_terminate
        self.finished = False
        self.terminated = False
        self.waits: list[int] = []

    def quit(self) -> None:
        pass

    def wait(self, milliseconds: int) -> bool:
        self.waits.append(milliseconds)
        if self.finished:
            return True
        if not self.terminated and self.finish_on_quit and milliseconds > 0:
            self.finished = True
            return True
        if self.terminated and self.finish_on_terminate:
            self.finished = True
            return True
        return False

    def terminate(self) -> None:
        self.terminated = True

    def isFinished(self) -> bool:  # noqa: N802 (API do Qt)
        return self.finished

    def objectName(self) -> str:  # noqa: N802 (API do Qt)
        return "fake-thread"


class _FakeWorker:
    def __init__(self) -> None:
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


def test_shutdown_waits_and_removes_finished_threads():
    thread = _FakeThread()
    worker = _FakeWorker()
    threads = {1: (thread, worker, {"id": 1})}
    cancelled: list[bool] = []

    remaining = lifecycle.shutdown_threads(
        threads,
        timeout=0.5,
        label="teste",
        cancel=lambda: cancelled.append(True),
    )
    assert remaining == {}
    assert cancelled == [True]
    assert thread.terminated is False
    assert worker.cancelled is False


def test_shutdown_terminates_stubborn_thread_and_keeps_reference(monkeypatch):
    thread = _FakeThread(finish_on_quit=False, finish_on_terminate=False)
    worker = _FakeWorker()
    threads = {1: (thread, worker, {"id": 1})}
    stuck: list = []
    monkeypatch.setattr(lifecycle, "note_stuck_qthread", stuck.append)

    remaining = lifecycle.shutdown_threads(threads, timeout=0.01, label="teste")
    assert thread.terminated is True
    assert worker.cancelled is True
    assert stuck == [thread]
    assert remaining == {1: (thread, worker, {"id": 1})}
