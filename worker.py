"""Fachada de compatibilidade do motor de download.

O código real vive em :mod:`hlsdl`. Mantido para scripts, testes e
importações antigas (``from worker import DownloadModel, ...``).
"""

from __future__ import annotations

from hlsdl.config import USER_AGENT
from hlsdl.downloader import FFMPEG_SIZE_RE, FFMPEG_TIME_RE, PROGRESS_RE, DownloadWorker
from hlsdl.model import DownloadModel, make_item
from hlsdl.naming import normalize_name, resolve_existing_file, shorten_name, url_digest
from hlsdl.queue import QueueManager
from hlsdl.services.procutils import (
    cleanup_thumbs,
    extract_thumbnail,
    probe_duration,
)
from hlsdl.services.procutils import (
    which as _which,
)
from hlsdl.services.scraper import HAS_SCRAPER, HtmlMediaScraper
from hlsdl.status import ACTIVE, FINAL, Status
from hlsdl.urlutils import extract_urls, normalize_url

__all__ = [
    "DownloadModel",
    "QueueManager",
    "DownloadWorker",
    "Status",
    "FINAL",
    "ACTIVE",
    "make_item",
    "extract_urls",
    "normalize_url",
    "normalize_name",
    "resolve_existing_file",
    "shorten_name",
    "url_digest",
    "cleanup_thumbs",
    "extract_thumbnail",
    "probe_duration",
    "_which",
    "HtmlMediaScraper",
    "HAS_SCRAPER",
    "USER_AGENT",
    "PROGRESS_RE",
    "FFMPEG_TIME_RE",
    "FFMPEG_SIZE_RE",
]
