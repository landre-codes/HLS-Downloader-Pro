"""Hooks de log: mensagens do Qt e exceções não tratadas."""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QtMsgType

from hlsdl.app import _log_unhandled, _qt_message_level


def test_qt_message_level_mapping():
    assert _qt_message_level(QtMsgType.QtDebugMsg) == logging.DEBUG
    assert _qt_message_level(QtMsgType.QtInfoMsg) == logging.INFO
    assert _qt_message_level(QtMsgType.QtWarningMsg) == logging.WARNING
    assert _qt_message_level(QtMsgType.QtCriticalMsg) == logging.ERROR
    assert _qt_message_level(QtMsgType.QtFatalMsg) == logging.CRITICAL


def test_unhandled_exception_is_logged(caplog, monkeypatch):
    monkeypatch.setattr("traceback.print_exception", lambda *args, **kwargs: None)
    with caplog.at_level(logging.CRITICAL, logger="hlsdl"):
        try:
            raise RuntimeError("falha proposital")
        except RuntimeError:
            _log_unhandled(*sys.exc_info())
    assert "exceção não tratada" in caplog.text
    assert caplog.records
    assert caplog.records[-1].exc_info is not None
    assert "falha proposital" in str(caplog.records[-1].exc_info[1])
