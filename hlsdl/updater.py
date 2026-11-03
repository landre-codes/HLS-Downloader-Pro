"""Verificação e download de atualizações via GitHub Releases.

Fluxo: consulta a última release, compara a versão (SemVer), baixa o
instalador e valida o SHA-256 publicado em ``SHA256SUMS-windows.txt``.
O Inno Setup é executado em modo silencioso com ``/CLOSEAPPLICATIONS``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import urllib.request

from PySide6.QtCore import QObject, Signal

from . import __version__, config

log = logging.getLogger("hlsdl")

GITHUB_REPO = "landre-codes/HLS-Downloader-Pro"
API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
USER_AGENT = "HLS-Downloader-Pro"


def version_tuple(value: str) -> tuple[int, ...]:
    """Converte "v1.3.1" em (1, 3, 1) para comparação."""
    cleaned = (value or "").strip().lstrip("vV")
    parts = []
    for part in cleaned.split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts) or (0,)


def _get_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


class Updater(QObject):
    checkingChanged = Signal(bool)
    checked = Signal(dict)
    downloadProgress = Signal(int)
    ready = Signal(str)
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._busy = False

    # ------------------------------------------------------------------ check
    def check(self) -> None:
        if self._busy:
            return
        self._busy = True
        self.checkingChanged.emit(True)
        threading.Thread(target=self._check, daemon=True).start()

    def _check(self) -> None:
        try:
            data = _get_json(API_LATEST)
            latest = str(data.get("tag_name") or "").lstrip("vV")
            assets = data.get("assets") or []
            installer = next(
                (a for a in assets if str(a.get("name", "")).endswith("-setup.exe")),
                None,
            )
            checksums = next(
                (a for a in assets if a.get("name") == "SHA256SUMS-windows.txt"),
                None,
            )
            info = {
                "available": version_tuple(latest) > version_tuple(__version__),
                "latest": latest,
                "current": __version__,
                "notes": str(data.get("body") or ""),
                "html_url": str(data.get("html_url") or ""),
                "installer_url": str((installer or {}).get("browser_download_url") or ""),
                "installer_name": str((installer or {}).get("name") or ""),
                "checksums_url": str((checksums or {}).get("browser_download_url") or ""),
            }
            self.checked.emit(info)
        except Exception as exc:
            log.warning("falha ao verificar atualizações: %s", exc)
            self.failed.emit(str(exc))
        finally:
            self._busy = False
            self.checkingChanged.emit(False)

    # --------------------------------------------------------------- download
    def download_and_verify(self, info: dict) -> None:
        if self._busy:
            return
        if not info.get("installer_url") or not info.get("checksums_url"):
            self.failed.emit("missing_assets")
            return
        self._busy = True
        self.checkingChanged.emit(True)
        threading.Thread(target=self._download, args=(info,), daemon=True).start()

    def _download(self, info: dict) -> None:
        try:
            folder = os.path.join(config.user_config_dir(), "updates")
            os.makedirs(folder, exist_ok=True)
            name = info.get("installer_name") or "HLS-Downloader-Pro-setup.exe"
            destination = os.path.join(folder, name)
            request = urllib.request.Request(
                info["installer_url"], headers={"User-Agent": USER_AGENT}
            )
            with urllib.request.urlopen(request, timeout=120) as response, open(destination, "wb") as fh:
                total = int(response.headers.get("Content-Length") or 0)
                done = 0
                last = -1
                while True:
                    chunk = response.read(262144)
                    if not chunk:
                        break
                    fh.write(chunk)
                    done += len(chunk)
                    if total:
                        pct = int(done * 100 / total)
                        if pct != last:
                            last = pct
                            self.downloadProgress.emit(pct)

            expected = self._expected_hash(info["checksums_url"], name)
            if not expected:
                self.failed.emit("missing_checksum")
                return
            actual = self._sha256(destination)
            if actual.lower() != expected.lower():
                self.failed.emit("checksum_mismatch")
                return
            self.ready.emit(destination)
        except Exception as exc:
            log.warning("falha ao baixar atualização: %s", exc)
            self.failed.emit(str(exc))
        finally:
            self._busy = False
            self.checkingChanged.emit(False)

    @staticmethod
    def _expected_hash(checksums_url: str, name: str) -> str:
        for line in _get_text(checksums_url).splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[-1].lstrip("*") == name:
                return parts[0]
        return ""

    @staticmethod
    def _sha256(path: str) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def is_busy(self) -> bool:
        return self._busy
