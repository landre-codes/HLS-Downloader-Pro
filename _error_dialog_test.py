"""Verifica o diálogo de erro: item com erro no modelo → linha mostra e o
diálogo abre com a mensagem completa (via QQmlExpression, sem item.property).

NOTA: exceções dentro do callback do QTimer crasham (0xC0000409) nessa build
do PySide6 — nada de raise no run(); coleta falhas e sai com código.
"""

from __future__ import annotations

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QFont
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression
from PySide6.QtWidgets import QApplication

from hlsdl.config import qml_path
from main import Bridge, default_output_folder
from worker import DownloadModel, QueueManager, Status

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
    app.setFont(QFont("Segoe UI", 10))

    outdir = default_output_folder()
    model = DownloadModel([])
    manager = QueueManager(model, outdir=outdir, concurrency=3)
    bridge = Bridge(
        manager, outdir,
        settings_path=os.path.join(tempfile.gettempdir(), "hlsdlp-errdialog-test.ini"),
    )

    model.add({
        "id": 1,
        "url": "https://exemplo.com/video.m3u8",
        "title": "https://exemplo.com/video.m3u8",
        "status": Status.ERROR,
        "progress": 0.0,
        "speed": "—",
        "size": "—",
        "error": "ERROR: [site] Este é o erro completo para diagnosticar.",
    })
    model.touch(0)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("downloadModel", model)
    engine.rootContext().setContextProperty("compressionModel", bridge.compression.model)
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.load(QUrl.fromLocalFile(qml_path()))
    root = engine.rootObjects()[0]
    ctx = engine.contextForObject(root)

    def run():
        from PySide6.QtCore import QModelIndex
        n = model.rowCount(QModelIndex())
        chk("linhas no modelo (python)", n, 1)
        err = model.data(model.index(0, 0), model.ERROR)
        chk("role ERROR do modelo", err, "ERROR: [site] Este é o erro completo para diagnosticar.")
        ev(ctx, root, "root.errorText = 'ERROR: msg de teste'")
        ev(ctx, root, "errorDialog.open()")
        v = ev(ctx, root, "errorDialog.visible")
        chk("dialog aberto", v, True)
        title = ev(ctx, root, "errorDialog.title")
        chk("titulo do dialog", title, "Detalhes do erro")
        txt = ev(ctx, root, "root.errorText")
        chk("texto do erro", txt, "ERROR: msg de teste")
        print("ERRO DIALOG", "OK" if not FAILS else "FALHOU", flush=True)
        os._exit(0 if not FAILS else 1)

    QTimer.singleShot(1500, run)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
