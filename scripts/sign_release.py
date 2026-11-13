"""Assina o manifesto SHA256SUMS de uma release com Ed25519.

Uso:
    python scripts/sign_release.py SHA256SUMS-windows.txt --key update_signing_key.pem

A saída é ``SHA256SUMS-windows.txt.sig`` (base64). O app verifica a assinatura
com a chave pública embutida em ``hlsdl/update_trust.py`` antes de aceitar
qualquer hash de instalador.
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _load_key(path: str) -> Ed25519PrivateKey:
    if path:
        data = Path(path).expanduser().read_bytes()
    else:
        data = os.environ.get("UPDATE_SIGNING_KEY", "").encode("utf-8")
    if not data:
        raise SystemExit("informe --key ou UPDATE_SIGNING_KEY")
    key = serialization.load_pem_private_key(data, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise SystemExit("a chave não é Ed25519")
    return key


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", help="arquivo de checksums a assinar")
    parser.add_argument("--key", default="", help="PEM da chave privada")
    args = parser.parse_args()
    manifest = Path(args.manifest).expanduser().resolve()
    if not manifest.is_file():
        print(f"manifesto não encontrado: {manifest}", file=sys.stderr)
        return 1
    signature = _load_key(args.key).sign(manifest.read_bytes())
    target = Path(str(manifest) + ".sig")
    target.write_text(base64.b64encode(signature).decode("ascii") + "\n",
                      encoding="ascii")
    print("assinatura:", target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
