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
import time

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


def shutdown_threads(
    threads: dict,
    *,
    timeout: float = 6.0,
    label: str = "thread",
    cancel=None,
) -> dict:
    """Cancela e aguarda as QThreads de um scheduler.

    ``threads`` é o dicionário ``id -> (QThread, worker, item)`` usado por
    ``QueueManager`` e ``CompressionManager``. Nunca descartamos a referência
    de uma thread ainda em execução: destruir uma ``QThread`` rodando faz o Qt
    abortar o processo com ``0xC0000409``. Se o cancelamento cooperativo não
    bastar dentro do prazo, encerramos a thread como último recurso e
    registramos a saída de emergência.

    Retorna um novo dicionário apenas com as threads que continuaram vivas.
    """
    if cancel is not None:
        cancel()
    deadline = time.monotonic() + timeout
    for thread, worker, _item in list(threads.values()):
        remaining = max(0.0, deadline - time.monotonic())
        try:
            thread.quit()
            if thread.wait(int(remaining * 1000)):
                continue
            log.warning(
                "%s %s não terminou em %.1fs; encerrando à força",
                label,
                thread.objectName() or thread,
                timeout,
            )
            try:
                worker.cancel()
            except Exception:
                log.exception("falha ao cancelar worker de %s", label)
            thread.terminate()
            if not thread.wait(2000):
                log.critical(
                    "%s %s continua viva após terminate; "
                    "registrando saída de emergência",
                    label,
                    thread,
                )
                note_stuck_qthread(thread)
        except RuntimeError:
            # Objeto C++ já destruído: nada a fazer.
            pass
    return {
        key: entry for key, entry in threads.items()
        if not entry[0].isFinished()
    }
