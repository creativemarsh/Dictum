"""
tab_stats.py
Panel de estadísticas de uso.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
import config
import history
from core.i18n import t
from gui import theme

STYLE_CARD = f"""
    QFrame#card {{
        background: {theme.SURFACE};
        border: 1px solid {theme.BORDER};
        border-radius: 10px;
    }}
"""

STYLE_HERO = f"""
    QFrame#card {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #13261f, stop:1 {theme.SURFACE});
        border: 1px solid #1f4434;
        border-radius: 12px;
    }}
"""

# (símbolo, color) de cada métrica
ICONS = {
    "words_total":    ("✦", theme.ACCENT_HI),
    "wpm":            ("⚡", theme.ORANGE),
    "time_recorded":  ("◷", theme.RED),
    "sessions_total": ("◎", "#5ab4f0"),
    "ai_corrections": ("✧", "#d08cf5"),
}


def _icon_badge(glyph: str, color: str) -> QLabel:
    c = QColor(color)
    lbl = QLabel(glyph)
    lbl.setFixedSize(30, 30)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(
        f"background: rgba({c.red()}, {c.green()}, {c.blue()}, 38);"
        f"border-radius: 15px; color: {color}; font-size: 14px;")
    return lbl


def _fmt_duration(secs: int) -> str:
    if secs < 60:
        return f"{secs} s"
    mins = secs // 60
    if mins >= 60:
        return f"{mins // 60}h {mins % 60}min"
    return f"{mins} min"


class StatCard(QFrame):
    def __init__(self, key: str, label: str, value: str, parent=None):
        super().__init__(parent)
        self.setObjectName("card")   # el estilo no debe heredarse a los QLabel hijos
        self.setStyleSheet(STYLE_CARD)
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 10, 12, 10)
        row.setSpacing(10)
        glyph, color = ICONS[key]
        row.addWidget(_icon_badge(glyph, color), alignment=Qt.AlignmentFlag.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(0)
        self._value_lbl = QLabel(value)
        self._value_lbl.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {theme.TEXT};")
        col.addWidget(self._value_lbl)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size: 11px; color: {theme.MUTED};")
        col.addWidget(lbl)
        row.addLayout(col, stretch=1)

    def set_value(self, value: str):
        self._value_lbl.setText(value)


class HeroCard(QFrame):
    """Métrica destacada: el tiempo ahorrado frente a escribir a mano."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(STYLE_HERO)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 16)
        lay.setSpacing(2)
        title = QLabel(t("stat_saved").upper())
        title.setStyleSheet(f"font-size: 10px; font-weight: 700; letter-spacing: 1px; color: {theme.GREEN};")
        lay.addWidget(title)
        self.value = QLabel("0 s")
        self.value.setStyleSheet(f"font-size: 34px; font-weight: 700; color: {theme.TEXT};")
        lay.addWidget(self.value)
        self.sub = QLabel()
        self.sub.setWordWrap(True)
        self.sub.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_2};")
        lay.addWidget(self.sub)


class StatsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: dict[str, StatCard] = {}
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)

        self._hero = HeroCard()
        layout.addWidget(self._hero)

        grid = QGridLayout()
        grid.setSpacing(8)
        specs = [
            ("words_total",    t("stat_words"),    "0"),
            ("wpm",            t("stat_wpm"),      f"0 {t('stat_wpm_unit')}"),
            ("time_recorded",  t("stat_time"),     "0 s"),
            ("sessions_total", t("stat_sessions"), "0"),
        ]
        for i, (key, label, default) in enumerate(specs):
            card = StatCard(key, label, default)
            self._cards[key] = card
            grid.addWidget(card, i // 2, i % 2)
        card = StatCard("ai_corrections", t("stat_ai"), "0")
        self._cards["ai_corrections"] = card
        grid.addWidget(card, 2, 0, 1, 2)
        layout.addLayout(grid)
        layout.addSpacing(4)

        # última transcripción
        last_lbl = QLabel(t("stat_last").upper())
        last_lbl.setStyleSheet("font-size: 10px; font-weight: 600; color: #5d5e6b; letter-spacing: 1px;")
        layout.addWidget(last_lbl)

        self._last_text = QLabel("—")
        self._last_text.setWordWrap(True)
        self._last_text.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_2};")
        layout.addWidget(self._last_text)

        layout.addStretch()

    def refresh(self):
        cfg   = config.load()
        stats = cfg.get("stats", {})

        words    = stats.get("words_total", 0)
        sessions = stats.get("sessions_total", 0)
        rec_s    = stats.get("time_recorded_s", 0)
        ai_corr  = stats.get("ai_corrections", 0)

        # tiempo ahorrado: escribir a mano (~40 PPM) menos lo que se tardó en dictar
        words_per_min_typing = 40
        saved_s = max(0, words * 60 // words_per_min_typing - rec_s)

        # velocidad de dictado (con muy poco audio la cifra no significa nada)
        wpm = round(words * 60 / rec_s) if rec_s >= 10 else 0

        # formato palabras
        if words >= 1000:
            words_str = f"{words / 1000:.1f}K"
        else:
            words_str = str(words)

        time_str  = _fmt_duration(rec_s)
        saved_str = _fmt_duration(saved_s)

        self._cards["words_total"].set_value(words_str)
        self._cards["wpm"].set_value(f"{wpm} {t('stat_wpm_unit')}")
        self._cards["time_recorded"].set_value(time_str)
        self._hero.value.setText(saved_str)
        self._hero.sub.setText(t("stat_saved_sub").format(words=words_str))
        self._cards["sessions_total"].set_value(str(sessions))
        self._cards["ai_corrections"].set_value(str(ai_corr))

        entries = history.load()
        self._last_text.setText(entries[0].get("text", "—") if entries else "—")
