"""Gerenciador de dependências externas.

Detecta, instala e atualiza as ferramentas de que o app precisa, **sem exigir
conhecimento de Python** do usuário:

* ``yt-dlp`` — baixado da release oficial (binário autônomo) para uma pasta do
  usuário e colocado no PATH. Em ambiente de desenvolvimento, pode ser
  atualizado via pip.
* ``ffmpeg``/``ffprobe`` — instalado pelo gerenciador de pacotes do sistema
  quando disponível; caso contrário, baixado como build estático.
* ``requests`` e ``beautifulsoup4`` — em build empacotado já vêm embutidos; em
  ambiente de desenvolvimento, atualizáveis via pip.
* ``PySide6`` — embutido no build empacotado.

A instalação **sempre exige confirmação do usuário** e roda em thread separada,
com a saída transmitida para a interface.
"""

from __future__ import annotations

import logging
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib.request
import zipfile
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal

from . import config
from .services.procutils import popen_kwargs, spawn_kwargs, terminate_tree

log = logging.getLogger("hlsdl")

USER_AGENT = "HLS-Downloader-Pro"

YTDLP_RELEASE = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/"
# Canais de release do yt-dlp (variantes oferecidas na interface).
YTDLP_CHANNELS = {
    "stable": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/",
    "nightly": "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest/download/",
    "master": "https://github.com/yt-dlp/yt-dlp-master-builds/releases/latest/download/",
}
YTDLP_VARIANTS = tuple(YTDLP_CHANNELS)
FFMPEG_WIN_ZIP = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
FFMPEG_LINUX_TAR = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
FFMPEG_MAC = "https://evermeet.cx/ffmpeg/getrelease/{name}/zip"


@dataclass
class ToolSpec:
    key: str
    name: str
    kind: str  # "ytdlp" | "binary" | "pip"
    module: str | None = None
    dist: str | None = None
    bins: tuple = ()
    required: bool = False
    description: str = ""


SPECS: list[ToolSpec] = [
    ToolSpec("ytdlp", "yt-dlp", "ytdlp", module="yt_dlp", dist="yt-dlp", bins=("yt-dlp",),
             required=True, description="Motor principal de download"),
    ToolSpec("ffmpeg", "ffmpeg", "binary", bins=("ffmpeg", "ffprobe"), required=True,
             description="Merge de vídeo+áudio, fallback HLS e miniaturas"),
    ToolSpec("requests", "requests", "pip", module="requests", dist="requests", required=False,
             description="Raspagem do HTML (fallback)"),
    ToolSpec("bs4", "beautifulsoup4", "pip", module="bs4", dist="beautifulsoup4", required=False,
             description="Parsing do HTML (fallback)"),
    ToolSpec("pyside6", "PySide6", "pip", module="PySide6", dist="PySide6", required=True,
             description="Interface gráfica (Qt 6)"),
]


@dataclass
class ToolStatus:
    key: str
    name: str
    kind: str
    description: str
    required: bool
    found: bool = False
    version: str = ""
    path: str = ""
    strategy: str = "none"      # download | package | pip | bundled | none
    installable: bool = False
    updateable: bool = False

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "kind": self.kind,
            "description": self.description,
            "required": self.required,
            "found": self.found,
            "version": self.version,
            "path": self.path,
            "strategy": self.strategy,
            "installable": self.installable,
            "updateable": self.updateable,
        }


# ---------------------------------------------------------------------------
# Detecção
# ---------------------------------------------------------------------------
def _module_found(name: str | None) -> bool:
    if not name:
        return False
    try:
        import importlib.util

        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def _pip_available() -> bool:
    if config.is_frozen():
        return False
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True, timeout=20, **popen_kwargs(),
        )
        return True
    except Exception:
        return False


def _module_version(dist: str) -> str:
    try:
        from importlib.metadata import version

        return version(dist)
    except Exception:
        return ""


def _binary_path(spec: ToolSpec) -> str:
    for name in spec.bins:
        found = config.find_binary(name)
        if found:
            return found
    return ""


def _binary_version(spec: ToolSpec, path: str) -> str:
    if not path:
        return ""
    try:
        if spec.key == "ffmpeg":
            out = subprocess.run(
                [path, "-version"], capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace", **popen_kwargs(),
            )
            lines = (out.stdout or "").splitlines()
            if lines:
                return lines[0].replace("ffmpeg version ", "").split(" ")[0]
        else:
            out = subprocess.run(
                [path, "--version"], capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace", **popen_kwargs(),
            )
            return (out.stdout or "").splitlines()[0].strip()
    except Exception:
        return ""
    return ""


def _ffmpeg_package_command() -> list[str] | None:
    """Comando do gerenciador de pacotes para instalar o ffmpeg (ou None)."""
    if os.name == "nt":
        if shutil.which("winget"):
            return ["winget", "install", "--id", "Gyan.FFmpeg", "-e", "--force",
                    "--accept-source-agreements", "--accept-package-agreements"]
        if shutil.which("choco"):
            return ["choco", "install", "ffmpeg", "-y"]
        if shutil.which("scoop"):
            return ["scoop", "install", "ffmpeg"]
        return None
    if sys.platform == "darwin":
        if shutil.which("brew"):
            return ["brew", "install", "ffmpeg"]
        return None
    prefix = ["pkexec"] if shutil.which("pkexec") else (["sudo"] if shutil.which("sudo") else [])
    if shutil.which("apt-get"):
        return prefix + ["apt-get", "install", "-y", "ffmpeg"]
    if shutil.which("dnf"):
        return prefix + ["dnf", "install", "-y", "ffmpeg"]
    if shutil.which("pacman"):
        return prefix + ["pacman", "-S", "--noconfirm", "ffmpeg"]
    return None


def _can_download_ffmpeg() -> bool:
    return os.name == "nt" or sys.platform in ("linux", "darwin")


def _strategy(spec: ToolSpec, variant: str = "stable") -> str:
    """Estratégia de instalação/atualização para uma ferramenta."""
    if spec.key == "ytdlp":
        # O canal "master" só existe como build do GitHub (não vai ao PyPI).
        if variant == "master":
            return "download"
        if not config.is_frozen() and _pip_available():
            return "pip"          # dev: mantém o pacote atualizado
        return "download"         # empacotado: binário autônomo
    if spec.kind == "binary":
        if os.name == "nt":
            # Windows: prefere o build estático gerenciado pelo app. Evita o
            # falso "já instalado" do winget e o PATH que só atualiza após
            # reiniciar o programa.
            if _can_download_ffmpeg():
                return "download"
            return "package" if _ffmpeg_package_command() else "none"
        # Linux/macOS: o gerenciador de pacotes do sistema é o caminho natural.
        if _ffmpeg_package_command():
            return "package"
        return "download" if _can_download_ffmpeg() else "none"
    # outros pacotes pip
    if config.is_frozen():
        return "bundled"
    return "pip" if _pip_available() else "none"


# ---------------------------------------------------------------------------
# Gerenciador
# ---------------------------------------------------------------------------
class DependencyManager(QObject):
    """Detecta e instala dependências, reportando por sinais Qt."""

    checked = Signal(list)
    installStarted = Signal(str)
    installOutput = Signal(str)
    installFinished = Signal(str, bool, str)  # key, ok, name

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._busy = False
        self._cancel = False
        self._proc = None
        self.variant = "stable"  # canal do yt-dlp: stable | nightly | master

    def set_variant(self, variant: str) -> None:
        if variant in YTDLP_VARIANTS and variant != self.variant:
            self.variant = variant
            self.check_all()

    def _ytdlp_base_url(self) -> str:
        return YTDLP_CHANNELS.get(self.variant, YTDLP_RELEASE)

    # ---------------------------------------------------------------- detecção
    def detect(self, spec: ToolSpec) -> ToolStatus:
        status = ToolStatus(
            key=spec.key, name=spec.name, kind=spec.kind,
            description=spec.description, required=spec.required,
        )
        if spec.kind == "pip":
            status.found = _module_found(spec.module or spec.dist)
            if status.found:
                status.version = _module_version(spec.dist or "")
        elif spec.kind == "ytdlp":
            # Disponível como binário autônomo OU como módulo Python (dev).
            binary = _binary_path(spec)
            module = _module_found(spec.module)
            status.found = bool(binary) or module
            if binary:
                status.path = binary
                status.version = _binary_version(spec, binary)
            elif module:
                status.version = _module_version(spec.dist or "")
        else:
            path = _binary_path(spec)
            status.found = bool(path)
            status.path = path
            if path:
                status.version = _binary_version(spec, path)
        strategy = _strategy(spec, self.variant)
        status.strategy = strategy
        status.installable = strategy in ("download", "package", "pip")
        status.updateable = status.found and status.installable
        return status

    def check_all(self) -> list[dict]:
        result = [self.detect(spec).to_dict() for spec in SPECS]
        self.checked.emit(result)
        return result

    def essentials_present(self) -> bool:
        return not self.missing_required()

    def missing_required(self) -> list[str]:
        return [s.name for s in SPECS if s.required and not self.detect(s).found]

    # -------------------------------------------------------------- instalação
    def _spec(self, key: str) -> ToolSpec | None:
        return next((s for s in SPECS if s.key == key), None)

    def install(self, key: str) -> bool:
        """Inicia a instalação/atualização de ``key``. Retorna False se ocupado."""
        if self._busy or self._cancel:
            return False
        spec = self._spec(key)
        if spec is None:
            return False
        job = self._job_for(spec)
        if job is None:
            self.installFinished.emit(key, False, spec.name)
            return False
        self._busy = True
        self.installStarted.emit(key)
        threading.Thread(target=self._run_job, args=(key, spec.name, job), daemon=True).start()
        return True

    def _job_for(self, spec: ToolSpec):
        strategy = _strategy(spec, self.variant)
        if strategy == "download":
            if spec.key == "ytdlp":
                return self._install_ytdlp
            return self._install_ffmpeg_download
        if strategy in ("pip", "package"):
            cmd = self._command_for(spec)
            if not cmd:
                return None
            return lambda: self._run_install(cmd)
        return None

    def _command_for(self, spec: ToolSpec) -> list[str] | None:
        if spec.kind == "ytdlp":
            if not _pip_available():
                return None
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade"]
            if self.variant == "nightly":
                cmd += ["--pre"]
            return cmd + ["yt-dlp"]
        if spec.kind == "pip":
            if not _pip_available():
                return None
            return [sys.executable, "-m", "pip", "install", "--upgrade", spec.dist or spec.name]
        return _ffmpeg_package_command()

    def _run_job(self, key: str, name: str, job) -> None:
        ok = False
        try:
            ok = bool(job())
        except Exception as exc:
            log.exception("falha instalando %s", name)
            self.installOutput.emit(f"erro: {exc}")
        finally:
            self._busy = False
            self.installFinished.emit(key, ok, name)
            self.check_all()

    def _run_install(self, cmd: list[str]) -> bool:
        log.info("instalando: %s", " ".join(cmd))
        self.installOutput.emit(f"$ {' '.join(cmd)}")
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
                **spawn_kwargs(),
            )
            self._proc = proc
            assert proc.stdout is not None
            for line in proc.stdout:
                if self._cancel:
                    terminate_tree(proc)
                    break
                self.installOutput.emit(line.rstrip("\n"))
            rc = proc.wait()
            if rc == 0:
                # A ferramenta pode ter sido instalada em pasta nova: reflete
                # no PATH e nas pastas conhecidas antes de re-detectar.
                config.ensure_tools_on_path()
            return rc == 0 and not self._cancel
        except FileNotFoundError:
            self.installOutput.emit(f"{cmd[0]}: executável não encontrado")
            return False
        finally:
            self._proc = None

    def cancel(self) -> None:
        """Encerra a instalação em andamento (chamado ao fechar o app)."""
        self._cancel = True
        terminate_tree(self._proc)

    # -------------------------------------------------------------- download
    def _download(self, url: str, dest: str) -> None:
        self.installOutput.emit(f"Baixando {url}")
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as fh:
            total = resp.headers.get("Content-Length")
            total = int(total) if total else 0
            done = 0
            last_report = 0
            while True:
                if self._cancel:
                    raise RuntimeError("cancelado")
                chunk = resp.read(262144)
                if not chunk:
                    break
                fh.write(chunk)
                done += len(chunk)
                if total and done - last_report >= 5 * 1024 * 1024:
                    last_report = done
                    self.installOutput.emit(f"... {done * 100 // total}%")

    def _make_executable(self, path: str) -> None:
        if os.name != "nt":
            os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def _install_ytdlp(self) -> bool:
        name = "yt-dlp.exe" if os.name == "nt" else "yt-dlp"
        if sys.platform == "darwin":
            asset = "yt-dlp_macos"
        elif os.name == "nt":
            asset = "yt-dlp.exe"
        else:
            asset = "yt-dlp"
        target = os.path.join(config.tools_dir(), name)
        tmp = target + ".download"
        self._download(self._ytdlp_base_url() + asset, tmp)
        os.replace(tmp, target)
        self._make_executable(target)
        ok = os.path.isfile(target) and os.path.getsize(target) > 0
        self.installOutput.emit(f"yt-dlp instalado em {target}" if ok else "falha ao baixar yt-dlp")
        if ok:
            config.ensure_tools_on_path()
        return ok

    def _extract_members(self, archive: str, wanted: set, target_dir: str) -> set:
        found: set = set()
        if archive.endswith(".zip"):
            with zipfile.ZipFile(archive) as zf:
                for info in zf.infolist():
                    base = os.path.basename(info.filename)
                    if base in wanted:
                        out = os.path.join(target_dir, base)
                        with zf.open(info) as src, open(out, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        self._make_executable(out)
                        found.add(base)
        else:
            with tarfile.open(archive, "r:xz") as tf:
                for member in tf.getmembers():
                    base = os.path.basename(member.name)
                    if member.isfile() and base in wanted:
                        src = tf.extractfile(member)
                        if src is None:
                            continue
                        out = os.path.join(target_dir, base)
                        with src, open(out, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        self._make_executable(out)
                        found.add(base)
        return found

    def _install_ffmpeg_download(self) -> bool:
        target_dir = config.tools_dir()
        tmp_dir = tempfile.mkdtemp(prefix="hlsdl-ffmpeg-")
        try:
            if os.name == "nt":
                archive = os.path.join(tmp_dir, "ffmpeg.zip")
                self._download(FFMPEG_WIN_ZIP, archive)
                found = self._extract_members(archive, {"ffmpeg.exe", "ffprobe.exe"}, target_dir)
                needed = "ffmpeg.exe"
            elif sys.platform == "darwin":
                found = set()
                for name in ("ffmpeg", "ffprobe"):
                    archive = os.path.join(tmp_dir, f"{name}.zip")
                    self._download(FFMPEG_MAC.format(name=name), archive)
                    found |= self._extract_members(archive, {name}, target_dir)
                needed = "ffmpeg"
            else:
                archive = os.path.join(tmp_dir, "ffmpeg.tar.xz")
                self._download(FFMPEG_LINUX_TAR, archive)
                found = self._extract_members(archive, {"ffmpeg", "ffprobe"}, target_dir)
                needed = "ffmpeg"
            ok = needed in found
            if ok:
                config.ensure_tools_on_path()
                spec = next(s for s in SPECS if s.key == "ffmpeg")
                version = _binary_version(spec, config.find_binary("ffmpeg") or "")
                self.installOutput.emit(
                    f"ffmpeg pronto (v{version}) em {target_dir}" if version
                    else f"ffmpeg pronto em {target_dir}"
                )
            else:
                self.installOutput.emit("falha ao extrair ffmpeg")
            return ok
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # -------------------------------------------------------------- atualização
    def update_all(self) -> None:
        """Atualiza em sequência todas as ferramentas atualizáveis."""
        def worker() -> None:
            for spec in SPECS:
                if self._cancel:
                    break
                if not self.detect(spec).found:
                    continue
                job = self._job_for(spec)
                if job is None:
                    continue
                while self._busy and not self._cancel:
                    time.sleep(0.2)
                if self._cancel:
                    break
                self._busy = True
                self.installStarted.emit(spec.key)
                self._run_job(spec.key, spec.name, job)

        threading.Thread(target=worker, daemon=True).start()

    def install_missing_required(self) -> None:
        """Instala, em sequência, todas as ferramentas obrigatórias ausentes."""
        def worker() -> None:
            for spec in SPECS:
                if self._cancel:
                    break
                if not spec.required or self.detect(spec).found:
                    continue
                job = self._job_for(spec)
                if job is None:
                    continue
                while self._busy and not self._cancel:
                    time.sleep(0.2)
                if self._cancel:
                    break
                self._busy = True
                self.installStarted.emit(spec.key)
                self._run_job(spec.key, spec.name, job)

        threading.Thread(target=worker, daemon=True).start()
