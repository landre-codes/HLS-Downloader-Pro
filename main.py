"""Fachada de compatibilidade do entry point.

O código real vive em :mod:`hlsdl`. Este módulo existe para preservar
``python main.py``, o empacotamento PyInstaller e os scripts/testes antigos.
"""

from __future__ import annotations

import sys

from hlsdl.app import (
    SingleInstance,
    _raise_window,
    _restore_geometry,
    _single_instance,
    main,
    setup_logging,
)
from hlsdl.bridge import Bridge
from hlsdl.config import (
    default_output_folder,
    log_path,
    qml_path,
    settings_path,
)
from hlsdl.i18n import tr
from hlsdl.model import DownloadModel, make_item
from hlsdl.queue import QueueManager
from hlsdl.status import Status

__all__ = [
    "main",
    "Bridge",
    "DownloadModel",
    "QueueManager",
    "Status",
    "default_output_folder",
    "settings_path",
    "qml_path",
    "log_path",
    "tr",
    "make_item",
    "SingleInstance",
    "setup_logging",
    "_single_instance",
    "_restore_geometry",
    "_raise_window",
]

if __name__ == "__main__":
    sys.exit(main())
