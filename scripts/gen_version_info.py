"""Gera build/version_info.txt (metadados do .exe para PyInstaller).

Lê a versão de ``hlsdl.__version__`` e escreve o arquivo no formato
VSVersionInfo. Rode antes de empacotar:

    python scripts/gen_version_info.py
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from hlsdl import __version__  # noqa: E402

OUT_DIR = os.path.join(ROOT, "build")
OUT = os.path.join(OUT_DIR, "version_info.txt")

TEMPLATE = """# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={tuple4},
    prodvers={tuple4},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'Landre Codes'),
          StringStruct('FileDescription', 'HLS Downloader Pro'),
          StringStruct('FileVersion', '{version}'),
          StringStruct('InternalName', 'HLS-Downloader-Pro'),
          StringStruct('LegalCopyright', 'Copyright (c) 2026 Landre Codes'),
          StringStruct('OriginalFilename', 'HLS-Downloader-Pro.exe'),
          StringStruct('ProductName', 'HLS Downloader Pro'),
          StringStruct('ProductVersion', '{version}')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def main() -> None:
    parts = (__version__.split(".") + ["0", "0", "0", "0"])[:4]
    nums = []
    for part in parts:
        digits = "".join(ch for ch in part if ch.isdigit())
        nums.append(int(digits or 0))
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(TEMPLATE.format(version=__version__, tuple4=tuple(nums)))
    print("gerado:", OUT, "->", __version__)


if __name__ == "__main__":
    main()
