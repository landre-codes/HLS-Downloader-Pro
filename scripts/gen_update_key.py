"""Gera um par de chaves Ed25519 para assinar releases.

Uso:
    python scripts/gen_update_key.py --out C:\\caminho\\update_signing_key.pem

A chave privada não deve ser commitada. Guarde-a em local seguro e configure
o conteúdo do arquivo no segredo UPDATE_SIGNING_KEY do GitHub Actions.
"""

from __future__ import annotations

import argparse
import base64
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="arquivo PEM da chave privada")
    parser.add_argument("--force", action="store_true", help="sobrescrever se existir")
    args = parser.parse_args()
    target = Path(args.out).expanduser().resolve()
    if target.exists() and not args.force:
        raise SystemExit(f"recusando sobrescrever {target}; use --force")
    target.parent.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    target.write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    public_raw = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    print("chave privada:", target)
    print("chave publica (base64):", base64.b64encode(public_raw).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
