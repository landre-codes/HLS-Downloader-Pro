"""Manifesto de release assinado, com identidade explícita.

O formato antigo (``SHA256SUMS-*.txt``) assinava apenas nomes e hashes.  Um
atacante com acesso à publicação de releases podia reaproveitar um manifesto
antigo e rotulá-lo como uma versão mais nova.  O formato novo inclui
``schema_version``, ``version``, ``tag`` e a lista de assets com tamanho e
SHA-256; a assinatura Ed25519 cobre exatamente esses bytes canônicos.

Formato canônico (JSON UTF-8, chaves ordenadas, sem espaços supérfluos):

    {"assets":[{"name":"...","sha256":"...","size":123}],
     "schema_version":1,"tag":"v1.5.0","version":"1.5.0"}

A verificação sempre ocorre antes do parsing: os bytes baixados precisam ter
assinatura válida e ser exatamente a serialização canônica do objeto.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from .update_trust import verify_update_manifest

SCHEMA_VERSION = 1
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ManifestError(ValueError):
    """Manifesto inválido, com motivo curto e estável."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    sha256: str
    size: int


def canonical_bytes(payload: dict) -> bytes:
    """Serialização canônica assinada/verificada pelo app."""
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _validate_payload(payload) -> dict:
    if not isinstance(payload, dict):
        raise ManifestError("invalid_manifest")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ManifestError("unsupported_schema")
    version = str(payload.get("version") or "").strip().lstrip("vV")
    tag = str(payload.get("tag") or "").strip()
    if not version or not re.fullmatch(r"\d+(?:\.\d+)*", version):
        raise ManifestError("invalid_version")
    if not tag:
        raise ManifestError("invalid_tag")
    raw_assets = payload.get("assets")
    if not isinstance(raw_assets, list) or not raw_assets:
        raise ManifestError("missing_assets")
    assets: list[dict] = []
    names: set[str] = set()
    for item in raw_assets:
        if not isinstance(item, dict):
            raise ManifestError("invalid_asset")
        name = str(item.get("name") or "").strip()
        digest = str(item.get("sha256") or "").strip().lower()
        raw_size = item.get("size")
        if isinstance(raw_size, bool) or not isinstance(raw_size, (int, str)):
            raise ManifestError("invalid_asset_size")
        try:
            size = int(raw_size)
        except (TypeError, ValueError) as exc:
            raise ManifestError("invalid_asset_size") from exc
        if not name or "/" in name or "\\" in name or name in (".", ".."):
            raise ManifestError("invalid_asset_name")
        if name in names:
            raise ManifestError("duplicate_asset")
        if size <= 0:
            raise ManifestError("invalid_asset_size")
        if not _SHA256_RE.fullmatch(digest):
            raise ManifestError("invalid_asset_hash")
        names.add(name)
        assets.append({"name": name, "sha256": digest, "size": size})
    assets.sort(key=lambda item: item["name"])
    return {
        "schema_version": SCHEMA_VERSION,
        "version": version,
        "tag": tag,
        "assets": assets,
    }


def build_manifest(version: str, tag: str, assets: list[dict]) -> dict:
    """Monta o objeto canônico (usado pelo script de release e por testes)."""
    return _validate_payload(
        {
            "schema_version": SCHEMA_VERSION,
            "version": version,
            "tag": tag,
            "assets": assets,
        }
    )


def parse_verified_manifest(
    data: bytes,
    signature: str | bytes,
    public_key_b64: str | None = None,
) -> dict:
    """Verifica a assinatura antes de interpretar o JSON."""
    ok, reason = verify_update_manifest(data, signature, public_key_b64)
    if not ok:
        raise ManifestError(reason)
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError("invalid_manifest") from exc
    normalized = _validate_payload(payload)
    if canonical_bytes(normalized) != data:
        raise ManifestError("non_canonical_manifest")
    return normalized


def validate_manifest_identity(
    manifest: dict,
    *,
    version: str,
    tag: str,
    asset_name: str,
    asset_size: int = 0,
    expected_hash: str = "",
) -> ReleaseAsset:
    """Exige igualdade estrita entre manifesto, API e asset escolhido."""
    expected_version = (version or "").strip().lstrip("vV")
    if manifest.get("version") != expected_version:
        raise ManifestError("version_mismatch")
    if manifest.get("tag") != tag:
        raise ManifestError("tag_mismatch")
    asset = next(
        (item for item in manifest.get("assets", []) if item.get("name") == asset_name),
        None,
    )
    if asset is None:
        raise ManifestError("asset_missing")
    if asset_size and int(asset["size"]) != int(asset_size):
        raise ManifestError("asset_size_mismatch")
    if expected_hash and asset["sha256"] != expected_hash.strip().lower():
        raise ManifestError("asset_hash_mismatch")
    return ReleaseAsset(
        name=str(asset["name"]),
        sha256=str(asset["sha256"]),
        size=int(asset["size"]),
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def asset_name_binds_tag(name: str, tag: str) -> bool:
    """Compatibilidade: o nome do asset legado precisa citar a versão da tag.

    Sem isso, um manifesto antigo (assinado) poderia ser reapresentado sob uma
    tag nova, pois o formato legado não carrega versão nem identidade.
    """
    version = (tag or "").strip().lstrip("vV")
    if not version:
        return False
    pattern = r"(?<!\d)" + re.escape(version) + r"(?!\d)"
    return bool(re.search(pattern, name or ""))


__all__ = [
    "ManifestError",
    "ReleaseAsset",
    "SCHEMA_VERSION",
    "asset_name_binds_tag",
    "build_manifest",
    "canonical_bytes",
    "parse_verified_manifest",
    "sha256_bytes",
    "validate_manifest_identity",
]
