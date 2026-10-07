"""
copy_button.py
Botón "copiar" que confirma visualmente la copia: cambia a "copiado ✓"
durante un momento y luego vuelve a su estado normal.
"""
from typing import Callable

import pyperclip
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import QTimer

from core.i18n import t

STYLE_COPIED = """
    QPushButton {{
        background: #1a2410;
        border: 1px solid #639922;
        border-radius: 6px;
        padding: {padding};
        font-size: {font_size};
        color: #97C459;
    }}
"""

FEEDBACK_MS = 1500


class CopyButton(QPushButton):
    def __init__(self, get_text: Callable[[], str], style: str,
                 padding: str = "5px 14px", font_size: str = "12px", parent=None):
        super().__init__(t("btn_copy"), parent)
        self._get_text = get_text
        self._style = style
        self._style_copied = STYLE_COPIED.format(padding=padding, font_size=font_size)
        self.setStyleSheet(style)

        # ancho suficiente para "copiado ✓", así el botón no cambia de tamaño
        fm = self.fontMetrics()
        self.setMinimumWidth(max(fm.horizontalAdvance(t("btn_copy")),
                                 fm.horizontalAdvance(t("btn_copied"))) + 40)

        self._reset_timer = QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.setInterval(FEEDBACK_MS)
        self._reset_timer.timeout.connect(self.reset)

        self.clicked.connect(self._copy)

    def _copy(self):
        text = self._get_text()
        if not text:
            return
        try:
            pyperclip.copy(text)
        except Exception:
            return
        self.setText(t("btn_copied"))
        self.setStyleSheet(self._style_copied)
        self._reset_timer.start()   # reinicia el contador si se vuelve a pulsar

    def reset(self):
        self._reset_timer.stop()
        self.setText(t("btn_copy"))
        self.setStyleSheet(self._style)
