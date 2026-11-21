"""Regressão da navegação lateral adaptativa e da preservação de páginas."""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QEvent, QMetaObject, QObject, QUrl
from PySide6.QtGui import QWindow
from PySide6.QtQml import QQmlApplicationEngine

from hlsdl.bridge import Bridge
from hlsdl.config import qml_path
from hlsdl.model import DownloadModel
from hlsdl.queue import QueueManager


def _pump(qapp, rounds: int = 50) -> None:
    for _ in range(rounds):
        qapp.processEvents()
        time.sleep(0.01)


def _build_app(qapp, tmp_path, fake_deps):
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
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("downloadModel", manager.model)
    engine.rootContext().setContextProperty(
        "compressionModel", bridge.compression.model
    )
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.load(QUrl.fromLocalFile(qml_path()))
    assert engine.rootObjects()
    root = engine.rootObjects()[0]
    root.show()
    _pump(qapp)
    return bridge, engine, root


def _teardown(qapp, engine, bridge, root) -> None:
    """Destrói a janela e o engine antes do próximo teste criar outro QML.

    ``deleteLater`` depende da fila de eventos; entregar os ``DeferredDelete``
    explicitamente evita que dois engines QML coexistam durante o teardown,
    que é onde o Qt Quick aborta com access violation no Windows.
    """
    root.close()
    _pump(qapp, 10)
    engine.deleteLater()
    qapp.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    _pump(qapp, 10)
    bridge.shutdown()


def test_main_uses_sidebar_without_recreating_pages():
    main = (Path(qml_path()).parent / "main.qml").read_text(encoding="utf-8")
    assert "AppSidebar {" in main
    assert 'objectName: "mainTabBar"' in main
    assert "property int currentIndex: 0" in main
    assert "TabBar {" not in main
    assert "SwipeView" not in main
    assert "StackLayout {" in main
    assert 'objectName: "mainStack"' in main
    assert "PageFrame {" in main
    assert "function reveal(direction)" in (
        Path(qml_path()).parent / "components" / "PageFrame.qml"
    ).read_text(encoding="utf-8")
    assert "clip: true" in main
    for shortcut in ("Ctrl+1", "Ctrl+2", "Ctrl+3", "Ctrl+4", "Ctrl+5"):
        assert f'sequence: "{shortcut}"' in main, shortcut
    assert "AboutPage {" in main
    assert 'objectName: "aboutPageFrame"' in main


def test_about_tab_is_reachable(qapp, tmp_path, fake_deps):
    bridge, engine, root = _build_app(qapp, tmp_path, fake_deps)
    root.resize(1366, 768)
    _pump(qapp)
    item = root.findChild(QObject, "navItem4")
    assert item is not None
    assert QMetaObject.invokeMethod(item, "click")
    _pump(qapp, 30)
    assert root.findChild(QObject, "mainTabBar").property("currentIndex") == 4
    assert root.findChild(QObject, "mainStack").property("currentIndex") == 4
    assert root.findChild(QObject, "aboutPage") is not None
    _teardown(qapp, engine, bridge, root)


def test_sidebar_switches_between_compact_expanded_and_drawer(
    qapp, tmp_path, fake_deps
):
    bridge, engine, root = _build_app(qapp, tmp_path, fake_deps)
    tab = root.findChild(QObject, "mainTabBar")
    menu = root.findChild(QObject, "navMenuButton")
    sidebar = root.findChild(QObject, "appSidebar")
    drawer = root.findChild(QObject, "navDrawer")
    scrim = root.findChild(QObject, "navScrim")
    page = root.findChild(QObject, "compressionPage")
    assert all((tab, menu, sidebar, drawer, scrim, page))

    # 940x620: sem rail permanente; menu abre o drawer sobreposto.
    root.resize(940, 620)
    _pump(qapp)
    assert sidebar.property("visible") is False
    assert menu.property("visible") is True
    assert drawer.property("visible") is False
    root.setProperty("navDrawerOpen", True)
    _pump(qapp, 20)
    assert drawer.property("visible") is True
    assert scrim.property("visible") is True
    assert drawer.property("width") == 220

    item2 = drawer.findChild(QObject, "navItem2")
    assert item2 is not None
    assert QMetaObject.invokeMethod(item2, "click")
    _pump(qapp, 30)
    assert tab.property("currentIndex") == 2
    assert drawer.property("visible") is False

    # 1160x800: rail compacta de 64 px; o hambúrguer continua disponível.
    root.resize(1160, 800)
    _pump(qapp)
    assert sidebar.property("visible") is True
    assert sidebar.property("width") == 64
    assert menu.property("visible") is True
    assert QMetaObject.invokeMethod(menu, "click")
    _pump(qapp, 30)
    assert sidebar.property("width") == 220
    # Expandir/retrair não pode voltar para uma aba anterior.
    assert tab.property("currentIndex") == 2
    assert QMetaObject.invokeMethod(menu, "click")
    _pump(qapp, 30)
    assert sidebar.property("width") == 64
    assert tab.property("currentIndex") == 2

    # A página não é recriada ao trocar de seção.
    page.setProperty("compFilterText", "alpha")
    _pump(qapp, 20)
    tab.setProperty("currentIndex", 3)
    _pump(qapp, 20)
    tab.setProperty("currentIndex", 2)
    _pump(qapp, 20)
    assert page.property("compFilterText") == "alpha"

    # Expandir/recolher o hambúrguer não pode voltar à seção anterior.
    assert QMetaObject.invokeMethod(menu, "click")
    _pump(qapp, 30)
    assert tab.property("currentIndex") == 2
    assert root.findChild(QObject, "mainStack").property("currentIndex") == 2
    assert QMetaObject.invokeMethod(menu, "click")
    _pump(qapp, 30)
    assert tab.property("currentIndex") == 2

    # 1366x768: rail expandida com ícone e texto; hambúrguer recolhe.
    root.resize(1366, 768)
    _pump(qapp)
    assert sidebar.property("width") == 220
    assert menu.property("visible") is True
    assert QMetaObject.invokeMethod(menu, "click")
    _pump(qapp, 30)
    assert sidebar.property("width") == 64
    assert QMetaObject.invokeMethod(menu, "click")
    _pump(qapp, 30)
    assert sidebar.property("width") == 220

    # Minimizar não pode rebaixar a janela maximizada nem manter o foco na
    # barra de título (o tooltip do toggle de tema abria junto com a janela).
    theme = root.findChild(QObject, "themeToggleButton")
    max_button = root.findChild(QObject, "maximizeButton")
    assert theme is not None and max_button is not None
    root.showMaximized()
    _pump(qapp, 60)
    assert root.property("isMaximized") is True
    theme.forceActiveFocus()
    _pump(qapp, 20)
    root.showMinimized()
    _pump(qapp, 60)
    root.showNormal()
    _pump(qapp, 100)
    assert root.property("isMaximized") is True
    assert root.property("visibility") == QWindow.Visibility.Maximized
    assert max_button.property("kind") == "restore"
    assert root.property("titleBarHasFocus") is False

    # Uma janela normal continua normal, e o foco não fica no toggle de tema.
    root.showNormal()
    _pump(qapp, 60)
    assert root.property("isMaximized") is False
    theme.forceActiveFocus()
    _pump(qapp, 20)
    root.showMinimized()
    _pump(qapp, 60)
    root.showNormal()
    _pump(qapp, 100)
    assert root.property("isMaximized") is False
    assert root.property("titleBarHasFocus") is False

    _teardown(qapp, engine, bridge, root)
