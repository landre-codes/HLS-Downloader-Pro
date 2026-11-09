"""Carrega os itens de uma playlist (YouTube ou sites em geral) via yt-dlp.

Usa ``--flat-playlist --dump-single-json`` para listar as entradas sem baixar
nada. Roda em thread separada e reporta por sinais Qt.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
from collections.abc import Callable

from PySide6.QtCore import QObject, Signal

from . import config
from .i18n import translator
from .services.procutils import spawn_kwargs, terminate_tree, which

log = logging.getLogger("hlsdl")


class PlaylistLoader(QObject):
    """Lista as entradas de uma playlist para seleção na interface."""

    loadingChanged = Signal(bool)
    loaded = Signal(list)   # [{index, id, title, url, duration, thumb}]
    failed = Signal(str)

    def __init__(self, translate: Callable[..., str] | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self._t = translate or translator("pt")
        self._busy = False
        self._cancel = False
        self._proc = None

    def set_translator(self, fn: Callable[..., str]) -> None:
        self._t = fn

    def _ytdlp_argv(self) -> list[str] | None:
        if not config.is_frozen():
            try:
                import yt_dlp  # noqa: F401

                return [sys.executable, "-m", "yt_dlp"]
            except ImportError:
                pass
        binary = which("yt-dlp")
        return [binary] if binary else None

    def _cookies_args(self, cookies: str) -> list[str]:
        if not cookies:
            return []
        if cookies.startswith("browser:"):
            name = cookies[len("browser:"):].strip().lower()
            return ["--cookies-from-browser", name] if name else []
        if cookies.startswith("file:"):
            path = cookies[len("file:"):].strip()
            return ["--cookies", path] if path and os.path.isfile(path) else []
        return []

    def load(self, url: str, limit: int = 200, cookies: str = "") -> None:
        """Inicia a listagem da playlist (não bloqueia a interface)."""
        if self._busy:
            return
        url = (url or "").strip()
        if not url:
            self.failed.emit(self._t("playlist_invalid"))
            return
        argv = self._ytdlp_argv()
        if not argv:
            self.failed.emit(self._t("err_ytdlp_missing"))
            return
        self._cancel = False
        self._busy = True
        self.loadingChanged.emit(True)
        threading.Thread(
            target=self._run, args=(argv, url, int(limit), cookies), daemon=True
        ).start()

    def _run(self, argv: list[str], url: str, limit: int, cookies: str) -> None:
        proc = None
        try:
            cmd = argv + [
                "--flat-playlist",
                "--dump-single-json",
                "--no-warnings",
                "--ignore-errors",
            ]
            if limit > 0:
                cmd += ["--playlist-end", str(limit)]
            cmd += self._cookies_args(cookies)
            cmd.append(url)
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                **spawn_kwargs(),
            )
            self._proc = proc
            try:
                out, err = proc.communicate(timeout=180)
            except subprocess.TimeoutExpired:
                terminate_tree(proc)
                out, err = proc.communicate()
                if not self._cancel:
                    self.failed.emit(self._t("playlist_load_failed", err="timeout"))
                return
            if self._cancel:
                return
            if proc.returncode != 0 and not (out or "").strip():
                msg = (err or "").strip().splitlines()
                self.failed.emit(msg[-1] if msg else self._t("playlist_load_failed", err=""))
                return
            data = json.loads(out or "{}")
            entries = data.get("entries") or [data]
            items = []
            for i, entry in enumerate(entries):
                if not entry:
                    continue
                item = self._to_item(entry, i)
                if item["url"]:
                    items.append(item)
            if not items:
                self.failed.emit(self._t("playlist_empty"))
                return
            self.loaded.emit(items)
        except Exception as exc:
            if not self._cancel:
                log.exception("falha ao carregar playlist")
                self.failed.emit(self._t("playlist_load_failed", err=exc))
        finally:
            self._proc = None
            self._busy = False
            self.loadingChanged.emit(False)

    def cancel(self) -> None:
        """Cancela a listagem em andamento (chamado ao fechar o app)."""
        self._cancel = True
        terminate_tree(self._proc)

    @staticmethod
    def _to_item(entry: dict, index: int) -> dict:
        title = entry.get("title") or entry.get("id") or f"#{index + 1}"
        url = entry.get("webpage_url") or entry.get("url") or ""
        video_id = entry.get("id") or ""
        if not str(url).startswith("http"):
            # Em modo --flat-playlist o YouTube traz apenas o ID. Outros
            # extractores também podem trazer só o ID; nesse caso não
            # inventamos uma URL do YouTube.
            extractor = str(
                entry.get("ie_key") or entry.get("extractor_key") or ""
            ).lower()
            if video_id and ("youtube" in extractor or not extractor):
                url = f"https://www.youtube.com/watch?v={video_id}"
            else:
                url = ""
        thumbs = entry.get("thumbnails") or []
        thumb = thumbs[-1].get("url", "") if thumbs else ""
        return {
            "index": index + 1,
            "id": video_id,
            "title": title,
            "url": url,
            "duration": entry.get("duration") or 0,
            "thumb": thumb,
        }
