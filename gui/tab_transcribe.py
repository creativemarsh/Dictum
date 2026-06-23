"""
tab_transcribe.py
Tab principal: estado, waveform animado, resultado y botones.
"""
import pyperclip
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QFrame, QSizePolicy, QTextEdit,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QPainter, QColor, QPen
import random

STYLE_BADGE = """
    QLabel {{
        background: #111116;
        border: 1px solid #2c2c2a;
        border-radius: 12px;
        padding: 4px 12px;
        font-size: 12px;
        color: {color};
    }}
"""

STYLE_COMBO = """
    QComboBox {
        background: #0d0d12;
        border: 1px solid #2c2c2a;
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 11px;
        color: #e8e6e3;
    }
    QComboBox::drop-down { border: none; width: 24px; }
"""

STYLE_BTN = """
    QPushButton {
        background: transparent;
        border: 1px solid #444441;
        border-radius: 6px;
        padding: 5px 14px;
        font-size: 12px;
        color: #888780;
    }
    QPushButton:hover { background: #2c2c2a; color: #e8e6e3; }
    QPushButton:pressed { background: #444441; }
"""

STYLE_BTN_CANCEL = """
    QPushButton {
        background: transparent;
        border: 1px solid #E24B4A;
        border-radius: 6px;
        padding: 5px 14px;
        font-size: 12px;
        color: #E24B4A;
    }
    QPushButton:hover { background: #2c1a1a; color: #ff6b6a; }
    QPushButton:pressed { background: #3c2a2a; }
"""

STYLE_OUTPUT = """
    QFrame {
        background: #111116;
        border: 1px solid #2c2c2a;
        border-radius: 8px;
    }
"""


class WaveformWidget(QWidget):
    """Waveform animado — barras que suben/bajan según el nivel de audio."""

    BAR_COUNT = 20
    BAR_W     = 3
    GAP       = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        self._levels = [0.15] * self.BAR_COUNT
        self._active = False
        self._target = 0.0

        self._timer = QTimer()
        self._timer.setInterval(60)
        self._timer.timeout.connect(self._animate)
        self._timer.start()

    def set_active(self, active: bool):
        self._active = active
        if not active:
            self._target = 0.0

    def set_level(self, rms: float):
        self._target = rms

    def _animate(self):
        if self._active:
            for i in range(self.BAR_COUNT):
                noise  = random.uniform(0.3, 1.0)
                target = self._target * noise
                self._levels[i] += (target - self._levels[i]) * 0.4
        else:
            for i in range(self.BAR_COUNT):
                self._levels[i] *= 0.7
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        total_w = self.BAR_COUNT * self.BAR_W + (self.BAR_COUNT - 1) * self.GAP
        x0 = (w - total_w) // 2

        for i, lvl in enumerate(self._levels):
            bar_h = max(4, int(lvl * (h - 8)))
            x = x0 + i * (self.BAR_W + self.GAP)
            y = (h - bar_h) // 2
            color = QColor("#E24B4A") if self._active else QColor("#444441")
            p.setBrush(color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x, y, self.BAR_W, bar_h, 2, 2)


class TranscribeTab(QWidget):
    cancel_clicked = pyqtSignal()
    tray_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "idle"
        self._result_text = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # ── estado ────────────────────────────────────────────────────────
        row = QHBoxLayout()
        self._badge = QLabel("esperando")
        self._badge.setStyleSheet(STYLE_BADGE.format(color="#888780"))
        row.addWidget(self._badge)
        row.addStretch()
        
        self._profile_combo = QComboBox()
        self._profile_combo.setStyleSheet(STYLE_COMBO)
        self._profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        self._load_profiles()
        row.addWidget(self._profile_combo)

        self._hint = QLabel("Alt para grabar")
        self._hint.setStyleSheet("font-size: 11px; color: #5f5e5a;")
        row.addWidget(self._hint)
        layout.addLayout(row)

        # ── waveform ──────────────────────────────────────────────────────
        self._wave = WaveformWidget()
        self._wave.setStyleSheet("background: #111116; border: 1px solid #2c2c2a; border-radius: 8px;")
        layout.addWidget(self._wave)

        # ── output ────────────────────────────────────────────────────────
        out_frame = QFrame()
        out_frame.setStyleSheet(STYLE_OUTPUT)
        out_layout = QVBoxLayout(out_frame)
        out_layout.setContentsMargins(12, 10, 12, 10)
        out_layout.setSpacing(6)

        lbl = QLabel("resultado")
        lbl.setStyleSheet("font-size: 11px; color: #5f5e5a; letter-spacing: 0.05em; text-transform: uppercase;")
        out_layout.addWidget(lbl)

        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setPlaceholderText("el texto procesado aparece aquí…")
        self._output.setMinimumHeight(100)
        self._output.setStyleSheet(self._output_style("#5f5e5a", italic=True))
        out_layout.addWidget(self._output)

        layout.addWidget(out_frame)

        # ── botones ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._btn_cancel = QPushButton("cancelar")
        self._btn_cancel.setStyleSheet(STYLE_BTN_CANCEL)
        self._btn_cancel.clicked.connect(self.cancel_clicked)
        self._btn_cancel.setVisible(False)
        btn_row.addWidget(self._btn_cancel)

        self._btn_copy = QPushButton("copiar")
        self._btn_copy.setStyleSheet(STYLE_BTN)
        self._btn_copy.clicked.connect(self._copy)
        self._btn_copy.setVisible(False)
        btn_row.addWidget(self._btn_copy)

        self._btn_paste = QPushButton("pegar directo")
        self._btn_paste.setStyleSheet(STYLE_BTN)
        self._btn_paste.clicked.connect(self._paste)
        self._btn_paste.setVisible(False)
        btn_row.addWidget(self._btn_paste)

        layout.addLayout(btn_row)

        # ── hint tray ─────────────────────────────────────────────────────
        self._btn_tray = QPushButton("Correr en segundo plano")
        self._btn_tray.setStyleSheet(STYLE_BTN)
        self._btn_tray.clicked.connect(self.tray_clicked)
        layout.addWidget(self._btn_tray, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()
        self.refresh_hint()

    @staticmethod
    def _output_style(color: str, italic: bool = False) -> str:
        italic_str = "italic" if italic else "normal"
        return f"""
            QTextEdit {{
                background: transparent;
                border: none;
                font-size: 14px;
                color: {color};
                font-style: {italic_str};
            }}
            QScrollBar:vertical {{
                background: #111116; width: 6px; border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: #444441; border-radius: 3px; min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """

    # ── API pública ────────────────────────────────────────────────────────
    
    def refresh_hint(self):
        import config
        from gui.tab_settings import _key_display_name
        cfg = config.load()
        hk = cfg.get("hotkey", "alt")
        lang = cfg.get("language", "es").upper()
        self._hint.setText(f"{_key_display_name(hk)} para grabar | Idioma: {lang}")

    def set_state(self, state: str):
        """state: 'idle' | 'recording' | 'processing' | 'cancelling' | 'done'"""
        self._state = state
        labels = {
            "idle":        ("esperando",     "#888780", False),
            "recording":   ("grabando…",     "#E24B4A", True),
            "processing":  ("procesando…",   "#EF9F27", False),
            "cancelling":  ("cancelando…",   "#888780", False),
            "done":        ("listo ✓",       "#639922", False),
        }
        text, color, wave_active = labels.get(state, labels["idle"])
        self._badge.setText(text)
        self._badge.setStyleSheet(STYLE_BADGE.format(color=color))
        self._wave.set_active(wave_active)

        self._btn_cancel.setVisible(state in ("recording", "processing"))
        self._btn_copy.setVisible(state == "done")
        self._btn_paste.setVisible(state == "done")

    @pyqtSlot(float)
    def update_level(self, rms: float):
        self._wave.set_level(rms)

    def set_result(self, text: str, ai_failed: bool = False, error_msg: str = ""):
        self._result_text = text
        
        display_text = text
        if ai_failed:
            display_text = f"⚠️ Error en IA: {error_msg}\n\nAquí está tu transcripción original:\n-----------------------------------\n{text}"
            
        self._output.setPlainText(display_text)
        self._output.setStyleSheet(self._output_style("#e8e6e3"))
        self.set_state("done")
        if ai_failed:
            self._badge.setText("listo (sin IA) ⚠️")
            self._badge.setStyleSheet(STYLE_BADGE.format(color="#EF9F27"))

    def show_error(self, msg: str):
        self._output.setPlainText(f"Error: {msg}")
        self._output.setStyleSheet(self._output_style("#E24B4A"))
        self.set_state("idle")

    # ── botones ────────────────────────────────────────────────────────────

    def _copy(self):
        if self._result_text:
            pyperclip.copy(self._result_text)

    def _paste(self):
        if self._result_text:
            pyperclip.copy(self._result_text)
            import keyboard
            keyboard.send("ctrl+v")

    def _load_profiles(self):
        import config
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
        if idx < 0: return
        import config
        cfg = config.load()
        pid = self._profile_combo.itemData(idx)
        cfg["active_profile_id"] = pid
        config.save(cfg)
