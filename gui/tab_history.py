from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QMessageBox,
)
from datetime import datetime, timedelta

from PyQt6.QtCore import Qt
import history as hist
from core.i18n import t
from gui.copy_button import CopyButton
from gui import theme

STYLE_CARD = f"""
    QFrame#card {{
        background: {theme.SURFACE};
        border: 1px solid {theme.BORDER};
        border-radius: 8px;
    }}
"""
STYLE_BTN = f"""
    QPushButton {{
        background: transparent;
        border: 1px solid {theme.BORDER_HI};
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 11px;
        color: {theme.MUTED};
    }}
    QPushButton:hover {{ background: {theme.BORDER}; color: {theme.TEXT}; }}
"""
STYLE_BTN_DANGER = f"""
    QPushButton {{
        background: transparent;
        border: 1px solid {theme.BORDER_HI};
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 11px;
        color: {theme.MUTED};
    }}
    QPushButton:hover {{ background: {theme.RED_BG}; border-color: {theme.RED_BORDER}; color: {theme.RED_TEXT}; }}
"""


SECTION_HEADER = f"font-size: 10px; font-weight: 600; color: {theme.FAINT}; letter-spacing: 1px;"


def _friendly_ts(ts: str) -> str:
    """'2026-10-07 10:02:00' → 'Hoy 10:02' / 'Ayer 10:02' / '07/10/2026 10:02'."""
    try:
        dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return ts or ""
    today = datetime.now().date()
    hm = dt.strftime("%H:%M")
    if dt.date() == today:
        return f"{t('today')} {hm}"
    if dt.date() == today - timedelta(days=1):
        return f"{t('yesterday')} {hm}"
    return dt.strftime("%d/%m/%Y ") + hm


class HistoryCard(QFrame):
    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("card")   # el estilo no debe heredarse a los QLabel hijos
        self.setStyleSheet(STYLE_CARD)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 10)
        layout.setSpacing(4)

        head = QHBoxLayout()
        ts = QLabel(_friendly_ts(entry.get("ts", "")))
        ts.setToolTip(entry.get("ts", ""))
        ts.setStyleSheet(f"font-size: 11px; color: {theme.FAINT};")
        head.addWidget(ts)
        head.addStretch()
        _text = entry.get("text", "")
        copy_btn = CopyButton(lambda: _text, STYLE_BTN, padding="3px 10px", font_size="11px")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        head.addWidget(copy_btn)
        layout.addLayout(head)

        text_lbl = QLabel(entry.get("text", ""))
        text_lbl.setWordWrap(True)
        text_lbl.setStyleSheet(f"font-size: 13px; color: {theme.TEXT};")
        text_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(text_lbl)


class HistoryTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 16)
        outer.setSpacing(10)

        header = QHBoxLayout()
        self._count_lbl = QLabel(t("hist_title"))
        self._count_lbl.setStyleSheet(SECTION_HEADER)
        header.addWidget(self._count_lbl)
        header.addStretch()
        clear_btn = QPushButton(t("hist_clear"))
        clear_btn.setStyleSheet(STYLE_BTN_DANGER)
        clear_btn.clicked.connect(self._clear)
        header.addWidget(clear_btn)
        outer.addLayout(header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{
                background: {theme.BG}; width: 6px; border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {theme.BORDER_HI}; border-radius: 3px; min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
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
            empty = QLabel(t("hist_empty"))
            empty.setStyleSheet(f"font-size: 13px; color: {theme.BORDER_HI}; font-style: italic;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._list_layout.insertWidget(0, empty)
        else:
            for i, entry in enumerate(entries):
                self._list_layout.insertWidget(i, HistoryCard(entry))

        n = len(entries)
        self._count_lbl.setText(f"{t('hist_title').upper()} · {n}")

    def _clear(self):
        if not hist.load():
            return
        answer = QMessageBox.question(
            self, t("hist_clear"), t("hist_clear_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        hist.clear()
        self.refresh()
