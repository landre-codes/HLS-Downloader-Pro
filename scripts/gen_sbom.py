"""Generate a minimal CycloneDX SBOM for the running environment.

Usage: python scripts/gen_sbom.py [output.json]
No third-party dependency is required; this is intentionally a small, auditable
inventory for releases.
"""

from __future__ import annotations

import json
import sys
from importlib.metadata import distributions
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hlsdl import __version__  # noqa: E402


def main() -> int:
    components = []
    seen = set()
    for dist in distributions():
        name = dist.metadata.get("Name") or ""
        version = dist.version or ""
        key = (name.lower(), version)
        if not name or key in seen:
            continue
        seen.add(key)
        components.append({
            "type": "library",
            "name": name,
            "version": version,
            "purl": f"pkg:pypi/{name.lower().replace('_', '-')}@{version}",
        })
    payload = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "HLS Downloader Pro",
                "version": __version__,
            }
        },
        "components": sorted(components, key=lambda item: item["name"].lower()),
    }
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist" / "sbom.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(f"SBOM: {target} ({len(components)} componentes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
