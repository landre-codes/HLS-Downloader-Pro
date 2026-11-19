"""Garante que o pacote instalável contém todo o código e os recursos QML."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]


def _project() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_bridge_parts_e_um_pacote_instalavel() -> None:
    packages = set(_project()["tool"]["setuptools"]["packages"])
    assert "hlsdl.bridge_parts" in packages
    assert (ROOT / "hlsdl" / "bridge_parts" / "__init__.py").is_file()


def test_recursos_qml_cobertos_pelo_package_data() -> None:
    patterns = _project()["tool"]["setuptools"]["package-data"]["hlsdl"]
    ui = ROOT / "hlsdl" / "ui"
    wanted = {".qml", ".js", ".svg"}

    missing = []
    for path in sorted(ui.rglob("*")):
        if not path.is_file() or path.suffix not in wanted:
            continue
        relative = path.relative_to(ROOT / "hlsdl").as_posix()
        if not any(PurePosixPath(relative).match(pattern) for pattern in patterns):
            missing.append(relative)

    assert not missing, f"recursos fora do package-data: {missing}"


def test_sbom_cyclonedx_e_gerado(tmp_path: Path) -> None:
    target = tmp_path / "sbom.json"
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "gen_sbom.py"), str(target)],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["bomFormat"] == "CycloneDX"
    assert data["specVersion"] == "1.5"
    assert data["metadata"]["component"]["name"] == "HLS Downloader Pro"
    assert any(item["name"].lower() == "pyside6" for item in data["components"])


def test_sbom_inclui_hash_do_bundle(tmp_path: Path) -> None:
    import hashlib

    bundle = tmp_path / "HLS-Downloader-Pro"
    bundle.mkdir()
    (bundle / "app.exe").write_bytes(b"binary")
    (bundle / "data.bin").write_bytes(b"data")
    target = tmp_path / "sbom.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "gen_sbom.py"),
            str(target),
            "--bundle",
            str(bundle),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(target.read_text(encoding="utf-8"))
    files = [item for item in data["components"] if item["type"] == "file"]
    assert {item["name"] for item in files} == {
        "HLS-Downloader-Pro/app.exe",
        "HLS-Downloader-Pro/data.bin",
    }
    by_name = {item["name"]: item for item in files}
    assert by_name["HLS-Downloader-Pro/app.exe"]["hashes"][0]["content"] == (
        hashlib.sha256(b"binary").hexdigest()
    )
    scope = next(
        prop for prop in data["metadata"]["properties"]
        if prop["name"] == "hlsdl:inventoryScope"
    )
    assert "pyinstaller-bundle" in scope["value"]
