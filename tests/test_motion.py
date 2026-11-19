"""Contratos de motion design e barra de título."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "hlsdl" / "ui"


def test_titlebar_minimize_restore_animation_contract():
    main = (UI / "main.qml").read_text(encoding="utf-8")
    assert "function minimizeAnimated()" in main
    assert "root.minimizeAnimated()" in main
    assert "minimizeAnimation" in main
    assert "restoreAnimation" in main
    assert "Motion.minimize" in main
    assert "Motion.restore" in main
    # Só pode existir um handler para o sinal, senão o componente nem carrega.
    assert main.count("onVisibilityChanged:") == 1


def test_titlebar_tooltips_are_compact_and_motion_tokens_are_used():
    title = (UI / "components" / "TitleBarButton.qml").read_text(encoding="utf-8")
    button = (UI / "components" / "AppButton.qml").read_text(encoding="utf-8")
    assert "maxWidth: 150" in title
    assert "minWidth: 96" in title
    assert "Motion.press" in title
    assert "Motion.fast" in title
    assert "focusPolicy: Qt.TabFocus" in title
    assert "control.visualFocus ? 1 : 0" in title
    assert "Motion.press" in button
    assert "Motion.fast" in button
