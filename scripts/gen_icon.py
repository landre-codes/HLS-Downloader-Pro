"""Gera assets/icon.ico (multi-resolução) e assets/icon.png a partir do design
do icon.svg, usando Pillow. Execute apenas quando o ícone mudar:

    python scripts/gen_icon.py
"""

from __future__ import annotations

import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
S = 1024  # desenha grande e reduz para suavizar as bordas


def main() -> None:
    os.makedirs(ASSETS, exist_ok=True)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = int(S * 4 / 128)
    radius = int(S * 24 / 128)
    draw.rounded_rectangle([pad, pad, S - pad, S - pad], radius=radius, fill="#1e88e5")
    points = [
        (int(x * S / 128), int(y * S / 128))
        for x, y in [(50, 34), (94, 64), (50, 94)]
    ]
    draw.polygon(points, fill="#ffffff")

    ico = os.path.join(ASSETS, "icon.ico")
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico, format="ICO", sizes=sizes)
    img.resize((256, 256), Image.LANCZOS).save(os.path.join(ASSETS, "icon.png"))
    print("gerado:", ico)


if __name__ == "__main__":
    main()
