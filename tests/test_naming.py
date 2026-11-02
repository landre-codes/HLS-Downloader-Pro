"""Testes de nomes de arquivo e resolução do arquivo gravado."""

from __future__ import annotations

import os

from hlsdl.naming import normalize_name, resolve_existing_file, shorten_name, url_digest


def test_url_digest_stable_and_short():
    a = url_digest("https://x.com/video.m3u8")
    b = url_digest("https://x.com/video.m3u8")
    c = url_digest("https://x.com/outro")
    assert a == b and len(a) == 10 and a != c


def test_normalize_name_removes_invalid():
    assert normalize_name("A?B*C/VIDEO") == "abcvideo"


def test_resolve_existing_file_finds_sanitized(tmp_path):
    # Simula o caso em que o yt-dlp imprime um nome que não bate com o disco.
    real = tmp_path / "video.mp4"
    real.write_bytes(b"x")
    resolved = resolve_existing_file(str(tmp_path / "video.mp4"))
    assert resolved == str(real)


def test_shorten_name_noop_when_short(tmp_path):
    p = tmp_path / "short.mp4"
    p.write_bytes(b"x")
    assert shorten_name(str(p)) == str(p)


def test_shorten_name_limits_length(tmp_path):
    long_name = ("a" * 60) + ".mp4"
    p = tmp_path / long_name
    p.write_bytes(b"x")
    new = shorten_name(str(p))
    base = os.path.splitext(os.path.basename(new))[0]
    assert len(base) <= 20
    assert os.path.exists(new)
