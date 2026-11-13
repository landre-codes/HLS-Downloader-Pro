"""Shared QThread lifecycle for download/compression schedulers.

Keeping this in one place avoids two copies of a subtle rule: a finished
QThread must be detached and deleted *after* its worker/item references are
cleared, otherwise every job leaks a thread and its captured item dict.
"""

from __future__ import annotations

import logging

from .lifecycle import shutdown_threads

log = logging.getLogger("hlsdl")


class JobThreadRegistry(dict):
    """``id -> (thread, worker, item)`` with deterministic cleanup."""

    @staticmethod
    def _cleanup(entry) -> None:
        try:
            thread, worker, _item = entry
        except (TypeError, ValueError):
            return
        try:
            worker._queue_item = None
        except Exception:
            pass
        try:
            thread.setParent(None)
            thread.deleteLater()
        except Exception:
            log.debug("não foi possível liberar QThread", exc_info=True)

    def pop(self, key, default=None):
        entry = dict.pop(self, key, default)
        if entry is not default:
            self._cleanup(entry)
        return entry

    def replace(self, entries: dict) -> None:
        """Replace the registry contents after a shutdown/recovery."""
        dict.clear(self)
        dict.update(self, entries)

    def shutdown(self, *, timeout: float = 6.0, label: str = "thread",
                 cancel=None) -> None:
        survivors = shutdown_threads(
            dict(self), timeout=timeout, label=label, cancel=cancel
        )
        self.replace(survivors)
