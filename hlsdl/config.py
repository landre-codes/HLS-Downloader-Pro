"""Configuração central: caminhos, constantes e localização de recursos.

Concentra a lógica de "onde ficam as coisas" que antes estava espalhada em
``main.py``/``worker.py``. Corrige o bug de persistência no binário
PyInstaller ``--onefile``: ``sys._MEIPASS`` é uma pasta temporária gravável
que some ao fechar, então builds congelados sempre usam a pasta do usuário.
"""

from __future__ import annotations

import glob
import os
import shutil
import sys
import tempfile

ORG = "HLSDownloader"
APP_NAME = "HLS Downloader Pro"
APP_ID = "HLS-Downloader-Pro"

# Navegadores suportados por `--cookies-from-browser` do yt-dlp
BROWSERS: list[str] = [
    "chrome",
    "chromium",
    "edge",
    "firefox",
    "opera",
    "vivaldi",
    "brave",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))


def is_frozen() -> bool:
    """True quando rodando empacotado (PyInstaller)."""
    return bool(getattr(sys, "frozen", False))


def resource_dir() -> str:
    """Pasta onde vivem os recursos (QML/JS): a própria pasta do pacote.

    Em dev é ``<repo>/hlsdl``; no PyInstaller é ``_MEIPASS/hlsdl`` (o add-data
    é gravado em ``hlsdl/ui``). ``_MEIPASS`` sozinho apontaria para a raiz.
    """
    return _PKG_DIR


def _dev_root() -> str:
    """Raiz do repositório em desenvolvimento."""
    return os.path.dirname(_PKG_DIR)


def app_dir() -> str:
    """Pasta do executável (build) ou raiz do repositório (dev)."""
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return _dev_root()


def is_portable() -> bool:
    """Modo portátil: settings/tools/log ao lado do executável.

    Ativado por ``--portable`` / ``HLSDL_PORTABLE=1`` ou por um arquivo
    ``portable.flag`` na pasta do executável.
    """
    if os.environ.get("HLSDL_PORTABLE", "").strip().lower() in ("1", "true", "yes"):
        return True
    try:
        return os.path.isfile(os.path.join(app_dir(), "portable.flag"))
    except OSError:
        return False


def user_config_dir() -> str:
    """Pasta de configuração/estado do usuário (sempre gravável)."""
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.path.join(os.path.expanduser("~"), ".config")
    folder = os.path.join(base, "HLSDownloaderPro")
    os.makedirs(folder, exist_ok=True)
    return folder


def settings_path() -> str:
    """Caminho do ``settings.ini``.

    Portátil -> ao lado do executável. Empacotado -> pasta do usuário. Em
    desenvolvimento, tenta ao lado do código e cai para a pasta do usuário se
    não houver permissão de escrita.
    """
    if is_portable():
        return os.path.join(app_dir(), "settings.ini")
    if is_frozen():
        return os.path.join(user_config_dir(), "settings.ini")
    local = os.path.join(_dev_root(), "settings.ini")
    try:
        if os.access(_dev_root(), os.W_OK):
            return local
    except OSError:
        pass
    return os.path.join(user_config_dir(), "settings.ini")


def log_path() -> str:
    """Caminho do arquivo de log."""
    if is_portable():
        return os.path.join(app_dir(), "hls_downloader.log")
    try:
        return os.path.join(user_config_dir(), "hls_downloader.log")
    except OSError:
        return os.path.join(_dev_root(), "hls_downloader.log")


def crash_log_path() -> str:
    """Caminho do log de falhas nativas (faulthandler)."""
    if is_portable():
        return os.path.join(app_dir(), "hlsdl-crash.log")
    try:
        return os.path.join(user_config_dir(), "hlsdl-crash.log")
    except OSError:
        return os.path.join(_dev_root(), "hlsdl-crash.log")


def diagnostics_path() -> str:
    """Onde salvar o relatório de diagnóstico."""
    if not is_frozen():
        target = os.path.join(_dev_root(), "diagnostico-hlsdl.txt")
        try:
            if os.access(_dev_root(), os.W_OK):
                return target
        except OSError:
            pass
    try:
        return os.path.join(user_config_dir(), "diagnostico-hlsdl.txt")
    except OSError:
        return os.path.join(tempfile.gettempdir(), "diagnostico-hlsdl.txt")


def qml_path() -> str:
    """Caminho do arquivo QML principal (tolera os dois layouts de build)."""
    candidates = [
        os.path.join(_PKG_DIR, "ui", "main.qml"),
        os.path.join(getattr(sys, "_MEIPASS", _PKG_DIR), "ui", "main.qml"),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return candidates[0]


def thumbs_dir() -> str:
    """Pasta temporária das miniaturas (apagada ao fechar o app)."""
    return os.path.join(tempfile.gettempdir(), "hlsdlp-thumbs")


def tools_dir() -> str:
    """Pasta de ferramentas baixadas pelo próprio app (yt-dlp/ffmpeg).

    Portátil -> ao lado do executável; caso contrário, na pasta do usuário.
    É adicionada ao PATH em tempo de execução.
    """
    if is_portable():
        folder = os.path.join(app_dir(), "tools")
    else:
        folder = os.path.join(user_config_dir(), "tools")
    os.makedirs(folder, exist_ok=True)
    return folder


def ensure_tools_on_path() -> None:
    """Prepara o PATH para encontrar as ferramentas gerenciadas/detectáveis.

    - No Windows, relê o PATH do registro (uma instalação via winget/choco só
      aparece no PATH depois de reiniciar o processo; aqui refletimos já).
    - Coloca a pasta de ferramentas do app na frente do PATH.
    """
    refresh_path_from_registry()
    folder = tools_dir()
    current = os.environ.get("PATH", "")
    parts = current.split(os.pathsep) if current else []
    if folder not in parts:
        os.environ["PATH"] = folder + os.pathsep + current


def refresh_path_from_registry() -> None:
    """No Windows, recompõe os.environ['PATH'] a partir do registro.

    Corrige o caso clássico em que o winget/choco instala a ferramenta e
    atualiza o PATH do usuário, mas o processo em execução continua com o PATH
    antigo e "não encontra" a ferramenta até reiniciar.
    """
    if os.name != "nt":
        return
    try:
        import winreg
    except ImportError:  # pragma: no cover
        return

    def _read(root, subkey: str) -> str:
        try:
            with winreg.OpenKey(root, subkey) as key:
                value, _ = winreg.QueryValueEx(key, "Path")
                return str(value)
        except OSError:
            return ""

    entries = os.environ.get("PATH", "").split(os.pathsep)
    seen = {e.lower() for e in entries if e}
    for root, subkey in (
        (winreg.HKEY_CURRENT_USER, "Environment"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
    ):
        for raw in _read(root, subkey).split(os.pathsep):
            raw = os.path.expandvars(raw).strip()
            if raw and raw.lower() not in seen:
                entries.append(raw)
                seen.add(raw.lower())
    os.environ["PATH"] = os.pathsep.join(entries)


def extra_bin_dirs() -> list[str]:
    """Pastas extras onde procurar binários (além do PATH)."""
    dirs: list[str] = []
    try:
        dirs.append(tools_dir())
    except OSError:
        pass
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            dirs.append(os.path.join(local, "Microsoft", "WinGet", "Links"))
            dirs.append(os.path.join(local, "Microsoft", "WinGet", "Packages"))
        dirs.append(r"C:\ProgramData\chocolatey\bin")
        dirs.append(os.path.join(os.path.expanduser("~"), "scoop", "shims"))
    return [d for d in dirs if d and os.path.isdir(d)]


def find_binary(name: str) -> str | None:
    """Localiza um executável no PATH e em pastas conhecidas do sistema.

    Em builds empacotados, ferramentas instaladas por winget/choco costumam
    ficar em pastas que não estão no PATH do processo; por isso procuramos
    também nesses locais antes de declarar "não encontrado".
    """
    for exe in (name, name + ".exe"):
        found = shutil.which(exe)
        if found:
            return found
    ext = ".exe" if os.name == "nt" else ""
    for base in extra_bin_dirs():
        for sub in ("", "bin"):
            candidate = os.path.join(base, sub, name + ext)
            if os.path.isfile(candidate):
                return candidate
        # Pacotes do winget ficam aninhados (Gyan.FFmpeg_*/ffmpeg-*/bin/*.exe).
        if base.lower().endswith("packages"):
            try:
                for candidate in glob.glob(os.path.join(base, "**", name + ext), recursive=True):
                    if os.path.isfile(candidate):
                        return candidate
            except OSError:
                pass
    return None


def default_output_folder() -> str:
    """Pasta padrão de downloads: ``~/Downloads/VideoDownloader``."""
    base = os.path.expanduser("~/Downloads")
    if not os.path.isdir(base):
        base = os.path.expanduser("~")
    return os.path.join(base, "VideoDownloader")
