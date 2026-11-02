"""Ponto de entrada do aplicativo.

Responsabilidades:
  - Configurar logging rotativo.
  - Criar o ``QApplication``.
  - Garantir instância única (``QLocalServer``/``QLocalSocket``) e ativar a
    janela existente quando uma segunda instância é aberta.
  - Montar modelo + gerenciador + ponte e carregar o QML.
  - Restaurar a geometria e encerrar os workers de forma graciosa.
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import QObject, QRect, QSettings, QUrl, Signal
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QMessageBox

from . import __version__, config
from .bridge import Bridge
from .config import (
    APP_ID,
    APP_NAME,
    ORG,
    default_output_folder,
    log_path,
    qml_path,
)
from .i18n import tr
from .model import DownloadModel
from .queue import QueueManager
from .services.procutils import cleanup_thumbs

log = logging.getLogger("hlsdl")

# Janela mínima (espelha o QML). A geometria salva só é aplicada se couber.
MIN_W, MIN_H = 940, 620


def setup_logging(verbose: bool = False) -> None:
    """Configura o log rotativo (evita crescimento infinito do arquivo)."""
    level = logging.DEBUG if verbose else logging.INFO
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    root = logging.getLogger()
    root.setLevel(level)
    if root.handlers:
        return
    try:
        handler = RotatingFileHandler(
            log_path(), maxBytes=2_000_000, backupCount=3, encoding="utf-8"
        )
        handler.setFormatter(fmt)
        root.addHandler(handler)
    except OSError:
        root.addHandler(logging.NullHandler())


# ===========================================================================
# Instância única
# ===========================================================================
_LOCK_FILES: list = []


def _acquire_process_lock() -> bool:
    """Adquire um lock de arquivo com trava do SO (liberada se o processo morrer).

    Usado como decisão de instância única: é robusto no Windows (msvcrt) e no
    Linux/macOS (fcntl). O servidor de socket só serve para *ativar* a janela.
    """
    lock_path = os.path.join(tempfile.gettempdir(), "hlsdlp-pro.lock")
    try:
        if os.name == "nt":
            import msvcrt

            fh = open(lock_path, "a+", encoding="utf-8")
            fh.write("x")
            fh.flush()
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fh = open(lock_path, "w", encoding="utf-8")
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    _LOCK_FILES.append(fh)  # mantém o handle aberto durante a vida do app
    return True


class SingleInstance(QObject):
    """Garante uma única instância e permite ativar a janela existente."""

    activated = Signal()

    def __init__(self, name: str, parent: QObject | None = None):
        super().__init__(parent)
        self._name = name
        self._primary = _acquire_process_lock()
        self._server: QLocalServer | None = None
        if self._primary:
            # Somos os donos: sobe um servidor local para receber pedidos de
            # ativação de eventuais segundas instâncias.
            QLocalServer.removeServer(name)
            self._server = QLocalServer(self)
            if self._server.listen(name):
                self._server.newConnection.connect(self._on_connection)

    def is_primary(self) -> bool:
        return self._primary

    def notify_existing(self, timeout: int = 500) -> bool:
        """Pede à instância principal que traga a janela para frente."""
        sock = QLocalSocket()
        sock.connectToServer(self._name)
        if not sock.waitForConnected(timeout):
            return False
        sock.write(b"RAISE")
        sock.flush()
        sock.waitForBytesWritten(timeout)
        sock.disconnectFromServer()
        return True

    def _on_connection(self) -> None:
        if self._server is None:
            return
        conn = self._server.nextPendingConnection()
        if conn is None:
            return
        conn.readyRead.connect(conn.deleteLater)
        conn.disconnected.connect(conn.deleteLater)
        self.activated.emit()


_SINGLE: SingleInstance | None = None


_WINDOWS_MUTEX = None


def _create_windows_mutex(name: str = "HLS-Downloader-Pro-Mutex") -> None:
    """Cria um mutex nomeado detectável pelo ``AppMutex`` do Inno Setup."""
    global _WINDOWS_MUTEX
    if os.name != "nt" or _WINDOWS_MUTEX is not None:
        return
    try:
        import ctypes

        handle = ctypes.windll.kernel32.CreateMutexW(None, False, name)
        if handle:
            _WINDOWS_MUTEX = handle
    except Exception:
        _WINDOWS_MUTEX = None


def _single_instance() -> bool:
    """True se esta instância é a principal; False se já existe outra."""
    global _SINGLE
    if _SINGLE is None:
        _SINGLE = SingleInstance(APP_ID)
    if _SINGLE.is_primary():
        return True
    _SINGLE.notify_existing()
    msg = tr("pt", "already_open")
    try:
        if isinstance(QApplication.instance(), QApplication):
            QMessageBox.information(None, APP_NAME, msg)
    except Exception:
        pass
    sys.stderr.write(msg + "\n")
    return False


# ===========================================================================
# Geometria
# ===========================================================================
def _restore_geometry(window, settings: QSettings) -> None:
    """Aplica a geometria salva (validando que ainda está em alguma tela)."""
    raw = settings.value("window/geometry", "", type=str)
    maximized = settings.value("window/maximized", False, type=bool)
    if raw:
        parts = raw.split(",")
        if len(parts) == 4:
            try:
                x, y, w, h = (int(p) for p in parts)
            except ValueError:
                x = y = w = h = 0
            if w >= MIN_W and h >= MIN_H:
                center = QRect(x, y, w, h).center()
                on_screen = any(
                    screen.availableGeometry().contains(center)
                    for screen in QGuiApplication.screens()
                )
                if on_screen:
                    window.setGeometry(x, y, w, h)
    if maximized:
        window.showMaximized()
    else:
        window.show()


def _raise_window(window) -> None:
    try:
        window.showNormal()
        window.raise_()
        window.requestActivate()
    except Exception:
        pass


# ===========================================================================
# main
# ===========================================================================
def main() -> int:
    if "--portable" in sys.argv:
        os.environ["HLSDL_PORTABLE"] = "1"
        sys.argv = [arg for arg in sys.argv if arg != "--portable"]
    setup_logging("--verbose" in sys.argv)

    app = QApplication(sys.argv)
    _create_windows_mutex()
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(__version__)

    # Fonte limpa e legível (Segoe UI no Windows; padrão do sistema no Linux)
    font = QFont("Segoe UI", 10) if os.name == "nt" else QFont("Sans Serif", 10)
    app.setFont(font)

    if not _single_instance():
        return 0

    # Ferramentas baixadas pelo próprio app (yt-dlp/ffmpeg) entram no PATH.
    try:
        config.ensure_tools_on_path()
    except OSError:
        pass

    # Miniaturas não ficam salvas no disco.
    app.aboutToQuit.connect(cleanup_thumbs)

    outdir = default_output_folder()
    model = DownloadModel([])
    manager = QueueManager(model, outdir=outdir, concurrency=3)
    bridge = Bridge(manager, outdir)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("downloadModel", model)
    engine.rootContext().setContextProperty("bridge", bridge)

    engine.load(QUrl.fromLocalFile(qml_path()))
    if not engine.rootObjects():
        sys.stderr.write("Falha ao carregar main.qml — Qt/QML não pôde inicializar.\n")
        QMessageBox.critical(None, APP_NAME, "Falha ao carregar a interface (main.qml).")
        return 1

    window = engine.rootObjects()[0]
    _restore_geometry(window, bridge._settings)

    if _SINGLE is not None:
        _SINGLE.activated.connect(lambda: _raise_window(window))

    # Encerramento gracioso: cancela downloads e aguarda as threads.
    app.aboutToQuit.connect(lambda: manager.shutdown())

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
