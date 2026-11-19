"""Raspagem de páginas HTML em busca de manifestos HLS ou mídia direta.

Dependência opcional: ``requests`` + ``beautifulsoup4``. Se ausentes, o
fallback fica desabilitado (``HAS_SCRAPER = False``) e o app segue funcional.

A política de rede é aplicada manualmente:

* somente HTTP/HTTPS;
* redirecionamentos são seguidos um a um (máximo configurável), revalidando
  esquema, destino local/privado e cabeçalhos a cada salto;
* ``Referer`` só é enviado entre origens iguais e nunca contém query,
  fragmento ou credenciais;
* o corpo é lido em streaming com limite de bytes descompactados.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlsplit

from ..netpolicy import (
    UrlPolicyError,
    redirect_allowed,
    referer_for,
    validate_http_url,
)

log = logging.getLogger("hlsdl")

try:
    import requests
    from bs4 import BeautifulSoup

    HAS_SCRAPER = True
except ImportError:  # pragma: no cover - ambiente sem as libs opcionais
    HAS_SCRAPER = False

M3U8_RE = re.compile(r"https?://[^\"'\s<>\\]+\.m3u8[^\"'\s<>\\]*", re.IGNORECASE)
DIRECT_MEDIA_RE = re.compile(
    r"https?://[^\"'\s<>\\]+\.(?:mp4|webm|mkv|mov|avi|mp3|m4a)[^\"'\s<>\\]*",
    re.IGNORECASE,
)

TRAILING = ".,;:!?)]}>\"'"
_MEDIA_EXT = (".mp4", ".webm", ".mkv", ".mov", ".avi", ".mp3", ".m4a")
_HTML_TYPES = (
    "text/html",
    "application/xhtml+xml",
    "application/xml",
    "text/xml",
    "text/plain",
)
_REDIRECT_CODES = {301, 302, 303, 307, 308}
_DEFAULT_MAX_BYTES = 4 * 1024 * 1024
_DEFAULT_MAX_REDIRECTS = 5
_READ_CHUNK = 64 * 1024


class _ResponseTooLarge(RuntimeError):
    pass


def _content_type_is_html(value: str) -> bool:
    ctype = (value or "").split(";", 1)[0].strip().lower()
    if not ctype:
        return True  # alguns servidores legados omitem Content-Type
    if ctype in _HTML_TYPES:
        return True
    # JSON-LD e páginas de player às vezes vêm como application/json.
    return ctype.endswith("+xml") or ctype == "application/json"


def _read_limited(response, max_bytes: int) -> bytes:
    """Lê o corpo descompactado sem exceder ``max_bytes``."""
    declared = response.headers.get("Content-Length")
    try:
        if declared and int(declared) > max_bytes:
            raise _ResponseTooLarge("declared_content_length")
    except (TypeError, ValueError):
        pass
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(_READ_CHUNK):
        if not chunk:
            continue
        total += len(chunk)
        if total > max_bytes:
            raise _ResponseTooLarge("response_too_large")
        chunks.append(chunk)
    return b"".join(chunks)


def _decode_body(body: bytes, response) -> str:
    # Não usar ``apparent_encoding``: em respostas em streaming ele tenta
    # carregar o corpo novamente e ignora o limite de bytes.
    encoding = getattr(response, "encoding", None) or "utf-8"
    try:
        return body.decode(encoding, errors="replace")
    except (LookupError, TypeError):
        return body.decode("utf-8", errors="replace")


class HtmlMediaScraper:
    """Encontra o melhor stream embutido no HTML de uma página."""

    def __init__(
        self,
        user_agent: str,
        timeout: int = 25,
        *,
        max_bytes: int = _DEFAULT_MAX_BYTES,
        max_redirects: int = _DEFAULT_MAX_REDIRECTS,
        session=None,
        allow_private_redirects: bool = False,
    ):
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_bytes = max(1, int(max_bytes))
        self.max_redirects = max(0, int(max_redirects))
        self.allow_private_redirects = bool(allow_private_redirects)
        self._session = session

    def _headers(self, referer: str = "") -> dict:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        if referer:
            headers["Referer"] = referer
        return headers

    def _fetch_page(self, url: str) -> tuple[str, str] | None:
        """Baixa a página seguindo redirects manualmente.

        Retorna ``(url_final, html)`` ou ``None``.
        """
        try:
            validate_http_url(url)
        except UrlPolicyError as exc:
            log.info("scraper: URL rejeitada (%s)", exc.reason)
            return None

        session = self._session or requests.Session()
        current = url
        referer = ""
        for hop in range(self.max_redirects + 1):
            try:
                validate_http_url(current)
            except UrlPolicyError as exc:
                log.info("scraper: destino rejeitado (%s)", exc.reason)
                return None
            try:
                response = session.get(
                    current,
                    headers=self._headers(referer),
                    timeout=(10, self.timeout),
                    allow_redirects=False,
                    stream=True,
                )
            except Exception as exc:  # rede/HTTP — sem candidato
                log.info(
                    "scraper: GET falhou (%s)",
                    type(exc).__name__,
                )
                return None

            try:
                if response.status_code in _REDIRECT_CODES:
                    location = response.headers.get("Location") or ""
                    if not location:
                        log.info("scraper: redirect sem Location")
                        return None
                    if hop >= self.max_redirects:
                        log.info("scraper: limite de redirecionamentos excedido")
                        return None
                    target = urljoin(current, location.strip())
                    allowed, reason = redirect_allowed(
                        url,
                        target,
                        allow_private=self.allow_private_redirects,
                    )
                    if not allowed:
                        log.warning("scraper: redirect bloqueado (%s)", reason)
                        return None
                    # O Referer do próximo salto é recalculado a partir do
                    # salto atual; entre origens diferentes ele é omitido.
                    referer = referer_for(target, current)
                    current = target
                    continue
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "")
                if not _content_type_is_html(content_type):
                    log.info("scraper: Content-Type não-HTML ignorado")
                    return None
                body = _read_limited(response, self.max_bytes)
                return current, _decode_body(body, response)
            except _ResponseTooLarge:
                log.warning(
                    "scraper: resposta excedeu o limite de %d bytes",
                    self.max_bytes,
                )
                return None
            except Exception as exc:
                log.info("scraper: falha ao ler página (%s)", type(exc).__name__)
                return None
            finally:
                try:
                    response.close()
                except Exception:
                    pass
        log.info("scraper: limite de redirecionamentos excedido")
        return None

    @staticmethod
    def _candidate_url(value: str, base_url: str) -> str:
        value = (value or "").strip().rstrip(TRAILING)
        if not value:
            return ""
        try:
            absolute = urljoin(base_url, value)
            validate_http_url(absolute)
        except (UrlPolicyError, ValueError):
            return ""
        return absolute

    def find(self, url: str) -> str | None:
        """Retorna a URL do stream (prioriza ``.m3u8``) ou ``None``."""
        if not HAS_SCRAPER:
            log.warning("scraper indisponível: requests/bs4 não instalados")
            return None

        page = self._fetch_page(url)
        if page is None:
            return None
        final_url, html = page

        soup = BeautifulSoup(html, "html.parser")
        raw: list[str] = []

        # 1) <source> e <video> dentro do documento
        for tag in soup.find_all(["source", "video"]):
            for attr in ("src", "data-src", "data-url"):
                val = tag.get(attr)
                if val:
                    raw.append(val)

        # 2) scripts JSON-LD (muitos players embutem o stream aqui)
        for script in soup.find_all("script", type="application/ld+json"):
            text = script.string or ""
            raw.extend(M3U8_RE.findall(text))
            raw.extend(DIRECT_MEDIA_RE.findall(text))

        # 3) regex no HTML bruto (JS inline, objetos JSON, etc.)
        raw.extend(M3U8_RE.findall(html))
        raw.extend(DIRECT_MEDIA_RE.findall(html))

        # 4) normalizar relativos, validar esquema e deduplicar
        seen: set = set()
        normalized: list[str] = []
        for value in raw:
            absolute = self._candidate_url(value, final_url)
            if not absolute:
                continue
            path = urlsplit(absolute).path.lower()
            if absolute not in seen and (
                ".m3u8" in absolute.lower() or path.endswith(_MEDIA_EXT)
            ):
                seen.add(absolute)
                normalized.append(absolute)

        # prioriza manifestos HLS
        normalized.sort(key=lambda u: (0 if ".m3u8" in u.lower() else 1, len(u)))
        return normalized[0] if normalized else None


__all__ = ["HAS_SCRAPER", "HtmlMediaScraper"]
