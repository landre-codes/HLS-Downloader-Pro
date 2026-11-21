"""Testes da ponte: persistência, idioma e configuração de cookies."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from hlsdl.bridge import Bridge
from hlsdl.deps import DependencyManager
from hlsdl.i18n import tr
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


def test_bridge_rewires_dependency_output_on_language_change(qapp, tmp_path):
    model = DownloadModel([])
    manager = QueueManager(model, outdir="out")
    dependency_manager = DependencyManager()
    bridge = Bridge(
        manager,
        "out",
        settings_path=str(tmp_path / "s.ini"),
        deps=dependency_manager,
        defer_detection=True,
    )
    bridge.setLanguage("en")
    assert dependency_manager._tr(
        "dep_log_downloading", url="https://example.com/file"
    ) == "Downloading https://example.com/file"
    for lang, expected in (
        ("pt_pt", "A transferir"),
        ("de", "wird heruntergeladen"),
        ("ar", "جارٍ تنزيل"),
        ("he", "מוריד"),
        ("ko", "다운로드 중"),
    ):
        bridge.setLanguage(lang)
        output = dependency_manager._tr(
            "dep_log_downloading", url="https://example.com/file"
        )
        assert expected in output, (lang, output)
    bridge.shutdown()


def test_language_flags(qapp, tmp_path, fake_deps):
    b = _bridge(tmp_path, fake_deps)
    languages = b.languages
    assert [item["code"] for item in languages] == [
        "pt", "pt_pt", "en", "es", "de", "it", "fr", "ru", "ar", "he", "ja", "ko", "zh"
    ]
    assert all(item["name"] for item in languages)
    assert [item["flag"] for item in languages] == [
        "br", "pt", "us", "es", "de", "it", "fr", "ru", "ar", "il", "jp", "kr", "cn"
    ]
    b.shutdown()


def test_rtl_languages_set_layout_direction(qapp, tmp_path, fake_deps):
    b = _bridge(tmp_path, fake_deps)
    assert b.isRtl is False
    b.setLanguage("ar")
    assert b.isRtl is True
    assert QGuiApplication.layoutDirection() == Qt.RightToLeft
    b.setLanguage("he")
    assert b.isRtl is True
    assert QGuiApplication.layoutDirection() == Qt.RightToLeft
    b.setLanguage("en")
    assert b.isRtl is False
    assert QGuiApplication.layoutDirection() == Qt.LeftToRight
    b.shutdown()


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


def test_copy_link_uses_the_imported_clipboard(qapp, tmp_path, fake_deps):
    b = _bridge(tmp_path, fake_deps)
    b.setLanguage("pt")
    QApplication.clipboard().clear()
    b.copyLink("https://example.com/path")
    assert QApplication.clipboard().text() == "https://example.com/path"


def test_copy_link_reports_unavailable_clipboard(
    qapp, tmp_path, fake_deps, monkeypatch
):
    b = _bridge(tmp_path, fake_deps)
    b.setLanguage("pt")
    messages: list[str] = []
    b.notifyText.connect(messages.append)
    monkeypatch.setattr(
        "hlsdl.bridge_parts.downloads.QApplication.clipboard",
        staticmethod(lambda: (_ for _ in ()).throw(RuntimeError("sem clipboard"))),
    )
    b.copyLink("https://example.com/path")
    assert messages and messages[-1] == tr("pt", "clipboard_unavailable")


def test_sidecars_setting_roundtrip(qapp, tmp_path, fake_deps):
    b = _bridge(tmp_path, fake_deps)
    assert b.sidecarsEnabled is False
    b.setSidecarsEnabled(True)
    assert b.sidecarsEnabled is True
    b2 = _bridge(tmp_path, fake_deps)
    assert b2.sidecarsEnabled is True
    b2.setSidecarsEnabled(False)
    assert b2.sidecarsEnabled is False
