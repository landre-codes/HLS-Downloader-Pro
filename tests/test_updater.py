"""Testes do verificador de atualizações (sem rede)."""

from __future__ import annotations

from hlsdl import __version__
from hlsdl import updater as updater_module
from hlsdl.updater import Updater, version_tuple


def test_version_tuple():
    assert version_tuple("v1.3.1") == (1, 3, 1)
    assert version_tuple("1.3") == (1, 3)
    assert version_tuple("v2.0.0-beta") == (2, 0, 0)


def test_check_detects_new_version(qapp, monkeypatch):
    payload = {
        "tag_name": "v99.0.0",
        "body": "notas",
        "html_url": "https://example/release",
        "assets": [
            {
                "name": "HLS-Downloader-Pro-99.0.0-setup.exe",
                "browser_download_url": "https://example/setup.exe",
            },
            {
                "name": "SHA256SUMS-windows.txt",
                "browser_download_url": "https://example/SHA256SUMS.txt",
            },
        ],
    }
    monkeypatch.setattr(updater_module, "_get_json", lambda url: payload)
    updater = Updater()
    got: list = []
    updater.checked.connect(got.append)

    updater._check()

    assert got and got[0]["available"] is True
    assert got[0]["latest"] == "99.0.0"
    assert got[0]["installer_name"].endswith("-setup.exe")
    assert got[0]["checksums_url"].endswith("SHA256SUMS.txt")


def test_check_detects_latest(qapp, monkeypatch):
    payload = {
        "tag_name": "v" + __version__,
        "assets": [],
        "html_url": "",
        "body": "",
    }
    monkeypatch.setattr(updater_module, "_get_json", lambda url: payload)
    updater = Updater()
    got: list = []
    updater.checked.connect(got.append)

    updater._check()

    assert got and got[0]["available"] is False


def test_expected_hash(monkeypatch):
    monkeypatch.setattr(
        updater_module, "_get_text",
        lambda url: "abc123  HLS-Downloader-Pro-1.3.0-setup.exe\n",
    )
    assert Updater._expected_hash("x", "HLS-Downloader-Pro-1.3.0-setup.exe") == "abc123"
    assert Updater._expected_hash("x", "missing.exe") == ""


def test_sha256(tmp_path):
    path = tmp_path / "file.bin"
    path.write_bytes(b"abc")
    assert Updater._sha256(str(path)) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
