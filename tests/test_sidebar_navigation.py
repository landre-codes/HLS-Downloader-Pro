"""Regressão da navegação lateral adaptativa e da preservação de páginas."""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QMetaObject, QObject, QUrl
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
    root.close()
    _pump(qapp, 10)
    engine.deleteLater()
    _pump(qapp, 10)
    bridge.shutdown()


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

    # Fecha e destrói o engine antes do próximo teste: a animação de largura
    # da rail não pode sobreviver ao teardown do QML em testes.
    root.close()
    _pump(qapp, 10)
    engine.deleteLater()
    _pump(qapp, 10)
    bridge.shutdown()
