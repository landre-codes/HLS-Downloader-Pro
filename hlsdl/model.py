"""Modelo da fila consumido pelo QML — dono único dos dados.

Cada item é um ``dict`` com as chaves: ``id``, ``url``, ``title``, ``status``
(``Status``), ``progress`` (float), ``speed``, ``size``, ``error`` e,
opcionalmente, ``path``/``thumb``. O ``QueueManager`` opera sobre a MESMA
lista exposta por :meth:`items` — corrige o bug de dessincronização em que
remoções afetavam apenas uma das cópias.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QModelIndex,
    QObject,
    QSortFilterProxyModel,
    Qt,
    Signal,
    Slot,
)

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
    ID = Qt.ItemDataRole.UserRole + 10
    SOURCE_INDEX = Qt.ItemDataRole.UserRole + 11

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
            self.ID: b"id",
            self.SOURCE_INDEX: b"sourceIndex",
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    @Slot(result="QVariantList")
    def snapshot(self) -> list[dict]:
        """Cópia somente-leitura para filtros/ordenação de exibição no QML.

        A ordem de ``_items`` permanece intacta: ela é a ordem de agendamento
        do :class:`QueueManager`. O snapshot carrega ``sourceIndex`` para que
        as ações da interface continuem apontando para o item correto mesmo
        quando a tabela é filtrada ou ordenada apenas visualmente.
        """
        rows: list[dict] = []
        for index, item in enumerate(self._items):
            status = item.get("status", Status.WAITING)
            rows.append({
                "sourceIndex": index,
                "title": item.get("title") or item.get("url", ""),
                "url": item.get("url", ""),
                "status": status.value if isinstance(status, Status) else str(status),
                "progress": round(float(item.get("progress", 0.0)), 1),
                "speed": item.get("speed", "-"),
                "size": item.get("size", "-"),
                "error": item.get("error", ""),
                "path": item.get("path", ""),
                "thumb": item.get("thumb", ""),
            })
        return rows

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
        if role == self.ID:
            return item.get("id", 0)
        if role == self.SOURCE_INDEX:
            return index.row()
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


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    return "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()


_STATUS_RANK = {
    "analyzing": 0,
    "downloading": 1,
    "encoding": 2,
    "verifying": 3,
    "waiting": 4,
    "paused": 5,
    "done": 6,
    "error": 7,
    "cancelled": 8,
    "skipped": 9,
}


class DownloadFilterProxyModel(QSortFilterProxyModel):
    """Filtro/ordenação de apresentação da fila de downloads.

    A ordem real continua em :class:`DownloadModel`/``QueueManager``. O proxy
    expõe ``sourceIndex`` para que as ações da UI nunca dependam da posição
    visual; a identidade estável também está no papel ``id``.
    """

    filterTextChanged = Signal()
    sortChanged = Signal()

    _ALIASES = {
        "status": "status",
        "titulo": "name",
        "título": "name",
        "nome": "name",
        "name": "name",
        "url": "name",
        "erro": "error",
        "error": "error",
        "tamanho": "speed",
        "size": "speed",
        "velocidade": "speed",
        "progresso": "progress",
        "progress": "progress",
    }

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._filter_text = ""
        self._status_labels: dict[str, str] = {}
        self._sort_key = ""
        self._sort_ascending = True
        # Ordenação é aplicada ao clicar no cabeçalho; progresso não deve
        # reordenar linhas continuamente durante o download.
        self.setDynamicSortFilter(False)

    @Property(str, notify=filterTextChanged)
    def filterText(self) -> str:
        return self._filter_text

    @filterText.setter
    def filterText(self, value: str) -> None:
        value = str(value or "")
        if value == self._filter_text:
            return
        self._filter_text = value
        self.invalidate()
        self.filterTextChanged.emit()

    @Property("QVariantMap", notify=filterTextChanged)
    def statusLabels(self) -> dict:
        return dict(self._status_labels)

    @statusLabels.setter
    def statusLabels(self, value) -> None:
        self._status_labels = {
            str(key): str(label) for key, label in dict(value or {}).items()
        }
        self.invalidate()

    @Property(str, notify=sortChanged)
    def sortKey(self) -> str:
        return self._sort_key

    @Property(bool, notify=sortChanged)
    def sortAscending(self) -> bool:
        return self._sort_ascending

    @Slot(str)
    def sortBy(self, key: str) -> None:
        if key not in ("name", "status", "progress"):
            return
        if key == self._sort_key:
            self._sort_ascending = not self._sort_ascending
        else:
            self._sort_key = key
            self._sort_ascending = key != "progress"
        self.sort(0, Qt.SortOrder.AscendingOrder if self._sort_ascending
                  else Qt.SortOrder.DescendingOrder)
        self.sortChanged.emit()

    def _tokens(self) -> list[tuple[str, str]]:
        tokens: list[tuple[str, str]] = []
        for part in _fold(self._filter_text).split():
            if ":" in part:
                field, term = part.split(":", 1)
                if not term:
                    continue
                tokens.append((self._ALIASES.get(field, ""), term))
            else:
                tokens.append(("", part))
        return tokens

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:  # noqa: N802
        tokens = self._tokens()
        if not tokens:
            return True
        model = self.sourceModel()
        if not isinstance(model, DownloadModel):
            return True
        items = model.items()
        if not (0 <= source_row < len(items)):
            return False
        item = items[source_row]
        status = item.get("status", Status.WAITING)
        status_id = status.value if isinstance(status, Status) else str(status)
        fields = {
            "name": [item.get("title", ""), item.get("url", "")],
            "status": [self._status_labels.get(status_id, status_id)],
            "progress": [f"{round(float(item.get('progress', 0.0)))}%",
                         str(item.get("progress", 0.0))],
            "speed": [item.get("speed", ""), item.get("size", "")],
            "error": [item.get("error", "")],
        }
        for field, term in tokens:
            values = fields.get(field, []) if field else [
                value for group in fields.values() for value in group
            ]
            if not any(term in _fold(value) for value in values):
                return False
        return True

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:  # noqa: N802
        model = self.sourceModel()
        if not isinstance(model, DownloadModel):
            return super().lessThan(left, right)
        items = model.items()
        left_item = items[left.row()]
        right_item = items[right.row()]
        if self._sort_key == "progress":
            a = float(left_item.get("progress", 0.0))
            b = float(right_item.get("progress", 0.0))
        elif self._sort_key == "status":
            def rank(item):
                value = item.get("status", Status.WAITING)
                name = value.value if isinstance(value, Status) else str(value)
                return _STATUS_RANK.get(name, 99)
            a, b = rank(left_item), rank(right_item)
        else:
            a = _fold(left_item.get("title") or left_item.get("url", ""))
            b = _fold(right_item.get("title") or right_item.get("url", ""))
        if a == b:
            return left.row() < right.row()
        return a < b

    def _source_row(self, row: int) -> int:
        if row < 0 or row >= self.rowCount():
            return -1
        return self.mapToSource(self.index(row, 0)).row()

    @Slot(int, result=int)
    def sourceIndexAt(self, row: int) -> int:
        return self._source_row(row)

    @Slot(int, result=str)
    def titleAt(self, row: int) -> str:
        model = self.sourceModel()
        source = self._source_row(row)
        if not isinstance(model, DownloadModel) or source < 0:
            return ""
        item = model.items()[source]
        return str(item.get("title") or item.get("url", ""))

    @Slot(int, result=float)
    def progressAt(self, row: int) -> float:
        model = self.sourceModel()
        source = self._source_row(row)
        if not isinstance(model, DownloadModel) or source < 0:
            return -1.0
        return float(model.items()[source].get("progress", 0.0))
