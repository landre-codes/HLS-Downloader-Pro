"""Testes da política de URLs/Referer e do scraper com servidores locais."""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import pytest

from hlsdl.netpolicy import (
    UrlPolicyError,
    is_local_host,
    is_local_url,
    redirect_allowed,
    referer_for,
    sanitize_referer,
    validate_http_url,
)
from hlsdl.services.scraper import HtmlMediaScraper


@pytest.mark.parametrize("url", ["file:///tmp/a.mp4", "ftp://host/a.mp4", "data:text/html,x", "javascript:alert(1)"])
def test_rejects_non_http_schemes(url):
    with pytest.raises(UrlPolicyError) as exc:
        validate_http_url(url)
    assert exc.value.reason == "unsupported_scheme"


def test_rejects_missing_host_and_bad_port():
    with pytest.raises(UrlPolicyError) as exc:
        validate_http_url("https:///path")
    assert exc.value.reason == "missing_host"
    with pytest.raises(UrlPolicyError) as exc:
        validate_http_url("https://example.com:abc/")
    assert exc.value.reason == "invalid_port"


def test_referer_removes_query_userinfo_and_fragment():
    page = "https://user:pass@example.com:8443/watch?token=CANARY_SECRET#frag"
    assert sanitize_referer(page) == "https://example.com:8443/watch"
    assert referer_for("https://example.com:8443/stream.m3u8", page) == (
        "https://example.com:8443/watch"
    )


def test_referer_is_never_forwarded_cross_origin():
    page = "https://site.example/watch?token=CANARY_SECRET"
    assert referer_for("https://cdn.example/master.m3u8", page) == ""
    assert referer_for("http://site.example/master.m3u8", page) == ""
    assert referer_for("https://site.example:8443/master.m3u8", page) == ""


def test_local_host_detection_and_redirect_policy():
    assert is_local_host("127.0.0.1")
    assert is_local_host("::1")
    assert is_local_host("192.168.1.10")
    assert is_local_host("localhost")
    assert not is_local_host("8.8.8.8")
    assert is_local_url("http://127.0.0.1:8080/a")
    allowed, reason = redirect_allowed(
        "https://public.example/page", "http://127.0.0.1/admin"
    )
    assert (allowed, reason) == (False, "private_destination")
    allowed, reason = redirect_allowed(
        "http://192.168.0.10/page", "http://192.168.0.11/admin"
    )
    assert (allowed, reason) == (True, "ok")
    allowed, reason = redirect_allowed(
        "https://public.example/page", "https://cdn.example/a"
    )
    assert (allowed, reason) == (True, "ok")


class _Server:
    def __init__(self, handler):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    @property
    def port(self) -> int:
        return self.httpd.server_address[1]

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=3)


def _handler_for(routes, seen):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append((self.path, dict(self.headers)))
            route = routes.get(urlsplit(self.path).path)
            if route is None:
                self.send_response(404)
                self.end_headers()
                return
            route(self)

        def log_message(self, *args):
            pass

    return Handler


def test_scraper_strips_query_from_same_origin_referer():
    seen: list = []
    routes = {}

    def start(handler):
        handler.send_response(302)
        handler.send_header("Location", "/landing")
        handler.end_headers()

    def landing(handler):
        body = b'<html><video src="/stream/master.m3u8"></video></html>'
        handler.send_response(200)
        handler.send_header("Content-Type", "text/html; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)

    routes["/start"] = start
    routes["/landing"] = landing
    server = _Server(_handler_for(routes, seen))
    try:
        url = f"http://127.0.0.1:{server.port}/start?token=CANARY_SECRET"
        found = HtmlMediaScraper("test-agent", timeout=5).find(url)
        assert found == f"http://127.0.0.1:{server.port}/stream/master.m3u8"
        landing_headers = seen[-1][1]
        assert "Referer" in landing_headers
        assert "CANARY_SECRET" not in landing_headers["Referer"]
        assert landing_headers["Referer"].endswith("/start")
    finally:
        server.close()


def test_scraper_does_not_send_referer_cross_origin():
    seen: list = []
    routes = {}
    other = _Server(_handler_for({
        "/landing": lambda handler: _send_html(
            handler, b"<html><video src='https://cdn.example/x.m3u8'></video></html>"
        )
    }, seen))
    target = f"http://localhost:{other.port}/landing"

    def start(handler):
        handler.send_response(302)
        handler.send_header("Location", target)
        handler.end_headers()

    routes["/start"] = start
    server = _Server(_handler_for(routes, []))
    try:
        url = f"http://127.0.0.1:{server.port}/start?token=CANARY_SECRET"
        found = HtmlMediaScraper("test-agent", timeout=5).find(url)
        assert found == "https://cdn.example/x.m3u8"
        assert "Referer" not in seen[-1][1]
    finally:
        server.close()
        other.close()


def _send_html(handler, body: bytes):
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def test_scraper_rejects_file_scheme_candidate():
    routes = {
        "/page": lambda handler: _send_html(
            handler, b'<html><video src="file:///tmp/private-video.mp4"></video></html>'
        )
    }
    server = _Server(_handler_for(routes, []))
    try:
        found = HtmlMediaScraper("test-agent", timeout=5).find(
            f"http://127.0.0.1:{server.port}/page"
        )
        assert found is None
    finally:
        server.close()


def test_scraper_stops_oversized_response():
    big = b"<html>" + b"x" * 8192 + b"</html>"
    routes = {"/page": lambda handler: _send_html(handler, big)}
    server = _Server(_handler_for(routes, []))
    try:
        scraper = HtmlMediaScraper("test-agent", timeout=5, max_bytes=1024)
        assert scraper.find(f"http://127.0.0.1:{server.port}/page") is None
    finally:
        server.close()


def test_scraper_rejects_non_html_content_type():
    def image(handler):
        body = b"\x89PNG"
        handler.send_response(200)
        handler.send_header("Content-Type", "image/png")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)

    server = _Server(_handler_for({"/page": image}, []))
    try:
        scraper = HtmlMediaScraper("test-agent", timeout=5)
        assert scraper.find(f"http://127.0.0.1:{server.port}/page") is None
    finally:
        server.close()
