"""
tab_settings.py
Ajustes: proveedor LLM, modelo, Whisper, hotkey, API keys.
"""
import httpx
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QTextEdit, QPushButton, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, QTimer, QThreadPool, pyqtSignal, pyqtSlot, QObject, QEvent
import config
from core.i18n import t, current_language as t_lang_loaded
from gui.widgets import ToggleSwitch, AccentPicker
from gui import theme

STYLE_SECTION = f"""
    QFrame#card {{
        background: {theme.SURFACE};
        border: 1px solid {theme.BORDER};
        border-radius: 8px;
    }}
"""
STYLE_INPUT = f"""
    QLineEdit {{
        background: {theme.INPUT};
        border: 1px solid {theme.BORDER};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 13px;
        color: {theme.TEXT};
    }}
    QLineEdit:focus {{ border-color: {theme.ACCENT}; }}
"""
STYLE_COMBO = f"""
    QComboBox {{
        background: {theme.INPUT};
        border: 1px solid {theme.BORDER};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 13px;
        color: {theme.TEXT};
    }}
    QComboBox::drop-down {{ border: none; width: 24px; }}
    QComboBox QAbstractItemView {{
        background: {theme.SURFACE};
        border: 1px solid {theme.BORDER_HI};
        color: {theme.TEXT};
        selection-background-color: {theme.ACCENT};
    }}
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
"""
STYLE_BTN_PRIMARY = f"""
    QPushButton {{
        background: {theme.ACCENT_SOLID};
        border: none;
        border-radius: 6px;
        padding: 6px 18px;
        font-size: 13px;
        color: {theme.ON_ACCENT};
        font-weight: 600;
    }}
    QPushButton:hover {{ background: {theme.ACCENT_SOLID_HI}; }}
"""
STYLE_CODE = f"""
    QLabel {{
        background: {theme.INPUT};
        border: 1px solid {theme.BORDER};
        border-radius: 6px;
        padding: 8px 12px;
        font-family: 'Consolas', monospace;
        font-size: 12px;
        color: {theme.CODE};
    }}
"""
STYLE_KEY_LABEL = f"""
    QLabel {{
        background: {theme.INPUT};
        border: 1px solid {theme.BORDER};
        border-radius: 6px;
        padding: 6px 14px;
        font-size: 13px;
        color: {theme.TEXT};
        min-width: 60px;
        qproperty-alignment: AlignCenter;
    }}
"""
STYLE_KEY_LABEL_ACTIVE = f"""
    QLabel {{
        background: {theme.INPUT};
        border: 1px solid {theme.ACCENT};
        border-radius: 6px;
        padding: 6px 14px;
        font-size: 13px;
        color: {theme.FAINT};
        min-width: 60px;
        qproperty-alignment: AlignCenter;
    }}
"""
STYLE_TEXTAREA = f"""
    QTextEdit {{
        background: {theme.INPUT};
        border: 1px solid {theme.BORDER};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
        color: {theme.TEXT};
    }}
    QTextEdit:focus {{ border-color: {theme.ACCENT}; }}
"""


def section(title: str) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("card")   # el estilo no debe heredarse a los QLabel hijos
    frame.setStyleSheet(STYLE_SECTION)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(10)
    lbl = QLabel(title)
    lbl.setStyleSheet(f"font-size: 11px; color: {theme.FAINT}; letter-spacing: 0.05em;")
    layout.addWidget(lbl)
    return frame, layout


LABEL_COLUMN_W = 108


def label(text: str, column: bool = True) -> QLabel:
    """Etiqueta de un campo. Con column=True tiene ancho fijo, para que los
    controles de todas las filas empiecen a la misma altura."""
    l = QLabel(text)
    l.setStyleSheet(f"font-size: 12px; color: {theme.MUTED};")
    if column:
        l.setFixedWidth(LABEL_COLUMN_W)
        l.setWordWrap(True)
    return l


def wrapped(lbl: QLabel) -> QLabel:
    lbl.setWordWrap(True)
    return lbl


class StatusLabel(QLabel):
    """Etiqueta de estado que no ocupa espacio mientras está vacía."""

    def setText(self, text: str):
        super().setText(text)
        self.setVisible(bool(text))


def _key_display_name(name: str) -> str:
    left, right = t("key_left"), t("key_right")
    _NAMES = {
        'left alt':    left.format(k='Alt'),
        'right alt':   right.format(k='Alt'),
        'left ctrl':   left.format(k='Ctrl'),
        'right ctrl':  right.format(k='Ctrl'),
        'left shift':  left.format(k='Shift'),
        'right shift': right.format(k='Shift'),
        'alt':   'Alt',   'ctrl':  'Ctrl',  'shift': 'Shift',
        'caps lock':   t("key_caps_lock"),
        'space':       t("key_space"),
        'tab':         'Tab',
        'esc':         'Escape',
        'insert':      'Insert',
        'delete':      t("key_delete"),
        'home':        t("key_home"),
        'end':         t("key_end"),
        'page up':     t("key_page_up"),
        'page down':   t("key_page_down"),
        'left windows':  left.format(k='Win'),
        'right windows': right.format(k='Win'),
        'windows': 'Windows',
        'menu':    t("key_menu"),
        'pause':   t("key_pause"),
        **{f'f{i}': f'F{i}' for i in range(1, 13)},
    }
    return _NAMES.get(name.lower(), name.upper() if len(name) == 1 else name.title())


class KeyFilter(QObject):
    key_pressed = pyqtSignal(int, str, int, int)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        # Atrapamos KeyPress y ShortcutOverride (vital para el Alt).
        # IGNORAMOS KeyRelease para evitar lecturas falsas cuando la tecla ya está suelta.
        if event.type() in (QEvent.Type.KeyPress, QEvent.Type.ShortcutOverride):
            # A veces Alt manda un código 0 en ShortcutOverride, lo procesamos igual.
            self.key_pressed.emit(event.key() if hasattr(event, 'key') else 0, event.text() if hasattr(event, 'text') else "", 0, 0)
            return True
        return False


class KeyCaptureWidget(QWidget):
    """Muestra la tecla configurada y permite cambiarla interceptando eventos de PyQt6."""
    key_changed  = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_key = 'alt'
        self._capturing   = False
        self._filter      = None
        self._setup_ui()

    def _setup_ui(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self._display = QLabel(_key_display_name('alt'))
        self._display.setStyleSheet(STYLE_KEY_LABEL)
        lay.addWidget(self._display)

        self._btn = QPushButton(t("btn_capture"))
        self._btn.setStyleSheet(STYLE_BTN)
        self._btn.setMinimumWidth(70)
        self._btn.clicked.connect(self._toggle)
        lay.addWidget(self._btn)

    # ── API pública ────────────────────────────────────────────────────────

    def set_key(self, key_name: str):
        self._current_key = key_name
        self._display.setText(_key_display_name(key_name))

    def get_key(self) -> str:
        return self._current_key

    # ── captura ────────────────────────────────────────────────────────────

    def _toggle(self):
        if not self._capturing:
            self._start_capture()
        else:
            self._cancel_capture()

    def _start_capture(self):
        self._capturing = True
        self._display.setText(t("waiting_key"))
        self._display.setStyleSheet(STYLE_KEY_LABEL_ACTIVE)
        self._btn.setText(f"✕ {t('btn_cancel_capture')}")
        
        from PyQt6.QtWidgets import QApplication
        self._filter = KeyFilter(self)
        self._filter.key_pressed.connect(self._on_captured_key)
        QApplication.instance().installEventFilter(self._filter)

    def _cancel_capture(self):
        if self._capturing:
            self._capturing = False
            if self._filter:
                from PyQt6.QtWidgets import QApplication
                QApplication.instance().removeEventFilter(self._filter)
                self._filter = None
        self._display.setStyleSheet(STYLE_KEY_LABEL)
        self._display.setText(_key_display_name(self._current_key))
        self._btn.setText(t("btn_capture"))

    def _on_captured_key(self, key: int, text: str, nvk: int, nsc: int):
        import sys
        from PyQt6.QtCore import Qt
        key_name = ""

        if sys.platform == 'win32':
            import ctypes
            # Verificación a nivel de hardware (kernel) en el milisegundo exacto.
            if ctypes.windll.user32.GetAsyncKeyState(161) & 0x8000: key_name = 'right shift'
            elif ctypes.windll.user32.GetAsyncKeyState(160) & 0x8000: key_name = 'left shift'
            elif ctypes.windll.user32.GetAsyncKeyState(163) & 0x8000: key_name = 'right ctrl'
            elif ctypes.windll.user32.GetAsyncKeyState(162) & 0x8000: key_name = 'left ctrl'
            elif ctypes.windll.user32.GetAsyncKeyState(165) & 0x8000: key_name = 'right alt'
            elif ctypes.windll.user32.GetAsyncKeyState(164) & 0x8000: key_name = 'left alt'
            elif ctypes.windll.user32.GetAsyncKeyState(92) & 0x8000: key_name = 'right windows'
            elif ctypes.windll.user32.GetAsyncKeyState(91) & 0x8000: key_name = 'left windows'
        else:
            import keyboard
            if key == Qt.Key.Key_Control:
                if keyboard.is_pressed('right ctrl'): key_name = 'right ctrl'
                else: key_name = 'left ctrl'
            elif key == Qt.Key.Key_Shift:
                if keyboard.is_pressed('right shift'): key_name = 'right shift'
                else: key_name = 'left shift'
            elif key in (Qt.Key.Key_Alt, Qt.Key.Key_AltGr):
                if keyboard.is_pressed('right alt') or keyboard.is_pressed('alt gr'): key_name = 'right alt'
                else: key_name = 'left alt'
            elif key == Qt.Key.Key_Meta:
                if keyboard.is_pressed('right windows'): key_name = 'right windows'
                else: key_name = 'left windows'

        if not key_name:
            # Si no es un modificador, o fallaron las APIs, delegamos al mapeo estándar
            key_name = self._map_qt_key_to_name(key, text)

        if key_name:
            self._apply_key(key_name)

    def _map_qt_key_to_name(self, key: int, text: str) -> str:
        from PyQt6.QtCore import Qt
        _QT_KEY_MAP = {
            Qt.Key.Key_Alt: 'alt',
            Qt.Key.Key_Control: 'ctrl',
            Qt.Key.Key_Shift: 'shift',
            Qt.Key.Key_Meta: 'windows',
            Qt.Key.Key_CapsLock: 'caps lock',
            Qt.Key.Key_Space: 'space',
            Qt.Key.Key_Tab: 'tab',
            Qt.Key.Key_Escape: 'esc',
            Qt.Key.Key_Insert: 'insert',
            Qt.Key.Key_Delete: 'delete',
            Qt.Key.Key_Home: 'home',
            Qt.Key.Key_End: 'end',
            Qt.Key.Key_PageUp: 'page up',
            Qt.Key.Key_PageDown: 'page down',
            Qt.Key.Key_Menu: 'menu',
            Qt.Key.Key_Pause: 'pause',
            Qt.Key.Key_Print: 'print screen',
            Qt.Key.Key_ScrollLock: 'scroll lock',
            Qt.Key.Key_NumLock: 'num lock',
            Qt.Key.Key_Enter: 'enter',
            Qt.Key.Key_Return: 'enter',
            Qt.Key.Key_Backspace: 'backspace',
        }
        for i in range(1, 13):
            _QT_KEY_MAP[getattr(Qt.Key, f"Key_F{i}")] = f"f{i}"

        if key in _QT_KEY_MAP:
            return _QT_KEY_MAP[key]

        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            return chr(key).lower()

        if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            return chr(key)

        if text and len(text) == 1 and text.isprintable():
            return text.lower()

        return ""

    def _apply_key(self, key_name: str):
        self._capturing = False
        if self._filter:
            from PyQt6.QtWidgets import QApplication
            QApplication.instance().removeEventFilter(self._filter)
            self._filter = None
        self._current_key = key_name
        self._display.setStyleSheet(STYLE_KEY_LABEL)
        self._display.setText(_key_display_name(key_name))
        self._btn.setText(t("btn_capture"))
        self.key_changed.emit(key_name)

    def hideEvent(self, event):
        if self._capturing:
            self._cancel_capture()
        super().hideEvent(event)


class NoScrollComboBox(QComboBox):
    """Ignora el scroll del mouse a menos que el widget tenga el foco activo."""
    def __init__(self, parent=None):
        super().__init__(parent)
        # sin esto el combo se ensancha hasta su opción más larga y empuja
        # el contenido fuera de la ventana
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(4)

    def wheelEvent(self, event):
        event.ignore()


def icon_button(glyph: str, tooltip: str, slot) -> QPushButton:
    """Botón cuadrado con un símbolo; el texto completo va en el tooltip."""
    b = QPushButton(glyph)
    b.setToolTip(tooltip)
    b.setFixedSize(28, 30)
    b.setStyleSheet(STYLE_BTN + "QPushButton { padding: 0; font-size: 14px; }")
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.clicked.connect(slot)
    return b


def section_desc(text: str) -> QLabel:
    l = QLabel(text)
    l.setWordWrap(True)
    l.setStyleSheet(f"font-size: 11px; color: {theme.FAINT}; margin-bottom: 2px;")
    return l


class CudaChecker(QObject):
    result = pyqtSignal(str, str)  # text, color

    def check(self):
        try:
            import ctranslate2
            if ctranslate2.get_cuda_device_count() > 0:
                self.result.emit(t("cuda_ok"), theme.GREEN)
            else:
                self.result.emit(t("cuda_cpu"), theme.AMBER)
        except Exception as e:
            self.result.emit(f"{t('cuda_error')}: {e}", theme.RED)


class OllamaFetcher(QObject):
    done  = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url

    def fetch(self):
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
            self.done.emit(models)
        except Exception as e:
            self.error.emit(str(e))


class SettingsTab(QWidget):
    saved = pyqtSignal()
    restart_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cfg = config.load()
        self._workers: set = set()
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(12)

        # ── Perfil de usuario ─────────────────────────────────────────────
        frm_p, play = section(t("profiles_title"))

        # --- bloque: generar con IA ---
        play.addWidget(section_desc(
            t("profile_gen_desc")
        ))

        gen_row = QHBoxLayout()
        self._gen_input = QLineEdit()
        self._gen_input.setStyleSheet(STYLE_INPUT)
        self._gen_input.setPlaceholderText(
            t("profile_gen_placeholder")
        )
        gen_row.addWidget(self._gen_input)
        self._gen_btn = QPushButton(f"✨ {t('btn_generate_profile')}")
        self._gen_btn.setStyleSheet(STYLE_BTN_PRIMARY)
        self._gen_btn.clicked.connect(self._generate_profile)
        gen_row.addWidget(self._gen_btn)
        play.addLayout(gen_row)

        self._gen_status = StatusLabel("")
        self._gen_status.setVisible(False)
        self._gen_status.setStyleSheet(f"font-size: 11px; color: {theme.MUTED};")
        play.addWidget(self._gen_status)

        self._gen_lang_note = QLabel(t("profile_lang_note"))
        self._gen_lang_note.setWordWrap(True)
        self._gen_lang_note.setStyleSheet(f"font-size: 11px; color: {theme.MUTED};")
        play.addWidget(self._gen_lang_note)

        # separador visual
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {theme.BORDER};")
        play.addWidget(sep)

        # --- bloque: edición manual ---
        play.addWidget(section_desc(t("profiles_manage")))

        row_prof_sel = QHBoxLayout()
        row_prof_sel.addWidget(label(t("profile_name")))
        self._setting_profile_combo = NoScrollComboBox()
        self._setting_profile_combo.setStyleSheet(STYLE_COMBO)
        self._setting_profile_combo.currentIndexChanged.connect(self._on_settings_profile_changed)
        row_prof_sel.addWidget(self._setting_profile_combo)

        self._btn_new_prof = icon_button("+", t("btn_new_profile").lstrip("+ "), self._add_profile)
        row_prof_sel.addWidget(self._btn_new_prof)

        self._btn_del_prof = icon_button("✕", t("btn_delete"), self._delete_profile)
        row_prof_sel.addWidget(self._btn_del_prof)
        play.addLayout(row_prof_sel)

        row_role = QHBoxLayout()
        row_role.addWidget(label(t("profile_role")))
        self._profile_role = QLineEdit()
        self._profile_role.setStyleSheet(STYLE_INPUT)
        self._profile_role.setPlaceholderText(t("profile_role_placeholder"))
        row_role.addWidget(self._profile_role)
        play.addLayout(row_role)

        play.addWidget(label(t("profile_terms"), column=False))
        self._profile_terms = QTextEdit()
        self._profile_terms.setFixedHeight(68)
        self._profile_terms.setStyleSheet(STYLE_TEXTAREA)
        self._profile_terms.setPlaceholderText(
            "Cloud Engineer, Kubernetes, Docker, deployment pipeline,\n"
            "load balancer, microservices, CI/CD, pull request, staging…"
        )
        play.addWidget(self._profile_terms)

        layout.addWidget(frm_p)

        # ── Proveedor LLM ─────────────────────────────────────────────────
        frm, flay = section(t("llm_section"))
        flay.addWidget(section_desc(
            t("llm_desc")
        ))

        row_prov = QHBoxLayout()
        row_prov.addWidget(label(t("llm_provider")))
        self._provider_combo = NoScrollComboBox()
        self._provider_combo.addItems(["Ollama (local)", f"OpenRouter ({t('cloud')})"])
        self._provider_combo.setStyleSheet(STYLE_COMBO)
        self._provider_combo.currentIndexChanged.connect(self._on_provider_change)
        row_prov.addWidget(self._provider_combo)
        flay.addLayout(row_prov)
        frm_provider = frm
        layout.addWidget(frm_provider)

        # ── Ollama ────────────────────────────────────────────────────────
        self._ollama_frame, olay = section("OLLAMA")
        olay.addWidget(section_desc(
            t("ollama_desc")
        ))

        row2 = QHBoxLayout()
        row2.addWidget(label(t("ollama_url")))
        self._ollama_url = QLineEdit()
        self._ollama_url.setStyleSheet(STYLE_INPUT)
        self._ollama_url.setPlaceholderText("http://localhost:11434")
        row2.addWidget(self._ollama_url)
        olay.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(label(t("model")))
        self._ollama_model_combo = NoScrollComboBox()
        self._ollama_model_combo.setStyleSheet(STYLE_COMBO)
        self._ollama_model_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row3.addWidget(self._ollama_model_combo)
        self._ollama_refresh_btn = icon_button("↻", t("refresh_models"), self._fetch_ollama_models)
        row3.addWidget(self._ollama_refresh_btn)
        olay.addLayout(row3)

        self._ollama_status = QLabel("")
        self._ollama_status.setWordWrap(True)
        self._ollama_status.setStyleSheet(f"font-size: 11px; color: {theme.MUTED};")
        olay.addWidget(self._ollama_status)

        # instalar modelo
        olay.addWidget(wrapped(label(t("ollama_install"), column=False)))
        self._ollama_install_combo = NoScrollComboBox()
        self._ollama_install_combo.setStyleSheet(STYLE_COMBO)
        self._ollama_install_combo.addItems([
            "llama3.2:3b", "llama3.1:8b", "mistral:7b",
            "qwen2.5:7b", "gemma3:4b", "phi4-mini:3.8b",
        ])
        olay.addWidget(self._ollama_install_combo)
        self._ollama_cmd_lbl = QLabel("ollama pull llama3.2:3b")
        self._ollama_cmd_lbl.setStyleSheet(STYLE_CODE)
        self._ollama_cmd_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        olay.addWidget(self._ollama_cmd_lbl)
        self._ollama_install_combo.currentTextChanged.connect(
            lambda m: self._ollama_cmd_lbl.setText(f"ollama pull {m}")
        )

        layout.addWidget(self._ollama_frame)

        # ── OpenRouter ────────────────────────────────────────────────────
        self._or_frame, orlay = section("OPENROUTER")
        orlay.addWidget(section_desc(
            t("openrouter_desc")
        ))

        row_key = QHBoxLayout()
        row_key.addWidget(label(t("api_key")))
        self._or_key = QLineEdit()
        self._or_key.setStyleSheet(STYLE_INPUT)
        self._or_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._or_key.setPlaceholderText("sk-or-…")
        row_key.addWidget(self._or_key)
        orlay.addLayout(row_key)

        row_model = QHBoxLayout()
        row_model.addWidget(label(t("model")))
        self._or_model_combo = NoScrollComboBox()
        self._or_model_combo.setStyleSheet(STYLE_COMBO)
        for m in config.OPENROUTER_FREE_MODELS:
            self._or_model_combo.addItem(m["label"], userData=m["id"])
        for custom_m in self._cfg.get("openrouter_custom_models", []):
            self._or_model_combo.addItem(custom_m, userData=custom_m)
        row_model.addWidget(self._or_model_combo)
        
        self._btn_add_or = icon_button("+", t("btn_new"), self._add_or_model)
        row_model.addWidget(self._btn_add_or)
        
        self._btn_del_or = icon_button("✕", t("btn_remove"), self._del_or_model)
        row_model.addWidget(self._btn_del_or)
        orlay.addLayout(row_model)

        layout.addWidget(self._or_frame)

        # ── Whisper ───────────────────────────────────────────────────────
        frm_w, wlay = section(t("transcription_settings"))
        wlay.addWidget(section_desc(
            t("whisper_desc")
        ))

        row_wm = QHBoxLayout()
        row_wm.addWidget(label(t("whisper_mode")))
        self._whisper_mode = NoScrollComboBox()
        self._whisper_mode.addItems([t("whisper_local"), t("whisper_api")])
        self._whisper_mode.setStyleSheet(STYLE_COMBO)
        self._whisper_mode.currentIndexChanged.connect(self._on_whisper_mode_change)
        row_wm.addWidget(self._whisper_mode)
        wlay.addLayout(row_wm)

        row_ws = QHBoxLayout()
        row_ws.addWidget(label(t("whisper_model")))
        self._whisper_size = NoScrollComboBox()
        self._whisper_size.addItems(["tiny", "base", "small", "medium", "large-v2"])
        self._whisper_size.setStyleSheet(STYLE_COMBO)
        row_ws.addWidget(self._whisper_size)
        wlay.addLayout(row_ws)

        row_dev = QHBoxLayout()
        row_dev.addWidget(label(t("whisper_device")))
        self._whisper_device = NoScrollComboBox()
        self._whisper_device.addItems([t("whisper_auto"), t("whisper_gpu"), t("whisper_cpu")])
        self._whisper_device.setStyleSheet(STYLE_COMBO)
        row_dev.addWidget(self._whisper_device)
        wlay.addLayout(row_dev)

        self._cuda_status = QLabel(t("cuda_checking"))
        self._cuda_status.setWordWrap(True)
        self._cuda_status.setStyleSheet(f"font-size: 11px; color: {theme.MUTED};")
        wlay.addWidget(self._cuda_status)
        self._check_cuda()

        # API fallback (Groq)
        self._whisper_api_frame = QFrame()
        api_layout = QVBoxLayout(self._whisper_api_frame)
        api_layout.setContentsMargins(0, 0, 0, 0)
        api_layout.setSpacing(8)

        row_wu = QHBoxLayout()
        row_wu.addWidget(label(t("api_provider")))
        self._whisper_api_combo = NoScrollComboBox()
        self._whisper_api_combo.setStyleSheet(STYLE_COMBO)
        for w in config.WHISPER_API_FREE:
            self._whisper_api_combo.addItem(w["label"], userData=w)
        row_wu.addWidget(self._whisper_api_combo)
        api_layout.addLayout(row_wu)

        row_wk = QHBoxLayout()
        row_wk.addWidget(label(t("api_key")))
        self._whisper_api_key = QLineEdit()
        self._whisper_api_key.setStyleSheet(STYLE_INPUT)
        self._whisper_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._whisper_api_key.setPlaceholderText("gsk_…")
        row_wk.addWidget(self._whisper_api_key)
        api_layout.addLayout(row_wk)

        wlay.addWidget(self._whisper_api_frame)
        layout.addWidget(frm_w)

        # ── Idioma & Hotkey ────────────────────────────────────────────────
        frm_misc, mlay = section(t("settings_general"))

        row_ui_lang = QHBoxLayout()
        row_ui_lang.addWidget(label(t("ui_language")))
        self._ui_lang_combo = NoScrollComboBox()
        self._ui_lang_combo.setStyleSheet(STYLE_COMBO)
        self._ui_lang_combo.addItems(["en — English", "es — Español"])
        row_ui_lang.addWidget(self._ui_lang_combo)
        mlay.addLayout(row_ui_lang)

        row_acc = QHBoxLayout()
        row_acc.addWidget(label(t("accent_color")))
        self._accent_picker = AccentPicker(
            theme.ACCENTS, {k: t(f"accent_{k}") for k in theme.ACCENTS})
        row_acc.addWidget(self._accent_picker)
        row_acc.addStretch()
        mlay.addLayout(row_acc)

        row_lang = QHBoxLayout()
        row_lang.addWidget(label(t("dictation_lang")))
        self._lang_combo = NoScrollComboBox()
        self._lang_combo.setStyleSheet(STYLE_COMBO)
        self._lang_combo.addItems(["es — Español", "en — English"])
        row_lang.addWidget(self._lang_combo)
        mlay.addLayout(row_lang)

        row_hk = QHBoxLayout()
        row_hk.addWidget(label(t("hotkey")))
        self._hotkey_capture = KeyCaptureWidget()
        row_hk.addWidget(self._hotkey_capture)
        mlay.addLayout(row_hk)

        row_hkm = QHBoxLayout()
        row_hkm.addWidget(label(t("hotkey_mode")))
        self._hotkey_mode = NoScrollComboBox()
        self._hotkey_mode.setStyleSheet(STYLE_COMBO)
        self._hotkey_mode.addItems([t("hotkey_hold"), t("hotkey_toggle")])
        row_hkm.addWidget(self._hotkey_mode)
        mlay.addLayout(row_hkm)

        self._auto_paste_cb = ToggleSwitch(t("auto_paste"))
        mlay.addWidget(self._auto_paste_cb)

        self._play_sounds_cb = ToggleSwitch(t("play_sounds"))
        mlay.addWidget(self._play_sounds_cb)

        self._show_overlay_cb = ToggleSwitch(t("show_overlay"))
        mlay.addWidget(self._show_overlay_cb)

        self._esc_cancels_cb = ToggleSwitch(t("esc_cancels"))
        mlay.addWidget(self._esc_cancels_cb)

        layout.addWidget(frm_misc)

        layout.addStretch()
        scroll.setWidget(inner)

        # ── Guardar: barra fija bajo el scroll, siempre visible ────────────
        footer = QWidget()
        footer.setObjectName("footer")
        footer.setStyleSheet(f"QWidget#footer {{ background: {theme.SURFACE}; border-top: 1px solid {theme.BORDER}; }}")
        frow = QHBoxLayout(footer)
        frow.setContentsMargins(16, 10, 16, 10)
        self._save_status = QLabel("")
        self._save_status.setStyleSheet(f"font-size: 12px; color: {theme.GREEN_HI}; background: transparent;")
        frow.addWidget(self._save_status)
        frow.addStretch()
        save_btn = QPushButton(t("btn_save_settings"))
        save_btn.setStyleSheet(STYLE_BTN_PRIMARY)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save)
        frow.addWidget(save_btn)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(scroll)
        outer.addWidget(footer)

    # ── carga ──────────────────────────────────────────────────────────────

    def _load_values(self):
        c = self._cfg
        
        self._setting_profile_combo.blockSignals(True)
        self._setting_profile_combo.clear()
        active_id = c.get("active_profile_id", "default")
        idx_to_select = 0
        for i, p in enumerate(c.get("profiles", [])):
            self._setting_profile_combo.addItem(p["name"], userData=p["id"])
            if p["id"] == active_id:
                idx_to_select = i
        self._setting_profile_combo.setCurrentIndex(idx_to_select)
        self._setting_profile_combo.blockSignals(False)
        self._current_setting_pid = active_id
        
        for p in c.get("profiles", []):
            if p["id"] == active_id:
                self._profile_role.setText(p.get("role", ""))
                self._profile_terms.setPlainText(p.get("custom_terms", ""))
                break

        provider = c.get("llm_provider", "ollama")
        self._provider_combo.setCurrentIndex(0 if provider == "ollama" else 1)
        self._on_provider_change(0 if provider == "ollama" else 1)

        self._ollama_url.setText(c.get("ollama_base_url", "http://localhost:11434"))
        self._or_key.setText(c.get("openrouter_api_key", ""))

        or_model = c.get("openrouter_model", "")
        found = False
        for i in range(self._or_model_combo.count()):
            if self._or_model_combo.itemData(i) == or_model:
                self._or_model_combo.setCurrentIndex(i)
                found = True
                break
        if not found and or_model:
            self._or_model_combo.setCurrentText(or_model)

        wmode = c.get("whisper_mode", "local")
        self._whisper_mode.setCurrentIndex(0 if wmode == "local" else 1)
        self._on_whisper_mode_change(0 if wmode == "local" else 1)

        wsize = c.get("whisper_model", "medium")
        idx = self._whisper_size.findText(wsize)
        if idx >= 0:
            self._whisper_size.setCurrentIndex(idx)

        dev_map = {"auto": 0, "cuda": 1, "cpu": 2}
        self._whisper_device.setCurrentIndex(dev_map.get(c.get("whisper_device", "auto"), 0))

        self._whisper_api_key.setText(c.get("whisper_api_key", ""))
        self._hotkey_capture.set_key(c.get("hotkey", "alt"))
        self._hotkey_mode.setCurrentIndex(0 if c.get("hotkey_mode", "hold") == "hold" else 1)

        lang = c.get("language", "es")
        lang_map = {"es": 0, "en": 1}
        self._lang_combo.setCurrentIndex(lang_map.get(lang, 0))

        ui_lang = c.get("ui_language", "en")
        ui_lang_map = {"en": 0, "es": 1}
        self._ui_lang_combo.setCurrentIndex(ui_lang_map.get(ui_lang, 0))
        self._accent_picker.set_value(c.get("accent", theme.DEFAULT_ACCENT))

        self._auto_paste_cb.setChecked(c.get("auto_paste", False))
        self._play_sounds_cb.setChecked(c.get("play_sounds", True))
        self._show_overlay_cb.setChecked(c.get("show_overlay", True))
        self._esc_cancels_cb.setChecked(c.get("esc_cancels", True))

        self._fetch_ollama_models()

    # ── slots ──────────────────────────────────────────────────────────────

    def _run_worker(self, worker: QObject, start, finished_signals) -> QThread:
        """Ejecuta worker.start en un hilo propio. Se guarda una referencia a
        hilo y worker hasta que terminan: si se soltaran antes (p.ej. al pulsar
        "refrescar" dos veces seguidas), Qt los destruiría en plena ejecución."""
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(start)
        for sig in finished_signals:
            sig.connect(thread.quit)
        pair = (thread, worker)
        self._workers.add(pair)
        thread.finished.connect(lambda: self._workers.discard(pair))
        thread.finished.connect(thread.deleteLater)
        thread.start()
        return thread

    def shutdown(self, timeout_ms: int = 1500):
        """Espera a los hilos en segundo plano antes de salir: destruir un
        QThread que sigue corriendo aborta el proceso."""
        for thread in self.findChildren(QThread):
            thread.quit()
            thread.wait(timeout_ms)

    def _check_cuda(self):
        checker = CudaChecker()
        checker.result.connect(self._on_cuda_result)
        self._run_worker(checker, checker.check, [checker.result])

    def _on_cuda_result(self, text: str, color: str):
        self._cuda_status.setText(text)
        self._cuda_status.setStyleSheet(f"font-size: 11px; color: {color};")

    def _on_provider_change(self, idx: int):
        self._ollama_frame.setVisible(idx == 0)
        self._or_frame.setVisible(idx == 1)

    def _on_whisper_mode_change(self, idx: int):
        self._whisper_api_frame.setVisible(idx == 1)

    def _fetch_ollama_models(self):
        self._ollama_status.setText(t("ollama_connecting"))
        self._ollama_model_combo.clear()
        base_url = self._ollama_url.text().strip() or "http://localhost:11434"

        self._fetcher = OllamaFetcher(base_url)
        self._fetcher.done.connect(self._on_ollama_models)
        self._fetcher.error.connect(self._on_ollama_error)
        self._run_worker(self._fetcher, self._fetcher.fetch, [self._fetcher.done, self._fetcher.error])

    def _on_ollama_models(self, models: list):
        if self.sender() is not self._fetcher:
            return   # respuesta de una consulta anterior
        self._ollama_model_combo.clear()
        if models:
            self._ollama_model_combo.addItems(models)
            saved = self._cfg.get("ollama_model", "")
            idx = self._ollama_model_combo.findText(saved)
            if idx >= 0:
                self._ollama_model_combo.setCurrentIndex(idx)
            self._ollama_status.setText(t("ollama_models_found").format(n=len(models)))
            self._ollama_status.setStyleSheet(f"font-size: 11px; color: {theme.GREEN};")
        else:
            self._ollama_status.setText(t("ollama_no_models"))
            self._ollama_status.setStyleSheet(f"font-size: 11px; color: {theme.AMBER};")

    def _on_ollama_error(self, err: str):
        if self.sender() is not self._fetcher:
            return
        self._ollama_status.setText(t("ollama_not_found"))
        self._ollama_status.setStyleSheet(f"font-size: 11px; color: {theme.RED};")

    def _save(self):
        cfg = config.load()
        
        pid = self._setting_profile_combo.currentData()
        for p in self._cfg.get("profiles", []):
            if p["id"] == pid:
                p["role"] = self._profile_role.text().strip()
                p["custom_terms"] = self._profile_terms.toPlainText().strip()
                break
        
        cfg["profiles"] = self._cfg.get("profiles", [])
        
        provider_idx = self._provider_combo.currentIndex()
        cfg["llm_provider"] = "ollama" if provider_idx == 0 else "openrouter"
        cfg["ollama_base_url"]    = self._ollama_url.text().strip() or "http://localhost:11434"
        cfg["ollama_model"]       = self._ollama_model_combo.currentText()
        cfg["openrouter_api_key"] = self._or_key.text().strip()
        cfg["openrouter_model"]   = self._or_model_combo.currentData() or ""
        
        custom_models = []
        for i in range(len(config.OPENROUTER_FREE_MODELS), self._or_model_combo.count()):
            m = self._or_model_combo.itemData(i)
            if m: custom_models.append(m)
        cfg["openrouter_custom_models"] = custom_models

        cfg["whisper_mode"]       = "local" if self._whisper_mode.currentIndex() == 0 else "api"
        cfg["whisper_model"]      = self._whisper_size.currentText()
        dev_map = {0: "auto", 1: "cuda", 2: "cpu"}
        cfg["whisper_device"]     = dev_map[self._whisper_device.currentIndex()]
        cfg["whisper_api_key"]    = self._whisper_api_key.text().strip()

        wapi = self._whisper_api_combo.currentData()
        if wapi:
            cfg["whisper_api_url"]   = wapi["url"]
            cfg["whisper_api_model"] = wapi["model"]

        cfg["hotkey"] = self._hotkey_capture.get_key()
        cfg["hotkey_mode"] = "hold" if self._hotkey_mode.currentIndex() == 0 else "toggle"
        lang_map = {0: "es", 1: "en"}
        cfg["language"] = lang_map.get(self._lang_combo.currentIndex(), "es")

        ui_lang_map = {0: "en", 1: "es"}
        cfg["ui_language"] = ui_lang_map.get(self._ui_lang_combo.currentIndex(), "en")
        cfg["accent"] = self._accent_picker.value()
        # idioma y color se aplican al construir la interfaz: hace falta reiniciar
        needs_restart = (cfg["ui_language"] != t_lang_loaded()
                         or cfg["accent"] != theme.ACCENT_KEY)

        cfg["auto_paste"] = self._auto_paste_cb.isChecked()
        cfg["play_sounds"] = self._play_sounds_cb.isChecked()
        cfg["show_overlay"] = self._show_overlay_cb.isChecked()
        cfg["esc_cancels"] = self._esc_cancels_cb.isChecked()

        config.save(cfg)
        self._cfg = cfg
        self._save_status.setText(f"✓ {t('saved')}")
        self.saved.emit()
        if needs_restart:
            self.restart_requested.emit()
        QTimer.singleShot(2000, lambda: self._save_status.setText(""))

    def _on_settings_profile_changed(self, idx: int):
        if idx < 0: return
        pid = self._setting_profile_combo.itemData(idx)
        
        if hasattr(self, "_current_setting_pid") and self._current_setting_pid:
            for p in self._cfg.get("profiles", []):
                if p["id"] == self._current_setting_pid:
                    p["role"] = self._profile_role.text().strip()
                    p["custom_terms"] = self._profile_terms.toPlainText().strip()
                    break
        
        self._current_setting_pid = pid
        for p in self._cfg.get("profiles", []):
            if p["id"] == pid:
                self._profile_role.setText(p.get("role", ""))
                self._profile_terms.setPlainText(p.get("custom_terms", ""))
                break

    def _add_profile(self):
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, t("profile_name"), t("profile_name_prompt"))
        if ok and text.strip():
            pid = text.strip().lower().replace(" ", "_")
            while any(p["id"] == pid for p in self._cfg.get("profiles", [])):
                pid += "_"
            
            self._cfg.setdefault("profiles", []).append({
                "id": pid,
                "name": text.strip(),
                "role": "",
                "custom_terms": ""
            })
            
            self._setting_profile_combo.addItem(text.strip(), userData=pid)
            self._setting_profile_combo.setCurrentIndex(self._setting_profile_combo.count() - 1)

    def _delete_profile(self):
        pid = self._setting_profile_combo.currentData()
        profiles = self._cfg.get("profiles", [])
        if len(profiles) <= 1:
            return
            
        self._cfg["profiles"] = [p for p in profiles if p["id"] != pid]
        idx = self._setting_profile_combo.currentIndex()
        self._setting_profile_combo.removeItem(idx)

    def _add_or_model(self):
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "OpenRouter", t("or_model_prompt"))
        if ok and text.strip():
            m_id = text.strip()
            for i in range(self._or_model_combo.count()):
                if self._or_model_combo.itemData(i) == m_id:
                    self._or_model_combo.setCurrentIndex(i)
                    return
            self._or_model_combo.addItem(m_id, userData=m_id)
            self._or_model_combo.setCurrentIndex(self._or_model_combo.count() - 1)

    def _del_or_model(self):
        idx = self._or_model_combo.currentIndex()
        if idx >= len(config.OPENROUTER_FREE_MODELS):
            self._or_model_combo.removeItem(idx)

    # ── generación de perfil con IA ────────────────────────────────────────

    def _generate_profile(self):
        desc = self._gen_input.text().strip()
        if not desc:
            self._gen_status.setText(t("profile_gen_empty"))
            self._gen_status.setStyleSheet(f"font-size: 11px; color: {theme.AMBER};")
            return
        self._gen_btn.setEnabled(False)
        self._gen_btn.setText(t("generating"))
        self._gen_status.setText("")

        from core.rewriter import ProfileGenerateSignals, ProfileGenerateTask
        self._profile_sigs = ProfileGenerateSignals()
        self._profile_sigs.done.connect(self._on_profile_generated)
        self._profile_sigs.error.connect(self._on_profile_error)
        task = ProfileGenerateTask(desc, self._profile_sigs)
        task.setAutoDelete(True)
        QThreadPool.globalInstance().start(task)

    def _on_profile_generated(self, role: str, terms: str):
        self._profile_role.setText(role)
        self._profile_terms.setPlainText(terms)
        self._gen_btn.setEnabled(True)
        self._gen_btn.setText(f"✨ {t('btn_generate_profile')}")
        self._gen_status.setText(f"✓ {t('profile_generated')}")
        self._gen_status.setStyleSheet(f"font-size: 11px; color: {theme.GREEN};")
        QTimer.singleShot(4000, lambda: self._gen_status.setText(""))

    def _on_profile_error(self, msg: str):
        self._gen_btn.setEnabled(True)
        self._gen_btn.setText(f"✨ {t('btn_generate_profile')}")
        self._gen_status.setText(f"Error: {msg}")
        self._gen_status.setStyleSheet(f"font-size: 11px; color: {theme.RED};")
