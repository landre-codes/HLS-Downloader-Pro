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
    cookies = tmp_path / "cookies.txt"
    cookies.write_text(
        "# Netscape HTTP Cookie File\n"
        ".example.com\tTRUE\t/\tFALSE\t0\tsession\tone\n",
        encoding="utf-8",
    )
    b.setCookiesEnabled(True)
    b.setCookiesBrowserIndex(0)
    b.setCookiesFile(str(cookies))
    assert b._build_cookies_arg() == "file:" + str(cookies)
    # A missing/invalid file no longer silently falls back to the browser.
    b.setCookiesFile(str(tmp_path / "missing.txt"))
    assert b._build_cookies_arg() == ""


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
    assert b.editUrl(0, "not a url") is False
    assert b.manager.items[0]["url"] == "https://b.com/2"


def test_add_links_returns_added_count(qapp, tmp_path, fake_deps):
    b = _bridge(tmp_path, fake_deps)
    assert b.addLinks("https://a.com/1\nhttps://b.com/2") == 2
    assert b.addLinks("https://a.com/1") == 0
    assert b.addLinks("not a url") == 0


def test_single_download_rejects_multiple_links(qapp, tmp_path, fake_deps):
    b = _bridge(tmp_path, fake_deps)
    assert b.downloadSingle("https://a.com/1\nhttps://b.com/2") is False
    assert b.single_manager.items == []


def test_batch_ignores_url_active_in_single_queue(qapp, tmp_path, fake_deps):
    from hlsdl.status import Status

    b = _bridge(tmp_path, fake_deps)
    b.single_manager.addText("https://a.com/1")
    b.single_manager.items[0]["status"] = Status.DOWNLOADING
    assert b.addLinks("https://a.com/1\nhttps://b.com/2") == 1
    assert [item["url"] for item in b.manager.items] == ["https://b.com/2"]
