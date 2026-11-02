"""Testes do pipeline de download/extração de dependências (sem rede)."""

from __future__ import annotations

import io
import os
import sys
import tarfile
import zipfile

from hlsdl import config, deps


def _make_zip(path, members):
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)


def _make_tar_xz(path, members):
    with tarfile.open(path, "w:xz") as tf:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))


def test_extract_from_zip(tmp_path):
    archive = tmp_path / "ffmpeg.zip"
    _make_zip(archive, {
        "ffmpeg-7.0-essentials_build/bin/ffmpeg.exe": b"FF",
        "ffmpeg-7.0-essentials_build/bin/ffprobe.exe": b"FP",
        "ffmpeg-7.0-essentials_build/README.txt": b"x",
    })
    target = tmp_path / "out"
    target.mkdir()
    found = deps.DependencyManager()._extract_members(
        str(archive), {"ffmpeg.exe", "ffprobe.exe"}, str(target)
    )
    assert found == {"ffmpeg.exe", "ffprobe.exe"}
    assert (target / "ffmpeg.exe").read_bytes() == b"FF"


def test_extract_from_tar_xz(tmp_path):
    archive = tmp_path / "ffmpeg.tar.xz"
    _make_tar_xz(archive, {
        "ffmpeg-6.1-static/ffmpeg": b"F",
        "ffmpeg-6.1-static/ffprobe": b"P",
    })
    target = tmp_path / "out"
    target.mkdir()
    found = deps.DependencyManager()._extract_members(
        str(archive), {"ffmpeg", "ffprobe"}, str(target)
    )
    assert found == {"ffmpeg", "ffprobe"}
    assert (target / "ffmpeg").read_bytes() == b"F"


def test_install_ytdlp_from_file_url(tmp_path, monkeypatch):
    tools = tmp_path / "tools"
    tools.mkdir()
    monkeypatch.setattr(config, "tools_dir", lambda: str(tools))
    monkeypatch.setattr(config, "ensure_tools_on_path", lambda: None)

    if os.name == "nt":
        asset = "yt-dlp.exe"
    elif sys.platform == "darwin":
        asset = "yt-dlp_macos"
    else:
        asset = "yt-dlp"
    payload = tmp_path / asset
    payload.write_bytes(b"binary-payload")
    monkeypatch.setattr(
        deps, "YTDLP_CHANNELS",
        {**deps.YTDLP_CHANNELS, "stable": tmp_path.as_uri() + "/"},
    )

    manager = deps.DependencyManager()
    output = []
    manager.installOutput.connect(output.append)

    assert manager._install_ytdlp() is True
    target = tools / ("yt-dlp.exe" if os.name == "nt" else "yt-dlp")
    assert target.exists() and target.read_bytes() == b"binary-payload"
    assert any("yt-dlp instalado" in line for line in output)


def test_strategy_frozen_prefers_download(monkeypatch):
    monkeypatch.setattr(config, "is_frozen", lambda: True)
    monkeypatch.setattr(config, "tools_dir", lambda: "/tmp/tools")
    spec = next(s for s in deps.SPECS if s.key == "ytdlp")
    assert deps._strategy(spec) == "download"


def test_strategy_source_pip_tools(monkeypatch):
    monkeypatch.setattr(config, "is_frozen", lambda: True)
    spec = next(s for s in deps.SPECS if s.key == "requests")
    assert deps._strategy(spec) == "bundled"


def test_detect_ytdlp_counts_python_module(monkeypatch):
    # Em desenvolvimento o yt-dlp pode existir só como módulo (sem binário).
    monkeypatch.setattr(deps, "_binary_path", lambda spec: "")
    monkeypatch.setattr(deps, "_module_found", lambda name: name == "yt_dlp")
    spec = next(s for s in deps.SPECS if s.key == "ytdlp")
    status = deps.DependencyManager().detect(spec)
    assert status.found is True
