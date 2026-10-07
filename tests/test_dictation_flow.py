"""
Pruebas del flujo de dictado sin micrófono ni teclado reales.

Se sustituyen sounddevice, keyboard y pyperclip por dobles, y Qt corre en
modo offscreen, así que funciona en CI (Linux) y en Windows.

    python -m unittest discover -s tests
"""
import os
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── dobles de módulos de hardware ────────────────────────────────────────────

import numpy as np

_sd = types.ModuleType("sounddevice")


class _FakeStream:
    def __init__(self, **kwargs):
        self._cb = kwargs["callback"]

    def start(self):
        from PyQt6.QtCore import QTimer
        chunk = (np.random.rand(800, 1) * 3000).astype("int16")
        QTimer.singleShot(0, lambda: self._cb(chunk, len(chunk), None, None))

    def stop(self):
        pass

    def close(self):
        pass


_sd.InputStream = _FakeStream
sys.modules["sounddevice"] = _sd

_hooks = []
_kb = types.ModuleType("keyboard")
_kb.on_press = lambda cb, suppress=False: _hooks.append(cb) or cb
_kb.unhook_all = lambda: _hooks.clear()
_kb.is_pressed = lambda key: False
_kb.send = lambda key: None
sys.modules["keyboard"] = _kb

_clipboard = []
_pc = types.ModuleType("pyperclip")
_pc.copy = lambda text: _clipboard.append(text)
sys.modules["pyperclip"] = _pc

# config / historial en un directorio temporal, nunca en el ~ real
_tmp_home = tempfile.mkdtemp(prefix="dictum-test-")
import config  # noqa: E402
import history  # noqa: E402
config.CONFIG_PATH = Path(_tmp_home) / "config.json"
history.HISTORY_PATH = Path(_tmp_home) / "history.json"

from PyQt6.QtCore import QEventLoop, QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

app = QApplication.instance() or QApplication(sys.argv)

import core.transcriber as transcriber_mod  # noqa: E402
from gui.main_window import MainWindow  # noqa: E402
from gui.copy_button import CopyButton  # noqa: E402
from gui.tab_history import HistoryCard  # noqa: E402


_windows = []


def spin(ms: int):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def key(name: str):
    return types.SimpleNamespace(name=name)


class DictationFlowTest(unittest.TestCase):
    def setUp(self):
        if config.CONFIG_PATH.exists():
            config.CONFIG_PATH.unlink()
        history.clear()
        _clipboard.clear()
        self.w = MainWindow()
        self.ov = self.w._overlay
        self.fake_backends(raw="hola mundo")

    def tearDown(self):
        self.w._hotkey.stop()
        self.ov.hide()
        _windows.append(self.w)   # mantener viva: sus hilos de ajustes pueden seguir corriendo

    def fake_backends(self, raw: str):
        tr, rw = self.w._transcriber, self.w._rewriter
        tr.transcribe = lambda wav: QTimer.singleShot(30, lambda: tr.done.emit(raw))
        rw.rewrite = lambda text: QTimer.singleShot(30, lambda: rw.done.emit(text.upper()))

    def record(self, seconds: float = 1.0):
        """Simula pulsar el hotkey, hablar `seconds` y soltarlo."""
        self.w._on_hotkey_pressed()
        spin(30)
        self.w._record_start -= seconds
        self.w._recorder.stop_recording()

    def press(self, name: str):
        for hook in list(_hooks):
            hook(key(name))
        spin(30)

    # ── flujo normal ────────────────────────────────────────────────────────

    def test_full_dictation_updates_overlay_and_clipboard(self):
        self.w._on_hotkey_pressed()
        spin(30)
        self.assertTrue(self.w._busy)
        self.assertEqual(self.ov._state, "recording")
        self.assertTrue(self.ov.isVisible())

        self.w._record_start -= 1
        self.w._recorder.stop_recording()
        spin(5)
        self.assertEqual(self.ov._state, "processing")

        spin(150)
        self.assertEqual(self.ov._state, "done")
        self.assertEqual(_clipboard[-1], "HOLA MUNDO")
        self.assertFalse(self.w._busy)
        self.assertEqual(history.load()[0]["text"], "HOLA MUNDO")
        self.assertEqual(config.load()["stats"]["words_total"], 2)

        spin(2000)
        self.assertFalse(self.ov.isVisible(), "el overlay debe ocultarse solo")

    def test_overlay_can_be_disabled(self):
        cfg = config.load()
        cfg["show_overlay"] = False
        config.save(cfg)
        self.w._on_hotkey_pressed()
        spin(30)
        self.assertTrue(self.w._busy)
        self.assertFalse(self.ov.isVisible())

    # ── Escape para cancelar ────────────────────────────────────────────────

    def test_escape_cancels_recording(self):
        self.w._on_hotkey_pressed()
        spin(30)
        self.press("esc")
        self.assertFalse(self.w._busy)
        self.assertFalse(self.w._recorder.is_recording())
        self.assertEqual(self.ov._state, "cancelled")
        self.assertEqual(self.w._tab_transcribe._state, "idle")

    def test_escape_cancels_processing_and_discards_late_result(self):
        class SlowTask(transcriber_mod.TranscribeTask):
            def run(self):
                time.sleep(0.3)
                self.signals.done.emit("resultado tardío")

        original = transcriber_mod.TranscribeTask
        transcriber_mod.TranscribeTask = SlowTask
        try:
            del self.w._transcriber.transcribe   # usar el método real
            self.record()
            spin(30)
            self.assertEqual(self.ov._state, "processing")
            self.press("esc")
            self.assertFalse(self.w._busy)
            spin(500)
            self.assertEqual(_clipboard, [])
            self.assertEqual(self.w._tab_transcribe._state, "idle")
        finally:
            transcriber_mod.TranscribeTask = original

    def test_escape_when_idle_does_nothing(self):
        self.press("esc")
        self.assertFalse(self.w._busy)
        self.assertFalse(self.ov.isVisible())

    def test_escape_can_be_disabled(self):
        cfg = config.load()
        cfg["esc_cancels"] = False
        config.save(cfg)
        self.w._on_hotkey_pressed()
        spin(30)
        self.press("esc")
        self.assertTrue(self.w._busy)

    # ── casos borde ─────────────────────────────────────────────────────────

    def test_accidental_tap_is_ignored(self):
        self.w._on_hotkey_pressed()
        spin(30)
        self.w._recorder.stop_recording()
        spin(100)
        self.assertFalse(self.w._busy)
        self.assertEqual(_clipboard, [])

    def test_empty_transcription_reports_no_speech(self):
        self.fake_backends(raw="   ")
        self.record()
        spin(150)
        self.assertEqual(self.ov._state, "no_speech")
        self.assertEqual(_clipboard, [])

    def test_ai_failure_falls_back_to_raw_text(self):
        rw = self.w._rewriter
        rw.rewrite = lambda text: QTimer.singleShot(30, lambda: rw.error.emit("Ollama caído"))
        self.record()
        spin(150)
        self.assertEqual(self.ov._state, "done_no_ai")
        self.assertEqual(_clipboard[-1], "hola mundo")
        self.assertEqual(config.load()["stats"]["ai_corrections"], 0)

    # ── botón copiar ────────────────────────────────────────────────────────

    def test_copy_button_shows_feedback_then_reverts(self):
        tab = self.w._tab_transcribe
        tab.set_result("abc")
        tab._btn_copy.click()
        self.assertEqual(_clipboard[-1], "abc")
        self.assertEqual(tab._btn_copy.text(), "copied ✓")
        spin(1700)
        self.assertEqual(tab._btn_copy.text(), "copy")

    def test_history_copy_and_clear_confirmation(self):
        history.save("entrada")
        self.w._tab_history.refresh()
        btn = self.w._tab_history.findChild(HistoryCard).findChild(CopyButton)
        btn.click()
        self.assertEqual(btn.text(), "copied ✓")

        original = QMessageBox.question
        try:
            QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
            self.w._tab_history._clear()
            self.assertTrue(history.load())
            QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
            self.w._tab_history._clear()
            self.assertFalse(history.load())
        finally:
            QMessageBox.question = original


class ConfigTest(unittest.TestCase):
    def setUp(self):
        if config.CONFIG_PATH.exists():
            config.CONFIG_PATH.unlink()

    def test_active_profile_reaches_the_prompt(self):
        from core.rewriter import build_system_prompt
        cfg = config.load()
        cfg["profiles"].append({"id": "ops", "name": "Ops", "role": "DevOps", "custom_terms": "Kubernetes"})
        cfg["active_profile_id"] = "ops"
        prompt = build_system_prompt(cfg)
        self.assertIn("DevOps", prompt)
        self.assertIn("Kubernetes", prompt)

    def test_legacy_profile_is_migrated(self):
        import json
        config.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        config.CONFIG_PATH.write_text(json.dumps(
            {"user_profile": {"role": "Médico", "custom_terms": "ECG"}}), encoding="utf-8")
        cfg = config.load()
        self.assertEqual(config.get_active_profile(cfg)["custom_terms"], "ECG")
        self.assertNotIn("user_profile", json.loads(config.CONFIG_PATH.read_text(encoding="utf-8")))

    def test_defaults_are_not_shared_between_loads(self):
        a = config.load()
        a["stats"]["words_total"] = 99
        self.assertEqual(config.load()["stats"]["words_total"], 0)


def tearDownModule():
    # esperar a los hilos de ajustes (CUDA / Ollama) antes de que Python salga
    for w in _windows:
        for thread, _ in list(w._tab_settings._workers):
            thread.wait(6000)


if __name__ == "__main__":
    unittest.main()
