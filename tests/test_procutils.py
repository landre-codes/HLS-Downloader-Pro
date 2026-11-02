"""Testes dos utilitários de processo (console oculto e kill da árvore)."""

from __future__ import annotations

import os
import subprocess
import sys
import time

from hlsdl.services.procutils import popen_kwargs, spawn_kwargs, terminate_tree


def test_popen_kwargs_hides_console_on_windows():
    kwargs = popen_kwargs()
    if os.name == "nt":
        assert kwargs["creationflags"] & 0x08000000  # CREATE_NO_WINDOW
        assert kwargs["startupinfo"].dwFlags & subprocess.STARTF_USESHOWWINDOW
        assert kwargs["startupinfo"].wShowWindow == subprocess.SW_HIDE
    else:
        assert kwargs == {}


def test_spawn_kwargs_starts_new_session_on_posix():
    kwargs = spawn_kwargs()
    if os.name == "nt":
        assert "creationflags" in kwargs
    else:
        assert kwargs["start_new_session"] is True


def test_terminate_tree_kills_running_process():
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        **spawn_kwargs(),
    )
    try:
        time.sleep(0.3)
        terminate_tree(proc)
        proc.wait(timeout=10)
        assert proc.poll() is not None
    finally:
        if proc.poll() is None:
            proc.kill()
