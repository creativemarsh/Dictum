"""
theme.py
Paleta, hoja de estilos global e iconos dibujados de Dictum.
"""
import sys

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPixmap, QPen

# ── paleta ───────────────────────────────────────────────────────────────────
BG        = "#1a1a1f"   # fondo de ventana
SURFACE   = "#111116"   # tarjetas
INPUT     = "#0d0d12"   # campos de texto
BORDER    = "#2c2c2a"
BORDER_HI = "#444441"
TEXT      = "#e8e6e3"
TEXT_2    = "#b4b2a9"
MUTED     = "#888780"
FAINT     = "#5f5e5a"
ACCENT    = "#534AB7"
ACCENT_HI = "#6358c8"
RED       = "#E24B4A"
ORANGE    = "#EF9F27"
GREEN     = "#639922"
GREEN_HI  = "#97C459"

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
    background: {BG};
}}
QTabBar {{
    qproperty-drawBase: 0;
    background: {SURFACE};
    border-bottom: 1px solid {BORDER};
}}
QTabBar::tab {{
    background: transparent;
    color: {MUTED};
    padding: 10px 16px 9px 16px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 12px;
}}
QTabBar::tab:selected {{
    color: {TEXT};
    border-bottom: 2px solid {ACCENT};
    font-weight: 600;
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

    white = QColor("#ffffff")
    # cápsula del micrófono
    p.setBrush(white)
    p.drawRoundedRect(QRectF(25 * s, 13 * s, 14 * s, 24 * s), 7 * s, 7 * s)
    # soporte en U + pie
    pen = QPen(white, 3.6 * s)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    arc = QPainterPath()
    arc.arcMoveTo(QRectF(19 * s, 18 * s, 26 * s, 24 * s), 180)
    arc.arcTo(QRectF(19 * s, 18 * s, 26 * s, 24 * s), 180, 180)
    p.drawPath(arc)
    p.drawLine(int(32 * s), int(42 * s), int(32 * s), int(49 * s))
    p.drawLine(int(25 * s), int(50 * s), int(39 * s), int(50 * s))
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
        c = QColor(SURFACE)
        colorref = ctypes.c_int(c.red() | (c.green() << 8) | (c.blue() << 16))
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(colorref), ctypes.sizeof(colorref))
    except Exception:
        pass
