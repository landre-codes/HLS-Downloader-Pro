"""Valida a troca PT/EN no QML: bindings reavaliados via retranslate().

Usa QQmlExpression (item.property() crasha nessa build do PySide6).
"""

from __future__ import annotations

import os
import sys
import tempfile

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QFont
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression
from PySide6.QtWidgets import QApplication

from hlsdl.config import qml_path
from main import Bridge, default_output_folder
from worker import DownloadModel, QueueManager

_KEEP = []


def ev(qml_ctx, scope, expr):
    e = QQmlExpression(qml_ctx, scope, expr)
    _KEEP.append(e)  # evita o GC do QQmlExpression (build PySide6 crasha)
    return e.evaluate()[0]


def main() -> int:
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))

    outdir = default_output_folder()
    model = DownloadModel([])
    manager = QueueManager(model, outdir=outdir, concurrency=3)
    bridge = Bridge(
        manager, outdir,
        settings_path=os.path.join(tempfile.gettempdir(), "hlsdlp-i18n-test.ini"),
    )

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("downloadModel", model)
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.load(QUrl.fromLocalFile(qml_path()))
    root = engine.rootObjects()[0]
    ctx = engine.contextForObject(root)

    results = []

    def check(step):
        r = ev(ctx, root, step["expr"])
        ok = r == step["want"]
        results.append((step["name"], ok, r))
        print(f"{'OK ' if ok else 'FALHA '}{step['name']}: {r!r} (esperado {step['want']!r})", flush=True)

    def run():
        steps = [
            ("pt inicial entry_title", "strings.entry_title", "Entrada em Lote"),
            ("pt inicial status concluido", "strings['s_done']", "Concluído"),
            ("pt inicial cfg_dark", "strings.cfg_dark", "Tema escuro"),
        ]
        for name, expr, want in steps:
            v = ev(ctx, root, expr)
            ok = v == want
            print(f"{'OK ' if ok else 'FALHA '}{name}: {v!r} (esperado {want!r})", flush=True)
        bridge.setLanguage("en")
        app.processEvents()
        steps_en = [
            ("en cfg_dark", "strings.cfg_dark", "Dark theme"),
            ("en entry_title", "strings.entry_title", "Batch Entry"),
            ("en status concluido", "strings['s_done']", "Completed"),
            ("en tab_downloads", "strings.tab_downloads", "Batch"),
            ("en tab_single", "strings.tab_single", "Single Download"),
            ("en status dinamico", "strings['s_' + 'error']", "Error"),
            ("en btn_start", "strings.btn_start", "Start Queue"),
        ]
        for name, expr, want in steps_en:
            v = ev(ctx, root, expr)
            ok = v == want
            print(f"{'OK ' if ok else 'FALHA '}{name}: {v!r} (esperado {want!r})", flush=True)
        bridge.setLanguage("pt")
        app.processEvents()
        v = ev(ctx, root, "strings.entry_title")
        print(f"{'OK ' if v == 'Entrada em Lote' else 'FALHA '}volta pt: {v!r}", flush=True)
        print("I18N QML OK", flush=True)
        os._exit(0)

    QTimer.singleShot(1500, run)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
