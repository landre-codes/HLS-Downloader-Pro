"""Testes do modo portátil (settings/log/tools ao lado do executável)."""

from __future__ import annotations

from hlsdl import config


def test_portable_via_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HLSDL_PORTABLE", "1")
    monkeypatch.setattr(config, "app_dir", lambda: str(tmp_path))

    assert config.is_portable() is True
    assert config.settings_path() == str(tmp_path / "settings.ini")
    assert config.log_path() == str(tmp_path / "hls_downloader.log")
    assert config.tools_dir() == str(tmp_path / "tools")
    assert (tmp_path / "tools").is_dir()


def test_portable_via_flag_file(monkeypatch, tmp_path):
    monkeypatch.delenv("HLSDL_PORTABLE", raising=False)
    (tmp_path / "portable.flag").write_text("", encoding="utf-8")
    monkeypatch.setattr(config, "app_dir", lambda: str(tmp_path))

    assert config.is_portable() is True
    assert config.settings_path() == str(tmp_path / "settings.ini")


def test_not_portable_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("HLSDL_PORTABLE", raising=False)
    monkeypatch.setattr(config, "app_dir", lambda: str(tmp_path))
    assert config.is_portable() is False


def test_qml_path_bundled_layout(monkeypatch, tmp_path):
    # Layout do PyInstaller: <_MEIPASS>/hlsdl/ui/main.qml e _PKG_DIR aponta
    # para <_MEIPASS>/hlsdl (assim como o __file__ do módulo congelado).
    meipass = tmp_path / "mei"
    pkg = meipass / "hlsdl"
    ui = pkg / "ui"
    ui.mkdir(parents=True)
    qml = ui / "main.qml"
    qml.write_text("Item {}", encoding="utf-8")

    monkeypatch.setattr(config, "_PKG_DIR", str(pkg))
    monkeypatch.setattr(config.sys, "_MEIPASS", str(meipass), raising=False)
    assert config.qml_path() == str(qml)
