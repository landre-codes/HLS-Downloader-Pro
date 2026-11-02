"""Testes da ponte: persistência, idioma e configuração de cookies."""

from __future__ import annotations

from hlsdl.bridge import Bridge
from hlsdl.model import DownloadModel
from hlsdl.queue import QueueManager


def _bridge(tmp_path, fake_deps):
    model = DownloadModel([])
    manager = QueueManager(model, outdir="out")
    return Bridge(manager, "out", settings_path=str(tmp_path / "s.ini"), deps=fake_deps)


def test_persistence_roundtrip(qapp, tmp_path, fake_deps):
    b = _bridge(tmp_path, fake_deps)
    b.setDark(False)
    b.setConcurrency(5)
    b.setLimitRateMB(7)
    b.setFragments(2)
    b.setCookiesEnabled(True)
    b.setCookiesBrowserIndex(3)  # firefox
    b.setLanguage("en")

    b2 = _bridge(tmp_path, fake_deps)
    assert b2.dark is False
    assert b2.concurrency == 5
    assert b2.limitRateMB == 7
    assert b2.fragments == 2
    assert b2.language == "en"
    assert b2.cookiesEnabled is True
    assert b2.cookiesBrowserIndex == 3
    assert b2._build_cookies_arg() == "browser:firefox"


def test_limit_rate_arg(qapp, tmp_path, fake_deps):
    b = _bridge(tmp_path, fake_deps)
    b.setLimitRateMB(10)
    assert b._limit_rate_arg() == "10M"
    b.setLimitRateMB(0)
    assert b._limit_rate_arg() == ""


def test_cookies_file_overrides_browser(qapp, tmp_path, fake_deps):
    b = _bridge(tmp_path, fake_deps)
    b.setCookiesEnabled(True)
    b.setCookiesBrowserIndex(0)
    b.setCookiesFile("C:/x/cookies.txt")
    assert b._build_cookies_arg() == "file:C:/x/cookies.txt"


def test_clamps_out_of_range(qapp, tmp_path, fake_deps):
    b = _bridge(tmp_path, fake_deps)
    b.setConcurrency(99)
    assert b.concurrency == 8
    b.setFragments(0)
    assert b.fragments == 1


def test_edit_url_slot(qapp, tmp_path, fake_deps):
    b = _bridge(tmp_path, fake_deps)
    b.addLinks("https://a.com/1")
    assert b.editUrl(0, "https://b.com/2")
    assert b.manager.items[0]["url"] == "https://b.com/2"
