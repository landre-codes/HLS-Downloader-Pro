"""Modelo da fila consumido pelo QML — dono único dos dados.

Cada item é um ``dict`` com as chaves: ``id``, ``url``, ``title``, ``status``
(``Status``), ``progress`` (float), ``speed``, ``size``, ``error`` e,
opcionalmente, ``path``/``thumb``. O ``QueueManager`` opera sobre a MESMA
lista exposta por :meth:`items` — corrige o bug de dessincronização em que
remoções afetavam apenas uma das cópias.
"""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Qt

from .status import Status


def make_item(item_id: int, url: str) -> dict:
    """Cria um item de fila no estado inicial."""
    return {
        "id": item_id,
        "url": url,
        "title": url,
        "status": Status.WAITING,
        "progress": 0.0,
        "speed": "—",
        "size": "—",
        "error": "",
    }


class DownloadModel(QAbstractListModel):
    """Expõe a fila de downloads como um modelo de lista."""

    URL = int(Qt.ItemDataRole.UserRole) + 1
    TITLE = Qt.ItemDataRole.UserRole + 2
    STATUS = Qt.ItemDataRole.UserRole + 3
    PROGRESS = Qt.ItemDataRole.UserRole + 4
    SPEED = Qt.ItemDataRole.UserRole + 5
    SIZE = Qt.ItemDataRole.UserRole + 6
    ERROR = Qt.ItemDataRole.UserRole + 7
    PATH = Qt.ItemDataRole.UserRole + 8
    THUMB = Qt.ItemDataRole.UserRole + 9

    def __init__(self, items: list[dict] | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self._items: list[dict] = items if items is not None else []

    # -------------------------------------------------------------- dados
    def items(self) -> list[dict]:
        """A lista viva de itens (compartilhada com o QueueManager)."""
        return self._items

    def roleNames(self) -> dict:
        return {
            self.URL: b"url",
            self.TITLE: b"title",
            self.STATUS: b"status",
            self.PROGRESS: b"progress",
            self.SPEED: b"speed",
            self.SIZE: b"size",
            self.ERROR: b"error",
            self.PATH: b"path",
            self.THUMB: b"thumb",
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        item = self._items[index.row()]
        if role == self.URL:
            return item.get("url", "")
        if role == self.TITLE:
            return item.get("title") or item.get("url", "")
        if role == self.STATUS:
            status = item.get("status", Status.WAITING)
            return status.value if isinstance(status, Status) else str(status)
        if role == self.PROGRESS:
            return round(float(item.get("progress", 0.0)), 1)
        if role == self.SPEED:
            return item.get("speed", "—")
        if role == self.SIZE:
            return item.get("size", "—")
        if role == self.ERROR:
            return item.get("error", "")
        if role == self.PATH:
            return item.get("path", "")
        if role == self.THUMB:
            return item.get("thumb", "")
        return None

    # ----------------------------------------------- mutações (com notificação)
    def add(self, item: dict) -> None:
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(item)
        self.endInsertRows()

    def touch(self, row: int) -> None:
        """Notifica o QML de que a linha ``row`` mudou."""
        if not (0 <= row < len(self._items)):
            return
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx)

    def index_of(self, item: dict) -> int:
        try:
            return self._items.index(item)
        except ValueError:
            return -1

    def remove_rows(self, rows: Iterable[int]) -> None:
        """Remove as linhas (ordem decrescente) da lista compartilhada."""
        for row in sorted(set(rows), reverse=True):
            if 0 <= row < len(self._items):
                self.beginRemoveRows(QModelIndex(), row, row)
                self._items.pop(row)
                self.endRemoveRows()
