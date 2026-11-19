"""Testes do verificador de atualizações (sem rede)."""

from __future__ import annotations

import base64
import hashlib

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hlsdl import __version__
from hlsdl import updater as updater_module
from hlsdl.release_manifest import ReleaseAsset
from hlsdl.update_trust import verify_update_manifest
from hlsdl.updater import Updater, version_tuple


def test_version_tuple():
    assert version_tuple("v1.3.1") == (1, 3, 1)
    assert version_tuple("1.3") == (1, 3)
    assert version_tuple("v2.0.0-beta") == (2, 0, 0)


def test_version_key_orders_prereleases_and_ignores_build():
    assert updater_module.version_key("v1.5.0") == updater_module.version_key("1.5")
    assert updater_module.version_key("1.5.0") > updater_module.version_key("1.5.0-rc1")
    assert updater_module.version_key("1.5.0-rc2") > updater_module.version_key("1.5.0-rc1")
    assert updater_module.version_key("1.5.0-beta.2") < updater_module.version_key("1.5.0-rc1")
    assert updater_module.version_key("1.5.0+build.7") == updater_module.version_key("1.5.0")
    assert updater_module.version_key("not-a-version") < updater_module.version_key("0.0.1")


def test_release_urls_restrict_to_github_hosts():
    assert updater_module._trusted_release_url(
        "https://github.com/landre-codes/HLS-Downloader-Pro/releases/download/v1/a.exe"
    )
    assert updater_module._trusted_release_url(
        "https://objects.githubusercontent.com/asset.exe"
    )
    assert not updater_module._trusted_release_url("https://evil.example/a.exe")
    assert not updater_module._trusted_release_url("http://github.com/a.exe")


def test_get_bytes_limits_manifest_size(monkeypatch):
    monkeypatch.setattr(
        updater_module.urllib.request, "urlopen",
        lambda request, timeout: _Response(b"0123456789"),
    )
    try:
        updater_module._get_bytes("https://github.com/x", max_bytes=5)
    except RuntimeError as exc:
        assert str(exc) == "response_too_large"
    else:
        raise AssertionError("manifesto grande foi aceito")


def test_get_bytes_rejects_untrusted_host():
    try:
        updater_module._get_bytes("https://evil.example/x")
    except RuntimeError as exc:
        assert str(exc) == "untrusted_release_host"
    else:
        raise AssertionError("host não confiável foi aceito")


def test_check_detects_new_version(qapp, monkeypatch):
    payload = {
        "tag_name": "v99.0.0",
        "body": "notas",
        "html_url": "https://example/release",
        "assets": [
            {
                "name": "HLS-Downloader-Pro-99.0.0-setup.exe",
                "browser_download_url": "https://github.com/landre-codes/HLS-Downloader-Pro/releases/download/v1/setup.exe",
            },
            {
                "name": "SHA256SUMS-windows.txt",
                "browser_download_url": "https://example/SHA256SUMS.txt",
            },
            {
                "name": "SHA256SUMS-windows.txt.sig",
                "browser_download_url": "https://example/SHA256SUMS.txt.sig",
            },
        ],
    }
    monkeypatch.setattr(updater_module, "_get_json", lambda url: payload)
    updater = Updater()
    got: list = []
    updater.checked.connect(got.append)

    updater._check()

    assert got and got[0]["available"] is True
    assert got[0]["latest"] == "99.0.0"
    assert got[0]["installer_name"].endswith("-setup.exe")
    assert got[0]["checksums_url"].endswith("SHA256SUMS.txt")
    assert got[0]["signature_url"].endswith("SHA256SUMS.txt.sig")


def test_check_detects_latest(qapp, monkeypatch):
    payload = {
        "tag_name": "v" + __version__,
        "assets": [],
        "html_url": "",
        "body": "",
    }
    monkeypatch.setattr(updater_module, "_get_json", lambda url: payload)
    updater = Updater()
    got: list = []
    updater.checked.connect(got.append)

    updater._check()

    assert got and got[0]["available"] is False


def test_expected_hash(monkeypatch):
    monkeypatch.setattr(
        updater_module, "_get_text",
        lambda url: "abc123  HLS-Downloader-Pro-1.3.0-setup.exe\n",
    )
    assert Updater._expected_hash("x", "HLS-Downloader-Pro-1.3.0-setup.exe") == "abc123"
    assert Updater._expected_hash("x", "missing.exe") == ""


def test_sha256(tmp_path):
    path = tmp_path / "file.bin"
    path.write_bytes(b"abc")
    assert Updater._sha256(str(path)) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


class _Response:
    def __init__(self, payload: bytes):
        self._payload = payload
        self._pos = 0
        self.headers = {"Content-Length": str(len(payload))}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def geturl(self) -> str:
        return "https://github.com/landre-codes/HLS-Downloader-Pro/releases/download/v1/HLS-setup.exe"

    def read(self, size: int) -> bytes:
        chunk = self._payload[self._pos:self._pos + size]
        self._pos += len(chunk)
        return chunk


def test_download_instala_apenas_apos_hash(qapp, monkeypatch, tmp_path):
    payload = b"installer-bytes"
    digest = hashlib.sha256(payload).hexdigest()
    monkeypatch.setattr(updater_module.config, "user_config_dir", lambda: str(tmp_path))
    monkeypatch.setattr(
        updater_module.urllib.request, "urlopen",
        lambda request, timeout: _Response(payload),
    )
    monkeypatch.setattr(
        Updater, "_verified_asset",
        classmethod(lambda cls, info, name: ReleaseAsset(name, digest, len(payload))),
    )
    updater = Updater()
    ready: list[str] = []
    updater.ready.connect(ready.append)

    updater._download({
        "installer_url": "https://github.com/landre-codes/HLS-Downloader-Pro/releases/download/v1/setup.exe",
        "installer_name": "HLS-Downloader-Pro-setup.exe",
        "checksums_url": "https://example/SHA256SUMS.txt",
        "signature_url": "https://example/SHA256SUMS.txt.sig",
    })

    destination = tmp_path / "updates" / "HLS-Downloader-Pro-setup.exe"
    assert ready == [str(destination)]
    assert destination.read_bytes() == payload
    assert not list((tmp_path / "updates").glob("*.part"))


def test_download_descarta_parcial_quando_hash_falha(qapp, monkeypatch, tmp_path):
    payload = b"corrupted"
    monkeypatch.setattr(updater_module.config, "user_config_dir", lambda: str(tmp_path))
    monkeypatch.setattr(
        updater_module.urllib.request, "urlopen",
        lambda request, timeout: _Response(payload),
    )
    monkeypatch.setattr(
        Updater, "_verified_asset",
        classmethod(lambda cls, info, name: ReleaseAsset(name, "0" * 64, len(payload))),
    )
    updater = Updater()
    failed: list[str] = []
    updater.failed.connect(failed.append)

    updater._download({
        "installer_url": "https://github.com/landre-codes/HLS-Downloader-Pro/releases/download/v1/setup.exe",
        "installer_name": "HLS-Downloader-Pro-setup.exe",
        "checksums_url": "https://example/SHA256SUMS.txt",
        "signature_url": "https://example/SHA256SUMS.txt.sig",
    })

    assert failed == ["checksum_mismatch"]
    updates = tmp_path / "updates"
    assert not (updates / "HLS-Downloader-Pro-setup.exe").exists()
    assert not list(updates.glob("*.part"))


def test_verify_update_manifest_ed25519():
    key = Ed25519PrivateKey.generate()
    public_raw = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    public_b64 = base64.b64encode(public_raw).decode("ascii")
    data = b"abc123  HLS-Downloader-Pro-1.4.0-setup.exe\n"
    signature = base64.b64encode(key.sign(data)).decode("ascii")
    assert verify_update_manifest(data, signature, public_b64) == (True, "ok")
    assert verify_update_manifest(data, signature + "\n", public_b64) == (True, "ok")
    assert verify_update_manifest(data, "  " + signature + "  ", public_b64) == (
        True,
        "ok",
    )
    assert verify_update_manifest(data + b"x", signature, public_b64) == (
        False, "invalid_signature"
    )
    assert verify_update_manifest(data, "", public_b64) == (
        False, "missing_signature"
    )


def test_verified_hash_rejeita_assinatura_invalida(monkeypatch):
    data = b"abc123  HLS-Downloader-Pro-1.4.0-setup.exe\n"
    monkeypatch.setattr(updater_module, "_get_bytes", lambda url: data)
    monkeypatch.setattr(updater_module, "_get_text", lambda url: "assinatura")
    monkeypatch.setattr(
        updater_module, "verify_update_manifest",
        lambda manifest, signature: (False, "invalid_signature"),
    )
    try:
        Updater._verified_expected_hash({
            "checksums_url": "https://example/SHA256SUMS.txt",
            "signature_url": "https://example/SHA256SUMS.txt.sig",
        }, "HLS-Downloader-Pro-1.4.0-setup.exe")
    except RuntimeError as exc:
        assert str(exc) == "invalid_signature"
    else:
        raise AssertionError("assinatura inv?lida foi aceita")


def test_verified_hash_aceita_manifesto_assinado(monkeypatch):
    data = b"abc123  HLS-Downloader-Pro-1.4.0-setup.exe\n"
    monkeypatch.setattr(updater_module, "_get_bytes", lambda url: data)
    monkeypatch.setattr(updater_module, "_get_text", lambda url: "assinatura")
    monkeypatch.setattr(
        updater_module, "verify_update_manifest",
        lambda manifest, signature: (True, "ok"),
    )
    assert Updater._verified_expected_hash({
        "checksums_url": "https://example/SHA256SUMS.txt",
        "signature_url": "https://example/SHA256SUMS.txt.sig",
        "latest": "1.4.0",
        "release_tag": "v1.4.0",
    }, "HLS-Downloader-Pro-1.4.0-setup.exe") == "abc123"


def test_legacy_manifest_cannot_be_replayed_under_new_tag(monkeypatch):
    data = b"abc123  HLS-Downloader-Pro-1.4.0-setup.exe\n"
    monkeypatch.setattr(updater_module, "_get_bytes", lambda url: data)
    monkeypatch.setattr(updater_module, "_get_text", lambda url: "assinatura")
    monkeypatch.setattr(
        updater_module, "verify_update_manifest",
        lambda manifest, signature: (True, "ok"),
    )
    try:
        Updater._verified_expected_hash({
            "checksums_url": "https://example/SHA256SUMS.txt",
            "signature_url": "https://example/SHA256SUMS.txt.sig",
            "latest": "9.9.9",
            "release_tag": "v9.9.9",
        }, "HLS-Downloader-Pro-1.4.0-setup.exe")
    except RuntimeError as exc:
        assert str(exc) == "manifest_asset_mismatch"
    else:
        raise AssertionError("manifesto antigo aceito sob tag nova")


def test_updater_shutdown_joins_auxiliary_thread(qapp):
    import threading
    import time

    updater = Updater()
    started = threading.Event()

    def worker():
        started.set()
        while not updater._cancel.wait(0.05):
            time.sleep(0.01)

    thread = threading.Thread(target=worker, daemon=True)
    updater._thread = thread
    thread.start()
    assert started.wait(1)
    updater.shutdown(timeout=2)
    assert not thread.is_alive()
