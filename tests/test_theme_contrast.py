"""Contraste mínimo dos tokens de tema (WCAG AA para texto normal)."""

from __future__ import annotations

import tempfile

from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression

from hlsdl.bridge import Bridge
from hlsdl.config import qml_path
from hlsdl.model import DownloadModel
from hlsdl.queue import QueueManager


def _contrast(a: QColor, b: QColor) -> float:
    def lum(color: QColor) -> float:
        r, g, bl = (channel / 255.0 for channel in (color.red(), color.green(), color.blue()))
        def linear(channel: float) -> float:
            return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        return 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(bl)
    l1, l2 = sorted((lum(a), lum(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def test_theme_text_contrast(qapp, fake_deps):
    engine = QQmlApplicationEngine()
    model = DownloadModel([])
    bridge = Bridge(
        QueueManager(model, outdir="out"),
        "out",
        settings_path=tempfile.mktemp(suffix=".ini"),
        deps=fake_deps,
    )
    engine.rootContext().setContextProperty("downloadModel", model)
    engine.rootContext().setContextProperty("compressionModel", bridge.compression.model)
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.load(QUrl.fromLocalFile(qml_path()))
    root = engine.rootObjects()[0]
    ctx = engine.contextForObject(root)

    def color(expr):
        return QQmlExpression(ctx, root, expr).evaluate()[0]

    for dark in (False, True):
        bridge.setDark(dark)
        qapp.processEvents()
        bg = color("root.theme.windowBg")
        pairs = [
            ("texto", color("root.theme.text"), bg),
            ("texto secundário", color("root.theme.textSecondary"), bg),
            ("texto mudo", color("root.theme.textMuted"), bg),
            ("accentText", color("root.theme.accentText"), bg),
            ("onAccent/accentFill", color("root.theme.onAccent"), color("root.theme.accentFill")),
            ("erro", color("root.theme.errorText"), bg),
        ]
        for name, fg, background in pairs:
            assert _contrast(fg, background) >= 4.5, (dark, name, _contrast(fg, background))
        on_accent = color("root.theme.onAccent")
        for badge in ("badgeDone", "badgeError", "badgeDownloading",
                      "badgeAnalyzing", "badgeEncoding", "badgeMuted"):
            assert _contrast(on_accent, color(f"root.theme.{badge}")) >= 4.5, (dark, badge)
        # O corpo do diálogo precisa ser opaco e usar o fundo do tema.
        assert color("confirmDeps.contentItem.color") == bg
    bridge.shutdown()
