"""Proteção de encerramento para QThreads que não puderam ser canceladas.

Destruir um ``QThread`` ainda em execução faz o Qt abortar o processo com
``0xC0000409``. Se nem o cancelamento cooperativo nem ``terminate()``
conseguirem parar uma thread (por exemplo, uma chamada nativa bloqueada),
registramos a thread e, no encerramento normal do interpretador, saímos com
``os._exit`` antes que o Qt tente destruí-la.

Isso só acontece no caminho de emergência: downloads já foram cancelados,
settings já foram salvos e o log é descarregado antes da saída.
"""

from __future__ import annotations

import atexit
import logging
import os

log = logging.getLogger("hlsdl")

_STUCK: list = []
_REGISTERED = False


def _force_exit() -> None:
    alive = False
    for thread in list(_STUCK):
        try:
            if thread.isRunning():
                alive = True
        except RuntimeError:
            continue
    if not alive:
        return
    log.critical(
        "QThread(s) ainda em execução no encerramento; "
        "saindo sem destruir objetos Qt"
    )
    try:
        logging.shutdown()
    except Exception:
        pass
    os._exit(0)


def note_stuck_qthread(thread) -> None:
    """Marca uma QThread que sobreviveu ao shutdown para a saída de emergência."""
    global _REGISTERED
    _STUCK.append(thread)
    if not _REGISTERED:
        atexit.register(_force_exit)
        _REGISTERED = True
