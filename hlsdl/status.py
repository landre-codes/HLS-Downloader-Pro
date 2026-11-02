"""Estados possíveis de um item da fila.

O status é a fonte única de verdade do domínio. A UI apenas o traduz em
texto (``s_<status>`` no ``i18n.js``) — nunca compara strings de apresentação.
"""

from __future__ import annotations

from enum import Enum


class Status(str, Enum):
    WAITING = "waiting"
    ANALYZING = "analyzing"
    DOWNLOADING = "downloading"
    ENCODING = "encoding"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"

    @property
    def is_final(self) -> bool:
        return self in FINAL


FINAL = frozenset({Status.DONE, Status.ERROR, Status.CANCELLED})

# Estados que representam um worker ativo (ocupando uma vaga de concorrência).
ACTIVE = frozenset({Status.ANALYZING, Status.DOWNLOADING, Status.ENCODING})
