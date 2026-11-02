"""Valida a troca entre os 8 idiomas e as opções de qualidade/arquivo."""

from __future__ import annotations

import os
import sys
import tempfile

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

EXPECTED_DONE = {
    "pt": "Concluído", "en": "Completed", "es": "Completado", "it": "Completato",
    "fr": "Terminé", "ru": "Завершено", "ja": "完了", "zh": "已完成",
}


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
    bridge = Bridge(
        manager, "out",
        settings_path=os.path.join(tempfile.gettempdir(), "hlsdlp-langs-test.ini"),
    )

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("downloadModel", model)
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.load(QUrl.fromLocalFile(qml_path()))
    root = engine.rootObjects()[0]
    ctx = engine.contextForObject(root)

    def run():
        for lang, expected in EXPECTED_DONE.items():
            bridge.setLanguage(lang)
            app.processEvents()
            chk(f"idioma {lang} s_done", ev(ctx, root, "strings.s_done"), expected)
            txt = ev(ctx, root, "strings.tab_single")
            assert txt, f"tab_single vazio em {lang}"

        # Opções de qualidade e arquivo
        bridge.setLanguage("pt")
        bridge.setFormatMode("video_audio")
        bridge.setQuality("1080")
        bridge.setContainer("mkv")
        chk("quality", bridge.quality, "1080")
        chk("container", bridge.container, "mkv")
        chk("qualidade visível", ev(ctx, root, "bridge.formatMode !== 'audio_only'"), True)

        bridge.setFormatMode("audio_only")
        app.processEvents()
        chk("container ajustado p/ áudio", bridge.container in ("mp3", "m4a", "wav", "flac", "opus"), True)

        print("LANGUAGES/OPTIONS", "OK" if not FAILS else "FALHOU", flush=True)
        os._exit(0 if not FAILS else 1)

    QTimer.singleShot(1200, run)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
