"""
main.py
=======
Ponto de entrada do HLS Downloader Pro.

Responsabilidades:
  - Criar o QApplication (necessário para QClipboard e QFileDialog).
  - Construir o modelo de fila + gerenciador (worker.py).
  - Expor a classe `Bridge` e o modelo como contexto para o QML.
  - Persistir configurações (tema, concorrência, pasta, cookies, geometria)
    em `settings.ini` ao lado do app (QSettings formato INI).
  - Carregar a interface `ui.qml`.
"""

from __future__ import annotations

import os
import shutil
import sys
from typing import List, Optional

from PyQt6.QtCore import QObject, QRect, QSettings, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtWidgets import QApplication, QFileDialog

from worker import DownloadModel, QueueManager, extract_urls

# Pasta do código. Em builds empacotados (PyInstaller --onefile) os arquivos
# ficam extraídos em sys._MEIPASS; no desenvolvimento, ao lado do main.py.
PROJECT_DIR = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))


def _settings_path() -> str:
    """settings.ini ao lado do app; se a pasta não for gravável (ex.: binário
    instalado em /usr/local), usa ~/.config/HLSDownloaderPro (Linux) ou
    %APPDATA%/HLSDownloaderPro (Windows)."""
    local = os.path.join(PROJECT_DIR, "settings.ini")
    try:
        if os.access(PROJECT_DIR, os.W_OK):
            return local
    except OSError:
        pass
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.path.join(os.path.expanduser("~"), ".config")
    base = os.path.join(base, "HLSDownloaderPro")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "settings.ini")


SETTINGS_PATH = _settings_path()

# Navegadores suportados por `--cookies-from-browser` do yt-dlp
BROWSERS: List[str] = [
    "chrome",
    "chromium",
    "edge",
    "firefox",
    "opera",
    "vivaldi",
    "brave",
]


class Bridge(QObject):
    """
    Ponte entre o QML e o backend. O QML chama os `@pyqtSlot` e reage aos
    sinais (`statsChanged`, `notifyText`, `outputFolderChanged`, ...).
    Também persiste as configurações em settings.ini.
    """

    statsChanged = pyqtSignal(int, int, int, int)   # aguardando, baixando, ok, erro
    notifyText = pyqtSignal(str)                    # notificação para o QML (toast)
    outputFolderChanged = pyqtSignal(str)
    darkChanged = pyqtSignal(bool)
    concurrencyChanged = pyqtSignal(int)
    cookiesEnabledChanged = pyqtSignal(bool)
    cookiesBrowserIndexChanged = pyqtSignal(int)
    cookiesFileChanged = pyqtSignal(str)

    def __init__(
        self,
        manager: QueueManager,
        default_outdir: str,
        parent: Optional[QObject] = None,
        settings_path: Optional[str] = None,
    ):
        super().__init__(parent)
        self.manager = manager
        self._settings = QSettings(
            settings_path or SETTINGS_PATH, QSettings.Format.IniFormat
        )

        # -------------------------------------------------- carrega o estado
        self._dark = self._settings.value("theme/dark", True, type=bool)
        self._concurrency = int(self._settings.value("download/concurrency", 3))
        self._concurrency = max(1, min(8, self._concurrency))
        self._output_folder = str(
            self._settings.value("download/folder", default_outdir)
        )
        self._cookies_enabled = self._settings.value("cookies/enabled", False, type=bool)
        self._cookies_browser_index = int(
            self._settings.value("cookies/browser_index", 0)
        )
        self._cookies_file = str(self._settings.value("cookies/file", ""))

        # ------------------------------------------------------- aplica tudo
        manager.statsChanged.connect(self.statsChanged.emit)
        manager.outdirChanged.connect(self.outputFolderChanged.emit)
        manager.outdir = self._output_folder
        manager.setConcurrency(self._concurrency)
        manager.setCookies(self._build_cookies_arg())

        # Detecção de ferramentas externas (exibida como aviso na GUI)
        self.ffmpeg_found = bool(shutil.which("ffmpeg") or shutil.which("ffmpeg.exe"))
        self.ytdlp_found = bool(shutil.which("yt-dlp") or shutil.which("yt-dlp.exe"))

    # ------------------------------------------------------- persistência
    def _save(self, key: str, value) -> None:
        self._settings.setValue(key, value)
        self._settings.sync()

    # ------------------------------------------------------------- atributos QML
    @pyqtProperty(str, notify=outputFolderChanged)
    def outputFolder(self) -> str:
        return self._output_folder

    @pyqtProperty(bool, notify=darkChanged)
    def dark(self) -> bool:
        return self._dark

    @pyqtProperty(int, notify=concurrencyChanged)
    def concurrency(self) -> int:
        return self._concurrency

    @pyqtProperty(bool, notify=cookiesEnabledChanged)
    def cookiesEnabled(self) -> bool:
        return self._cookies_enabled

    @pyqtProperty(int, notify=cookiesBrowserIndexChanged)
    def cookiesBrowserIndex(self) -> int:
        return self._cookies_browser_index

    @pyqtProperty(str, notify=cookiesFileChanged)
    def cookiesFile(self) -> str:
        return self._cookies_file

    @pyqtProperty(bool, constant=True)
    def ffmpegAvailable(self) -> bool:
        return self.ffmpeg_found

    @pyqtProperty(bool, constant=True)
    def ytdlpAvailable(self) -> bool:
        return self.ytdlp_found

    # ---------------------------------------------------------------- slots
    @pyqtSlot(str)
    def addLinks(self, text: str) -> None:
        """Adiciona links colados/importados (um por linha), sem duplicados."""
        added, skipped = self.manager.addText(text)
        if added and skipped:
            self.notifyText.emit(
                f"{added} link(s) adicionados, {skipped} duplicado(s) ignorado(s)."
            )
        elif added:
            self.notifyText.emit(f"{added} link(s) adicionados à fila.")
        elif skipped:
            self.notifyText.emit(f"{skipped} link(s) duplicado(s) ignorado(s).")
        else:
            self.notifyText.emit("Nenhum link válido encontrado.")

    @pyqtSlot()
    def pasteFromClipboard(self) -> None:
        """Lê a área de transferência e adiciona todos os links detectados."""
        text = QApplication.clipboard().text()
        if text.strip():
            self.addLinks(text)
        else:
            self.notifyText.emit("A área de transferência está vazia.")

    @pyqtSlot()
    def importTxt(self) -> None:
        """Abre um diálogo para importar um arquivo .txt com uma URL por linha."""
        path, _ = QFileDialog.getOpenFileName(
            None,
            "Selecionar lista de links (.txt)",
            "",
            "Arquivos de texto (*.txt);;Todos os arquivos (*.*)",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                content = handle.read()
            self.addLinks(content)
        except OSError as exc:
            self.notifyText.emit(f"Falha ao ler o arquivo: {exc}")

    @pyqtSlot()
    def chooseOutputFolder(self) -> None:
        """Abre um diálogo para escolher a pasta de destino dos downloads."""
        path = QFileDialog.getExistingDirectory(
            None, "Escolher pasta de saída", self._output_folder
        )
        if path:
            self._output_folder = path
            self.manager.setOutdir(path)
            self._save("download/folder", path)
            self.outputFolderChanged.emit(path)
            self.notifyText.emit(f"Pasta de saída: {path}")

    @pyqtSlot(int)
    def setConcurrency(self, n: int) -> None:
        n = max(1, min(8, int(n)))
        if n == self._concurrency:
            return
        self._concurrency = n
        self.manager.setConcurrency(n)
        self._save("download/concurrency", n)
        self.concurrencyChanged.emit(n)

    @pyqtSlot(bool)
    def setDark(self, value: bool) -> None:
        value = bool(value)
        if value == self._dark:
            return
        self._dark = value
        self._save("theme/dark", value)
        self.darkChanged.emit(value)

    # -------------------------------------------------------------- cookies
    def _build_cookies_arg(self) -> str:
        """Converte a configuração atual em "browser:<nome>" / "file:<path>" / ""."""
        if not self._cookies_enabled:
            return ""
        if self._cookies_file.strip():
            return "file:" + self._cookies_file.strip()
        if 0 <= self._cookies_browser_index < len(BROWSERS):
            return "browser:" + BROWSERS[self._cookies_browser_index]
        return ""

    def _push_cookies(self) -> None:
        self.manager.setCookies(self._build_cookies_arg())

    @pyqtSlot(bool)
    def setCookiesEnabled(self, value: bool) -> None:
        value = bool(value)
        if value == self._cookies_enabled:
            return
        self._cookies_enabled = value
        self._save("cookies/enabled", value)
        self._push_cookies()
        self.cookiesEnabledChanged.emit(value)

    @pyqtSlot(int)
    def setCookiesBrowserIndex(self, index: int) -> None:
        index = max(0, min(len(BROWSERS) - 1, int(index)))
        if index == self._cookies_browser_index:
            return
        self._cookies_browser_index = index
        self._save("cookies/browser_index", index)
        self._push_cookies()
        self.cookiesBrowserIndexChanged.emit(index)

    @pyqtSlot(str)
    def setCookiesFile(self, path: str) -> None:
        path = (path or "").strip()
        if path == self._cookies_file:
            return
        self._cookies_file = path
        self._save("cookies/file", path)
        self._push_cookies()
        self.cookiesFileChanged.emit(path)

    @pyqtSlot()
    def chooseCookiesFile(self) -> None:
        """Seleciona um arquivo de cookies no formato Netscape (cookies.txt)."""
        path, _ = QFileDialog.getOpenFileName(
            None,
            "Selecionar arquivo de cookies (Netscape)",
            "",
            "Arquivos de cookie (*.txt);;Todos os arquivos (*.*)",
        )
        if path:
            self.setCookiesFile(path)

    # -------------------------------------------------------- janela/geometria
    @pyqtSlot(int, int, int, int, bool)
    def saveGeometry(self, x: int, y: int, w: int, h: int, maximized: bool) -> None:
        self._save("window/geometry", f"{x},{y},{w},{h}")
        self._save("window/maximized", maximized)

    @pyqtSlot()
    def startQueue(self) -> None:
        self.manager.start()
        self.notifyText.emit("Fila iniciada.")

    @pyqtSlot()
    def cancelAll(self) -> None:
        self.manager.cancelAll()
        self.notifyText.emit("Downloads cancelados.")

    @pyqtSlot(int)
    def cancelItem(self, row: int) -> None:
        self.manager.cancelItem(row)
        self.notifyText.emit("Item cancelado.")

    @pyqtSlot(int, str)
    def editUrl(self, row: int, new_url: str) -> bool:
        ok = self.manager.editUrl(row, new_url)
        if ok:
            self.notifyText.emit("Link atualizado e reenfileirado.")
        else:
            self.notifyText.emit(
                "Não foi possível atualizar (em andamento ou duplicado)."
            )
        return ok

    @pyqtSlot(str)
    def copyLink(self, url: str) -> None:
        QGuiApplication.clipboard().setText(url)
        self.notifyText.emit("Link copiado para a área de transferência.")

    @pyqtSlot()
    def clearFinished(self) -> None:
        self.manager.clearFinished()

    @pyqtSlot()
    def clearAll(self) -> None:
        self.manager.clearAll()

    @pyqtSlot(str)
    def openDownloadPath(self, path: str) -> None:
        """Abre o gerenciador de arquivos na pasta onde o arquivo foi salvo."""
        import subprocess

        folder = os.path.dirname(path)
        if not os.path.isdir(folder):
            return
        if os.name == "nt":
            subprocess.Popen(["explorer", folder])
        else:
            subprocess.Popen(["xdg-open", folder])


def default_output_folder() -> str:
    """Pasta padrão: ~/Downloads/VideoDownloader (com fallback para temp)."""
    base = os.path.expanduser("~/Downloads")
    if not os.path.isdir(base):
        base = os.path.expanduser("~")
    return os.path.join(base, "VideoDownloader")


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
            if w >= 800 and h >= 500:
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


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("HLS Downloader Pro")
    app.setOrganizationName("HLSDownloader")
    app.setApplicationDisplayName("HLS Downloader Pro")

    # Fonte limpa e legível (Segoe UI no Windows; padrão do sistema no Linux)
    font = QFont("Segoe UI", 10) if os.name == "nt" else QFont("Sans Serif", 10)
    app.setFont(font)

    outdir = default_output_folder()
    model = DownloadModel([])
    manager = QueueManager(model, outdir=outdir, concurrency=3)
    bridge = Bridge(manager, outdir)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("downloadModel", model)
    engine.rootContext().setContextProperty("bridge", bridge)

    qml_file = os.path.join(PROJECT_DIR, "ui.qml")
    engine.load(QUrl.fromLocalFile(qml_file))

    if not engine.rootObjects():
        sys.stderr.write("Falha ao carregar ui.qml — Qt/QML não pôde inicializar.\n")
        return 1

    window = engine.rootObjects()[0]
    _restore_geometry(window, bridge._settings)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
