"""Gera pacotes de distribuição do HLS Downloader Pro.

Uso:
    python exportar.py

Saída em ``dist/``:
    HLS-Downloader-Pro-<versao>-source.zip
    HLS-Downloader-Pro-<versao>-portable-win64.zip   (quando o build existe)
    SHA256SUMS.txt

O ZIP portátil inclui ``portable.flag``: settings, logs e ferramentas ficam
ao lado do executável, sem gravar em %APPDATA%.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from hlsdl.exporter import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
