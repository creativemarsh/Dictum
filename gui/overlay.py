"""
overlay.py
Widget flotante que muestra el estado del dictado (grabando, procesando,
listo...) por encima de cualquier ventana. No recibe foco ni clicks, para no
interferir con la app en la que el usuario está escribiendo (ni con el
auto-pegado).
"""
import math
import time

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import (
    Qt, QTimer, QRectF, QPropertyAnimation, QEasingCurve, pyqtSlot,
)
from PyQt6.QtGui import QPainter, QColor, QFont, QFontMetrics, QCursor, QPainterPath

from core.i18n import t

RED    = "#f25f5c"
ORANGE = "#f5a524"
GREEN  = "#3ecf8e"
PURPLE = "#7c6cf6"
GREY   = "#8a8b98"
TEXT   = "#ececf1"
MUTED  = "#5d5e6b"

# estado → (clave i18n, color, ms antes de ocultarse; 0 = permanece)
STATES = {
    "recording":  ("overlay_recording",  RED,    0),
    "processing": ("overlay_processing", ORANGE, 0),
    "done":       ("overlay_done",       GREEN,  1500),
    "pasted":     ("overlay_pasted",     GREEN,  1500),
    "done_no_ai": ("overlay_done_no_ai", ORANGE, 2500),
    "cancelled":  ("overlay_cancelled",  GREY,   1000),
    "no_speech":  ("overlay_no_speech",  GREY,   1800),
    "error":      ("overlay_error",      RED,    3500),
}

BAR_COUNT = 12
HEIGHT    = 40
MARGIN_BOTTOM = 72


class DictationOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._state = "idle"
        self._detail = ""
        self._color = QColor(PURPLE)
        self._level = 0.0
        self._bars = [0.1] * BAR_COUNT
        self._phase = 0.0
        self._t0 = 0.0
        self.esc_hint = True

        self._font = QFont()
        self._font.setPointSizeF(10)
        self._font.setWeight(QFont.Weight.DemiBold)
        self._small = QFont()
        self._small.setPointSizeF(8.5)

        self._tick = QTimer(self)
        self._tick.setInterval(40)
        self._tick.timeout.connect(self._animate)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.fade_out)

        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(180)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.finished.connect(self._on_fade_finished)

    # ── API pública ────────────────────────────────────────────────────────

    def set_state(self, state: str, detail: str = ""):
        """state: una clave de STATES o 'idle' (oculta el overlay)."""
        if state not in STATES:
            self.fade_out()
            return
        key, color, hide_ms = STATES[state]
        if state == "recording" and self._state != "recording":
            self._t0 = time.monotonic()
            self._bars = [0.1] * BAR_COUNT
        self._state = state
        self._detail = detail
        self._color = QColor(color)

        self._hide_timer.stop()
        if hide_ms:
            self._hide_timer.start(hide_ms)
        if not self._tick.isActive():
            self._tick.start()

        self._resize_and_place()
        self._fade_in()
        self.update()

    @pyqtSlot(float)
    def update_level(self, rms: float):
        self._level = rms

    @pyqtSlot()
    def fade_out(self):
        self._hide_timer.stop()
        if not self.isVisible():
            return
        self._fade.stop()
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._fade.start()

    # ── internos ───────────────────────────────────────────────────────────

    def _fade_in(self):
        self._fade.stop()
        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.show()
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.96)
        self._fade.start()

    def _on_fade_finished(self):
        if self._fade.endValue() == 0.0:
            self.hide()
            self._tick.stop()
            self._state = "idle"

    def _label(self) -> str:
        text = t(STATES[self._state][0])
        if self._state == "recording":
            secs = int(time.monotonic() - self._t0)
            text = f"{text}  {secs // 60}:{secs % 60:02d}"
        return text

    def _hint(self) -> str:
        if self._state in ("recording", "processing"):
            return t("overlay_esc_hint") if self.esc_hint else ""
        return self._detail

    def _content_widths(self) -> tuple[int, int, int]:
        fm_main = QFontMetrics(self._font)
        fm_small = QFontMetrics(self._small)
        # ancho fijo para el texto principal mientras graba, así el timer
        # no hace "temblar" el overlay cada segundo
        sample = self._label().rsplit("  ", 1)[0] + "  00:00" if self._state == "recording" else self._label()
        main = fm_main.horizontalAdvance(sample) + 4
        hint = self._hint()
        # +4: margen para que el redondeo de métricas no recorte el texto
        hint_w = min(fm_small.horizontalAdvance(hint) + 4, 320) if hint else 0
        graphic = BAR_COUNT * 5 if self._state == "recording" else (26 if self._state == "processing" else 0)
        return main, hint_w, graphic

    def _resize_and_place(self):
        main, hint_w, graphic = self._content_widths()
        w = 16 + 10 + 10 + main + (14 + graphic if graphic else 0) + (14 + hint_w if hint_w else 0) + 18
        self.resize(w, HEIGHT)

        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        self.move(geo.x() + (geo.width() - w) // 2, geo.y() + geo.height() - HEIGHT - MARGIN_BOTTOM)

    def _animate(self):
        self._phase += 0.04 * 2 * math.pi
        if self._state == "recording":
            for i in range(BAR_COUNT):
                wobble = 0.55 + 0.45 * math.sin(self._phase * 1.7 + i * 0.9)
                target = max(0.12, self._level * wobble)
                self._bars[i] += (target - self._bars[i]) * 0.45
        self.update()

    def paintEvent(self, event):
        if self._state not in STATES:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = r.height() / 2

        # fondo tipo "píldora"
        path = QPainterPath()
        path.addRoundedRect(r, radius, radius)
        p.fillPath(path, QColor(23, 24, 29, 245))
        border = QColor(self._color)
        border.setAlpha(150)
        p.setPen(border)
        p.drawPath(path)

        x = 16.0
        cy = r.center().y()

        # punto de estado (late mientras graba)
        dot_r = 4.5
        if self._state == "recording":
            halo = QColor(self._color)
            halo.setAlpha(int(60 + 50 * (0.5 + 0.5 * math.sin(self._phase))))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(halo)
            p.drawEllipse(QRectF(x - 3, cy - dot_r - 3, (dot_r + 3) * 2, (dot_r + 3) * 2))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._color)
        p.drawEllipse(QRectF(x, cy - dot_r, dot_r * 2, dot_r * 2))
        x += 10 + 10

        main_w, hint_w, graphic = self._content_widths()

        # texto principal
        p.setFont(self._font)
        p.setPen(QColor(TEXT))
        p.drawText(QRectF(x, 0, main_w + 2, r.height()),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._label())
        x += main_w + 14

        # gráfico: barras (grabando) o puntos (procesando)
        if self._state == "recording":
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self._color)
            max_h = r.height() - 16
            for i, lvl in enumerate(self._bars):
                h = max(3.0, lvl * max_h)
                p.drawRoundedRect(QRectF(x + i * 5, cy - h / 2, 3, h), 1.5, 1.5)
            x += graphic + 14
        elif self._state == "processing":
            p.setPen(Qt.PenStyle.NoPen)
            for i in range(3):
                a = 0.5 + 0.5 * math.sin(self._phase * 1.3 - i * 0.9)
                c = QColor(self._color)
                c.setAlphaF(0.25 + 0.75 * a)
                p.setBrush(c)
                p.drawEllipse(QRectF(x + i * 9, cy - 3, 6, 6))
            x += graphic + 14

        # texto secundario (Esc para cancelar / detalle del error)
        if hint_w:
            p.setFont(self._small)
            p.setPen(QColor(MUTED if self._state != "error" else "#ff8f8c"))
            fm = QFontMetrics(self._small)
            hint = fm.elidedText(self._hint(), Qt.TextElideMode.ElideRight, hint_w)
            p.drawText(QRectF(x, 0, hint_w + 2, r.height()),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, hint)
        p.end()
