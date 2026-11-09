"""Escala automática da interface conforme o tamanho da tela."""

from __future__ import annotations

import os

from hlsdl.app import apply_ui_scale, compute_ui_scale


def test_compute_ui_scale_grows_with_width():
    assert compute_ui_scale(0) == 1.0
    assert compute_ui_scale(1280) == 1.0
    assert compute_ui_scale(1600) == 1.0
    assert compute_ui_scale(1920) == 1.10
    assert compute_ui_scale(2560) == 1.26
    # Telas muito grandes não estouram o layout.
    assert compute_ui_scale(3840) == 1.28
    assert compute_ui_scale(7680) == 1.28


def test_apply_ui_scale_override(monkeypatch):
    monkeypatch.delenv("QT_SCALE_FACTOR", raising=False)
    monkeypatch.delenv("HLSDL_UI_SCALE", raising=False)
    argv = ["app.exe", "--ui-scale", "1.5", "--verbose"]
    assert apply_ui_scale(argv) == 1.5
    assert argv == ["app.exe", "--verbose"]
    assert os.environ["QT_SCALE_FACTOR"] == "1.50"


def test_apply_ui_scale_env(monkeypatch):
    monkeypatch.delenv("QT_SCALE_FACTOR", raising=False)
    monkeypatch.setenv("HLSDL_UI_SCALE", "1,2")
    argv = ["app.exe"]
    assert apply_ui_scale(argv) == 1.2
    assert os.environ["QT_SCALE_FACTOR"] == "1.20"


def test_auto_scale_does_not_stack_on_system_dpi(monkeypatch):
    monkeypatch.delenv("QT_SCALE_FACTOR", raising=False)
    monkeypatch.delenv("HLSDL_UI_SCALE", raising=False)
    monkeypatch.setattr("hlsdl.app._system_screen_width", lambda: 3840)
    monkeypatch.setattr("hlsdl.app._system_dpi_scale", lambda: 1.5)
    argv = ["app.exe"]
    assert apply_ui_scale(argv) == 1.0
    assert "QT_SCALE_FACTOR" not in os.environ


def test_fit_window_to_screen(qapp):
    from PySide6.QtGui import QGuiApplication, QWindow

    from hlsdl.app import _fit_window_to_screen

    window = QWindow()
    window.setGeometry(0, 0, 9999, 9999)
    _fit_window_to_screen(window)
    available = QGuiApplication.primaryScreen().availableGeometry()
    assert window.width() <= available.width()
    assert window.height() <= available.height()


def test_clamp_geometry_fits_screen(qapp):
    from PySide6.QtGui import QGuiApplication

    from hlsdl.app import _clamp_geometry

    available = QGuiApplication.primaryScreen().availableGeometry()
    clamped = _clamp_geometry(0, 0, available.width() + 400, available.height() + 200)
    assert clamped is not None
    x, y, w, h = clamped
    assert w <= available.width()
    assert h <= available.height()
    assert x >= available.x()
    assert y >= available.y()
    assert x + w <= available.x() + available.width()
    assert y + h <= available.y() + available.height()
    # Centro fora de qualquer tela: não reposiciona.
    assert _clamp_geometry(-99999, -99999, 1200, 800) is None
