"""
theme.py
Paleta, hoja de estilos global e iconos dibujados de Dictum.
"""
import sys

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPixmap, QPen

# ── paleta ───────────────────────────────────────────────────────────────────
BG        = "#0f1014"   # fondo de ventana
SURFACE   = "#17181d"   # tarjetas
SURFACE_2 = "#1f2027"   # elementos elevados / hover
INPUT     = "#121318"   # campos de texto
BORDER    = "#262730"
BORDER_HI = "#34353f"
TEXT      = "#ececf1"
TEXT_2    = "#b9bac4"
MUTED     = "#8a8b98"
FAINT     = "#5d5e6b"
ACCENT    = "#7c6cf6"
ACCENT_HI = "#9184ff"
RED       = "#f25f5c"
ORANGE    = "#f5a524"
GREEN     = "#3ecf8e"
GREEN_HI  = "#6ee7b0"

STATE_COLORS = {
    "idle":       ACCENT,
    "recording":  RED,
    "processing": ORANGE,
}

STYLE = f"""
QMainWindow, QWidget {{
    background: {BG};
    color: {TEXT};
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}}
QTabWidget::pane {{
    border: none;
    border-top: 1px solid {BORDER};
    background: {BG};
}}
QTabWidget::tab-bar {{
    left: 12px;
}}
QTabBar {{
    qproperty-drawBase: 0;
    background: transparent;
}}
QTabBar::tab {{
    background: transparent;
    color: {MUTED};
    padding: 6px 11px;
    margin: 10px 1px 10px 1px;
    border: none;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    background: {SURFACE_2};
    color: {TEXT};
}}
QTabBar::tab:hover:!selected {{
    color: {TEXT_2};
}}
QFrame#card QLabel, QFrame#card QCheckBox {{
    background: transparent;
}}
QCheckBox {{
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {BORDER_HI};
    border-radius: 4px;
    background: {INPUT};
}}
QCheckBox::indicator:hover {{
    border-color: {ACCENT};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_HI};
    border-radius: 2px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {FAINT};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QScrollBar:horizontal {{ height: 0; }}
QToolTip {{
    background: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER_HI};
    padding: 4px 8px;
}}
QMenu {{
    background: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER_HI};
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 18px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background: {ACCENT};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 4px 6px;
}}
QComboBox QAbstractItemView {{
    background: {SURFACE};
    border: 1px solid {BORDER_HI};
    color: {TEXT};
    selection-background-color: {ACCENT};
    outline: none;
}}
QDialog QPushButton, QMessageBox QPushButton {{
    background: transparent;
    border: 1px solid {BORDER_HI};
    border-radius: 6px;
    padding: 5px 16px;
    min-width: 64px;
    color: {TEXT};
}}
QDialog QPushButton:hover, QMessageBox QPushButton:hover {{
    background: {BORDER};
}}
QDialog QPushButton:default, QMessageBox QPushButton:default {{
    background: {ACCENT};
    border-color: {ACCENT};
}}
QDialog QLineEdit {{
    background: {INPUT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 10px;
}}
QDialog QLineEdit:focus {{
    border-color: {ACCENT};
}}
"""


def draw_mic(p: QPainter, rect: QRectF, color: QColor) -> None:
    """Dibuja un micrófono centrado en rect (diseñado sobre una rejilla de 64)."""
    s = rect.width() / 64.0
    ox, oy = rect.x(), rect.y()
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawRoundedRect(QRectF(ox + 25 * s, oy + 13 * s, 14 * s, 24 * s), 7 * s, 7 * s)
    pen = QPen(color, 3.6 * s)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    arc_rect = QRectF(ox + 19 * s, oy + 18 * s, 26 * s, 24 * s)
    arc = QPainterPath()
    arc.arcMoveTo(arc_rect, 180)
    arc.arcTo(arc_rect, 180, 180)
    p.drawPath(arc)
    p.drawLine(QPointF(ox + 32 * s, oy + 42 * s), QPointF(ox + 32 * s, oy + 49 * s))
    p.drawLine(QPointF(ox + 25 * s, oy + 50 * s), QPointF(ox + 39 * s, oy + 50 * s))
    p.restore()


def app_icon(state: str = "idle", size: int = 64) -> QIcon:
    """Icono de Dictum: un micrófono blanco sobre un círculo del color del estado."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size / 64.0
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(STATE_COLORS.get(state, ACCENT)))
    p.drawEllipse(QRectF(2 * s, 2 * s, 60 * s, 60 * s))
    draw_mic(p, QRectF(0, 0, size, size), QColor("#ffffff"))
    p.end()
    return QIcon(pm)


def apply_dark_title_bar(widget) -> None:
    """En Windows 10/11 pide a DWM una barra de título oscura (y del color
    de la app en Windows 11). En otros sistemas no hace nada."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        hwnd = int(widget.winId())
        dwm = ctypes.windll.dwmapi
        on = ctypes.c_int(1)
        # 20 = DWMWA_USE_IMMERSIVE_DARK_MODE (19 en builds antiguas de Win10)
        for attr in (20, 19):
            if dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(on), ctypes.sizeof(on)) == 0:
                break
        # 35 = DWMWA_CAPTION_COLOR (solo Windows 11), formato COLORREF 0x00BBGGRR
        c = QColor(BG)
        colorref = ctypes.c_int(c.red() | (c.green() << 8) | (c.blue() << 16))
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(colorref), ctypes.sizeof(colorref))
    except Exception:
        pass
