"""Exportação de pacotes para distribuição (fonte, portátil e hashes).

Uso:
    python exportar.py

Saída em ``dist/``:
    HLS-Downloader-Pro-<versao>-source.zip
    HLS-Downloader-Pro-<versao>-portable-win64.zip   (se o build existir)
    SHA256SUMS.txt
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path

from . import __version__

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BUILD = DIST / "HLS-Downloader-Pro"

IGNORE = shutil.ignore_patterns(
    "__pycache__",
    "*.py[cod]",
    "*.log",
    ".venv",
    "venv",
    ".git",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "build",
    "dist",
    "test_out",
    "settings.ini",
    "portable.flag",
    "diagnostico-hlsdl.txt",
    "*.qmlc",
)

SOURCE_DIRS = ("hlsdl", "tests", "scripts", "assets", "installer")
SOURCE_FILES = (
    "main.py",
    "worker.py",
    "requirements.txt",
    "pyproject.toml",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "diagnostico.py",
    "exportar.py",
    "iniciar.cmd",
    "smoke_test.py",
)
DOC_FILES = ("README.md", "CHANGELOG.md", "LICENSE", "THIRD_PARTY_NOTICES.md")


def version() -> str:
    return __version__


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_source(destination: Path) -> None:
    """Copia o código e a documentação, sem caches nem artefatos."""
    destination.mkdir(parents=True, exist_ok=True)
    for name in SOURCE_DIRS:
        source = ROOT / name
        if source.is_dir():
            shutil.copytree(source, destination / name, ignore=IGNORE)
    for name in SOURCE_FILES:
        source = ROOT / name
        if source.is_file():
            shutil.copy2(source, destination / name)


def make_zip(source_dir: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    target = target.with_suffix("")
    archive = shutil.make_archive(str(target), "zip", root_dir=source_dir)
    return Path(archive)


def export_source(dist_dir: Path) -> Path:
    staging = Path(tempfile.mkdtemp(prefix="hlsdl-source-"))
    try:
        source = staging / "source"
        copy_source(source)
        return make_zip(
            source, dist_dir / f"HLS-Downloader-Pro-{version()}-source.zip"
        )
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def export_portable(dist_dir: Path, build_dir: Path = BUILD) -> Path | None:
    """Empacota o build onedir com ``portable.flag`` e documentação."""
    exe = build_dir / "HLS-Downloader-Pro.exe"
    if not exe.is_file():
        return None
    staging = Path(tempfile.mkdtemp(prefix="hlsdl-portable-"))
    try:
        portable = staging / "portable"
        portable.mkdir(parents=True, exist_ok=True)
        shutil.copytree(build_dir, portable, ignore=IGNORE, dirs_exist_ok=True)
        (portable / "portable.flag").write_text("", encoding="utf-8")
        for name in DOC_FILES:
            source = ROOT / name
            if source.is_file():
                shutil.copy2(source, portable / name)
        (portable / "LEIA-ME.txt").write_text(
            "HLS Downloader Pro — versão portátil\n\n"
            "1. Extraia todo o conteúdo em uma pasta local.\n"
            "2. Execute HLS-Downloader-Pro.exe.\n\n"
            "O arquivo portable.flag mantém settings.ini, logs e ferramentas\n"
            "dentro desta pasta (bom para pen drive).\n",
            encoding="utf-8",
        )
        return make_zip(
            portable,
            dist_dir / f"HLS-Downloader-Pro-{version()}-portable-win64.zip",
        )
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def export(
    dist_dir: Path | str | None = None,
    build_dir: Path | str | None = None,
    include_portable: bool = True,
) -> dict[str, Path]:
    """Gera os pacotes e o arquivo de hashes; devolve os caminhos criados."""
    dist = Path(dist_dir) if dist_dir else DIST
    dist.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, Path] = {}

    source_zip = export_source(dist)
    artifacts["source"] = source_zip

    if include_portable:
        portable = export_portable(
            dist, Path(build_dir) if build_dir else BUILD
        )
        if portable is not None:
            artifacts["portable"] = portable

    installer = next((dist / "installer").glob("*setup.exe"), None)
    if installer is not None:
        artifacts["installer"] = installer

    lines = [
        f"{sha256(path)}  {path.name}"
        for path in artifacts.values()
        if path.exists()
    ]
    checksums = dist / "SHA256SUMS.txt"
    checksums.write_text("\n".join(lines) + "\n", encoding="utf-8")
    artifacts["checksums"] = checksums
    return artifacts


def main() -> int:
    artifacts = export()
    for name, path in artifacts.items():
        print(f"[ok] {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
