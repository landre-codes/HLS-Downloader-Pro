"""Persistent download/compression queue snapshots."""

from __future__ import annotations

import logging
import os

from .integrity import read_json, write_json_atomic

log = logging.getLogger("hlsdl")
VERSION = 1


def save(path: str, downloads: list[dict], compression: list[dict]) -> None:
    payload = {
        "version": VERSION,
        "downloads": [
            {
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "status": getattr(item.get("status"), "value", str(item.get("status") or "")),
            }
            for item in downloads
            if item.get("url")
        ],
        "compression": [
            {"input": item.get("input", "")}
            for item in compression
            if item.get("input")
            and getattr(item.get("status"), "value", str(item.get("status") or ""))
            not in ("done", "cancelled", "skipped")
        ],
    }
    try:
        write_json_atomic(path, payload)
    except OSError:
        log.exception("não foi possível salvar a fila em %s", path)


def load(path: str) -> dict:
    data = read_json(path)
    if not data or int(data.get("version") or 0) != VERSION:
        return {"downloads": [], "compression": []}
    downloads = [
        item for item in data.get("downloads") or []
        if isinstance(item, dict) and item.get("url")
    ]
    compression = [
        item for item in data.get("compression") or []
        if isinstance(item, dict) and item.get("input")
    ]
    return {"downloads": downloads, "compression": compression}


def clear(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass
