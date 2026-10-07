"""
main_window.py
Ventana principal de Dictum con tabs: Transcripción / Estadísticas / Ajustes
"""
import time
import pyperclip
import keyboard
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QSystemTrayIcon, QMenu,
    QApplication,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QIcon, QAction

import config
from core.audio_capture import AudioRecorder, HotkeyListener
from core.transcriber   import Transcriber
from core.rewriter      import Rewriter
from core import sounds
import history
from gui.tab_transcribe import TranscribeTab
from gui.tab_stats      import StatsTab
from gui.tab_settings   import SettingsTab
from gui.tab_history    import HistoryTab
from gui.overlay        import DictationOverlay
from core.i18n import t

# Pulsaciones más cortas que esto se consideran accidentales: Whisper tiende a
# "alucinar" texto con fragmentos de audio tan breves.
MIN_RECORDING_S = 0.35

STYLE = """
QMainWindow, QWidget {
    background: #1a1a1f;
    color: #e8e6e3;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}
QTabWidget::pane {
    border: none;
    background: #1a1a1f;
}
QTabBar::tab {
    background: transparent;
    color: #888780;
    padding: 8px 20px;
    border-bottom: 2px solid transparent;
    font-size: 12px;
}
QTabBar::tab:selected {
    color: #e8e6e3;
    border-bottom: 2px solid #534AB7;
    font-weight: 500;
}
QTabBar::tab:hover {
    color: #b4b2a9;
}
QFrame#card QLabel, QFrame#card QCheckBox {
    background: transparent;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #444441;
    border-radius: 4px;
    background: #0d0d12;
}
QCheckBox::indicator:hover {
    border-color: #534AB7;
}
QCheckBox::indicator:checked {
    background: #534AB7;
    border-color: #534AB7;
}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dictum")
        self.setMinimumWidth(380)
        self.setMinimumHeight(480)
        self.setStyleSheet(STYLE)

        self._setup_core()
        self._setup_ui()
        self._setup_tray()
        self._connect_signals()
        self._start_hotkey()

    # ── setup ──────────────────────────────────────────────────────────────

    def _setup_core(self):
        self._recorder    = AudioRecorder()
        cfg               = config.load()
        self._hotkey      = HotkeyListener(hotkey=cfg.get("hotkey", "alt"))
        self._transcriber = Transcriber()
        self._rewriter    = Rewriter()
        self._last_raw    = ""
        self._record_start: float = 0.0
        self._busy        = False
        self._overlay     = DictationOverlay()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # titlebar
        titlebar = self._make_titlebar()
        layout.addWidget(titlebar)

        # tabs
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        layout.addWidget(self._tabs)

        self._tab_transcribe = TranscribeTab()
        self._tab_stats      = StatsTab()
        self._tab_settings   = SettingsTab()
        self._tab_history    = HistoryTab()

        self._tabs.addTab(self._tab_transcribe, t("tab_transcribe"))
        self._tabs.addTab(self._tab_stats,      t("tab_stats"))
        self._tabs.addTab(self._tab_history,    t("tab_history"))
        self._tabs.addTab(self._tab_settings,   t("tab_settings"))

    def _make_titlebar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(38)
        bar.setStyleSheet("background: #111116; border-bottom: 1px solid #2c2c2a;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 0, 14, 0)

        dots = QHBoxLayout()
        dots.setSpacing(6)
        for color in ["#E24B4A", "#EF9F27", "#639922"]:
            d = QLabel()
            d.setFixedSize(11, 11)
            d.setStyleSheet(f"background:{color}; border-radius:5px;")
            dots.addWidget(d)
        layout.addLayout(dots)

        title = QLabel("Dictum")
        title.setStyleSheet("color: #888780; font-size: 13px; font-weight: 500; margin-left: 8px;")
        layout.addWidget(title)
        layout.addStretch()

        btn_style = """
            QPushButton { background: transparent; border: none; color: #888780; font-size: 16px; }
            QPushButton:hover { color: #e8e6e3; }
        """
        btn_close_style = """
            QPushButton { background: transparent; border: none; color: #888780; font-size: 16px; }
            QPushButton:hover { color: #E24B4A; }
        """
        
        minimize_btn = QPushButton("−")
        minimize_btn.setFixedSize(28, 24)
        minimize_btn.setStyleSheet(btn_style)
        minimize_btn.clicked.connect(self.showMinimized)
        layout.addWidget(minimize_btn)
        
        maximize_btn = QPushButton("□")
        maximize_btn.setFixedSize(28, 24)
        maximize_btn.setStyleSheet(btn_style)
        maximize_btn.clicked.connect(lambda: self.showNormal() if self.isMaximized() else self.showMaximized())
        layout.addWidget(maximize_btn)
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 24)
        close_btn.setStyleSheet(btn_close_style)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        return bar

    def _setup_tray(self):
        self._tray = QSystemTrayIcon(self)
        self._update_tray_icon("idle")
        cfg = config.load()
        self._tray.setToolTip(f"Dictum — {cfg.get('hotkey', 'alt').title()} {t('tray_record_hint', 'para grabar')}")

        menu = QMenu()
        show_action = QAction(t("tray_show"), self)
        quit_action = QAction(t("tray_quit"), self)
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._tray_activated)
        self._tray.show()

    def _update_tray_icon(self, state: str):
        from PyQt6.QtGui import QPixmap, QColor, QPainter
        colors = {
            "idle": "#534AB7",
            "recording": "#E24B4A",
            "processing": "#EF9F27"
        }
        pm = QPixmap(32, 32)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(colors.get(state, "#534AB7")))
        p.drawEllipse(2, 2, 28, 28)
        p.end()
        self._tray.setIcon(QIcon(pm))

    def _connect_signals(self):
        # recorder → UI
        self._recorder.started.connect(self._on_recording_started)
        self._recorder.level.connect(self._tab_transcribe.update_level)
        self._recorder.level.connect(self._overlay.update_level)
        self._recorder.finished.connect(self._on_audio_ready)
        self._recorder.error.connect(self._on_recorder_error)

        # transcriber → rewriter → UI
        self._transcriber.done.connect(self._on_raw_text)
        self._transcriber.error.connect(self._on_transcriber_error)
        self._rewriter.done.connect(self._on_result_ready)
        self._rewriter.error.connect(self._on_rewriter_error)

        # cancel button
        self._tab_transcribe.cancel_clicked.connect(self._on_cancel)
        
        # tray button
        self._tab_transcribe.tray_clicked.connect(self._to_tray)

        # settings saved
        self._tab_settings.saved.connect(self._on_settings_saved)

    def _start_hotkey(self):
        cfg = config.load()
        self._hotkey = HotkeyListener(hotkey=cfg.get("hotkey", "alt"))
        self._hotkey.pressed.connect(self._on_hotkey_pressed)
        self._hotkey.released.connect(self._on_hotkey_released)
        self._hotkey.cancel_pressed.connect(self._on_cancel)
        self._hotkey.start()

    # ── estado ─────────────────────────────────────────────────────────────

    def _set_state(self, state: str, detail: str = ""):
        """Propaga el estado del dictado a la pestaña, el tray y el overlay.
        state: 'idle' | 'recording' | 'processing' | 'done' | 'pasted' |
               'done_no_ai' | 'cancelled' | 'no_speech' | 'error'
        """
        tray = state if state in ("recording", "processing") else "idle"
        self._update_tray_icon(tray)

        if state in ("idle", "recording", "processing"):
            self._tab_transcribe.set_state(state)
        elif state in ("cancelled", "no_speech"):
            self._tab_transcribe.set_state("idle")

        cfg = config.load()
        if cfg.get("show_overlay", True):
            self._overlay.esc_hint = cfg.get("esc_cancels", True)
            self._overlay.set_state(state, detail)
        else:
            self._overlay.set_state("idle")

    def _reset_busy(self, reset_hotkey: bool = True):
        self._busy = False
        self._hotkey.set_cancel_armed(False)
        if reset_hotkey:
            self._hotkey.reset_state()

    def _fail(self, msg: str):
        self._reset_busy()
        self._tab_transcribe.show_error(msg)
        self._set_state("error", msg.splitlines()[0] if msg else "")
        sounds.play(sounds.ERROR)

    # ── slots ──────────────────────────────────────────────────────────────

    @pyqtSlot()
    def _on_hotkey_pressed(self):
        cfg  = config.load()
        mode = cfg.get("hotkey_mode", "hold")

        if mode == "toggle":
            if self._recorder.is_recording():
                self._recorder.stop_recording()
            elif not self._busy:
                self._recorder.start_recording()
        else:
            if not self._busy:
                self._recorder.start_recording()

    @pyqtSlot()
    def _on_hotkey_released(self):
        cfg  = config.load()
        mode = cfg.get("hotkey_mode", "hold")
        if mode == "hold":
            self._recorder.stop_recording()

    @pyqtSlot()
    def _on_cancel(self):
        if not self._busy:
            return
        # Se descarta todo lo que esté en vuelo: el audio, y cualquier resultado
        # que llegue después del transcriptor o del LLM.
        was_recording = self._recorder.is_recording()
        self._recorder.cancel_recording()
        self._transcriber.cancel()
        self._rewriter.cancel()
        # Si se cancela mientras se mantiene pulsado el hotkey (modo hold), no
        # se reinicia su estado: la auto-repetición de la tecla volvería a
        # empezar una grabación al instante.
        self._reset_busy(reset_hotkey=not was_recording)
        self._set_state("cancelled")
        sounds.play(sounds.CANCEL)

    @pyqtSlot(str)
    def _on_recorder_error(self, msg: str):
        if self._busy and time.monotonic() - self._record_start < MIN_RECORDING_S:
            # toque accidental tan corto que no llegó ni un bloque de audio
            self._reset_busy()
            self._set_state("idle")
            return
        self._fail(msg)

    @pyqtSlot(str)
    def _on_transcriber_error(self, msg: str):
        self._fail(msg)

    @pyqtSlot()
    def _on_recording_started(self):
        self._busy = True
        self._record_start = time.monotonic()
        self._hotkey.set_cancel_armed(config.load().get("esc_cancels", True))
        self._set_state("recording")
        sounds.play(sounds.START)

    @pyqtSlot(bytes)
    def _on_audio_ready(self, wav_bytes: bytes):
        elapsed = time.monotonic() - self._record_start
        if elapsed < MIN_RECORDING_S:
            self._reset_busy()
            self._set_state("idle")
            return
        self._set_state("processing")
        self._transcriber.transcribe(wav_bytes)
        config.update_stat("sessions_total", 1)
        config.update_stat("time_recorded_s", int(elapsed))

    @pyqtSlot(str)
    def _on_raw_text(self, raw: str):
        if not raw.strip():
            self._reset_busy()
            self._set_state("no_speech")
            return
        self._last_raw = raw
        self._rewriter.rewrite(raw)

    @pyqtSlot(str)
    def _on_rewriter_error(self, msg: str):
        if self._last_raw:
            self._on_result_ready(self._last_raw, ai_failed=True, error_msg=msg)
        else:
            self._fail(msg)

    @pyqtSlot(str)
    def _on_result_ready(self, text: str, ai_failed: bool = False, error_msg: str = ""):
        self._reset_busy()
        self._tab_transcribe.set_result(text, ai_failed=ai_failed, error_msg=error_msg)
        history.save(text)
        self._tab_history.refresh()
        word_count = len(text.split())
        config.update_stat("words_total", word_count)
        if not ai_failed:
            config.update_stat("ai_corrections", 1)
        self._tab_stats.refresh()
        pyperclip.copy(text)

        cfg = config.load()
        auto_paste = cfg.get("auto_paste", False)
        if ai_failed:
            self._set_state("done_no_ai", error_msg.splitlines()[0] if error_msg else "")
        else:
            self._set_state("pasted" if auto_paste else "done")
        sounds.play(sounds.DONE)

        if auto_paste:
            # Aseguramos que la ventana no intercepte el ctrl+v al pegar globalmente
            QTimer.singleShot(50, lambda: keyboard.send("ctrl+v"))

    def closeEvent(self, event):
        self._hotkey.stop()
        self._overlay.close()
        QApplication.quit()

    @pyqtSlot()
    def _to_tray(self):
        self.hide()
        cfg = config.load()
        self._tray.showMessage("Dictum", f"{t('tray_running', 'Corriendo en el tray')} — {cfg.get('hotkey', 'alt').title()} {t('tray_record_hint', 'para grabar')}", QSystemTrayIcon.MessageIcon.Information, 2000)

    @pyqtSlot()
    def _on_settings_saved(self):
        # Reiniciar el listener con el nuevo hotkey
        self._hotkey.stop()
        self._start_hotkey()
        new_hotkey = self._hotkey.hotkey
        # Actualizar tray
        self._tray.setToolTip(f"Dictum — {new_hotkey.title()} {t('tray_record_hint', 'para grabar')}")
        self._tab_transcribe.refresh_hint()
        self._tab_transcribe._load_profiles()

    @pyqtSlot(QSystemTrayIcon.ActivationReason)
    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show()
            self.raise_()
