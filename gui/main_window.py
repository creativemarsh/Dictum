"""
main_window.py
Ventana principal de Dictum con tabs: Transcripción / Estadísticas / Ajustes
"""
import time
import pyperclip
import winsound
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
import history
from gui.tab_transcribe import TranscribeTab
from gui.tab_stats      import StatsTab
from gui.tab_settings   import SettingsTab
from gui.tab_history    import HistoryTab

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
        self._hotkey.start()

    # ── setup ──────────────────────────────────────────────────────────────

    def _setup_core(self):
        self._recorder    = AudioRecorder()
        cfg               = config.load()
        self._hotkey      = HotkeyListener(hotkey=cfg.get("hotkey", "alt"))
        self._transcriber = Transcriber()
        self._rewriter    = Rewriter()
        self._last_raw    = ""
        self._record_start: float = 0.0
        self._busy             = False
        self._cancel_requested = False

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

        self._tabs.addTab(self._tab_transcribe, "transcripción")
        self._tabs.addTab(self._tab_stats,      "estadísticas")
        self._tabs.addTab(self._tab_history,    "historial")
        self._tabs.addTab(self._tab_settings,   "ajustes")

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
        self._tray.setToolTip(f"Dictum — {cfg.get('hotkey', 'alt').title()} para grabar")

        menu = QMenu()
        show_action = QAction("Mostrar", self)
        quit_action = QAction("Salir", self)
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._tray_activated)
        self._tray.show()

    def _update_tray_icon(self, state: str):
        from PyQt6.QtGui import QPixmap, QColor
        pm = QPixmap(16, 16)
        colors = {
            "idle": "#534AB7",
            "recording": "#E24B4A",
            "processing": "#EF9F27"
        }
        pm.fill(QColor(colors.get(state, "#534AB7")))
        self._tray.setIcon(QIcon(pm))

    def _connect_signals(self):
        # hotkey → recorder (guarded by _busy)
        self._hotkey.pressed.connect(self._on_hotkey_pressed)
        self._hotkey.released.connect(self._on_hotkey_released)

        # recorder → UI
        self._recorder.started.connect(self._on_recording_started)
        self._recorder.level.connect(self._tab_transcribe.update_level)
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
        self._cancel_requested = True
        self._tab_transcribe.set_state("cancelling")
        self._recorder.stop_recording()

    def _reset_busy(self):
        self._busy = False
        self._cancel_requested = False
        self._hotkey.reset_state()
        self._update_tray_icon("idle")

    @pyqtSlot(str)
    def _on_recorder_error(self, msg: str):
        self._reset_busy()
        if self._cancel_requested:
            self._tab_transcribe.set_state("idle")
        else:
            self._tab_transcribe.show_error(msg)
            cfg = config.load()
            if cfg.get("play_sounds", True):
                winsound.Beep(300, 300)

    @pyqtSlot(str)
    def _on_transcriber_error(self, msg: str):
        if self._cancel_requested:
            self._reset_busy()
            self._tab_transcribe.set_state("idle")
        else:
            self._reset_busy()
            self._tab_transcribe.show_error(msg)
            cfg = config.load()
            if cfg.get("play_sounds", True):
                winsound.Beep(300, 300)

    @pyqtSlot()
    def _on_recording_started(self):
        self._busy = True
        self._record_start = time.monotonic()
        self._tab_transcribe.set_state("recording")
        self._update_tray_icon("recording")
        cfg = config.load()
        if cfg.get("play_sounds", True):
            winsound.Beep(600, 100)

    @pyqtSlot(bytes)
    def _on_audio_ready(self, wav_bytes: bytes):
        if self._cancel_requested:
            self._reset_busy()
            self._tab_transcribe.set_state("idle")
            return
        elapsed = time.monotonic() - self._record_start
        self._tab_transcribe.set_state("processing")
        self._update_tray_icon("processing")
        self._transcriber.transcribe(wav_bytes)
        config.update_stat("sessions_total", 1)
        config.update_stat("time_recorded_s", int(elapsed))

    @pyqtSlot(str)
    def _on_raw_text(self, raw: str):
        if self._cancel_requested:
            self._reset_busy()
            self._tab_transcribe.set_state("idle")
            return
        self._last_raw = raw
        self._rewriter.rewrite(raw)

    @pyqtSlot(str)
    def _on_rewriter_error(self, msg: str):
        if self._cancel_requested:
            self._reset_busy()
            self._tab_transcribe.set_state("idle")
            return
        self._reset_busy()
        if self._last_raw:
            self._on_result_ready(self._last_raw, ai_failed=True, error_msg=msg)
        else:
            self._tab_transcribe.show_error(msg)
            cfg = config.load()
            if cfg.get("play_sounds", True):
                winsound.Beep(300, 300)

    @pyqtSlot(str)
    def _on_result_ready(self, text: str, ai_failed: bool = False, error_msg: str = ""):
        was_cancelled = self._cancel_requested
        self._reset_busy()
        if was_cancelled:
            self._tab_transcribe.set_state("idle")
            return
        self._tab_transcribe.set_result(text, ai_failed=ai_failed, error_msg=error_msg)
        self._tab_stats.refresh()
        history.save(text)
        self._tab_history.refresh()
        word_count = len(text.split())
        config.update_stat("words_total", word_count)
        config.update_stat("ai_corrections", 1)
        pyperclip.copy(text)

        cfg = config.load()
        if cfg.get("play_sounds", True):
            winsound.Beep(1200, 150)
        
        if cfg.get("auto_paste", False):
            # Aseguramos que la ventana no intercepte el ctrl+v al pegar globalmente
            QTimer.singleShot(50, lambda: keyboard.send("ctrl+v"))

    def closeEvent(self, event):
        self._hotkey.stop()
        QApplication.quit()

    @pyqtSlot()
    def _to_tray(self):
        self.hide()
        cfg = config.load()
        self._tray.showMessage("Dictum", f"Corriendo en el tray — {cfg.get('hotkey', 'alt').title()} para grabar", QSystemTrayIcon.MessageIcon.Information, 2000)

    @pyqtSlot()
    def _on_settings_saved(self):
        # Detener hotkey anterior
        self._hotkey.stop()
        # Cargar nueva config
        cfg = config.load()
        new_hotkey = cfg.get("hotkey", "alt")
        # Iniciar nuevo hotkey
        self._hotkey = HotkeyListener(hotkey=new_hotkey)
        self._hotkey.pressed.connect(self._on_hotkey_pressed)
        self._hotkey.released.connect(self._on_hotkey_released)
        self._hotkey.start()
        # Actualizar tray
        self._tray.setToolTip(f"Dictum — {new_hotkey.title()} para grabar")
        self._tab_transcribe.refresh_hint()
        self._tab_transcribe._load_profiles()

    @pyqtSlot(QSystemTrayIcon.ActivationReason)
    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show()
            self.raise_()
