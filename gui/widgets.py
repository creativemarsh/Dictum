"""
widgets.py
Componentes visuales propios: el botón de micrófono animado y el interruptor.
"""
import math

from PyQt6.QtWidgets import QWidget, QCheckBox, QSizePolicy
from PyQt6.QtCore import (
    Qt, QTimer, QRectF, QPointF, QSize, QPropertyAnimation, QEasingCurve,
    pyqtSignal, pyqtProperty,
)
from PyQt6.QtGui import QPainter, QColor, QPen, QRadialGradient, QPainterPath, QFontMetrics

from gui import theme


class MicButton(QWidget):
    """Botón circular grande que muestra el estado del dictado.

    - idle:       violeta, con un halo suave
    - recording:  rojo, con anillos que crecen con el volumen de la voz
    - processing: naranja, con un arco que gira alrededor
    - done:       verde, con un check
    Se puede pulsar para empezar o terminar un dictado.
    """
    clicked = pyqtSignal()

    SIZE = 140
    RADIUS = 34

    COLORS = {
        "idle":       theme.ACCENT,
        "recording":  theme.RED,
        "processing": theme.ORANGE,
        "done":       theme.GREEN,
        "done_no_ai": theme.ORANGE,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self._state = "idle"
        self._level = 0.0
        self._smooth = 0.0
        self._phase = 0.0
        self._hover = False
        self._pressed = False

        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)

    # ── API ─────────────────────────────────────────────────────────────────

    def set_state(self, state: str):
        if state not in self.COLORS:
            state = "idle"
        self._state = state
        if state in ("recording", "processing"):
            self._timer.start()
        else:
            self._level = 0.0
            # deja que los anillos se apaguen suavemente
            self._timer.start()
        self.update()

    def set_level(self, rms: float):
        self._level = rms

    # ── animación ───────────────────────────────────────────────────────────

    def _tick(self):
        self._phase += 0.033
        target = self._level if self._state == "recording" else 0.0
        self._smooth += (target - self._smooth) * 0.25
        if self._state not in ("recording", "processing") and self._smooth < 0.005:
            self._smooth = 0.0
            self._timer.stop()
        self.update()

    # ── eventos ─────────────────────────────────────────────────────────────

    def _inside(self, pos) -> bool:
        c = QPointF(self.width() / 2, self.height() / 2)
        return math.hypot(pos.x() - c.x(), pos.y() - c.y()) <= self.RADIUS + 6

    def event(self, e):
        t = e.type()
        if t == e.Type.HoverMove:
            hover = self._inside(e.position())
            if hover != self._hover:
                self._hover = hover
                self.setCursor(Qt.CursorShape.PointingHandCursor if hover else Qt.CursorShape.ArrowCursor)
                self.update()
        elif t == e.Type.HoverLeave:
            self._hover = False
            self.update()
        return super().event(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self._inside(e.position()):
            self._pressed = True
            self.update()

    def mouseReleaseEvent(self, e):
        was = self._pressed
        self._pressed = False
        self.update()
        if was and self._inside(e.position()):
            self.clicked.emit()

    # ── pintura ─────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        color = QColor(self.COLORS[self._state])
        r = self.RADIUS * (0.96 if self._pressed else 1.0)

        # halo exterior
        glow = QRadialGradient(c, r * 1.95)
        g0 = QColor(color)
        g0.setAlpha(70 if self._state != "idle" else (60 if self._hover else 38))
        g1 = QColor(color)
        g1.setAlpha(0)
        glow.setColorAt(0.45, g0)
        glow.setColorAt(1.0, g1)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(c, r * 1.95, r * 1.95)

        # anillos de voz al grabar
        if self._state == "recording" or self._smooth > 0:
            for i in range(3):
                k = (self._phase * 0.8 + i / 3.0) % 1.0
                # siempre dentro del widget: r + 4 + 30 = SIZE / 2
                ring_r = r + 4 + k * (12 + 18 * self._smooth)
                ring = QColor(color)
                ring.setAlphaF(max(0.0, (1 - k)) * (0.25 + 0.6 * self._smooth))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(ring, 2))
                p.drawEllipse(c, ring_r, ring_r)

        # círculo principal con degradado
        body = QRadialGradient(QPointF(c.x() - r * 0.35, c.y() - r * 0.45), r * 1.6)
        top = QColor(color).lighter(135 if self._hover else 120)
        bottom = QColor(color).darker(115)
        body.setColorAt(0.0, top)
        body.setColorAt(1.0, bottom)
        p.setPen(QPen(QColor(255, 255, 255, 40), 1))
        p.setBrush(body)
        p.drawEllipse(c, r, r)

        # arco giratorio al procesar
        if self._state == "processing":
            arc_r = r + 9
            pen = QPen(color, 3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            start = int(-self._phase * 360 * 1.2 * 16) % (360 * 16)
            p.drawArc(QRectF(c.x() - arc_r, c.y() - arc_r, arc_r * 2, arc_r * 2), start, 100 * 16)

        # icono central
        white = QColor("#ffffff")
        if self._state in ("done", "done_no_ai"):
            pen = QPen(white, 4.5)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            path = QPainterPath(QPointF(c.x() - r * 0.36, c.y() + r * 0.02))
            path.lineTo(c.x() - r * 0.08, c.y() + r * 0.30)
            path.lineTo(c.x() + r * 0.40, c.y() - r * 0.28)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
        else:
            icon = r * 1.5
            theme.draw_mic(p, QRectF(c.x() - icon / 2, c.y() - icon / 2, icon, icon), white)
        p.end()


class ToggleSwitch(QCheckBox):
    """Interruptor tipo iOS con el texto a la izquierda. Es un QCheckBox,
    así que isChecked()/setChecked() funcionan igual."""

    TRACK_W, TRACK_H = 36, 20

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._pos = 0.0
        self._anim = QPropertyAnimation(self, b"knob", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)

    def _get_knob(self) -> float:
        return self._pos

    def _set_knob(self, v: float):
        self._pos = v
        self.update()

    knob = pyqtProperty(float, _get_knob, _set_knob)

    def setChecked(self, on: bool):
        super().setChecked(on)
        self._anim.stop()
        self._pos = 1.0 if on else 0.0
        self.update()

    def _animate(self, on: bool):
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def sizeHint(self) -> QSize:
        fm = QFontMetrics(self.font())
        return QSize(fm.horizontalAdvance(self.text()) + self.TRACK_W + 16, max(26, fm.height() + 8))

    def minimumSizeHint(self) -> QSize:
        return QSize(self.TRACK_W + 40, self.sizeHint().height())

    def hitButton(self, pos) -> bool:
        return self.rect().contains(pos)   # toda la fila es clicable

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # texto
        p.setPen(QColor(theme.TEXT if self.isEnabled() else theme.FAINT))
        p.setFont(self.font())
        text_rect = QRectF(0, 0, w - self.TRACK_W - 12, h)
        fm = QFontMetrics(self.font())
        p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   fm.elidedText(self.text().strip(), Qt.TextElideMode.ElideRight, int(text_rect.width())))

        # pista
        track = QRectF(w - self.TRACK_W, (h - self.TRACK_H) / 2, self.TRACK_W, self.TRACK_H)
        off, on = QColor(theme.BORDER_HI), QColor(theme.ACCENT)
        mix = QColor(
            int(off.red() + (on.red() - off.red()) * self._pos),
            int(off.green() + (on.green() - off.green()) * self._pos),
            int(off.blue() + (on.blue() - off.blue()) * self._pos),
        )
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(mix)
        p.drawRoundedRect(track, self.TRACK_H / 2, self.TRACK_H / 2)

        # botón
        d = self.TRACK_H - 4
        x = track.x() + 2 + (self.TRACK_W - d - 4) * self._pos
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QRectF(x, track.y() + 2, d, d))
        p.end()
