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

import faulthandler
import logging
import os
import platform
import sys
import tempfile
import threading
import traceback
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import (
    QObject,
    QRect,
    QSettings,
    Qt,
    QtMsgType,
    QUrl,
    Signal,
    qInstallMessageHandler,
)
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
    app_dir,
    crash_log_path,
    default_output_folder,
    is_frozen,
    is_portable,
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

_LOG_CONFIGURED = False
_CRASH_FILE = None
_QT_HANDLER = None


def _qt_message_level(mode: QtMsgType) -> int:
    """Converte o nível de mensagem do Qt para o nível de logging."""
    return {
        QtMsgType.QtDebugMsg: logging.DEBUG,
        QtMsgType.QtInfoMsg: logging.INFO,
        QtMsgType.QtWarningMsg: logging.WARNING,
        QtMsgType.QtCriticalMsg: logging.ERROR,
        QtMsgType.QtFatalMsg: logging.CRITICAL,
    }.get(mode, logging.INFO)


def _qt_message_handler(mode, context, message) -> None:
    """Registra avisos do Qt/QML no log (importante no build sem console)."""
    logger = logging.getLogger("qt")
    # Aviso benigno do Qt ao montar o SwipeView de 5 páginas; não afeta a UI.
    if "Window.window only supports types derived from Item" in message:
        logger.debug("aviso Qt ignorado: %s", message)
        return
    level = _qt_message_level(mode)
    if context is not None and getattr(context, "file", ""):
        logger.log(level, "%s (%s:%s)", message, context.file, context.line)
    else:
        logger.log(level, "%s", message)
    if mode == QtMsgType.QtFatalMsg:
        try:
            stream = sys.__stderr__
            if stream is not None:
                stream.write(message + "\n")
                stream.flush()
        except Exception:
            pass
        os.abort()


def _log_unhandled(exc_type, exc_value, exc_tb) -> None:
    """Hook global para exceções não tratadas na thread principal."""
    logging.getLogger("hlsdl").critical(
        "exceção não tratada", exc_info=(exc_type, exc_value, exc_tb)
    )
    try:
        traceback.print_exception(exc_type, exc_value, exc_tb)
    except Exception:
        pass


def _thread_excepthook(args) -> None:
    """Hook para exceções não tratadas em threads de download/compressão."""
    thread_name = getattr(getattr(args, "thread", None), "name", "?")
    logging.getLogger("hlsdl").critical(
        "exceção não tratada na thread %s",
        thread_name,
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )


def _enable_crash_log() -> None:
    """Ativa o faulthandler em um arquivo (falhas nativas do Qt/ffmpeg)."""
    global _CRASH_FILE
    candidates = []
    if not is_frozen():
        candidates.append(os.path.join(app_dir(), "hlsdl-crash.log"))
    try:
        candidates.append(crash_log_path())
    except OSError:
        pass
    for candidate in dict.fromkeys(candidates):
        try:
            _CRASH_FILE = open(candidate, "a", encoding="utf-8", buffering=1)
            faulthandler.enable(file=_CRASH_FILE, all_threads=True)
            return
        except OSError:
            _CRASH_FILE = None


def setup_logging(verbose: bool = False) -> None:
    """Configura logs rotativos, crash log, hooks e mensagens do Qt/QML."""
    global _LOG_CONFIGURED
    if _LOG_CONFIGURED:
        return
    _LOG_CONFIGURED = True

    level = logging.DEBUG if verbose else logging.INFO
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    root = logging.getLogger()
    root.setLevel(level)

    destinations: list[str] = []
    try:
        destinations.append(log_path())
    except OSError:
        pass
    if not is_frozen():
        dev_log = os.path.join(app_dir(), "hls_downloader.log")
        if os.path.normcase(dev_log) not in {os.path.normcase(p) for p in destinations}:
            destinations.append(dev_log)

    for path in dict.fromkeys(destinations):
        try:
            handler = RotatingFileHandler(
                path, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
            )
            handler.setFormatter(fmt)
            root.addHandler(handler)
        except OSError:
            continue
    if not root.handlers:
        root.addHandler(logging.NullHandler())

    try:
        stream = logging.StreamHandler()
        stream.setFormatter(fmt)
        root.addHandler(stream)
    except Exception:
        pass

    _enable_crash_log()
    sys.excepthook = _log_unhandled
    try:
        threading.excepthook = _thread_excepthook
    except Exception:
        pass
    global _QT_HANDLER
    try:
        _QT_HANDLER = qInstallMessageHandler(_qt_message_handler)
    except Exception:
        _QT_HANDLER = None

    log.info(
        "iniciando %s %s | python=%s | frozen=%s | portable=%s",
        APP_NAME,
        __version__,
        platform.python_version(),
        is_frozen(),
        is_portable(),
    )


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
def _clamp_geometry(x: int, y: int, w: int, h: int) -> tuple[int, int, int, int] | None:
    """Encaixa a geometria na tela disponível.

    Protege contra geometrias salvas em outra escala/DPI (ex.: janela lógica
    de 1920 px em uma tela que, com escala 110%, só oferece 1745 px).
    """
    center = QRect(x, y, w, h).center()
    for screen in QGuiApplication.screens():
        available = screen.availableGeometry()
        if not available.contains(center):
            continue
        width = max(1, min(w, available.width()))
        height = max(1, min(h, available.height()))
        left = max(available.x(), min(x, available.x() + available.width() - width))
        top = max(available.y(), min(y, available.y() + available.height() - height))
        return left, top, width, height
    return None


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
                geometry = _clamp_geometry(x, y, w, h)
                if geometry:
                    window.setGeometry(*geometry)
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
# Escala da interface
# ===========================================================================
UI_SCALE_BASE_WIDTH = 1600.0
UI_SCALE_MIN = 1.0
UI_SCALE_MAX = 1.28


def compute_ui_scale(width: int) -> float:
    """Escala global modesta a partir da largura lógica da tela.

    A ideia é aumentar fonte, ícones e espaçamentos juntos (via
    ``QT_SCALE_FACTOR``), em vez de só a fonte — o que desalinharia as
    tabelas. Telas até ~1600 px ficam em 100%; 1080p ganha ~10%; 1440p
    ~26%; acima disso o ganho é limitado a 128% para não estourar layouts.
    """
    if width <= 0:
        return UI_SCALE_MIN
    scale = (width / UI_SCALE_BASE_WIDTH) ** 0.5
    return round(max(UI_SCALE_MIN, min(UI_SCALE_MAX, scale)), 2)


def _system_screen_width() -> int:
    """Largura lógica da tela no Windows (0 quando indisponível)."""
    if os.name != "nt":
        return 0
    try:
        import ctypes

        return int(ctypes.windll.user32.GetSystemMetrics(0))
    except Exception:
        return 0


def apply_ui_scale(argv: list[str] | None = None) -> float:
    """Aplica a escala antes do ``QApplication`` (o Qt lê no startup).

    Aceita ``--ui-scale 1.25`` / ``--ui-scale=1.25`` ou a variável
    ``HLSDL_UI_SCALE`` para sobrescrever a detecção automática.
    """
    args = sys.argv if argv is None else argv
    override = os.environ.get("HLSDL_UI_SCALE", "").strip()
    explicit = bool(override)
    for index, arg in enumerate(args):
        if arg == "--ui-scale" and index + 1 < len(args):
            override = args[index + 1]
            explicit = True
            del args[index:index + 2]
            break
        if arg.startswith("--ui-scale="):
            override = arg.split("=", 1)[1]
            explicit = True
            del args[index]
            break

    scale = compute_ui_scale(_system_screen_width())
    if explicit:
        try:
            scale = max(0.75, min(2.0, float(override.replace(",", "."))))
        except ValueError:
            pass

    if (explicit or scale > UI_SCALE_MIN) and "QT_SCALE_FACTOR" not in os.environ:
        os.environ["QT_SCALE_FACTOR"] = f"{scale:.2f}"
    return scale


# ===========================================================================
# main
# ===========================================================================
def _ensure_std_streams() -> None:
    """Em build --windowed, sys.stdout/stderr podem ser None."""
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")


def main() -> int:
    _ensure_std_streams()
    if "--version" in sys.argv:
        print(f"HLS Downloader Pro {__version__}")
        return 0
    if "--portable" in sys.argv:
        os.environ["HLSDL_PORTABLE"] = "1"
        sys.argv = [arg for arg in sys.argv if arg != "--portable"]
    apply_ui_scale()
    if "--diagnose" in sys.argv:
        from .diagnostics import run as run_diagnostics

        return run_diagnostics()
    setup_logging("--verbose" in sys.argv)

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
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
    engine.rootContext().setContextProperty("compressionModel", bridge.compression.model)
    engine.rootContext().setContextProperty("bridge", bridge)

    engine.load(QUrl.fromLocalFile(qml_path()))
    if not engine.rootObjects():
        log.critical("falha ao carregar main.qml")
        sys.stderr.write("Falha ao carregar main.qml — Qt/QML não pôde inicializar.\n")
        QMessageBox.critical(None, APP_NAME, "Falha ao carregar a interface (main.qml).")
        return 1

    window = engine.rootObjects()[0]
    _restore_geometry(window, bridge._settings)

    if _SINGLE is not None:
        _SINGLE.activated.connect(lambda: _raise_window(window))

    # Encerramento gracioso: cancela downloads/playlist/instalação e aguarda.
    app.aboutToQuit.connect(bridge.shutdown)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
