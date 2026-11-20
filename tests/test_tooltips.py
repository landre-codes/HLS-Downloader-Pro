"""Tooltips ricos: abertura programática, limites e conteúdo contextual."""

from __future__ import annotations

import time

from PySide6.QtCore import QMetaObject, QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression

from hlsdl.bridge import Bridge
from hlsdl.config import qml_path
from hlsdl.model import DownloadModel, make_item
from hlsdl.queue import QueueManager
from hlsdl.status import Status


def _pump(qapp, rounds: int = 50) -> None:
    for _ in range(rounds):
        qapp.processEvents()
        time.sleep(0.01)


def _ev(ctx, scope, expr):
    expression = QQmlExpression(ctx, scope, expr)
    result = expression.evaluate()
    if expression.hasError():
        raise AssertionError(expression.error().toString())
    return result[0] if isinstance(result, tuple) else result


def test_rich_tooltips_open_inside_window_and_expose_shortcut(qapp, tmp_path, fake_deps):
    manager = QueueManager(DownloadModel([]), outdir=str(tmp_path / "out"))
    bridge = Bridge(
        manager,
        str(tmp_path / "out"),
        settings_path=str(tmp_path / "settings.ini"),
        state_path=str(tmp_path / "queue.json"),
        deps=fake_deps,
        defer_detection=True,
    )
    bridge.setLanguage("pt")
    item = make_item(1, "https://example.com/a")
    item.update(title="Aula de física", status=Status.WAITING)
    manager.model.add(item)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("downloadModel", manager.model)
    engine.rootContext().setContextProperty(
        "compressionModel", bridge.compression.model
    )
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.load(QUrl.fromLocalFile(qml_path()))
    root = engine.rootObjects()[0]
    root.resize(1160, 800)
    root.show()
    _ev(engine.contextForObject(root), root, "tabBar.currentIndex = 2")
    _pump(qapp, 70)

    header = root.findChild(QObject, "compHeaderName")
    assert header is not None
    tips = root.findChildren(QObject, "appToolTip")
    assert len(tips) > 20  # a UI inteira usa o componente, não o ToolTip cru

    sort_tip = next(
        tip for tip in tips
        if tip.property("title") == "Arquivo"
        and "ordenar" in tip.property("text").lower()
    )
    assert sort_tip.property("title") == "Arquivo"
    assert "ordenar" in sort_tip.property("text").lower()
    assert "nome" in sort_tip.property("footer").lower()
    QMetaObject.invokeMethod(sort_tip, "openTip")
    _pump(qapp, 25)
    assert sort_tip.property("visible") is True
    x = sort_tip.property("x")
    y = sort_tip.property("y")
    width = sort_tip.property("width")
    height = sort_tip.property("height")
    assert width <= 380
    assert x >= 8 and x + width <= root.property("width") - 8
    assert y >= 8 and y + height <= root.property("height") - 8

    # O conteúdo deve ficar centralizado nos dois eixos, não apenas alinhado
    # à esquerda/topo como no ToolTip padrão.
    for name in ("tipTitleText", "tipBodyText", "tipFooterText"):
        text_item = sort_tip.findChild(QObject, name)
        assert text_item is not None, name
        centered = _ev(
            engine.contextForObject(text_item),
            text_item,
            "horizontalAlignment === Text.AlignHCenter"
            " && verticalAlignment === Text.AlignVCenter",
        )
        assert centered is True, name

    title = sort_tip.findChild(QObject, "tipTitleText")
    assert abs((title.property("x") + title.property("width") / 2)
               - title.parent().property("width") / 2) <= 1

    column = sort_tip.findChild(QObject, "tooltipContentColumn")
    assert column is not None
    host = column.parent()
    assert abs(column.property("y")
               - (host.property("height") - column.property("height")) / 2) <= 1

    QMetaObject.invokeMethod(sort_tip, "close")
    _pump(qapp, 40)
    assert sort_tip.property("visible") is False

    _ev(engine.contextForObject(root), root, "tabBar.currentIndex = 1")
    _pump(qapp, 60)
    paste_tip = next(
        tip for tip in root.findChildren(QObject, "appToolTip")
        if tip.property("shortcut") == "Ctrl+V"
    )
    assert paste_tip.property("title") == "Colar da Área de Transferência"
    assert "transferência" in paste_tip.property("text").lower()

    bridge.shutdown()
