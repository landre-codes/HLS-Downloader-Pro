"""Captura screenshots reais das abas para revisão visual (offscreen).

Uso:
    python scripts/ui_snapshot.py saida/
    QT_SCALE_FACTOR=1.5 python scripts/ui_snapshot.py saida-150/

No Windows, usa as fontes do sistema via QT_QPA_FONTDIR (o plugin offscreen do
Qt não carrega fontes por padrão). Não toca no settings/queue reais: tudo é
gravado na pasta de saída.
"""

from __future__ import annotations

import argparse
import os
import sys
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
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from hlsdl import config  # noqa: E402
from hlsdl.bridge import Bridge  # noqa: E402
from hlsdl.model import DownloadModel  # noqa: E402
from hlsdl.queue import QueueManager  # noqa: E402

DEFAULT_SIZES = "940x620,1160x800,1366x768,1920x1080"


def _parse_sizes(value: str) -> list[tuple[int, int]]:
    sizes = []
    for item in value.split(","):
        width, _, height = item.partition("x")
        sizes.append((int(width), int(height)))
    return sizes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", help="pasta para os PNGs")
    parser.add_argument("--sizes", default=DEFAULT_SIZES)
    parser.add_argument("--themes", default="dark,light")
    parser.add_argument("--tabs", default="0,1,2,3")
    parser.add_argument(
        "--states", action="store_true",
        help="captura também toast longo e diálogo de erro",
    )
    args = parser.parse_args()

    out = Path(args.output).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    sizes = _parse_sizes(args.sizes)
    themes = [item.strip() for item in args.themes.split(",") if item.strip()]
    tabs = [int(item) for item in args.tabs.split(",") if item.strip()]

    app = QApplication.instance() or QApplication([])
    app.setFont(QFont("Segoe UI", 10) if os.name == "nt" else QFont("Sans Serif", 10))
    model = DownloadModel([])
    bridge = Bridge(
        QueueManager(model, outdir=str(out / "out")),
        str(out / "out"),
        settings_path=str(out / "settings.ini"),
        state_path=str(out / "queue.json"),
        defer_detection=True,
    )
    bridge.setLanguage("pt")

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
    tabbar = window.findChild(QObject, "mainTabBar")
    if tabbar is None:
        print("mainTabBar não encontrada", file=sys.stderr)
        return 1
    window.show()

    jobs: list[tuple] = [
        (size, theme, tab)
        for size in sizes
        for theme in themes
        for tab in tabs
    ]
    if args.states:
        jobs = [(sizes[0], theme, "state") for theme in themes] + jobs
    index = 0

    def grab(name: str) -> None:
        if isinstance(window, QQuickWindow):
            image = window.grabWindow()
        else:
            screen = QApplication.primaryScreen()
            if screen is None:
                print("sem QScreen", file=sys.stderr)
                return
            image = screen.grabWindow(int(window.winId())).toImage()
        target = out / f"{name}.png"
        ok = image.save(str(target), "PNG")
        print(("ok " if ok else "fail ") + str(target), flush=True)

    def open_error(size: tuple[int, int], theme: str) -> None:
        toast = window.findChild(QObject, "toast")
        if toast is not None:
            toast.setProperty("visible", False)
        window.setProperty(
            "errorText",
            "Falha ao validar a saída de compressão: hdr_metadata:"
            "content_light_missing. O arquivo original foi preservado.",
        )
        dialog = window.findChild(QObject, "errorDialog")
        if dialog is not None:
            QMetaObject.invokeMethod(dialog, "open")
        QTimer.singleShot(
            350, lambda: grab(f"{size[0]}x{size[1]}-{theme}-error")
        )
        QTimer.singleShot(
            650,
            lambda: dialog.setProperty("detailsVisible", True) if dialog else None,
        )
        QTimer.singleShot(
            950, lambda: grab(f"{size[0]}x{size[1]}-{theme}-error-details")
        )

    def step() -> None:
        nonlocal index
        if index >= len(jobs):
            bridge.shutdown()
            app.quit()
            return
        size, theme, tab = jobs[index]
        index += 1
        bridge.setDark(theme == "dark")
        window.resize(*size)
        dialog = window.findChild(QObject, "errorDialog")
        if dialog is not None:
            QMetaObject.invokeMethod(dialog, "close")
        toast = window.findChild(QObject, "toast")
        if toast is not None:
            toast.setProperty("visible", False)
        if tab == "state":
            bridge.notifyText.emit(
                "Não foi possível concluir a operação: a resposta do servidor "
                "excedeu o limite configurado e o download foi cancelado. "
                "Verifique a URL e tente novamente."
            )
            QTimer.singleShot(
                250, lambda: grab(f"{size[0]}x{size[1]}-{theme}-toast")
            )
            QTimer.singleShot(650, lambda: open_error(size, theme))
            QTimer.singleShot(2200, step)
            return
        tabbar.setProperty("currentIndex", int(tab))
        QTimer.singleShot(
            450, lambda: grab(f"{size[0]}x{size[1]}-{theme}-tab{tab}")
        )
        QTimer.singleShot(520, step)

    QTimer.singleShot(500, step)
    app.exec()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
