"""Diagnóstico rápido do HLS Downloader Pro.

Uso:
    python diagnostico.py

Também disponível no executável: ``HLS-Downloader-Pro.exe --diagnose``.
Gera ``diagnostico-hlsdl.txt`` e imprime o relatório.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from hlsdl.diagnostics import run  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(run())
