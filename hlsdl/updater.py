"""Verificação e download de atualizações via GitHub Releases.

Fluxo: consulta a última release, compara a versão (SemVer), baixa o
instalador e valida o SHA-256 publicado em um manifesto assinado. Preferimos o
manifesto canônico ``release-manifest-windows.json`` (que vincula versão, tag,
nome, tamanho e hash do asset); o formato legado ``SHA256SUMS-windows.txt``
continua aceito apenas quando o nome do asset cita a versão da tag.

O Inno Setup é executado em modo silencioso com ``/CLOSEAPPLICATIONS``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import urllib.request
from urllib.parse import urlsplit

from PySide6.QtCore import QObject, Signal

from . import __version__, config
from .release_manifest import (
    ReleaseAsset,
    asset_name_binds_tag,
    parse_verified_manifest,
    validate_manifest_identity,
)
from .update_trust import verify_update_manifest

log = logging.getLogger("hlsdl")

GITHUB_REPO = "landre-codes/HLS-Downloader-Pro"
API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
USER_AGENT = "HLS-Downloader-Pro"
MANIFEST_ASSET_NAMES = (
    "release-manifest-windows.json",
    "release-manifest.json",
)
TRUSTED_RELEASE_HOSTS = frozenset({"github.com", "api.github.com"})
TRUSTED_RELEASE_SUFFIXES = (".githubusercontent.com",)
MAX_API_BYTES = 2 * 1024 * 1024
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_SIGNATURE_BYTES = 16 * 1024


def _trusted_release_url(url: str) -> bool:
    """Restringe metadados/assets aos hosts do GitHub Releases."""
    try:
        parts = urlsplit((url or "").strip())
    except ValueError:
        return False
    if parts.scheme.lower() != "https" or not parts.hostname:
        return False
    host = parts.hostname.lower()
    return host in TRUSTED_RELEASE_HOSTS or any(
        host.endswith(suffix) for suffix in TRUSTED_RELEASE_SUFFIXES
    )


def _read_limited(response, max_bytes: int) -> bytes:
    declared = response.headers.get("Content-Length")
    try:
        if declared and int(declared) > max_bytes:
            raise RuntimeError("response_too_large")
    except (TypeError, ValueError):
        pass
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(65536)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise RuntimeError("response_too_large")
        chunks.append(chunk)
    return b"".join(chunks)


def _get_trusted_bytes(url: str, max_bytes: int, timeout: int) -> bytes:
    if not _trusted_release_url(url):
        raise RuntimeError("untrusted_release_host")
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        final_url = response.geturl()
        if not _trusted_release_url(final_url):
            raise RuntimeError("untrusted_release_redirect")
        return _read_limited(response, max_bytes)


def version_tuple(value: str) -> tuple[int, ...]:
    """Converte "v1.3.1" em (1, 3, 1) para comparação simples."""
    cleaned = (value or "").strip().lstrip("vV")
    parts = []
    for part in cleaned.split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts) or (0,)


_VERSION_RE = re.compile(
    r"^[vV]?(?P<nums>\d+(?:\.\d+)*)"
    r"(?:[-.]?(?P<stage>dev|alpha|beta|rc|pre)[.-]?(?P<pre>\d+)?)?"
    r"(?:\+[0-9A-Za-z.-]+)?$",
    re.IGNORECASE,
)
_STAGE_RANK = {"dev": -1, "alpha": 0, "beta": 1, "rc": 2, "pre": 2}


def version_key(value: str) -> tuple[int, ...]:
    """Chave de comparação semântica, explícita para prereleases.

    Aceita ``v1.5.0``, ``1.5``, ``1.5.0-rc1``, ``1.5.0-beta.2`` e
    ``1.5.0+build``. Versões inválidas comparam como zero e nunca são
    oferecidas como atualização.
    """
    cleaned = (value or "").strip()
    match = _VERSION_RE.fullmatch(cleaned)
    if not match:
        return (0, 0, 0, -2, 0)
    numbers = [int(part) for part in match.group("nums").split(".")]
    while len(numbers) < 3:
        numbers.append(0)
    stage = (match.group("stage") or "").lower()
    rank = 3 if not stage else _STAGE_RANK.get(stage, -2)
    pre = int(match.group("pre") or 0)
    return (*numbers, rank, pre)


def _get_json(url: str) -> dict:
    data = _get_trusted_bytes(url, MAX_API_BYTES, timeout=30)
    return json.loads(data.decode("utf-8"))


def _get_bytes(url: str, max_bytes: int = MAX_MANIFEST_BYTES) -> bytes:
    return _get_trusted_bytes(url, max_bytes, timeout=20)


def _get_text(url: str, max_bytes: int = MAX_SIGNATURE_BYTES) -> str:
    return _get_bytes(url, max_bytes=max_bytes).decode("utf-8", errors="replace")


def _asset_by_name(assets: list, names: tuple[str, ...]) -> dict:
    return next(
        (
            asset
            for asset in assets
            if str(asset.get("name") or "") in names
        ),
        {},
    )


def _asset_named(assets: list, name: str) -> dict:
    return next(
        (asset for asset in assets if str(asset.get("name") or "") == name),
        {},
    )


class Updater(QObject):
    checkingChanged = Signal(bool)
    checked = Signal(dict)
    downloadProgress = Signal(int)
    ready = Signal(str)
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._busy = False
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None
        self._closing = False

    # ------------------------------------------------------------------ check
    def check(self) -> None:
        if self._busy or self._closing:
            return
        self._busy = True
        self.checkingChanged.emit(True)
        self._thread = threading.Thread(target=self._check, daemon=True)
        self._thread.start()

    def _check(self) -> None:
        try:
            data = _get_json(API_LATEST)
            if self._cancel.is_set():
                return
            tag_name = str(data.get("tag_name") or "")
            latest = tag_name.lstrip("vV")
            assets = data.get("assets") or []
            installer = next(
                (a for a in assets if str(a.get("name", "")).endswith("-setup.exe")),
                {},
            )
            checksums = _asset_named(assets, "SHA256SUMS-windows.txt")
            signature = _asset_named(assets, "SHA256SUMS-windows.txt.sig")
            manifest = _asset_by_name(assets, MANIFEST_ASSET_NAMES)
            manifest_name = str(manifest.get("name") or "")
            manifest_signature = _asset_named(assets, manifest_name + ".sig") if manifest else {}
            installer_name = str(installer.get("name") or "")
            try:
                installer_size = int(installer.get("size") or 0)
            except (TypeError, ValueError):
                installer_size = 0
            info = {
                "available": version_key(latest) > version_key(__version__),
                "latest": latest,
                "current": __version__,
                "release_tag": tag_name,
                "release_version": latest,
                "notes": str(data.get("body") or ""),
                "html_url": str(data.get("html_url") or ""),
                "installer_url": str(installer.get("browser_download_url") or ""),
                "installer_name": installer_name,
                "installer_size": installer_size,
                "checksums_url": str(checksums.get("browser_download_url") or ""),
                "signature_url": str(signature.get("browser_download_url") or ""),
                "manifest_url": str(manifest.get("browser_download_url") or ""),
                "manifest_signature_url": str(
                    manifest_signature.get("browser_download_url") or ""
                ),
            }
            blocked = self._verify_release_identity(info, tag_name, latest)
            if blocked:
                info["available"] = False
                info["integrity_error"] = blocked
            self.checked.emit(info)
        except Exception as exc:
            log.warning("falha ao verificar atualizações: %s", exc)
            if not self._closing:
                self.failed.emit(str(exc))
        finally:
            self._busy = False
            if not self._closing:
                self.checkingChanged.emit(False)

    @staticmethod
    def _verify_release_identity(info: dict, tag_name: str, latest: str) -> str:
        """Verifica o manifesto (quando presente) e devolve motivo de bloqueio.

        ``""`` significa release aceitável. No formato legado, exige que o nome
        do instalador cite a versão da tag; sem isso um manifesto antigo poderia
        ser reapresentado como release nova.
        """
        manifest_url = str(info.get("manifest_url") or "")
        if manifest_url:
            signature_url = str(info.get("manifest_signature_url") or "")
            if not signature_url:
                return "missing_signature"
            try:
                data = _get_bytes(manifest_url)
                signature = _get_text(signature_url)
                manifest = parse_verified_manifest(data, signature)
                validate_manifest_identity(
                    manifest,
                    version=latest,
                    tag=tag_name,
                    asset_name=str(info.get("installer_name") or ""),
                    asset_size=int(info.get("installer_size") or 0),
                )
                if version_key(str(manifest.get("version") or "")) <= version_key(
                    __version__
                ):
                    return "downgrade_blocked"
            except Exception as exc:
                log.warning("manifesto de release inválido: %s", exc)
                return str(exc) or "invalid_manifest"
            return ""
        if not info.get("installer_url"):
            return "missing_assets"
        installer_name = str(info.get("installer_name") or "")
        if not asset_name_binds_tag(installer_name, tag_name):
            return "manifest_asset_mismatch"
        if not info.get("checksums_url") or not info.get("signature_url"):
            return "missing_signature"
        return ""

    # --------------------------------------------------------------- download
    def download_and_verify(self, info: dict) -> None:
        if self._busy or self._closing:
            return
        if not info.get("installer_url"):
            self.failed.emit("missing_assets")
            return
        signed_manifest = bool(info.get("manifest_url"))
        signed_legacy = bool(info.get("checksums_url"))
        if not signed_manifest and not signed_legacy:
            self.failed.emit("missing_assets")
            return
        if signed_manifest and not info.get("manifest_signature_url"):
            self.failed.emit("missing_signature")
            return
        if signed_legacy and not signed_manifest and not info.get("signature_url"):
            self.failed.emit("missing_signature")
            return
        self._busy = True
        self._cancel.clear()
        self.checkingChanged.emit(True)
        self._thread = threading.Thread(
            target=self._download, args=(info,), daemon=True
        )
        self._thread.start()

    def _download(self, info: dict) -> None:
        try:
            folder = os.path.join(config.user_config_dir(), "updates")
            os.makedirs(folder, exist_ok=True)
            name = os.path.basename(
                str(info.get("installer_name") or "HLS-Downloader-Pro-setup.exe")
            )
            if not name.lower().endswith(".exe"):
                name = "HLS-Downloader-Pro-setup.exe"
            destination = os.path.join(folder, name)
            partial = destination + ".part"
            asset = self._verified_asset(info, name)
            installer_url = str(info["installer_url"])
            if not _trusted_release_url(installer_url):
                raise RuntimeError("untrusted_release_host")
            request = urllib.request.Request(
                installer_url, headers={"User-Agent": USER_AGENT}
            )
            try:
                with urllib.request.urlopen(request, timeout=120) as response, open(partial, "wb") as fh:
                    if not _trusted_release_url(response.geturl()):
                        raise RuntimeError("untrusted_release_redirect")
                    total = int(response.headers.get("Content-Length") or 0)
                    if asset.size and total and total > asset.size:
                        self._remove_quiet(partial)
                        if not self._closing:
                            self.failed.emit("size_mismatch")
                        return
                    done = 0
                    last = -1
                    while True:
                        if self._cancel.is_set():
                            raise RuntimeError("cancelled")
                        chunk = response.read(262144)
                        if not chunk:
                            break
                        done += len(chunk)
                        if asset.size and done > asset.size:
                            self._remove_quiet(partial)
                            if not self._closing:
                                self.failed.emit("size_mismatch")
                            return
                        fh.write(chunk)
                        if total:
                            pct = int(done * 100 / total)
                            if pct != last:
                                last = pct
                                self.downloadProgress.emit(pct)

                if asset.size and os.path.getsize(partial) != asset.size:
                    self._remove_quiet(partial)
                    if not self._closing:
                        self.failed.emit("size_mismatch")
                    return
                actual = self._sha256(partial)
                if actual.lower() != asset.sha256.lower():
                    self._remove_quiet(partial)
                    if not self._closing:
                        self.failed.emit("checksum_mismatch")
                    return
                if self._cancel.is_set():
                    self._remove_quiet(partial)
                    return
                os.replace(partial, destination)
                if not self._closing:
                    self.ready.emit(destination)
            except Exception:
                self._remove_quiet(partial)
                raise
        except Exception as exc:
            log.warning("falha ao baixar atualizacao: %s", exc)
            if not self._closing:
                self.failed.emit(str(exc))
        finally:
            self._busy = False
            if not self._closing:
                self.checkingChanged.emit(False)

    @staticmethod
    def _remove_quiet(path: str) -> None:
        try:
            os.remove(path)
        except OSError:
            pass

    @classmethod
    def _verified_asset(cls, info: dict, name: str) -> ReleaseAsset:
        """Valida a identidade da release e devolve o asset esperado."""
        manifest_url = str(info.get("manifest_url") or "")
        if manifest_url:
            signature_url = str(info.get("manifest_signature_url") or "")
            if not signature_url:
                raise RuntimeError("missing_signature")
            data = _get_bytes(manifest_url)
            signature = _get_text(signature_url)
            manifest = parse_verified_manifest(data, signature)
            version = str(info.get("release_version") or info.get("latest") or "")
            tag = str(info.get("release_tag") or f"v{version.lstrip('vV')}")
            return validate_manifest_identity(
                manifest,
                version=version,
                tag=tag,
                asset_name=name,
                asset_size=int(info.get("installer_size") or 0),
            )

        checksums_url = str(info.get("checksums_url") or "")
        signature_url = str(info.get("signature_url") or "")
        if not checksums_url or not signature_url:
            raise RuntimeError("missing_signature")
        data = _get_bytes(checksums_url)
        signature = _get_text(signature_url)
        ok, reason = verify_update_manifest(data, signature)
        if not ok:
            raise RuntimeError(reason)
        version = str(info.get("release_version") or info.get("latest") or "")
        tag = str(info.get("release_tag") or f"v{version.lstrip('vV')}")
        if not asset_name_binds_tag(name, tag):
            raise RuntimeError("manifest_asset_mismatch")
        digest = cls._hash_from_text(data.decode("utf-8", errors="replace"), name)
        if not digest:
            raise RuntimeError("missing_checksum")
        return ReleaseAsset(
            name=name,
            sha256=digest,
            size=int(info.get("installer_size") or 0),
        )

    @classmethod
    def _verified_expected_hash(cls, info: dict, name: str) -> str:
        """Compatibilidade: valida a assinatura e extrai o hash do instalador."""
        return cls._verified_asset(info, name).sha256

    @staticmethod
    def _hash_from_text(text: str, name: str) -> str:
        for line in text.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[-1].lstrip("*") == name:
                return parts[0]
        return ""

    @staticmethod
    def _expected_hash(checksums_url: str, name: str) -> str:
        return Updater._hash_from_text(_get_text(checksums_url), name)

    @staticmethod
    def _sha256(path: str) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def cancel(self) -> None:
        """Cancela a operação em andamento sem emitir sinais de fechamento."""
        self._cancel.set()

    def shutdown(self, timeout: float = 3.0) -> None:
        """Marca o updater como fechado, cancela e aguarda a thread auxiliar."""
        self._closing = True
        self._cancel.set()
        thread = self._thread
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=max(0.0, timeout))
        self._thread = None

    def is_busy(self) -> bool:
        return self._busy
