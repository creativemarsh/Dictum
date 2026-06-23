"""
tab_settings.py
Ajustes: proveedor LLM, modelo, Whisper, hotkey, API keys.
"""
import httpx
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QTextEdit, QPushButton, QFrame, QScrollArea, QSizePolicy, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, QTimer, QThreadPool, pyqtSignal, pyqtSlot, QObject, QEvent
import config

STYLE_SECTION = """
    QFrame {
        background: #111116;
        border: 1px solid #2c2c2a;
        border-radius: 8px;
    }
"""
STYLE_INPUT = """
    QLineEdit {
        background: #0d0d12;
        border: 1px solid #2c2c2a;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 13px;
        color: #e8e6e3;
    }
    QLineEdit:focus { border-color: #534AB7; }
"""
STYLE_COMBO = """
    QComboBox {
        background: #0d0d12;
        border: 1px solid #2c2c2a;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 13px;
        color: #e8e6e3;
    }
    QComboBox::drop-down { border: none; width: 24px; }
    QComboBox QAbstractItemView {
        background: #111116;
        border: 1px solid #444441;
        color: #e8e6e3;
        selection-background-color: #534AB7;
    }
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
"""
STYLE_BTN_PRIMARY = """
    QPushButton {
        background: #534AB7;
        border: none;
        border-radius: 6px;
        padding: 6px 18px;
        font-size: 13px;
        color: #e8e6e3;
        font-weight: 500;
    }
    QPushButton:hover { background: #6358c8; }
"""
STYLE_CODE = """
    QLabel {
        background: #0d0d12;
        border: 1px solid #2c2c2a;
        border-radius: 6px;
        padding: 8px 12px;
        font-family: 'Consolas', monospace;
        font-size: 12px;
        color: #9FE1CB;
    }
"""
STYLE_KEY_LABEL = """
    QLabel {
        background: #0d0d12;
        border: 1px solid #2c2c2a;
        border-radius: 6px;
        padding: 6px 14px;
        font-size: 13px;
        color: #e8e6e3;
        min-width: 140px;
        qproperty-alignment: AlignCenter;
    }
"""
STYLE_KEY_LABEL_ACTIVE = """
    QLabel {
        background: #0d0d12;
        border: 1px solid #534AB7;
        border-radius: 6px;
        padding: 6px 14px;
        font-size: 13px;
        color: #5f5e5a;
        min-width: 140px;
        qproperty-alignment: AlignCenter;
    }
"""
STYLE_TEXTAREA = """
    QTextEdit {
        background: #0d0d12;
        border: 1px solid #2c2c2a;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
        color: #e8e6e3;
    }
    QTextEdit:focus { border-color: #534AB7; }
"""


def section(title: str) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setStyleSheet(STYLE_SECTION)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(10)
    lbl = QLabel(title)
    lbl.setStyleSheet("font-size: 11px; color: #5f5e5a; letter-spacing: 0.05em;")
    layout.addWidget(lbl)
    return frame, layout


def label(text: str) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet("font-size: 12px; color: #888780;")
    return l


def _key_display_name(name: str) -> str:
    _NAMES = {
        'left alt':    'Alt Izquierdo',
        'right alt':   'Alt Derecho',
        'left ctrl':   'Ctrl Izquierdo',
        'right ctrl':  'Ctrl Derecho',
        'left shift':  'Shift Izquierdo',
        'right shift': 'Shift Derecho',
        'alt':   'Alt',   'ctrl':  'Ctrl',  'shift': 'Shift',
        'caps lock':   'Bloq Mayús',
        'space':       'Espacio',
        'tab':         'Tab',
        'esc':         'Escape',
        'insert':      'Insert',
        'delete':      'Supr',
        'home':        'Inicio',
        'end':         'Fin',
        'page up':     'Re Pág',
        'page down':   'Av Pág',
        'left windows':  'Win Izq',
        'right windows': 'Win Der',
        'windows': 'Windows',
        'menu':    'Menú',
        'pause':   'Pausa',
        **{f'f{i}': f'F{i}' for i in range(1, 13)},
    }
    return _NAMES.get(name.lower(), name.upper() if len(name) == 1 else name.title())


class KeyFilter(QObject):
    key_pressed = pyqtSignal(int, str, int)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            self.key_pressed.emit(event.key(), event.text(), event.nativeVirtualKey())
            return True
        return False


class KeyCaptureWidget(QWidget):
    """Muestra la tecla configurada y permite cambiarla presionando cualquier tecla."""
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

        self._btn = QPushButton('Capturar')
        self._btn.setStyleSheet(STYLE_BTN)
        self._btn.setFixedWidth(90)
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
        self._display.setText('esperando tecla…')
        self._display.setStyleSheet(STYLE_KEY_LABEL_ACTIVE)
        self._btn.setText('✕ Cancelar')
        
        # Instalar filtro de eventos global en la aplicación
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
        self._btn.setText('Capturar')

    def _on_captured_key(self, key: int, text: str, nvk: int):
        # Diferenciar modificadores izquierdo/derecho en Windows (virtual key codes)
        _MODIFIERS_MAP = {
            160: 'left shift',
            161: 'right shift',
            162: 'left ctrl',
            163: 'right ctrl',
            164: 'left alt',
            165: 'right alt',
        }

        if nvk in _MODIFIERS_MAP:
            key_name = _MODIFIERS_MAP[nvk]
        else:
            key_name = self._map_qt_key_to_name(key, text)

        if key_name:
            self._apply_key(key_name)

    def _map_qt_key_to_name(self, key: int, text: str) -> str:
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
        self._btn.setText('Capturar')
        self.key_changed.emit(key_name)

    def hideEvent(self, event):
        if self._capturing:
            self._cancel_capture()
        super().hideEvent(event)


class NoScrollComboBox(QComboBox):
    """Ignora el scroll del mouse a menos que el widget tenga el foco activo."""
    def wheelEvent(self, event):
        event.ignore()


def section_desc(text: str) -> QLabel:
    l = QLabel(text)
    l.setWordWrap(True)
    l.setStyleSheet("font-size: 11px; color: #5f5e5a; margin-bottom: 2px;")
    return l


class CudaChecker(QObject):
    result = pyqtSignal(str, str)  # text, color

    def check(self):
        try:
            import torch
            if torch.cuda.is_available():
                name = torch.cuda.get_device_name(0)
                self.result.emit(f"CUDA disponible — {name}", "#639922")
            else:
                self.result.emit("CUDA no disponible — se usará CPU", "#EF9F27")
        except Exception as e:
            self.result.emit(f"CUDA no disponible: {e}", "#E24B4A")


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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cfg = config.load()
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # ── Perfil de usuario ─────────────────────────────────────────────
        frm_p, play = section("PERFIL DE USUARIO")

        # --- bloque: generar con IA ---
        play.addWidget(section_desc(
            "Describí tu trabajo y la IA generará el rol y los términos técnicos automáticamente."
        ))

        gen_row = QHBoxLayout()
        self._gen_input = QLineEdit()
        self._gen_input.setStyleSheet(STYLE_INPUT)
        self._gen_input.setPlaceholderText(
            "ej: \"Cloud Engineer\" o \"DevOps en startup, pipelines CI/CD en GCP y AWS\""
        )
        gen_row.addWidget(self._gen_input)
        self._gen_btn = QPushButton("✨ Generar perfil")
        self._gen_btn.setStyleSheet(STYLE_BTN_PRIMARY)
        self._gen_btn.setFixedWidth(120)
        self._gen_btn.clicked.connect(self._generate_profile)
        gen_row.addWidget(self._gen_btn)
        play.addLayout(gen_row)

        self._gen_status = QLabel("")
        self._gen_status.setStyleSheet("font-size: 11px; color: #888780;")
        play.addWidget(self._gen_status)

        # separador visual
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2c2c2a;")
        play.addWidget(sep)

        # --- bloque: edición manual ---
        play.addWidget(section_desc("Gestiona tus perfiles:"))

        row_prof_sel = QHBoxLayout()
        row_prof_sel.addWidget(label("perfil a editar"))
        self._setting_profile_combo = NoScrollComboBox()
        self._setting_profile_combo.setStyleSheet(STYLE_COMBO)
        self._setting_profile_combo.currentIndexChanged.connect(self._on_settings_profile_changed)
        row_prof_sel.addWidget(self._setting_profile_combo)

        self._btn_new_prof = QPushButton("+ Nuevo")
        self._btn_new_prof.setStyleSheet(STYLE_BTN)
        self._btn_new_prof.clicked.connect(self._add_profile)
        row_prof_sel.addWidget(self._btn_new_prof)

        self._btn_del_prof = QPushButton("✕ Eliminar")
        self._btn_del_prof.setStyleSheet(STYLE_BTN)
        self._btn_del_prof.clicked.connect(self._delete_profile)
        row_prof_sel.addWidget(self._btn_del_prof)
        play.addLayout(row_prof_sel)

        row_role = QHBoxLayout()
        row_role.addWidget(label("rol"))
        self._profile_role = QLineEdit()
        self._profile_role.setStyleSheet(STYLE_INPUT)
        self._profile_role.setPlaceholderText("ej: Cloud Engineer, trabajo con AWS, GCP y Kubernetes")
        row_role.addWidget(self._profile_role)
        play.addLayout(row_role)

        play.addWidget(label("términos técnicos (separados por coma)"))
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
        frm, flay = section("PROVEEDOR DE IA")
        flay.addWidget(section_desc(
            "El modelo de IA toma el texto crudo de Whisper y lo limpia: "
            "elimina muletillas, aplica correcciones verbales y respeta tu vocabulario."
        ))

        row = QHBoxLayout()
        row.addWidget(label("proveedor"))
        self._provider_combo = NoScrollComboBox()
        self._provider_combo.addItems(["Ollama (local)", "OpenRouter (nube)"])
        self._provider_combo.setStyleSheet(STYLE_COMBO)
        self._provider_combo.currentIndexChanged.connect(self._on_provider_change)
        row.addWidget(self._provider_combo)
        flay.addLayout(row)
        frm_provider = frm
        layout.addWidget(frm_provider)

        # ── Ollama ────────────────────────────────────────────────────────
        self._ollama_frame, olay = section("OLLAMA")
        olay.addWidget(section_desc(
            "Corre modelos localmente en tu PC. Gratis, sin enviar datos a internet. "
            "Requiere GPU con ≥ 6 GB de VRAM o una CPU potente."
        ))

        row2 = QHBoxLayout()
        row2.addWidget(label("URL base"))
        self._ollama_url = QLineEdit()
        self._ollama_url.setStyleSheet(STYLE_INPUT)
        self._ollama_url.setPlaceholderText("http://localhost:11434")
        row2.addWidget(self._ollama_url)
        olay.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(label("modelo"))
        self._ollama_model_combo = NoScrollComboBox()
        self._ollama_model_combo.setStyleSheet(STYLE_COMBO)
        self._ollama_model_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row3.addWidget(self._ollama_model_combo)
        self._ollama_refresh_btn = QPushButton("↻ refresh")
        self._ollama_refresh_btn.setStyleSheet(STYLE_BTN)
        self._ollama_refresh_btn.clicked.connect(self._fetch_ollama_models)
        row3.addWidget(self._ollama_refresh_btn)
        olay.addLayout(row3)

        self._ollama_status = QLabel("")
        self._ollama_status.setStyleSheet("font-size: 11px; color: #888780;")
        olay.addWidget(self._ollama_status)

        # instalar modelo
        olay.addWidget(label("instalar modelo (ejecuta en tu terminal):"))
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
            "Acceso a modelos en la nube vía API. Los modelos marcados \":free\" "
            "son gratuitos pero pueden tener límites de velocidad."
        ))

        row_key = QHBoxLayout()
        row_key.addWidget(label("API key"))
        self._or_key = QLineEdit()
        self._or_key.setStyleSheet(STYLE_INPUT)
        self._or_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._or_key.setPlaceholderText("sk-or-…")
        row_key.addWidget(self._or_key)
        orlay.addLayout(row_key)

        row_model = QHBoxLayout()
        row_model.addWidget(label("modelo"))
        self._or_model_combo = NoScrollComboBox()
        self._or_model_combo.setStyleSheet(STYLE_COMBO)
        for m in config.OPENROUTER_FREE_MODELS:
            self._or_model_combo.addItem(m["label"], userData=m["id"])
        for custom_m in self._cfg.get("openrouter_custom_models", []):
            self._or_model_combo.addItem(custom_m, userData=custom_m)
        row_model.addWidget(self._or_model_combo)
        
        self._btn_add_or = QPushButton("+ Nuevo")
        self._btn_add_or.setStyleSheet(STYLE_BTN)
        self._btn_add_or.clicked.connect(self._add_or_model)
        row_model.addWidget(self._btn_add_or)
        
        self._btn_del_or = QPushButton("✕ Quitar")
        self._btn_del_or.setStyleSheet(STYLE_BTN)
        self._btn_del_or.clicked.connect(self._del_or_model)
        row_model.addWidget(self._btn_del_or)
        orlay.addLayout(row_model)

        layout.addWidget(self._or_frame)

        # ── Whisper ───────────────────────────────────────────────────────
        frm_w, wlay = section("TRANSCRIPCIÓN (WHISPER)")
        wlay.addWidget(section_desc(
            "Whisper convierte tu voz a texto. "
            "Modo local usa tu GPU (rápido, privado). "
            "Modo API usa Groq Whisper en la nube (gratis con límite de tasa)."
        ))

        row_wm = QHBoxLayout()
        row_wm.addWidget(label("modo"))
        self._whisper_mode = NoScrollComboBox()
        self._whisper_mode.addItems(["Local (CUDA)", "API externa"])
        self._whisper_mode.setStyleSheet(STYLE_COMBO)
        self._whisper_mode.currentIndexChanged.connect(self._on_whisper_mode_change)
        row_wm.addWidget(self._whisper_mode)
        wlay.addLayout(row_wm)

        row_ws = QHBoxLayout()
        row_ws.addWidget(label("modelo local"))
        self._whisper_size = NoScrollComboBox()
        self._whisper_size.addItems(["tiny", "base", "small", "medium", "large-v2"])
        self._whisper_size.setStyleSheet(STYLE_COMBO)
        row_ws.addWidget(self._whisper_size)
        wlay.addLayout(row_ws)

        row_dev = QHBoxLayout()
        row_dev.addWidget(label("dispositivo"))
        self._whisper_device = NoScrollComboBox()
        self._whisper_device.addItems(["Automático", "CUDA (GPU)", "CPU"])
        self._whisper_device.setStyleSheet(STYLE_COMBO)
        row_dev.addWidget(self._whisper_device)
        wlay.addLayout(row_dev)

        self._cuda_status = QLabel("verificando CUDA…")
        self._cuda_status.setStyleSheet("font-size: 11px; color: #888780;")
        wlay.addWidget(self._cuda_status)
        self._check_cuda()

        # API fallback (Groq)
        self._whisper_api_frame = QFrame()
        api_layout = QVBoxLayout(self._whisper_api_frame)
        api_layout.setContentsMargins(0, 0, 0, 0)
        api_layout.setSpacing(8)

        row_wu = QHBoxLayout()
        row_wu.addWidget(label("proveedor API"))
        self._whisper_api_combo = NoScrollComboBox()
        self._whisper_api_combo.setStyleSheet(STYLE_COMBO)
        for w in config.WHISPER_API_FREE:
            self._whisper_api_combo.addItem(w["label"], userData=w)
        row_wu.addWidget(self._whisper_api_combo)
        api_layout.addLayout(row_wu)

        row_wk = QHBoxLayout()
        row_wk.addWidget(label("API key"))
        self._whisper_api_key = QLineEdit()
        self._whisper_api_key.setStyleSheet(STYLE_INPUT)
        self._whisper_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._whisper_api_key.setPlaceholderText("gsk_…")
        row_wk.addWidget(self._whisper_api_key)
        api_layout.addLayout(row_wk)

        wlay.addWidget(self._whisper_api_frame)
        layout.addWidget(frm_w)

        # ── Idioma & Hotkey ────────────────────────────────────────────────
        frm_misc, mlay = section("GENERAL")

        row_lang = QHBoxLayout()
        row_lang.addWidget(label("idioma de dictado"))
        self._lang_combo = NoScrollComboBox()
        self._lang_combo.setStyleSheet(STYLE_COMBO)
        self._lang_combo.addItems(["es — Español", "en — English", "pt — Português"])
        row_lang.addWidget(self._lang_combo)
        mlay.addLayout(row_lang)

        row_hk = QHBoxLayout()
        row_hk.addWidget(label("tecla de dictado"))
        self._hotkey_capture = KeyCaptureWidget()
        row_hk.addWidget(self._hotkey_capture)
        mlay.addLayout(row_hk)

        row_hkm = QHBoxLayout()
        row_hkm.addWidget(label("modo de activación"))
        self._hotkey_mode = NoScrollComboBox()
        self._hotkey_mode.setStyleSheet(STYLE_COMBO)
        self._hotkey_mode.addItems(["Mantener presionada", "Un toque (Iniciar/Parar)"])
        row_hkm.addWidget(self._hotkey_mode)
        mlay.addLayout(row_hkm)

        self._auto_paste_cb = QCheckBox(" Pegar automáticamente al terminar (Ctrl+V)")
        self._auto_paste_cb.setStyleSheet("color: #e8e6e3; font-size: 13px;")
        mlay.addWidget(self._auto_paste_cb)

        self._play_sounds_cb = QCheckBox(" Reproducir sonidos al grabar y procesar")
        self._play_sounds_cb.setStyleSheet("color: #e8e6e3; font-size: 13px;")
        mlay.addWidget(self._play_sounds_cb)

        layout.addWidget(frm_misc)

        # ── Guardar ────────────────────────────────────────────────────────
        save_btn = QPushButton("guardar ajustes")
        save_btn.setStyleSheet(STYLE_BTN_PRIMARY)
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._save_status = QLabel("")
        self._save_status.setStyleSheet("font-size: 12px; color: #639922;")
        self._save_status.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._save_status)

        layout.addStretch()
        scroll.setWidget(inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

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
        lang_map = {"es": 0, "en": 1, "pt": 2}
        self._lang_combo.setCurrentIndex(lang_map.get(lang, 0))

        self._auto_paste_cb.setChecked(c.get("auto_paste", False))
        self._play_sounds_cb.setChecked(c.get("play_sounds", True))

        self._fetch_ollama_models()

    # ── slots ──────────────────────────────────────────────────────────────

    def _check_cuda(self):
        self._cuda_thread = QThread()
        self._cuda_checker = CudaChecker()
        self._cuda_checker.moveToThread(self._cuda_thread)
        self._cuda_thread.started.connect(self._cuda_checker.check)
        self._cuda_checker.result.connect(self._on_cuda_result)
        self._cuda_checker.result.connect(self._cuda_thread.quit)
        self._cuda_thread.start()

    def _on_cuda_result(self, text: str, color: str):
        self._cuda_status.setText(text)
        self._cuda_status.setStyleSheet(f"font-size: 11px; color: {color};")

    def _on_provider_change(self, idx: int):
        self._ollama_frame.setVisible(idx == 0)
        self._or_frame.setVisible(idx == 1)

    def _on_whisper_mode_change(self, idx: int):
        self._whisper_api_frame.setVisible(idx == 1)

    def _fetch_ollama_models(self):
        self._ollama_status.setText("conectando con Ollama…")
        self._ollama_model_combo.clear()
        base_url = self._ollama_url.text().strip() or "http://localhost:11434"

        self._fetch_thread = QThread()
        self._fetcher = OllamaFetcher(base_url)
        self._fetcher.moveToThread(self._fetch_thread)
        self._fetch_thread.started.connect(self._fetcher.fetch)
        self._fetcher.done.connect(self._on_ollama_models)
        self._fetcher.done.connect(self._fetch_thread.quit)
        self._fetcher.error.connect(self._on_ollama_error)
        self._fetcher.error.connect(self._fetch_thread.quit)
        self._fetch_thread.start()

    def _on_ollama_models(self, models: list):
        self._ollama_model_combo.clear()
        if models:
            self._ollama_model_combo.addItems(models)
            saved = self._cfg.get("ollama_model", "")
            idx = self._ollama_model_combo.findText(saved)
            if idx >= 0:
                self._ollama_model_combo.setCurrentIndex(idx)
            self._ollama_status.setText(f"{len(models)} modelo(s) instalado(s)")
            self._ollama_status.setStyleSheet("font-size: 11px; color: #639922;")
        else:
            self._ollama_status.setText("Ollama no tiene modelos instalados aún")
            self._ollama_status.setStyleSheet("font-size: 11px; color: #EF9F27;")

    def _on_ollama_error(self, err: str):
        self._ollama_status.setText(f"Ollama no encontrado — ¿está corriendo?")
        self._ollama_status.setStyleSheet("font-size: 11px; color: #E24B4A;")

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
        lang_map = {0: "es", 1: "en", 2: "pt"}
        cfg["language"] = lang_map.get(self._lang_combo.currentIndex(), "es")

        cfg["auto_paste"] = self._auto_paste_cb.isChecked()
        cfg["play_sounds"] = self._play_sounds_cb.isChecked()

        config.save(cfg)
        self._cfg = cfg
        self._save_status.setText("✓ guardado")
        self.saved.emit()
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
        text, ok = QInputDialog.getText(self, "Nuevo Perfil", "Nombre del perfil:")
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
        text, ok = QInputDialog.getText(self, "Nuevo Modelo OpenRouter", "ID del modelo (ej: openai/gpt-4o):")
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
            self._gen_status.setText("Escribe tu puesto o descripción primero.")
            self._gen_status.setStyleSheet("font-size: 11px; color: #EF9F27;")
            return
        self._gen_btn.setEnabled(False)
        self._gen_btn.setText("generando…")
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
        self._gen_btn.setText("✨ Generar")
        self._gen_status.setText("✓ perfil generado — revisá y guardá los ajustes")
        self._gen_status.setStyleSheet("font-size: 11px; color: #639922;")
        QTimer.singleShot(4000, lambda: self._gen_status.setText(""))

    def _on_profile_error(self, msg: str):
        self._gen_btn.setEnabled(True)
        self._gen_btn.setText("✨ Generar")
        self._gen_status.setText(f"Error: {msg}")
        self._gen_status.setStyleSheet("font-size: 11px; color: #E24B4A;")
