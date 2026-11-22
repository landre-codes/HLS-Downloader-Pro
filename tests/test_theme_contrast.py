"""Contraste mínimo dos tokens de tema (WCAG AA para texto normal)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QEvent, QUrl
from PySide6.QtGui import QColor
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlExpression
from PySide6.QtQuick import QQuickItem

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
        card = color("root.theme.cardBg")
        pairs = [
            ("texto", color("root.theme.text"), bg),
            ("texto secundário", color("root.theme.textSecondary"), bg),
            ("texto mudo", color("root.theme.textMuted"), bg),
            ("accentText", color("root.theme.accentText"), bg),
            ("onAccent/accentFill", color("root.theme.onAccent"), color("root.theme.accentFill")),
            ("erro", color("root.theme.errorText"), bg),
            ("sucesso", color("root.theme.successText"), bg),
            ("ocupado", color("root.theme.busyText"), bg),
            ("texto no card", color("root.theme.text"), card),
            ("texto secundário no card", color("root.theme.textSecondary"), card),
            ("texto mudo no card", color("root.theme.textMuted"), card),
            ("accentText no card", color("root.theme.accentText"), card),
            ("erro no card", color("root.theme.errorText"), card),
            ("sucesso no card", color("root.theme.successText"), card),
            ("ocupado no card", color("root.theme.busyText"), card),
        ]
        for name, fg, background in pairs:
            assert _contrast(fg, background) >= 4.5, (dark, name, _contrast(fg, background))
        on_accent = color("root.theme.onAccent")
        for badge in ("badgeDone", "badgeError", "badgeDownloading",
                      "badgeAnalyzing", "badgeEncoding", "badgeMuted"):
            assert _contrast(on_accent, color(f"root.theme.{badge}")) >= 4.5, (dark, badge)
        # O cartão do diálogo precisa ser opaco e usar o fundo de card do tema.
        assert (color("confirmDeps.contentItem.cardColor")
                == color("root.theme.cardBg"))

    # Controles extraídos para arquivos próprios precisam herdar o estilo
    # Material do app; sem isso o ComboBox cai no tema padrão (texto preto).
    bridge.setDark(True)
    qapp.processEvents()
    combo = next(
        item for item in root.findChildren(QQuickItem)
        if item.property("visible")
        and ("AppQualityCombo" in item.metaObject().className()
             or "AppComboBox" in item.metaObject().className())
    )
    content = combo.property("contentItem")
    assert content is not None
    text_color = content.property("color")
    assert isinstance(text_color, QColor)
    assert text_color.lightnessF() > 0.5, text_color.name()

    # Botões: base, hover e pressed preenchidos precisam manter texto branco
    # legível; o tonal precisa manter o texto de acento sobre as três camadas.
    button_components = []
    button_objects = []

    def make_button(variant):
        component = QQmlComponent(engine)
        component.setData(
            (
                "import QtQuick\n"
                "import \"components\"\n"
                f"AppButton {{ variant: \"{variant}\" }}\n"
            ).encode(),
            QUrl.fromLocalFile(str(Path(qml_path()).parent / "ButtonUnderTest.qml")),
        )
        assert component.status() == QQmlComponent.Ready, component.errorString()
        button = component.create()
        assert button is not None, component.errorString()
        button.setParent(root)
        button.setVisible(False)
        button_components.append(component)
        button_objects.append(button)
        qapp.processEvents()
        return button

    for dark in (False, True):
        bridge.setDark(dark)
        qapp.processEvents()
        for variant in ("primary", "success", "warning", "danger"):
            button = make_button(variant)
            for prop in ("_filledBase", "_filledHover", "_filledDown"):
                value = button.property(prop)
                assert isinstance(value, QColor), (dark, variant, prop, value)
                assert _contrast(QColor("#ffffff"), value) >= 4.5, (
                    dark, variant, prop, value.name()
                )
            button.setProperty("enabled", False)
            qapp.processEvents()
            disabled_text = button.property("_textColor")
            disabled_bg = button.property("_filledDisabled")
            assert _contrast(disabled_text, disabled_bg) >= 3.0, (
                dark, variant, "disabled", disabled_text.name(), disabled_bg.name()
            )

        button = make_button("tonal")
        for prop in ("_tonalBg", "_tonalHover", "_tonalDown"):
            value = button.property(prop)
            assert isinstance(value, QColor), (dark, prop, value)
            assert _contrast(button.property("_textColor"), value) >= 4.5, (
                dark, prop, value.name()
            )
        button.setProperty("enabled", False)
        qapp.processEvents()
        disabled_text = button.property("_textColor")
        disabled_bg = button.property("_tonalDisabled")
        assert _contrast(disabled_text, disabled_bg) >= 3.0, (
            dark, "tonal disabled", disabled_text.name(), disabled_bg.name()
        )

    root.close()
    qapp.processEvents()
    engine.deleteLater()
    qapp.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qapp.processEvents()
    bridge.shutdown()
