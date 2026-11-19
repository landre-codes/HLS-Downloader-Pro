"""Testes do manifesto de release assinado e da ligação com a tag/API."""

from __future__ import annotations

import base64
import hashlib
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hlsdl import update_trust
from hlsdl import updater as updater_module
from hlsdl.release_manifest import (
    ManifestError,
    asset_name_binds_tag,
    build_manifest,
    canonical_bytes,
    parse_verified_manifest,
    sha256_bytes,
    validate_manifest_identity,
)
from hlsdl.updater import Updater


def _keypair():
    key = Ed25519PrivateKey.generate()
    public_raw = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return key, base64.b64encode(public_raw).decode("ascii")


def _signed_manifest(key, version="1.5.1", tag="v1.5.1", name="HLS-setup.exe",
                     payload=b"installer"):
    manifest = build_manifest(
        version=version,
        tag=tag,
        assets=[{"name": name, "sha256": sha256_bytes(payload), "size": len(payload)}],
    )
    data = canonical_bytes(manifest)
    signature = base64.b64encode(key.sign(data)).decode("ascii")
    return manifest, data, signature


def test_signed_manifest_roundtrip_and_tamper_detection():
    key, public_b64 = _keypair()
    manifest, data, signature = _signed_manifest(key)
    parsed = parse_verified_manifest(data, signature, public_b64)
    assert parsed == manifest

    tampered = json.loads(data)
    tampered["tag"] = "v9.9.9"
    with pytest.raises(ManifestError) as exc:
        parse_verified_manifest(canonical_bytes(tampered), signature, public_b64)
    assert exc.value.reason == "invalid_signature"

    # Reassinar um conteúdo não canônico também é rejeitado.
    non_canonical = json.dumps(tampered, indent=2).encode("utf-8")
    bad_sig = base64.b64encode(key.sign(non_canonical)).decode("ascii")
    with pytest.raises(ManifestError) as exc:
        parse_verified_manifest(non_canonical, bad_sig, public_b64)
    assert exc.value.reason == "non_canonical_manifest"


def test_manifest_identity_binds_version_tag_name_size_and_hash():
    key, _ = _keypair()
    manifest, _, _ = _signed_manifest(key)
    asset = validate_manifest_identity(
        manifest,
        version="1.5.1",
        tag="v1.5.1",
        asset_name="HLS-setup.exe",
        asset_size=9,
        expected_hash=sha256_bytes(b"installer"),
    )
    assert asset.sha256 == sha256_bytes(b"installer")

    for kwargs, reason in (
        ({"version": "1.5.2"}, "version_mismatch"),
        ({"tag": "v1.5.2"}, "tag_mismatch"),
        ({"asset_name": "other.exe"}, "asset_missing"),
        ({"asset_size": 10}, "asset_size_mismatch"),
        ({"expected_hash": "0" * 64}, "asset_hash_mismatch"),
    ):
        params = {
            "version": "1.5.1",
            "tag": "v1.5.1",
            "asset_name": "HLS-setup.exe",
            "asset_size": 9,
        }
        params.update(kwargs)
        with pytest.raises(ManifestError) as exc:
            validate_manifest_identity(manifest, **params)
        assert exc.value.reason == reason


def test_replayed_manifest_cannot_claim_newer_tag():
    key, _ = _keypair()
    old, _, _ = _signed_manifest(key, version="1.4.0", tag="v1.4.0")
    with pytest.raises(ManifestError) as exc:
        validate_manifest_identity(
            old,
            version="9.9.9",
            tag="v9.9.9",
            asset_name="HLS-setup.exe",
        )
    assert exc.value.reason == "version_mismatch"


def test_legacy_asset_name_must_bind_tag():
    assert asset_name_binds_tag("HLS-Downloader-Pro-1.5.1-setup.exe", "v1.5.1")
    assert not asset_name_binds_tag("HLS-Downloader-Pro-1.5.1-setup.exe", "v9.9.9")
    assert not asset_name_binds_tag("HLS-Downloader-Pro-11.5.1-setup.exe", "v1.5.1")
    assert not asset_name_binds_tag("HLS-Downloader-Pro-setup.exe", "v1.5.1")


def test_updater_verifies_signed_manifest_identity(monkeypatch):
    key, public_b64 = _keypair()
    manifest, data, signature = _signed_manifest(key)
    monkeypatch.setattr(update_trust, "UPDATE_PUBLIC_KEY_B64", public_b64)
    monkeypatch.setattr(updater_module, "_get_bytes", lambda url: data)
    monkeypatch.setattr(updater_module, "_get_text", lambda url: signature)
    info = {
        "manifest_url": "https://example/release-manifest-windows.json",
        "manifest_signature_url": "https://example/release-manifest-windows.json.sig",
        "release_version": "1.5.1",
        "release_tag": "v1.5.1",
        "installer_name": "HLS-setup.exe",
        "installer_size": 9,
    }
    asset = Updater._verified_asset(info, "HLS-setup.exe")
    assert asset.size == 9
    assert asset.sha256 == sha256_bytes(b"installer")


def test_updater_check_blocks_replayed_or_mismatched_manifest(monkeypatch):
    key, public_b64 = _keypair()
    manifest, data, signature = _signed_manifest(
        key, version="1.4.0", tag="v1.4.0", name="HLS-Downloader-Pro-1.4.0-setup.exe"
    )
    monkeypatch.setattr(update_trust, "UPDATE_PUBLIC_KEY_B64", public_b64)
    monkeypatch.setattr(updater_module, "_get_bytes", lambda url: data)
    monkeypatch.setattr(updater_module, "_get_text", lambda url: signature)
    payload = {
        "tag_name": "v99.0.0",
        "body": "",
        "html_url": "",
        "assets": [
            {
                "name": "HLS-Downloader-Pro-1.4.0-setup.exe",
                "browser_download_url": "https://github.com/landre-codes/HLS-Downloader-Pro/releases/download/v1/setup.exe",
                "size": 9,
            },
            {
                "name": "release-manifest-windows.json",
                "browser_download_url": "https://example/manifest.json",
            },
            {
                "name": "release-manifest-windows.json.sig",
                "browser_download_url": "https://example/manifest.json.sig",
            },
        ],
    }
    monkeypatch.setattr(updater_module, "_get_json", lambda url: payload)
    updater = Updater()
    got: list = []
    updater.checked.connect(got.append)
    updater._check()
    assert got
    assert got[0]["available"] is False
    assert got[0]["integrity_error"] == "version_mismatch"
    assert manifest["version"] == "1.4.0"


def test_download_rejects_wrong_declared_size(qapp, monkeypatch, tmp_path):
    from hlsdl.release_manifest import ReleaseAsset

    payload = b"installer-bytes"
    monkeypatch.setattr(updater_module.config, "user_config_dir", lambda: str(tmp_path))
    monkeypatch.setattr(
        updater_module.urllib.request, "urlopen",
        lambda request, timeout: _Response(payload),
    )
    monkeypatch.setattr(
        Updater, "_verified_asset",
        classmethod(lambda cls, info, name: ReleaseAsset(name, hashlib.sha256(payload).hexdigest(), len(payload) + 1)),
    )
    updater = Updater()
    failed: list[str] = []
    updater.failed.connect(failed.append)
    updater._download({
        "installer_url": "https://github.com/landre-codes/HLS-Downloader-Pro/releases/download/v1/setup.exe",
        "installer_name": "HLS-Downloader-Pro-setup.exe",
    })
    assert failed == ["size_mismatch"]
    assert not (tmp_path / "updates" / "HLS-Downloader-Pro-setup.exe").exists()


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
