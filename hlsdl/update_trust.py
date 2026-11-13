"""Verificação da assinatura Ed25519 do manifesto de atualizações.

O SHA-256 sozinho não prova autoria: se a release do GitHub for comprometida,
instalador e checksum podem ser trocados juntos. O manifesto de checksums é
assinado no processo de release com uma chave privada Ed25519 e verificado
aqui com a chave pública embutida no aplicativo.
"""

from __future__ import annotations

import base64
import binascii

# Chave pública Ed25519 (raw, 32 bytes) usada nas releases.
# A chave privada correspondente NÃO fica no repositório; veja
# scripts/gen_update_key.py e a documentação de release.
UPDATE_PUBLIC_KEY_B64 = "nWRqck0Ckxq2nwYsF92GvMKwlC5zNTNPlnwNHZI0EVA="


def verify_update_manifest(
    data: bytes,
    signature_b64: str | bytes,
    public_key_b64: str | None = None,
) -> tuple[bool, str]:
    """Valida ``data`` contra uma assinatura Ed25519 em base64.

    Retorna ``(ok, reason)`` com motivos curtos:
    ``ok``, ``missing_signature``, ``invalid_signature``,
    ``cryptography_missing`` ou ``not_configured``.
    """
    if not signature_b64:
        return False, "missing_signature"
    key_b64 = public_key_b64 or UPDATE_PUBLIC_KEY_B64
    if not key_b64:
        return False, "not_configured"
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError:
        return False, "cryptography_missing"

    try:
        raw_signature = base64.b64decode(
            signature_b64.encode("ascii") if isinstance(signature_b64, str)
            else signature_b64,
            validate=True,
        )
        public_key = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(key_b64, validate=True)
        )
        public_key.verify(raw_signature, data)
        return True, "ok"
    except (ValueError, TypeError, binascii.Error):
        return False, "invalid_signature"
    except InvalidSignature:
        return False, "invalid_signature"
