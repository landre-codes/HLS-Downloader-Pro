"""Cookie scoping and text-import encoding tests."""

from __future__ import annotations

from hlsdl.bridge import Bridge
from hlsdl.downloader import DownloadWorker


def _cookies_file(tmp_path) -> str:
    path = tmp_path / "cookies.txt"
    path.write_text(
        "# Netscape HTTP Cookie File\r\n"
        ".example.com\tTRUE\t/\tFALSE\t0\tsession\tone\r\n"
        "#HttpOnly_.example.com\tTRUE\t/\tTRUE\t0\tauth\tsecret\r\n"
        ".other.com\tTRUE\t/\tFALSE\t0\tleak\tbad\r\n",
        encoding="utf-8",
    )
    return str(path)


def test_cookie_header_is_scoped_by_domain_and_secure(tmp_path):
    worker = DownloadWorker("https://cdn.example.com/v", str(tmp_path),
                            cookies="file:" + _cookies_file(tmp_path))
    header = worker._ffmpeg_cookie_header("https://cdn.example.com/stream.m3u8")
    assert "session=one" in header
    assert "auth=secret" in header
    assert "leak=bad" not in header
    # Secure cookie must not be sent over http.
    insecure = worker._ffmpeg_cookie_header("http://cdn.example.com/stream.m3u8")
    assert "session=one" in insecure
    assert "auth=secret" not in insecure


def test_cookie_file_validation(tmp_path):
    good = _cookies_file(tmp_path)
    assert Bridge._cookies_file_valid(good)
    assert not Bridge._cookies_file_valid(str(tmp_path / "missing.txt"))
    empty = tmp_path / "empty.txt"
    empty.write_text("", encoding="utf-8")
    assert not Bridge._cookies_file_valid(str(empty))


def test_decode_text_file_utf16_and_ansi():
    text = "https://a.example/v\nhttps://b.example/v\n"
    assert Bridge._decode_text_file(text.encode("utf-16")) == text
    assert Bridge._decode_text_file(text.encode("utf-8-sig")) == text
    assert Bridge._decode_text_file("Olá https://a.example/v".encode("cp1252")).startswith("Olá")
