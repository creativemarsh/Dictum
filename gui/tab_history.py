import pyperclip
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea,
)
from PyQt6.QtCore import Qt
import history as hist

STYLE_CARD = """
    QFrame {
        background: #111116;
        border: 1px solid #2c2c2a;
        border-radius: 8px;
    }
"""
STYLE_BTN = """
    QPushButton {
        background: transparent;
        border: 1px solid #444441;
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 11px;
        color: #888780;
    }
    QPushButton:hover { background: #2c2c2a; color: #e8e6e3; }
"""
STYLE_BTN_DANGER = """
    QPushButton {
        background: transparent;
        border: 1px solid #E24B4A;
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 11px;
        color: #E24B4A;
    }
    QPushButton:hover { background: #3a1515; color: #E24B4A; }
"""


class HistoryCard(QFrame):
    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        self.setStyleSheet(STYLE_CARD)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        ts = QLabel(entry.get("ts", ""))
        ts.setStyleSheet("font-size: 10px; color: #5f5e5a;")
        layout.addWidget(ts)

        text_lbl = QLabel(entry.get("text", ""))
        text_lbl.setWordWrap(True)
        text_lbl.setStyleSheet("font-size: 13px; color: #e8e6e3;")
        text_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(text_lbl)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        copy_btn = QPushButton("copiar")
        copy_btn.setStyleSheet(STYLE_BTN)
        _text = entry.get("text", "")
        copy_btn.clicked.connect(lambda: pyperclip.copy(_text))
        btn_row.addWidget(copy_btn)
        layout.addLayout(btn_row)


class HistoryTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        header = QHBoxLayout()
        self._count_lbl = QLabel("historial")
        self._count_lbl.setStyleSheet("font-size: 11px; color: #5f5e5a; letter-spacing: 0.05em;")
        header.addWidget(self._count_lbl)
        header.addStretch()
        clear_btn = QPushButton("limpiar todo")
        clear_btn.setStyleSheet(STYLE_BTN_DANGER)
        clear_btn.clicked.connect(self._clear)
        header.addWidget(clear_btn)
        outer.addLayout(header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                background: #1a1a1f; width: 6px; border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #444441; border-radius: 3px; min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(self._scroll)

        self._inner = QWidget()
        self._inner.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._inner)
        self._list_layout.setContentsMargins(0, 0, 4, 0)
        self._list_layout.setSpacing(8)
        self._list_layout.addStretch()
        self._scroll.setWidget(self._inner)

    def refresh(self):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        entries = hist.load()

        if not entries:
            empty = QLabel("aún no hay transcripciones guardadas")
            empty.setStyleSheet("font-size: 13px; color: #444441; font-style: italic;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._list_layout.insertWidget(0, empty)
        else:
            for i, entry in enumerate(entries):
                self._list_layout.insertWidget(i, HistoryCard(entry))

        n = len(entries)
        self._count_lbl.setText(f"historial — {n} entrada{'s' if n != 1 else ''}")

    def _clear(self):
        hist.clear()
        self.refresh()
