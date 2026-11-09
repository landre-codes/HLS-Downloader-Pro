"""Redação de dados sensíveis em logs.

URLs de HLS costumam carregar tokens de sessão na query string
(``?token=...``, ``?hdnts=...``, ``?signature=...``) e o yt-dlp/ffmpeg pode
imprimir a URL completa em mensagens de erro. Este módulo remove esses valores
antes que cheguem aos arquivos de log, preservando nomes de parâmetros e
caminhos para facilitar o diagnóstico.

A redação é aplicada globalmente por :class:`RedactionFilter` em todos os
handlers configurados por :func:`hlsdl.app.setup_logging`.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlsplit, urlunsplit

# Captura URLs em texto livre (inclusive as que terminam em pontuação).
_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
# Cabeçalhos que carregam credenciais.
_AUTH_RE = re.compile(
    r"(?i)\b(authorization\s*:\s*(?:bearer|basic)\s+)[^\s,;]+"
)
_COOKIE_HEADER_RE = re.compile(r"(?i)\b((?:set-)?cookie\s*:\s*)[^\r\n]+")
# Argumentos de linha de comando que apontam para arquivos de cookies.
_COOKIE_FILE_ARG_RE = re.compile(
    r"(?i)(--cookies\s+)(\"[^\"]*\"|'[^']*'|[^\s\"']+)"
)
_BEARER_RE = re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]+")
_TRAILING_PUNCTUATION = ".,;:!?)]}"


def _redact_query(query: str) -> str:
    """Mantém os nomes dos parâmetros e substitui todos os valores por ***."""
    if not query:
        return ""
    pairs: list[str] = []
    for pair in query.split("&"):
        if not pair:
            continue
        key, separator, _value = pair.partition("=")
        pairs.append(f"{key}=***" if separator else key)
    return "&".join(pairs)


def _redact_url(url: str) -> str:
    """Remove credenciais, query string e fragmento de uma URL."""
    suffix = ""
    while url and url[-1] in _TRAILING_PUNCTUATION:
        suffix = url[-1] + suffix
        url = url[:-1]
    try:
        parts = urlsplit(url)
    except ValueError:
        return url + suffix

    netloc = parts.netloc
    if "@" in netloc:
        # user:senha@host -> ***@host
        netloc = "***@" + netloc.rsplit("@", 1)[1]
    query = _redact_query(parts.query)
    fragment = "***" if parts.fragment else ""
    return urlunsplit((parts.scheme, netloc, parts.path, query, fragment)) + suffix


def redact_text(text: str) -> str:
    """Redige URLs assinadas, tokens, cookies e cabeçalhos de autorização."""
    if not text:
        return text or ""
    text = _AUTH_RE.sub(r"\1***", text)
    text = _BEARER_RE.sub(r"\1***", text)
    text = _COOKIE_HEADER_RE.sub(r"\1***", text)
    text = _COOKIE_FILE_ARG_RE.sub(r"\1***", text)
    text = _URL_RE.sub(lambda match: _redact_url(match.group(0)), text)
    return text


class RedactionFilter(logging.Filter):
    """Filtro de logging que redige a mensagem final e tracebacks."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            # Não impeça a emissão do log por causa de um formato inválido.
            return True
        redacted = redact_text(message)
        if redacted != message:
            record.msg = redacted
            record.args = ()

        if record.exc_info and not record.exc_text:
            try:
                record.exc_text = logging.Formatter().formatException(record.exc_info)
            except Exception:
                record.exc_text = None
        if record.exc_text:
            record.exc_text = redact_text(record.exc_text)
        if record.stack_info:
            record.stack_info = redact_text(record.stack_info)
        return True
