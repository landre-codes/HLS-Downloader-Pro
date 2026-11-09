"""Diálogos nativos com os botões traduzidos pelo aplicativo.

``QMessageBox`` usa os textos padrão do Qt ("OK", "Cancel", ...), que podem
ficar em inglês mesmo quando a interface está em outro idioma. Este helper
troca o texto do botão padrão e mantém o restante do diálogo nativo.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

from .i18n import DEFAULT_LANG, tr


def show_message(
    parent: QWidget | None,
    icon: QMessageBox.Icon,
    title: str,
    text: str,
    lang: str = DEFAULT_LANG,
) -> int:
    """Mostra um ``QMessageBox`` modal com o botão OK no idioma atual."""
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    button = box.button(QMessageBox.StandardButton.Ok)
    if button is not None:
        button.setText(tr(lang, "btn_ok"))
    return int(box.exec())
