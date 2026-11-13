# ruff: noqa: F401, F403, F405

from __future__ import annotations

import os

from PySide6.QtCore import Property, Slot
from PySide6.QtWidgets import QApplication, QFileDialog

from ..status import FINAL as FINAL_STATUSES
from ..urlutils import extract_urls, normalize_url
from .signals import *


class DownloadsMixin(BridgeSignals):

    @Property("QVariantMap", notify=lastItemChanged)
    def lastItem(self) -> dict:
        return self._last_item

    def _on_item_updated(self, item: dict) -> None:
        # A aba Individual sÃ³ reflete o item iniciado por downloadSingle().
        if self._single_item_id is None or item.get("id") != self._single_item_id:
            return
        status = item.get("status")
        self._last_item = {
            "url": item.get("url", ""),
            "title": item.get("title") or item.get("url", ""),
            "status": getattr(status, "value", str(status)),
            "progress": round(float(item.get("progress", 0.0)), 1),
            "speed": item.get("speed", "â€”"),
            "size": item.get("size", "â€”"),
            "error": item.get("error", ""),
            "path": item.get("path", ""),
            "thumbnail": item.get("thumb", ""),
        }
        self.lastItemChanged.emit()

    def _sync_single_item(self) -> None:
        """Limpa o card individual se o item saiu da fila individual."""
        if self._single_item_id is None:
            return
        if any(i["id"] == self._single_item_id for i in self.single_manager.items):
            return
        self._single_item_id = None
        self._last_item = {}
        self.lastItemChanged.emit()

    def _single_row(self) -> int:
        if self._single_item_id is None:
            return -1
        for row, item in enumerate(self.single_manager.items):
            if item.get("id") == self._single_item_id:
                return row
        return -1

    @Property(bool, notify=queueActiveChanged)
    def queueActive(self) -> bool:
        return self._queue_active

    @Property(bool, notify=queuePausedChanged)
    def queuePaused(self) -> bool:
        return self._queue_paused

    def _on_queue_state(self, active: bool, paused: bool) -> None:
        if active != self._queue_active:
            self._queue_active = active
            self.queueActiveChanged.emit(active)
        if paused != self._queue_paused:
            self._queue_paused = paused
            self.queuePausedChanged.emit(paused)

    @Slot(str)
    def addLinksAndStart(self, text: str) -> None:
        """Adiciona links (ex.: selecionados de uma playlist) e inicia a fila."""
        if self._deps_busy:
            self.notifyText.emit(self._tr("deps_busy_start"))
            return
        added, skipped = self.manager.addText(text, self._single_active_urls())
        if added:
            self.notifyText.emit(self._tr("links_added", a=added))
        elif skipped:
            self.notifyText.emit(self._tr("links_skipped", s=skipped))
        self.manager.start()

    def _single_active_urls(self) -> list[str]:
        return self.single_manager.active_urls()

    @Slot(str, result=int)
    def addLinks(self, text: str) -> int:
        added, skipped = self.manager.addText(text, self._single_active_urls())
        if added and skipped:
            self.notifyText.emit(self._tr("links_added_skipped", a=added, s=skipped))
        elif added:
            self.notifyText.emit(self._tr("links_added", a=added))
        elif skipped:
            self.notifyText.emit(self._tr("links_skipped", s=skipped))
        else:
            self.notifyText.emit(self._tr("no_links"))
        return added

    @Slot(result=int)
    def pasteFromClipboard(self) -> int:
        text = QApplication.clipboard().text()
        if text.strip():
            return self.addLinks(text)
        self.notifyText.emit(self._tr("clipboard_empty"))
        return 0

    @Slot()
    def importTxt(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            None,
            self._tr("dlg_links"),
            "",
            self._tr("filter_text"),
        )
        if path:
            self.importTxtPath(path)

    @staticmethod
    def _decode_text_file(raw: bytes) -> str:
        """Decode UTF-8/UTF-16/ANSI text files from Windows and Linux."""
        if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
            candidates = ("utf-16", "utf-16-le", "utf-16-be")
        elif raw.startswith(b"\xef\xbb\xbf"):
            candidates = ("utf-8-sig", "utf-8")
        else:
            candidates = ("utf-8", "utf-8-sig", "cp1252", "latin-1")
        for encoding in candidates:
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")

    @Slot(str)
    def importTxtPath(self, path: str) -> None:
        """LÃª um .txt (usado pelo botÃ£o e pelo arrastar-e-soltar)."""
        if not path:
            return
        try:
            with open(path, "rb") as handle:
                raw = handle.read()
            content = self._decode_text_file(raw)
        except OSError as exc:
            self.notifyText.emit(self._tr("read_failed", err=exc))
            return
        self.addLinks(content)

    @Slot(str, result=bool)
    def downloadSingle(self, url: str) -> bool:
        """Adiciona um Ãºnico link Ã  fila individual e a inicia.

        Retorna True apenas quando um link vÃ¡lido foi adicionado; o QML usa
        esse retorno para limpar o campo somente em caso de sucesso.
        """
        if self._deps_busy:
            self.notifyText.emit(self._tr("deps_busy_start"))
            return False
        url = (url or "").strip()
        if not url:
            self.notifyText.emit(self._tr("no_links"))
            return False
        urls = extract_urls(url)
        if not urls:
            self.notifyText.emit(self._tr("no_links"))
            return False
        if len(urls) > 1:
            self.notifyText.emit(self._tr("single_multiple"))
            return False
        url = urls[0]
        normalized = normalize_url(url)
        # Evita baixar de novo algo que jÃ¡ estÃ¡ ativo no lote. Itens
        # finalizados podem ser reenfileirados.
        if self.manager.has_active_url(url):
            self.notifyText.emit(self._tr("links_skipped", s=1))
            return False
        if self.single_manager.has_active_url(url):
            self.notifyText.emit(self._tr("links_skipped", s=1))
            return False

        current_row = self._single_row()
        if current_row >= 0:
            current = self.single_manager.items[current_row]
            if current["status"] not in FINAL_STATUSES:
                if normalize_url(current["url"]) == normalized:
                    self._on_item_updated(current)
                    self.notifyText.emit(self._tr("links_skipped", s=1))
                else:
                    self.notifyText.emit(self._tr("single_busy"))
                return False

        self.single_manager.clearFinished()
        self._sync_single_item()
        before = len(self.single_manager.items)
        added, skipped = self.single_manager.addText(url)
        if added:
            item = self.single_manager.items[before]
            self._single_item_id = item["id"]
            self._on_item_updated(item)
            self.single_manager.start()
            return True
        if skipped:
            # Duplicado ativo na fila individual: foca o item existente.
            match = next(
                (i for i in reversed(self.single_manager.items)
                 if normalize_url(i["url"]) == normalized),
                None,
            )
            if match is not None:
                self._single_item_id = match["id"]
                self._on_item_updated(match)
            self.notifyText.emit(self._tr("links_skipped", s=1))
        else:
            self.notifyText.emit(self._tr("no_links"))
        return False

    @Slot()
    def cancelSingle(self) -> None:
        row = self._single_row()
        if row >= 0:
            self.single_manager.cancelItem(row)
            self.notifyText.emit(self._tr("item_cancelled"))

    @Slot()
    def retrySingle(self) -> None:
        if self._deps_busy:
            self.notifyText.emit(self._tr("deps_busy_start"))
            return
        row = self._single_row()
        if row >= 0:
            self.single_manager.retryItem(row)
            self.single_manager.start()

    @Slot()
    def startQueue(self) -> None:
        if self._deps_busy:
            self.notifyText.emit(self._tr("deps_busy_start"))
            return
        self.manager.start()
        self.notifyText.emit(self._tr("queue_started"))

    @Slot()
    def pauseQueue(self) -> None:
        self.manager.pause()
        self.notifyText.emit(self._tr("queue_paused"))

    @Slot()
    def resumeQueue(self) -> None:
        self.manager.resume()
        self.notifyText.emit(self._tr("queue_resumed"))

    @Slot()
    def cancelAll(self) -> None:
        self.manager.cancelAll()
        self.notifyText.emit(self._tr("downloads_cancelled"))

    @Slot(int)
    def cancelItem(self, row: int) -> None:
        self.manager.cancelItem(row)
        self.notifyText.emit(self._tr("item_cancelled"))

    @Slot(int)
    def removeItem(self, row: int) -> None:
        self.manager.removeItem(row)
        self._sync_single_item()
        self.notifyText.emit(self._tr("item_removed"))

    @Slot(int)
    def retryItem(self, row: int) -> None:
        if self._deps_busy:
            self.notifyText.emit(self._tr("deps_busy_start"))
            return
        self.manager.retryItem(row)

    @Slot(int, str)
    def editUrl(self, row: int, new_url: str) -> bool:
        ok = self.manager.editUrl(row, new_url)
        self.notifyText.emit(self._tr("link_updated" if ok else "link_update_failed"))
        return ok

    @Slot(str)
    def copyLink(self, url: str) -> None:
        QGuiApplication.clipboard().setText(url)
        self.notifyText.emit(self._tr("link_copied"))

    @Slot()
    def clearFinished(self) -> None:
        self.manager.clearFinished()
        self._sync_single_item()

    @Slot()
    def clearAll(self) -> None:
        self.manager.clearAll()
        self.single_manager.clearAll()
        self._single_item_id = None
        self._last_item = {}
        self.lastItemChanged.emit()


