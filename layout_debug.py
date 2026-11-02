"""Dump da árvore de geometria do QML para depuração do layout.

NOTA: nao usamos item.property() aqui — nessa build do PySide6 ler certas
propriedades QML pelo Python crasha o processo (0xC0000409, __fastfail).
"""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QFont
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from hlsdl.config import qml_path
from main import Bridge, default_output_folder
from worker import DownloadModel, QueueManager


def dump(item, depth=0):
    kind = item.metaObject().className().split(".")[-1]
    vis = "" if item.isVisible() else " [INVISIVEL]"
    print(
        f"{'  ' * depth}{kind} x={item.x()} y={item.y()} w={item.width():.0f} "
        f"h={item.height():.0f}{vis}", flush=True
    )
    for child in item.childItems():
        dump(child, depth + 1)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("HLS Downloader Pro Debug")
    app.setFont(QFont("Segoe UI", 10))

    outdir = default_output_folder()
    model = DownloadModel([])
    manager = QueueManager(model, outdir=outdir, concurrency=3)
    bridge = Bridge(manager, outdir)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("downloadModel", model)
    engine.rootContext().setContextProperty("bridge", bridge)
    qml_file = sys.argv[1] if len(sys.argv) > 1 else qml_path()
    engine.load(QUrl.fromLocalFile(qml_file))

    root = engine.rootObjects()[0]
    print("WINDOW:", root.width(), "x", root.height())

    def do_dump():
        root.show()
        QTimer.singleShot(600, lambda: (dump(root.contentItem()), os._exit(0)))

    QTimer.singleShot(2500, do_dump)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
