"""Exportação de pacotes (fonte/portátil) e hashes."""

from __future__ import annotations

import hashlib
import zipfile

from hlsdl import __version__
from hlsdl.exporter import export, sha256, version


def test_version_matches_package():
    assert version() == __version__


def test_sha256(tmp_path):
    target = tmp_path / "arquivo.bin"
    target.write_bytes(b"hls-downloader-pro")
    assert sha256(target) == hashlib.sha256(b"hls-downloader-pro").hexdigest()


def test_export_source_zip_and_checksums(tmp_path):
    artifacts = export(dist_dir=tmp_path, include_portable=False)
    source = artifacts["source"]
    assert source.is_file()
    with zipfile.ZipFile(source) as archive:
        names = archive.namelist()
    assert "hlsdl/app.py" in names
    assert "main.py" in names
    assert "requirements.txt" in names
    assert not any("__pycache__" in name for name in names)
    checksums = tmp_path / "SHA256SUMS.txt"
    assert checksums.is_file()
    assert source.name in checksums.read_text(encoding="utf-8")
