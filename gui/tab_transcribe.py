"""
tab_transcribe.py
Tab principal: estado, waveform animado, resultado y botones.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QFrame, QTextEdit, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor

import config
from core.i18n import t
from gui import theme
from gui.copy_button import CopyButton
from gui.widgets import MicButton

STYLE_BADGE = """
    QLabel {{
        background: {bg};
        border: 1px solid {border};
        border-radius: 11px;
        padding: 3px 11px;
        font-size: 12px;
        font-weight: 600;
        color: {color};
    }}
"""

STYLE_COMBO = f"""
    QComboBox {{
        background: {theme.INPUT};
        border: 1px solid {theme.BORDER};
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 12px;
        color: {theme.TEXT};
        min-width: 110px;
    }}
    QComboBox:hover {{ border-color: {theme.BORDER_HI}; }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
"""

STYLE_BTN = f"""
    QPushButton {{
        background: transparent;
        border: 1px solid {theme.BORDER_HI};
        border-radius: 6px;
        padding: 5px 14px;
        font-size: 12px;
        color: {theme.MUTED};
    }}
    QPushButton:hover {{ background: {theme.BORDER}; color: {theme.TEXT}; }}
    QPushButton:pressed {{ background: {theme.BORDER_HI}; }}
"""

STYLE_BTN_CANCEL = f"""
    QPushButton {{
        background: transparent;
        border: 1px solid {theme.RED};
        border-radius: 6px;
        padding: 5px 14px;
        font-size: 12px;
        color: {theme.RED};
    }}
    QPushButton:hover {{ background: #2a1719; color: #ff8a87; }}
    QPushButton:pressed {{ background: #3a1d20; }}
"""

STYLE_CARD = f"""
    QFrame#card {{
        background: {theme.SURFACE};
        border: 1px solid {theme.BORDER};
        border-radius: 10px;
    }}
"""

STYLE_BANNER = """
    QLabel {{
        background: {bg};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 8px 10px;
        font-size: 12px;
        color: {color};
    }}
"""

STYLE_OUTPUT = f"""
    QTextEdit {{
        background: transparent;
        border: none;
        font-size: 14px;
        color: {theme.TEXT};
        selection-background-color: {theme.ACCENT};
    }}
"""

# estado → (clave i18n de la etiqueta, color)
BADGES = {
    "idle":       ("status_idle",       theme.MUTED),
    "recording":  ("status_recording",  theme.RED),
    "processing": ("status_processing", theme.ORANGE),
    "cancelling": ("status_canceling",  theme.MUTED),
    "done":       ("status_done",       theme.GREEN_HI),
    "done_no_ai": ("status_done_no_ai", theme.ORANGE),
}

# colores de los avisos: (fondo, borde, texto)
BANNERS = {
    "warning": ("#2a2112", "#5c4416", "#f7c35f"),
    "error":   ("#2a1719", "#5e2629", "#ff8f8c"),
}


def _tinted(color: str, alpha: int) -> str:
    c = QColor(color)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {alpha})"


class TranscribeTab(QWidget):
    cancel_clicked = pyqtSignal()
    mic_clicked    = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "idle"
        self._result_text = ""
        self._pasted = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(12)

        # ── cabecera: estado + perfil ─────────────────────────────────────
        row = QHBoxLayout()
        row.setSpacing(8)
        self._badge = QLabel()
        row.addWidget(self._badge)
        row.addStretch()

        prof_lbl = QLabel(t("lbl_profile"))
        prof_lbl.setStyleSheet(f"font-size: 11px; color: {theme.FAINT};")
        row.addWidget(prof_lbl)
        self._profile_combo = QComboBox()
        self._profile_combo.setStyleSheet(STYLE_COMBO)
        self._profile_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self._profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        self._load_profiles()
        row.addWidget(self._profile_combo)
        layout.addLayout(row)

        # ── zona de dictado: onda + instrucción ───────────────────────────
        hero = QFrame()
        hero.setObjectName("card")
        hero.setStyleSheet(STYLE_CARD)
        hlay = QVBoxLayout(hero)
        hlay.setContentsMargins(16, 4, 16, 12)
        hlay.setSpacing(2)

        self._mic = MicButton()
        self._mic.clicked.connect(self.mic_clicked)
        hlay.addWidget(self._mic, alignment=Qt.AlignmentFlag.AlignCenter)

        self._hint = QLabel()
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {theme.TEXT};")
        hlay.addWidget(self._hint)

        self._subhint = QLabel()
        self._subhint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subhint.setStyleSheet(f"font-size: 11px; color: {theme.FAINT};")
        hlay.addWidget(self._subhint)

        self._btn_cancel = QPushButton(t("btn_cancel"))
        self._btn_cancel.setStyleSheet(STYLE_BTN_CANCEL)
        self._btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_cancel.clicked.connect(self.cancel_clicked)
        self._btn_cancel.setVisible(False)
        # reservar su hueco aunque esté oculto, para que la tarjeta no salte
        sp = self._btn_cancel.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self._btn_cancel.setSizePolicy(sp)
        hlay.addSpacing(6)
        hlay.addWidget(self._btn_cancel, alignment=Qt.AlignmentFlag.AlignCenter)
        # altura fija: si falta espacio cede la tarjeta del resultado, no esta
        hero.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(hero)

        # ── aviso / error (separado del texto) ────────────────────────────
        self._banner = QLabel()
        self._banner.setWordWrap(True)
        self._banner.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._banner.setVisible(False)
        layout.addWidget(self._banner)

        # ── resultado ─────────────────────────────────────────────────────
        out_frame = QFrame()
        out_frame.setObjectName("card")
        out_frame.setStyleSheet(STYLE_CARD)
        out_layout = QVBoxLayout(out_frame)
        out_layout.setContentsMargins(14, 10, 10, 10)
        out_layout.setSpacing(6)

        head = QHBoxLayout()
        lbl = QLabel(t("lbl_result").upper())
        lbl.setStyleSheet(f"font-size: 10px; font-weight: 600; color: {theme.FAINT}; letter-spacing: 1px;")
        head.addWidget(lbl)
        head.addStretch()
        self._btn_copy = CopyButton(self._output_text, STYLE_BTN)
        self._btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_copy.setVisible(False)
        head.addWidget(self._btn_copy)
        out_layout.addLayout(head)

        self._output = QTextEdit()
        self._output.setPlaceholderText(t("placeholder_result"))
        self._output.setToolTip(t("result_editable"))
        self._output.setMinimumHeight(48)
        self._output.setStyleSheet(STYLE_OUTPUT)
        self._output.setReadOnly(True)
        out_layout.addWidget(self._output)

        layout.addWidget(out_frame, stretch=1)
        self.set_state("idle")

    def _output_text(self) -> str:
        # el usuario puede corregir el resultado antes de copiarlo
        return self._output.toPlainText().strip() or self._result_text

    # ── API pública ────────────────────────────────────────────────────────

    def refresh_hint(self):
        from gui.tab_settings import _key_display_name
        cfg = config.load()
        key = _key_display_name(cfg.get("hotkey", "alt"))
        toggle = cfg.get("hotkey_mode", "hold") == "toggle"

        hints = {
            "idle":       t("hint_toggle" if toggle else "hint_hold"),
            "recording":  t("hint_press_again" if toggle else "hint_release"),
            "processing": t("hint_processing"),
            "cancelling": t("hint_processing"),
            "done":       t("hint_pasted" if self._pasted else "hint_done"),
            "done_no_ai": t("hint_pasted" if self._pasted else "hint_done"),
        }
        self._hint.setText(hints.get(self._state, hints["idle"]).format(key=key))

        lang = cfg.get("language", "es").upper()
        self._subhint.setText(f"{t('hint_lang')}: {lang}")

        cancel = t("btn_cancel")
        self._btn_cancel.setText(f"{cancel} (Esc)" if cfg.get("esc_cancels", True) else cancel)

    def set_state(self, state: str):
        """state: 'idle' | 'recording' | 'processing' | 'cancelling' | 'done' | 'done_no_ai'"""
        self._state = state
        key, color = BADGES.get(state, BADGES["idle"])
        self._badge.setText(f"●  {t(key)}")
        self._badge.setStyleSheet(STYLE_BADGE.format(
            bg=_tinted(color, 28), border=_tinted(color, 90), color=color))

        self._mic.set_state(state)
        self._btn_cancel.setVisible(state in ("recording", "processing"))
        self._btn_copy.setVisible(state in ("done", "done_no_ai"))
        self._btn_copy.reset()
        if state in ("recording", "processing"):
            self._banner.setVisible(False)
        self.refresh_hint()

    @pyqtSlot(float)
    def update_level(self, rms: float):
        self._mic.set_level(rms)

    def set_result(self, text: str, ai_failed: bool = False, error_msg: str = "", pasted: bool = False):
        self._result_text = text
        self._pasted = pasted
        self._output.setPlainText(text)
        self._output.setReadOnly(False)
        if ai_failed:
            self._show_banner("warning", f"⚠  {t('ai_failed_banner')}\n{error_msg}".strip())
            self.set_state("done_no_ai")
        else:
            self._banner.setVisible(False)
            self.set_state("done")

    def show_error(self, msg: str):
        self._show_banner("error", f"✕  {msg}")
        self.set_state("idle")

    def _show_banner(self, kind: str, text: str):
        bg, border, color = BANNERS[kind]
        self._banner.setStyleSheet(STYLE_BANNER.format(bg=bg, border=border, color=color))
        self._banner.setText(text)
        self._banner.setVisible(True)

    # ── perfiles ───────────────────────────────────────────────────────────

    def _load_profiles(self):
        cfg = config.load()
        self._profile_combo.blockSignals(True)
        self._profile_combo.clear()
        active_id = cfg.get("active_profile_id", "default")
        idx_to_select = 0
        for i, p in enumerate(cfg.get("profiles", [])):
            self._profile_combo.addItem(p["name"], userData=p["id"])
            if p["id"] == active_id:
                idx_to_select = i
        self._profile_combo.setCurrentIndex(idx_to_select)
        self._profile_combo.blockSignals(False)

    def _on_profile_changed(self, idx: int):
        if idx < 0:
            return
        cfg = config.load()
        cfg["active_profile_id"] = self._profile_combo.itemData(idx)
        config.save(cfg)
