"""Regressão: filtro da fila de compressão esconde linhas sem perder o modelo."""

from __future__ import annotations

import time

from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression

from hlsdl.bridge import Bridge
from hlsdl.config import qml_path
from hlsdl.model import DownloadModel
from hlsdl.queue import QueueManager


def _pump(qapp, rounds: int = 40) -> None:
    for _ in range(rounds):
        qapp.processEvents()
        time.sleep(0.01)


def test_compression_filter_hides_and_restores_rows(qapp, tmp_path, fake_deps):
    for name in ("alpha.mp4", "beta.mp4"):
        (tmp_path / name).write_bytes(b"x")

    manager = QueueManager(DownloadModel([]), outdir=str(tmp_path))
    bridge = Bridge(
        manager,
        str(tmp_path),
        settings_path=str(tmp_path / "settings.ini"),
        deps=fake_deps,
    )
    bridge.compression.add_paths(
        [str(tmp_path / "alpha.mp4"), str(tmp_path / "beta.mp4")]
    )

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("downloadModel", manager.model)
    engine.rootContext().setContextProperty(
        "compressionModel", bridge.compression.model
    )
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.load(QUrl.fromLocalFile(qml_path()))
    root = engine.rootObjects()[0]
    ctx = engine.contextForObject(root)

    def ev(expr):
        result = QQmlExpression(ctx, root, expr).evaluate()
        return result[0] if isinstance(result, tuple) else result

    root.show()
    ev("tabBar.currentIndex = 3")
    _pump(qapp, 60)

    page = root.findChild(QObject, "compressionPage")
    listing = root.findChild(QObject, "compressionList")
    assert page is not None and listing is not None
    assert listing.property("count") == 2
    full_height = listing.property("contentHeight")

    page.setProperty("compFilterText", "alpha")
    _pump(qapp, 20)
    assert listing.property("contentHeight") < full_height

    page.setProperty("compFilterText", "")
    _pump(qapp, 20)
    assert listing.property("contentHeight") == full_height

    bridge.shutdown()
