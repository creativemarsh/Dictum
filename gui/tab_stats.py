"""
tab_stats.py
Panel de estadísticas de uso.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QFrame
from PyQt6.QtCore import Qt
import config

STYLE_CARD = """
    QFrame {
        background: #111116;
        border: 1px solid #2c2c2a;
        border-radius: 8px;
    }
"""

ICONS = {
    "words_total":    "✦",
    "sessions_total": "◎",
    "time_recorded":  "◷",
    "time_saved":     "◈",
    "wpm":            "⚡",
    "ai_corrections": "✧",
}


class StatCard(QFrame):
    def __init__(self, icon: str, label: str, value: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(STYLE_CARD)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        lbl_row = QLabel(f"{icon}  {label}")
        lbl_row.setStyleSheet("font-size: 11px; color: #5f5e5a;")
        layout.addWidget(lbl_row)

        self._value_lbl = QLabel(value)
        self._value_lbl.setStyleSheet("font-size: 20px; font-weight: 500; color: #e8e6e3;")
        layout.addWidget(self._value_lbl)

    def set_value(self, value: str):
        self._value_lbl.setText(value)


class StatsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: dict[str, StatCard] = {}
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        grid = QGridLayout()
        grid.setSpacing(8)

        specs = [
            ("words_total",    "✦", "palabras dictadas", "0"),
            ("wpm",            "⚡", "velocidad prom.",   "0 PPM"),
            ("time_recorded",  "◷", "tiempo grabado",    "0 min"),
            ("time_saved",     "◈", "tiempo ahorrado",   "0 min"),
            ("sessions_total", "◎", "sesiones hoy",      "0"),
            ("ai_corrections", "✧", "correcciones IA",   "0"),
        ]

        for i, (key, icon, label, default) in enumerate(specs):
            card = StatCard(icon, label, default)
            self._cards[key] = card
            grid.addWidget(card, i // 2, i % 2)

        layout.addLayout(grid)

        # última transcripción
        sep = QFrame()
        sep.setStyleSheet("background: #2c2c2a; max-height: 1px;")
        layout.addWidget(sep)

        last_lbl = QLabel("última transcripción")
        last_lbl.setStyleSheet("font-size: 11px; color: #5f5e5a; letter-spacing: 0.05em;")
        layout.addWidget(last_lbl)

        self._last_text = QLabel("—")
        self._last_text.setWordWrap(True)
        self._last_text.setStyleSheet("font-size: 13px; color: #888780; line-height: 1.5;")
        layout.addWidget(self._last_text)

        layout.addStretch()

    def refresh(self):
        cfg   = config.load()
        stats = cfg.get("stats", {})

        words    = stats.get("words_total", 0)
        sessions = stats.get("sessions_total", 0)
        rec_s    = stats.get("time_recorded_s", 0)
        ai_corr  = stats.get("ai_corrections", 0)

        # tiempo grabado
        rec_min = rec_s // 60
        if rec_min >= 60:
            time_str = f"{rec_min // 60}h {rec_min % 60}min"
        else:
            time_str = f"{rec_min} min"

        # tiempo ahorrado: estimamos 40 PPM de escritura manual
        words_per_min_typing = 40
        saved_min = words // words_per_min_typing if words > 0 else 0
        if saved_min >= 60:
            saved_str = f"{saved_min // 60}h {saved_min % 60}min"
        else:
            saved_str = f"{saved_min} min"

        # velocidad dictado
        wpm = (words // (rec_min or 1)) if rec_min > 0 else 0

        # formato palabras
        if words >= 1000:
            words_str = f"{words / 1000:.1f}K"
        else:
            words_str = str(words)

        self._cards["words_total"].set_value(words_str)
        self._cards["wpm"].set_value(f"{wpm} PPM")
        self._cards["time_recorded"].set_value(time_str)
        self._cards["time_saved"].set_value(saved_str)
        self._cards["sessions_total"].set_value(str(sessions))
        self._cards["ai_corrections"].set_value(str(ai_corr))
