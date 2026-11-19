"""Generate a minimal CycloneDX SBOM for the running build environment.

Usage: python scripts/gen_sbom.py [output.json] [--bundle PATH]
No third-party dependency is required; this is intentionally a small, auditable
inventory for releases. The environment list reflects the Python build
environment; ``--bundle`` adds the actual files shipped by PyInstaller with
their SHA-256, so the artifact is represented byte-for-byte. The
``hlsdl:inventoryScope`` property records which part is which.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from importlib.metadata import distributions
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hlsdl import __version__  # noqa: E402


def _license_name(dist) -> str:
    expression = dist.metadata.get("License-Expression") or ""
    if expression:
        return str(expression).strip()
    classifiers = dist.metadata.get_all("Classifier") or []
    for classifier in classifiers:
        prefix = "License ::"
        if str(classifier).startswith(prefix):
            return str(classifier).split("::")[-1].strip()
    return str(dist.metadata.get("License") or "").strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bundle_components(bundle: Path) -> list[dict]:
    """Lista cada arquivo do bundle com hash e tamanho reais."""
    if not bundle.exists():
        raise SystemExit(f"bundle não encontrado: {bundle}")
    files: list[tuple[str, Path]] = []
    if bundle.is_file():
        files.append((bundle.name, bundle))
    else:
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                relative = path.relative_to(bundle).as_posix()
                files.append((f"{bundle.name}/{relative}", path))
    components = []
    for name, path in files:
        components.append(
            {
                "type": "file",
                "name": name,
                "version": __version__,
                "hashes": [{"alg": "SHA-256", "content": _sha256(path)}],
                "properties": [
                    {"name": "hlsdl:size", "value": str(path.stat().st_size)}
                ],
            }
        )
    return components


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", nargs="?", default=str(ROOT / "dist" / "sbom.json"))
    parser.add_argument(
        "--bundle",
        default="",
        help="arquivo ou pasta do build PyInstaller para hashear",
    )
    args = parser.parse_args()

    components = []
    seen = set()
    for dist in distributions():
        name = dist.metadata.get("Name") or ""
        version = dist.version or ""
        key = (name.lower(), version)
        if not name or key in seen:
            continue
        seen.add(key)
        component = {
            "type": "library",
            "name": name,
            "version": version,
            "purl": f"pkg:pypi/{name.lower().replace('_', '-')}@{version}",
        }
        license_name = _license_name(dist)
        if license_name:
            component["licenses"] = [{"license": {"name": license_name}}]
        components.append(component)

    bundle_components: list[dict] = []
    if args.bundle:
        bundle_components = _bundle_components(Path(args.bundle).expanduser().resolve())
        components.extend(bundle_components)

    properties = [
        {
            "name": "hlsdl:inventoryScope",
            "value": "build-environment"
            + (" + pyinstaller-bundle" if bundle_components else ""),
        }
    ]
    if args.bundle:
        properties.append(
            {"name": "hlsdl:bundleRoot", "value": Path(args.bundle).name}
        )

    payload = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "HLS Downloader Pro",
                "version": __version__,
            },
            "properties": properties,
        },
        "components": sorted(components, key=lambda item: item["name"].lower()),
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(
        f"SBOM: {target} ({len(components)} componentes, "
        f"{len(bundle_components)} do bundle)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


if __name__ == "__main__":
    raise SystemExit(main())
