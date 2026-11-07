"""Diagnóstico de ambiente e das telas."""

from __future__ import annotations

from hlsdl.config import crash_log_path
from hlsdl.diagnostics import collect_lines


def test_crash_log_path_named():
    assert crash_log_path().endswith("hlsdl-crash.log")


def test_collect_lines_has_environment(qapp):
    text = "\n".join(collect_lines())
    assert "diagnóstico" in text
    assert "Python" in text
    assert "PySide6" in text
    assert "Telas" in text
    assert "GPUs e encoders" in text
