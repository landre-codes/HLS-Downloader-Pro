"""Raspagem de páginas HTML em busca de manifestos HLS ou mídia direta.

Dependência opcional: ``requests`` + ``beautifulsoup4``. Se ausentes, o
fallback fica desabilitado (``HAS_SCRAPER = False``) e o app segue funcional.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

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


class HtmlMediaScraper:
    """Encontra o melhor stream embutido no HTML de uma página."""

    def __init__(self, user_agent: str, timeout: int = 25):
        self.user_agent = user_agent
        self.timeout = timeout

    def find(self, url: str) -> str | None:
        """Retorna a URL do stream (prioriza ``.m3u8``) ou ``None``."""
        if not HAS_SCRAPER:
            log.warning("scraper indisponível: requests/bs4 não instalados")
            return None

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": url,
        }
        try:
            resp = requests.get(
                url, headers=headers, timeout=self.timeout, allow_redirects=True
            )
            resp.raise_for_status()
        except Exception as exc:  # rede/HTTP — sem candidato
            log.info("scraper: GET falhou (%s)", exc)
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
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
        raw.extend(M3U8_RE.findall(resp.text))
        raw.extend(DIRECT_MEDIA_RE.findall(resp.text))

        # 4) normalizar relativos e deduplicar
        seen: set = set()
        normalized: list[str] = []
        for value in raw:
            value = value.strip().rstrip(TRAILING)
            if value.startswith("//"):
                value = "https:" + value
            elif not value.startswith("http"):
                value = urljoin(resp.url, value)
            if value not in seen and ("m3u8" in value or value.lower().endswith(_MEDIA_EXT)):
                seen.add(value)
                normalized.append(value)

        # prioriza manifestos HLS
        normalized.sort(key=lambda u: (0 if ".m3u8" in u else 1, len(u)))
        return normalized[0] if normalized else None
