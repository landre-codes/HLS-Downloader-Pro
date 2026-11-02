"""Configuração compartilhada dos testes (pytest).

Força o backend offscreen do Qt antes de importar PySide6 e fornece helpers
para rodar o loop de eventos sem uma GUI real.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402
from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def process_until(qapp, predicate, timeout: float = 10.0, interval: float = 0.01) -> bool:
    """Roda o loop de eventos até ``predicate()`` ser verdadeiro (ou timeout)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        qapp.processEvents()
        if predicate():
            return True
        time.sleep(interval)
    qapp.processEvents()
    return bool(predicate())


class FakeDeps(QObject):
    """Substituto de ``DependencyManager`` para testes sem detecção real."""

    checked = Signal(list)
    installStarted = Signal(str)
    installOutput = Signal(str)
    installFinished = Signal(str, bool, str)

    def __init__(self, items=None, parent=None):
        super().__init__(parent)
        self._items = items or []

    def check_all(self):
        self.checked.emit(self._items)
        return self._items

    def install(self, key):
        return False

    def update_pip_tools(self):
        pass

    def essentials_present(self):
        return True


@pytest.fixture
def fake_deps():
    return FakeDeps([])
