"""Gera o manifesto canônico de uma release (para assinatura Ed25519).

Uso (Windows/Linux):
    python scripts/gen_release_manifest.py --version 1.5.0 --tag v1.5.0 \
        --output release-manifest-windows.json INSTALADOR.exe PORTABLE.zip SBOM.json

O arquivo de saída é JSON UTF-8 canônico (sem newline). Assine-o com
``scripts/sign_release.py``; o app verifica a assinatura antes de interpretar
qualquer campo e exige que versão, tag, nome e tamanho do asset coincidam com
os metadados da API do GitHub.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hlsdl.release_manifest import build_manifest, canonical_bytes  # noqa: E402


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", help="assets publicados na release")
    parser.add_argument("--version", required=True, help="versão sem o prefixo v")
    parser.add_argument("--tag", required=True, help="tag exata da release (ex.: v1.5.0)")
    parser.add_argument("--output", required=True, help="manifesto JSON de saída")
    args = parser.parse_args()

    version = args.version.strip().lstrip("vV")
    tag_version = args.tag.strip().lstrip("vV")
    if version != tag_version:
        print(
            f"versão {version} não corresponde à tag {args.tag}",
            file=sys.stderr,
        )
        return 2

    assets = []
    names = set()
    for raw in args.files:
        path = Path(raw).expanduser().resolve()
        if not path.is_file():
            print(f"asset não encontrado: {path}", file=sys.stderr)
            return 1
        if path.name in names:
            print(f"asset duplicado: {path.name}", file=sys.stderr)
            return 1
        names.add(path.name)
        assets.append(
            {
                "name": path.name,
                "sha256": _sha256(path),
                "size": path.stat().st_size,
            }
        )

    payload = build_manifest(version=version, tag=args.tag.strip(), assets=assets)
    target = Path(args.output).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(canonical_bytes(payload))
    print(f"manifesto: {target} ({len(assets)} assets)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
