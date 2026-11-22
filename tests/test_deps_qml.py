"""Testes de dependências e carregamento do QML."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QMetaObject, QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression

from hlsdl.bridge import Bridge
from hlsdl.config import qml_path
from hlsdl.deps import SPECS, DependencyManager
from hlsdl.downloader import DownloadWorker
from hlsdl.model import DownloadModel
from hlsdl.queue import QueueManager
from tests.conftest import process_until


def _teardown(qapp, engine, bridge) -> None:
    """Fecha as janelas e destrói o engine antes do próximo teste QML."""
    for obj in engine.rootObjects():
        obj.close()
    for _ in range(10):
        qapp.processEvents()
    engine.deleteLater()
    qapp.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    for _ in range(10):
        qapp.processEvents()
    bridge.shutdown()


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
    _teardown(qapp, engine, bridge)


def test_settings_scrollbar_is_on_the_right(qapp, fake_deps):
    model = DownloadModel([])
    manager = QueueManager(model, outdir="out")
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

    ev("tabBar.currentIndex = 3")
    qapp.processEvents()
    x = ev("settingsScroll.ScrollBar.vertical.x")
    width = ev("settingsScroll.ScrollBar.vertical.width")
    horizontal = ev("settingsScroll.ScrollBar.horizontal.visible")
    assert x > 0, "scrollbar vertical ficou no canto esquerdo"
    assert width > 4
    assert horizontal is False
    _teardown(qapp, engine, bridge)


def test_qml_icon_paths_are_absolute(qapp, fake_deps):
    model = DownloadModel([])
    manager = QueueManager(model, outdir="out")
    bridge = Bridge(manager, "out", deps=fake_deps)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("downloadModel", model)
    engine.rootContext().setContextProperty("compressionModel", bridge.compression.model)
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.load(QUrl.fromLocalFile(qml_path()))
    root = engine.rootObjects()[0]
    ctx = engine.contextForObject(root)
    value = QQmlExpression(ctx, root, "root.iconPath('play')").evaluate()[0]
    url = value if isinstance(value, QUrl) else QUrl(str(value))
    assert url.isLocalFile(), value
    assert Path(url.toLocalFile()).is_file(), value
    _teardown(qapp, engine, bridge)


def test_qml_controls_usam_estilo_material():
    ui = Path(qml_path()).parent
    missing = []
    for path in sorted(ui.rglob("*.qml")):
        text = path.read_text(encoding="utf-8")
        if "import QtQuick.Controls\n" in text and "import QtQuick.Controls.Material\n" not in text:
            missing.append(str(path.relative_to(ui)))
    assert not missing, f"QML sem import Material: {missing}"


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
    _teardown(qapp, engine, bridge)


def test_qml_quality_prompt_opens_and_closing_rejects(qapp, fake_deps, tmp_path):
    class FakeQualityWorker:
        def __init__(self) -> None:
            self.decisions: list[bool] = []

        def respond_quality(self, allow: bool) -> None:
            self.decisions.append(allow)

        def cancel(self) -> None:
            pass

    model = DownloadModel([])
    manager = QueueManager(model, outdir="out")
    bridge = Bridge(
        manager, "out", settings_path=str(tmp_path / "settings.ini"),
        deps=fake_deps, defer_detection=True,
    )
    path = tmp_path / "video.mp4"
    path.write_bytes(b"x")
    bridge.compression.add_paths([str(path)])
    item = bridge.compression.items[0]
    worker = FakeQualityWorker()
    bridge.compression._threads[item["id"]] = (object(), worker, item)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("downloadModel", model)
    engine.rootContext().setContextProperty(
        "compressionModel", bridge.compression.model
    )
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.load(QUrl.fromLocalFile(qml_path()))
    root = engine.rootObjects()[0]
    root.show()
    dialog = next(
        (obj for obj in root.findChildren(QObject)
         if obj.objectName() == "qualityConfirmDialog"),
        None,
    )
    assert dialog is not None

    report = {
        "bitrate_before": 15_000_000,
        "bitrate_after": 450_000,
        "width_before": 1920,
        "height_before": 1080,
        "width_after": 1920,
        "height_after": 1080,
        "ssim": 0.93,
        "quality_warning": "bitrate_drop",
    }
    bridge.compression._request_quality(item, report)
    assert process_until(qapp, lambda: dialog.property("opened") is True)
    assert dialog.property("prompt")["id"] == item["id"]

    assert QMetaObject.invokeMethod(dialog, "close") is True
    assert process_until(qapp, lambda: worker.decisions == [False])
    assert dialog.property("opened") is False

    bridge.compression._request_quality(item, report)
    assert process_until(qapp, lambda: dialog.property("opened") is True)
    accept = next(
        obj for obj in root.findChildren(QObject)
        if obj.objectName() == "qualityConfirmAccept"
    )
    assert QMetaObject.invokeMethod(accept, "click") is True
    assert process_until(qapp, lambda: worker.decisions == [False, True])

    bridge.compression._threads.clear()
    _teardown(qapp, engine, bridge)
