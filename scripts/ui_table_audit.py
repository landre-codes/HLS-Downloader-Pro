"""Captura evidências visuais das tabelas (filtro, ordenação e tooltips).

Uso:
    python scripts/ui_table_audit.py saida/

Os dados são sintéticos: nenhum arquivo de mídia real é lido/convertido. O
script roda em Qt offscreen, usa caminhos temporários e não toca no
settings/queue do usuário.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if os.name == "nt" and not os.environ.get("QT_QPA_FONTDIR"):
    fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    if fonts.is_dir():
        os.environ["QT_QPA_FONTDIR"] = str(fonts)

from PySide6.QtCore import QMetaObject, QObject, QTimer, QUrl  # noqa: E402
from PySide6.QtGui import QFont  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from hlsdl import config  # noqa: E402
from hlsdl.bridge import Bridge  # noqa: E402
from hlsdl.compress import CompressStatus, make_item  # noqa: E402
from hlsdl.model import DownloadModel, make_item as make_download_item  # noqa: E402
from hlsdl.queue import QueueManager  # noqa: E402
from hlsdl.status import Status  # noqa: E402


def _pump(app: QApplication, rounds: int = 45) -> None:
    for _ in range(rounds):
        app.processEvents()
        time.sleep(0.01)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", help="pasta para os PNGs e o manifesto")
    args = parser.parse_args()

    out = Path(args.output).expanduser().resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="hlsdl-ui-audit-"))
    data = work / "out"
    data.mkdir()

    app = QApplication.instance() or QApplication([])
    app.setFont(QFont("Segoe UI", 10) if os.name == "nt" else QFont("Sans Serif", 10))
    model = DownloadModel([])
    bridge = Bridge(
        QueueManager(model, outdir=str(data)),
        str(data),
        settings_path=str(work / "settings.ini"),
        state_path=str(work / "queue.json"),
        defer_detection=True,
    )
    bridge.setLanguage("pt")

    compression = [
        ("alpha-documentary.mp4", CompressStatus.DONE, 100.0, 66.7,
         114_000_000, 38_000_000, "hevc_nvenc", ""),
        ("beta-lecture-4k.mp4", CompressStatus.ENCODING, 42.0, 0.0,
         61_000_000, 0, "hevc_qsv", ""),
        ("gamma-archive.mkv", CompressStatus.ERROR, 0.0, 0.0,
         28_000_000, 0, "", "ffmpeg: invalid data found"),
        ("delta-camera.mp4", CompressStatus.WAITING, 0.0, 0.0,
         18_000_000, 0, "", ""),
    ]
    for index, (name, status, progress, saving, before, after, encoder, error) in enumerate(
        compression
    ):
        path = data / name
        path.write_bytes(b"x")
        item = make_item(index + 1, str(path))
        item.update(
            status=status,
            progress=progress,
            saving=saving,
            size_before=before,
            size_after=after,
            encoder=encoder,
            error=error,
            bitrate_before=6_000_000,
            bitrate_after=2_100_000 if after else 0,
            ssim=0.982 if after else 0,
        )
        bridge.compression.model.add(item)

    downloads = [
        ("Documentário de arquivo", Status.DONE, 100.0, "-", "480 MiB"),
        ("Aula de física", Status.DOWNLOADING, 38.0, "2,4 MiB/s", "120 MiB"),
        ("Entrevista", Status.ERROR, 12.0, "-", "34 MiB"),
        ("Podcast semanal", Status.WAITING, 0.0, "-", "-"),
    ]
    for index, (title, status, progress, speed, size) in enumerate(downloads):
        item = make_download_item(index + 1, f"https://example.com/item/{index}")
        item.update(
            title=title,
            status=status,
            progress=progress,
            speed=speed,
            size=size,
            error="HTTP 403" if status is Status.ERROR else "",
        )
        model.add(item)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.rootContext().setContextProperty("downloadModel", model)
    engine.rootContext().setContextProperty(
        "compressionModel", bridge.compression.model
    )
    engine.load(QUrl.fromLocalFile(config.qml_path()))
    if not engine.rootObjects():
        print("falha ao carregar main.qml", file=sys.stderr)
        return 1
    window = engine.rootObjects()[0]
    window.show()

    tabbar = window.findChild(QObject, "mainTabBar")
    compression_page = window.findChild(QObject, "compressionPage")
    batch_page = window.findChild(QObject, "batchPage")
    comp_filter = window.findChild(QObject, "compFilter")
    batch_filter = window.findChild(QObject, "batchFilter")
    if not all((tabbar, compression_page, batch_page, comp_filter, batch_filter)):
        print("objetos QML esperados não encontrados", file=sys.stderr)
        return 1

    manifest: list[dict] = []
    failures: list[str] = []

    def grab(name: str, meta: dict) -> None:
        image = (window.grabWindow() if isinstance(window, QQuickWindow)
                 else QApplication.primaryScreen().grabWindow(int(window.winId())).toImage())
        target = out / f"{name}.png"
        if not image.save(str(target), "PNG"):
            failures.append(f"falha ao salvar {target}")
            return
        manifest.append({"file": target.name, **meta})
        print("ok", target, flush=True)

    def set_tab(index: int) -> None:
        tabbar.setProperty("currentIndex", index)
        _pump(app, 65)

    def resize(width: int, height: int) -> None:
        window.resize(width, height)
        _pump(app, 40)

    def open_tooltip(predicate) -> bool:
        tips = window.findChildren(QObject, "appToolTip")
        chosen = next((tip for tip in tips if predicate(tip)), None)
        if chosen is None:
            failures.append("tooltip não encontrado")
            return False
        QMetaObject.invokeMethod(chosen, "openTip")
        _pump(app, 20)
        return chosen.property("visible") is True

    def close_tooltips() -> None:
        for tip in window.findChildren(QObject, "appToolTip"):
            if tip.property("visible"):
                tip.setProperty("visible", False)
        _pump(app, 8)

    def set_filter(field: QObject, text: str) -> None:
        field.setProperty("text", text)
        _pump(app, 30)

    def scenario(name: str, theme: str, tab: int, width: int, height: int,
                 action=None) -> None:
        bridge.setDark(theme == "dark")
        resize(width, height)
        set_tab(tab)
        if action is not None:
            action()
            _pump(app, 25)
        grab(name, {
            "theme": theme, "tab": tab, "width": width, "height": height,
        })

    # Tabela de compressão: normal, filtrada, ordenada e tema escuro.
    scenario("1160x800-light-compression-rows", "light", 3, 1160, 800)
    set_filter(comp_filter, "status:erro")
    grab("1160x800-light-compression-filter", {
        "theme": "light", "tab": 3, "width": 1160, "height": 800,
        "filter": "status:erro",
    })
    set_filter(comp_filter, "")
    header = window.findChild(QObject, "compHeaderName")
    QMetaObject.invokeMethod(header, "activate")
    _pump(app, 20)
    grab("1160x800-light-compression-sorted", {
        "theme": "light", "tab": 3, "width": 1160, "height": 800,
        "sort": "name asc",
    })
    open_tooltip(lambda tip: tip.property("title") == "Arquivo"
                 and "ordenar" in tip.property("text").lower())
    grab("1160x800-light-tooltip-sort", {
        "theme": "light", "tab": 3, "width": 1160, "height": 800,
        "tooltip": "sort name",
    })
    close_tooltips()
    scenario("1160x800-dark-compression-rows", "dark", 3, 1160, 800)
    scenario("940x620-light-compression-rows", "light", 3, 940, 620)

    # Ajustes recolhidos liberam a fila em 940x620 (UX-19-06).
    def toggle_settings() -> None:
        expression = QQmlExpression(
            engine.contextForObject(compression_page),
            compression_page,
            "toggleSettings()",
        )
        expression.evaluate()
        _pump(app, 25)

    toggle_settings()
    grab("940x620-light-compression-collapsed", {
        "theme": "light", "tab": 3, "width": 940, "height": 620,
        "settings": "collapsed",
    })
    toggle_settings()

    # Fila de downloads: ordenação por título, filtro por status e tooltip.
    scenario("1160x800-light-batch-rows", "light", 1, 1160, 800)
    set_filter(batch_filter, "status:erro")
    grab("1160x800-light-batch-filter", {
        "theme": "light", "tab": 1, "width": 1160, "height": 800,
        "filter": "status:erro",
    })
    set_filter(batch_filter, "")
    batch_header = window.findChild(QObject, "batchHeaderName")
    QMetaObject.invokeMethod(batch_header, "activate")
    _pump(app, 20)
    grab("1160x800-light-batch-sorted", {
        "theme": "light", "tab": 1, "width": 1160, "height": 800,
        "sort": "name asc",
    })
    open_tooltip(lambda tip: tip.property("shortcut") == "Ctrl+V")
    grab("1160x800-light-tooltip-shortcut", {
        "theme": "light", "tab": 1, "width": 1160, "height": 800,
        "tooltip": "paste shortcut",
    })
    close_tooltips()
    scenario("1160x800-dark-batch-rows", "dark", 1, 1160, 800)
    scenario("940x620-light-batch-rows", "light", 1, 940, 620)

    (out / "manifest.json").write_text(
        json.dumps({"screenshots": manifest, "failures": failures},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"captures": len(manifest), "failures": failures},
                     ensure_ascii=False), flush=True)
    bridge.shutdown()
    app.quit()
    shutil.rmtree(work, ignore_errors=True)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
