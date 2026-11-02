"""Verifica que o SwipeView segue o TabBar por binding (não trava na aba).

Regressão do bug em que `views.currentIndex = 1` quebrava o binding e prendia
a interface na aba Configurações.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression
from PySide6.QtWidgets import QApplication

from hlsdl.bridge import Bridge
from hlsdl.config import qml_path
from hlsdl.model import DownloadModel
from hlsdl.queue import QueueManager

_KEEP = []
FAILS = []


def ev(ctx, scope, expr):
    e = QQmlExpression(ctx, scope, expr)
    _KEEP.append(e)
    return e.evaluate()[0]


def chk(name, got, want):
    ok = got == want
    print(f"{'OK ' if ok else 'FALHA '}{name}: {got!r} (esperado {want!r})", flush=True)
    if not ok:
        FAILS.append(name)


def main() -> int:
    app = QApplication(sys.argv)
    model = DownloadModel([])
    manager = QueueManager(model, outdir="out")
    bridge = Bridge(manager, "out")

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("downloadModel", model)
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.load(QUrl.fromLocalFile(qml_path()))
    root = engine.rootObjects()[0]
    ctx = engine.contextForObject(root)

    def run():
        # Vai para Configurações e volta várias vezes.
        ev(ctx, root, "tabBar.currentIndex = 1")
        chk("aba 1 -> views", ev(ctx, root, "views.currentIndex"), 1)
        ev(ctx, root, "tabBar.currentIndex = 0")
        chk("aba 0 -> views", ev(ctx, root, "views.currentIndex"), 0)
        ev(ctx, root, "tabBar.currentIndex = 1")
        chk("aba 1 (2a vez) -> views", ev(ctx, root, "views.currentIndex"), 1)
        ev(ctx, root, "tabBar.currentIndex = 0")
        chk("aba 0 (2a vez) -> views", ev(ctx, root, "views.currentIndex"), 0)
        print("TAB BINDING", "OK" if not FAILS else "FALHOU", flush=True)
        os._exit(0 if not FAILS else 1)

    QTimer.singleShot(1200, run)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
