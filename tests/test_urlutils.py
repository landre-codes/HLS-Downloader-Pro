"""Testes de URL: extração, normalização e deduplicação."""

from __future__ import annotations

from hlsdl.urlutils import extract_urls, normalize_url


def test_extract_urls_basic():
    urls = extract_urls("texto https://a.com/v1 mais https://b.com/p?q=1.\nhttps://c.com/m.m3u8")
    assert urls == ["https://a.com/v1", "https://b.com/p?q=1", "https://c.com/m.m3u8"]


def test_extract_urls_empty():
    assert extract_urls("") == []
    assert extract_urls("sem links aqui") == []


def test_extract_urls_strips_trailing_punctuation():
    assert extract_urls("veja (https://x.com/video).") == ["https://x.com/video"]


def test_normalize_ignores_fragment_and_trailing_slash():
    assert normalize_url("https://A.com/Path/#frag") == normalize_url("https://a.com/Path")


def test_normalize_preserves_path_case():
    # Servidores podem ser case-sensitive no path: não devemos igualar.
    assert normalize_url("https://a.com/X") != normalize_url("https://a.com/x")


def test_extract_urls_dedup():
    assert extract_urls("https://a.com/1\nhttps://a.com/1") == ["https://a.com/1"]
