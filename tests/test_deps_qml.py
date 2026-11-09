"""Testes de dependências e carregamento do QML."""

from __future__ import annotations

import os

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression

from hlsdl.bridge import Bridge
from hlsdl.config import qml_path
from hlsdl.deps import SPECS, DependencyManager
from hlsdl.downloader import DownloadWorker
from hlsdl.model import DownloadModel
from hlsdl.queue import QueueManager


def test_detect_returns_all_tools(qapp):
    manager = DependencyManager()
    items = manager.check_all()
    assert len(items) == len(SPECS)
    keys = {d["key"] for d in items}
    assert keys == {"ytdlp", "ffmpeg", "requests", "bs4", "pyside6"}
    assert all("found" in d and "installable" in d for d in items)


def test_essentials_report(qapp):
    manager = DependencyManager()
    # PySide6 está importado (somos nós): deve ser detectado.
    assert manager.detect(next(s for s in SPECS if s.key == "pyside6")).found


def test_qml_loads(qapp, fake_deps):
    if not os.path.exists(qml_path()):
        pytest.skip("main.qml não encontrado")
    model = DownloadModel([])
    manager = QueueManager(model, outdir="out")
    bridge = Bridge(manager, "out", deps=fake_deps)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("downloadModel", model)
    engine.rootContext().setContextProperty("compressionModel", bridge.compression.model)
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.load(QUrl.fromLocalFile(qml_path()))
    assert engine.rootObjects(), "main.qml não carregou"


class _NoopWorker(DownloadWorker):
    def run(self) -> None:  # type: ignore[override]
        self.statusChanged.emit("analyzing")
        self.finished.emit()


def test_qml_single_download_validates_and_isolates(qapp, fake_deps):
    model = DownloadModel([])
    manager = QueueManager(model, outdir="out", worker_factory=_NoopWorker)
    manager.addText("https://lote/1")
    bridge = Bridge(manager, "out", deps=fake_deps)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("downloadModel", model)
    engine.rootContext().setContextProperty("compressionModel", bridge.compression.model)
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.load(QUrl.fromLocalFile(qml_path()))
    root = engine.rootObjects()[0]
    ctx = engine.contextForObject(root)

    def ev(expr):
        return QQmlExpression(ctx, root, expr).evaluate()[0]

    ev("singleUrl.text = 'isto-nao-e-url'")
    ev("root.startSingle()")
    assert ev("singleUrl.text") == "isto-nao-e-url"
    assert len(bridge.single_manager.items) == 0

    ev("singleUrl.text = 'https://video/1'")
    ev("root.startSingle()")
    assert ev("singleUrl.text") == ""
    assert len(bridge.single_manager.items) == 1
    assert manager.items[0]["status"].value == "waiting"
    bridge.shutdown()
