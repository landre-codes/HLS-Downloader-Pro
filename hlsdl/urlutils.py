"""Extração e normalização de URLs."""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)

TRAILING = ".,;:!?)]}>\"'"


def extract_urls(text: str) -> list[str]:
    """Extrai URLs válidas de um texto, ignorando duplicatas."""
    if not text:
        return []
    urls: list[str] = []
    seen: set = set()
    for line in text.splitlines():
        for match in URL_RE.finditer(line):
            raw = match.group(0)
            url = raw.rstrip(TRAILING)  # remove pontuação final acidental
            if url not in seen:
                seen.add(url)
                urls.append(url)
    return urls


def normalize_url(url: str) -> str:
    """Normaliza uma URL para comparação.

    Ignora fragmento e barra final. Diferente da versão antiga, NÃO coloca o
    path/query em minúsculas (evita falsos duplicados em servidores
    case-sensitive); apenas esquema e host são normalizados.
    """
    u = (url or "").strip()
    if not u:
        return ""
    u = u.split("#", 1)[0]
    parts = urlsplit(u)
    if parts.scheme or parts.netloc:
        return urlunsplit(
            (parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), parts.query, "")
        )
    return u.rstrip("/")


def is_probably_url(value: str) -> bool:
    return bool(URL_RE.fullmatch((value or "").strip()))
