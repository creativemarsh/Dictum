"""
main_window.py
Ventana principal de Dictum con tabs: Transcripción / Estadísticas / Ajustes
"""
import time
import pyperclip
import keyboard
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QSystemTrayIcon, QMenu,
    QApplication,
)
from PyQt6.QtCore import QTimer, pyqtSlot
from PyQt6.QtGui import QAction

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
from gui                import theme
from core.i18n import t

# Pulsaciones más cortas que esto se consideran accidentales: Whisper tiende a
# "alucinar" texto con fragmentos de audio tan breves.
MIN_RECORDING_S = 0.35




class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dictum")
        self.setMinimumWidth(380)
        self.setMinimumHeight(520)
        self.resize(440, 600)
        self.setStyleSheet(theme.STYLE)
        self.setWindowIcon(theme.app_icon())
        self._tray_hint_shown = False

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

    def _setup_tray(self):
        self._tray = QSystemTrayIcon(self)
        self._update_tray_icon("idle")
        self._update_tray_tooltip()

        menu = QMenu(self)
        show_action = QAction(t("tray_show"), self)
        settings_action = QAction(t("tray_settings"), self)
        quit_action = QAction(t("tray_quit"), self)
        show_action.triggered.connect(self._show_window)
        settings_action.triggered.connect(lambda: self._show_window(tab=self._tab_settings))
        quit_action.triggered.connect(self._quit)
        menu.addAction(show_action)
        menu.addAction(settings_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._tray_activated)
        self._tray.show()

    def _hotkey_name(self) -> str:
        from gui.tab_settings import _key_display_name
        return _key_display_name(config.load().get("hotkey", "alt"))

    def _update_tray_tooltip(self):
        self._tray.setToolTip(f"Dictum — {t('hint_hold').format(key=self._hotkey_name())}")

    def _update_tray_icon(self, state: str):
        self._tray.setIcon(theme.app_icon(state, 32))

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
        self._tab_transcribe.mic_clicked.connect(self._on_mic_clicked)

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
    def _on_mic_clicked(self):
        """El botón grande funciona siempre como interruptor: empezar / terminar."""
        if self._recorder.is_recording():
            self._recorder.stop_recording()
        elif not self._busy:
            self._recorder.start_recording()

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
        # Si Dictum es la ventana activa (se dictó con el botón), Ctrl+V pegaría
        # el texto dentro de la propia app: en ese caso basta con el portapapeles.
        auto_paste = config.load().get("auto_paste", False) and not self.isActiveWindow()
        self._tab_transcribe.set_result(text, ai_failed=ai_failed, error_msg=error_msg, pasted=auto_paste)
        history.save(text)
        self._tab_history.refresh()
        word_count = len(text.split())
        config.update_stat("words_total", word_count)
        if not ai_failed:
            config.update_stat("ai_corrections", 1)
        self._tab_stats.refresh()
        pyperclip.copy(text)

        if ai_failed:
            self._set_state("done_no_ai", error_msg.splitlines()[0] if error_msg else "")
        else:
            self._set_state("pasted" if auto_paste else "done")
        sounds.play(sounds.DONE)

        if auto_paste:
            # Aseguramos que la ventana no intercepte el ctrl+v al pegar globalmente
            QTimer.singleShot(50, lambda: keyboard.send("ctrl+v"))

    def showEvent(self, event):
        super().showEvent(event)
        theme.apply_dark_title_bar(self)

    def closeEvent(self, event):
        # Dictum es una app de bandeja: cerrar la ventana no detiene el dictado.
        # Para salir del todo está "Salir" en el menú del icono.
        if self._tray.isVisible():
            event.ignore()
            self.hide()
            if not self._tray_hint_shown:
                self._tray_hint_shown = True
                self._tray.showMessage(
                    t("tray_hidden_title"),
                    t("tray_hidden_msg").format(key=self._hotkey_name()),
                    QSystemTrayIcon.MessageIcon.Information, 3000)
            return
        self._quit()

    @pyqtSlot()
    def _quit(self):
        self._hotkey.stop()
        self._overlay.close()
        self._tray.hide()
        self._tab_settings.shutdown()
        QApplication.quit()

    def _show_window(self, tab=None):
        if tab is not None:
            self._tabs.setCurrentWidget(tab)
        self.showNormal()
        self.raise_()
        self.activateWindow()

    @pyqtSlot()
    def _on_settings_saved(self):
        # Reiniciar el listener con el nuevo hotkey
        self._hotkey.stop()
        self._start_hotkey()
        self._update_tray_tooltip()
        self._tab_transcribe.refresh_hint()
        self._tab_transcribe._load_profiles()

    @pyqtSlot(QSystemTrayIcon.ActivationReason)
    def _tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self._show_window()
