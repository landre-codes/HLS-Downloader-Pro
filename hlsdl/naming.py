"""Nomes de arquivo estáveis e resolução do arquivo realmente gravado."""

from __future__ import annotations

import hashlib
import logging
import os
import re

log = logging.getLogger("hlsdl")

# Caracteres proibidos no Windows (ASCII) e seus equivalentes fullwidth que o
# yt-dlp usa ao sanitizar com --windows-filenames (ex.: '?' -> '？' U+FF1F).
_INVALID_CHARS_RE = re.compile(
    r"[?*<>|\":/\\\uFF1F\uFF0A\uFF1C\uFF1E\uFF5C\uFF02\uFF1A\uFF0F]"
)


def normalize_name(name: str) -> str:
    """Remove caracteres proibidos/fullwidth de um nome de arquivo."""
    return _INVALID_CHARS_RE.sub("", name).lower()


def url_digest(url: str, length: int = 10) -> str:
    """Hash curto e estável de uma URL (mesmo link -> mesmo nome de arquivo)."""
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:length]


def resolve_existing_file(path: str) -> str:
    """Retorna o caminho real de um arquivo recém-baixado.

    O yt-dlp (algumas versões) imprime em ``after_move:filepath`` um caminho
    sanitizado que NÃO corresponde ao nome gravado no disco (o arquivo fica
    com caracteres fullwidth, ex.: '?'). Então ``os.path.exists`` falha mesmo
    com o download concluído. Aqui procuramos o arquivo no diretório pelo
    nome normalizado (sem caracteres proibidos/fullwidth).
    """
    if path and os.path.exists(path):
        return path
    if not path:
        return ""
    d, base = os.path.split(path)
    want = normalize_name(base)
    if not want:
        return ""
    try:
        candidates = [
            os.path.join(d, n) for n in os.listdir(d) if normalize_name(n) == want
        ]
    except OSError:
        return ""
    if not candidates:
        return ""
    # se houver mais de um, prefere o mais recente (acabou de ser baixado)
    try:
        candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    except OSError:
        pass
    return candidates[0]


def shorten_name(path: str, limit: int = 20) -> str:
    """Renomeia o arquivo para um nome curto (base <= ``limit`` caracteres).

    O limite é aplicado por CARACTERES (não bytes), então nunca quebra
    acentos/UTF-8. Se já está curto, devolve o caminho sem mexer.
    """
    folder, name = os.path.split(path)
    base, ext = os.path.splitext(name)
    if len(base) <= limit:
        return path
    base = base[:limit].rstrip(" ._-")
    if not base:
        base = "video"
    target = os.path.join(folder, base + ext)
    n = 2
    while os.path.exists(target) and os.path.normcase(target) != os.path.normcase(path):
        target = os.path.join(folder, f"{base}-{n}{ext}")
        n += 1
    if os.path.normcase(target) == os.path.normcase(path):
        return path
    try:
        os.rename(path, target)
        log.info("nome encurtado: %r -> %r", name, os.path.basename(target))
        return target
    except OSError:
        return path
