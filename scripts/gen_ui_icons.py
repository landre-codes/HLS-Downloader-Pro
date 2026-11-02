"""Gera os ícones SVG da interface (tema claro/escuro).

Execute apenas se quiser regenerar: python scripts/gen_ui_icons.py
"""

from __future__ import annotations

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "hlsdl", "ui", "icons")

COLORS = {"light": "#3c4043", "dark": "#dfe3e8"}

# path/stroke por ícone (viewBox 24x24)
PATHS = {
    "edit": '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
    "copy": (
        '<rect x="9" y="9" width="12" height="12" rx="2"/>'
        '<path d="M5 15V5a2 2 0 0 1 2-2h10"/>'
    ),
    "retry": '<path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 3v6h-6"/>',
    "cancel": '<path d="M18 6 6 18M6 6l12 12"/>',
    "open": (
        '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8'
        'a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>'
    ),
    "play": '<path d="M8 5v14l11-7Z" fill="COLOR" stroke="none"/>',
}

TEMPLATE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
    'fill="none" stroke="COLOR" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round">{body}</svg>\n'
)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    for theme, color in COLORS.items():
        for name, body in PATHS.items():
            content = TEMPLATE.format(body=body.replace("COLOR", color))
            content = content.replace("COLOR", color)
            with open(os.path.join(OUT, f"{name}_{theme}.svg"), "w", encoding="utf-8") as fh:
                fh.write(content)
    print("ícones gerados em", OUT)


if __name__ == "__main__":
    main()
