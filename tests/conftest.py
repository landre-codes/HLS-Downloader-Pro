"""Configuração compartilhada dos testes (pytest).

Força o backend offscreen do Qt antes de importar PySide6 e fornece helpers
para rodar o loop de eventos sem uma GUI real.
"""

from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Never restore/save the developer's real queue during tests.
os.environ.setdefault(
    "HLSDL_QUEUE_STATE",
    str(Path(tempfile.gettempdir()) / "hlsdlp-test-queue.json"),
)
# O probe de dispositivos QSV abre subprocessos e threads nativas; em máquinas
# sem driver/hardware ele pode sobreviver ao teardown dos testes. A suíte
# funcional de GPU define HLSDL_TEST_QSV=1 e mantém o probe habilitado.
if not os.environ.get("HLSDL_TEST_QSV"):
    os.environ.setdefault("HLSDL_DISABLE_QSV_PROBE", "1")

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


@pytest.fixture(autouse=True)
def _sidecars_enabled_for_tests():
    """Isola a flag global de sidecars entre testes."""
    from hlsdl.integrity import set_sidecars_enabled

    set_sidecars_enabled(True)
    yield
    set_sidecars_enabled(True)


@pytest.fixture(autouse=True)
def _shutdown_qt_helpers(monkeypatch):
    """Encerra Bridges/CompressionManagers criados no teste.

    Produção chama ``Bridge.shutdown()`` ao fechar a janela. Testes que apenas
    deixam o objeto sair de escopo podem destruir um QObject enquanto uma
    thread auxiliar (ex.: detecção QSV) ainda emite sinais, causando access
    violation no teardown do Qt. Este fixture reproduz o ciclo de vida real sem
    persistir estado em disco.
    """
    from hlsdl.bridge import Bridge
    from hlsdl.compress import CompressionManager
    from hlsdl.queue import QueueManager

    bridges: list = []
    managers: list = []
    queues: list = []
    original_bridge_init = Bridge.__init__
    original_compression_init = CompressionManager.__init__
    original_queue_init = QueueManager.__init__

    def bridge_init(self, *args, **kwargs):
        original_bridge_init(self, *args, **kwargs)
        bridges.append(self)

    def compression_init(self, *args, **kwargs):
        original_compression_init(self, *args, **kwargs)
        managers.append(self)

    def queue_init(self, *args, **kwargs):
        original_queue_init(self, *args, **kwargs)
        queues.append(self)

    monkeypatch.setattr(Bridge, "__init__", bridge_init)
    monkeypatch.setattr(CompressionManager, "__init__", compression_init)
    monkeypatch.setattr(QueueManager, "__init__", queue_init)
    yield

    for bridge in reversed(bridges):
        bridge._shutting_down = True
        try:
            bridge.compression.shutdown(timeout=2.0)
        except Exception:
            pass
        try:
            bridge.updater.shutdown(timeout=1.0)
        except Exception:
            pass
        try:
            bridge.similarity.shutdown(timeout=1.0)
        except Exception:
            pass
        for manager in (bridge.single_manager, bridge.manager):
            try:
                manager.shutdown(timeout=2.0)
            except Exception:
                pass
        for thread in list(getattr(bridge, "_aux_threads", [])):
            if thread.is_alive() and thread is not threading.current_thread():
                thread.join(timeout=1.0)
    for manager in reversed(managers):
        try:
            manager.shutdown(timeout=2.0)
        except Exception:
            pass
    for queue in reversed(queues):
        try:
            queue.shutdown(timeout=2.0)
        except Exception:
            pass


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
