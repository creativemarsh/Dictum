"""
audio_capture.py
Captura audio mientras el hotkey esté presionado.
Emite señales Qt para integración con la GUI.
"""
import io
import wave
import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QObject, pyqtSignal, QThread
import keyboard
import threading
import time


SAMPLE_RATE = 16000   # Whisper espera 16kHz
CHANNELS    = 1
DTYPE       = "int16"


class AudioRecorder(QObject):
    """
    Graba audio entre press y release del hotkey.
    Señales:
        started()           — empezó a grabar
        finished(bytes)     — WAV completo en memoria
        level(float)        — nivel RMS 0-1 para waveform (cada ~50ms)
    """
    started  = pyqtSignal()
    finished = pyqtSignal(bytes)
    level    = pyqtSignal(float)
    error    = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._recording = False
        self._frames: list[np.ndarray] = []

    # ── pública ────────────────────────────────────────────────────────────

    def is_recording(self) -> bool:
        return self._recording

    def start_recording(self):
        if self._recording:
            return
        self._frames = []
        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                blocksize=int(SAMPLE_RATE * 0.05),   # bloques de 50ms
                callback=self._callback,
            )
            self._stream.start()
            self._recording = True
            self.started.emit()
        except Exception as e:
            self._recording = False
            self.error.emit(f"Error de micrófono: {e}")

    def stop_recording(self):
        if not self._recording:
            return
        self._recording = False
        try:
            if hasattr(self, "_stream") and self._stream:
                self._stream.stop()
                self._stream.close()
        except Exception as e:
            import sys
            print(f"[AudioRecorder] Error al detener stream: {e}", file=sys.stderr)

        if not self._frames:
            self.error.emit("No se capturó audio.")
            return

        wav_bytes = self._frames_to_wav()
        self.finished.emit(wav_bytes)

    # ── privada ────────────────────────────────────────────────────────────

    def _callback(self, indata: np.ndarray, frames, time, status):
        if not self._recording:
            return
        chunk = indata.copy()
        self._frames.append(chunk)
        # nivel RMS normalizado para la waveform
        rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2))) / 32768.0
        self.level.emit(min(rms * 8, 1.0))   # amplificado para que se vea bonito

    def _frames_to_wav(self) -> bytes:
        audio = np.concatenate(self._frames, axis=0)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)          # int16 = 2 bytes
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio.tobytes())
        return buf.getvalue()


class HotkeyListener(QObject):
    """
    Escucha el hotkey global en un hilo separado.
    Señales:
        pressed()
        released()
    """
    pressed  = pyqtSignal()
    released = pyqtSignal()

    def __init__(self, hotkey: str = "alt", parent=None):
        super().__init__(parent)
        self.hotkey = hotkey
        self._active = False

    def reset_state(self):
        self._active = False

    def start(self):
        try:
            self._press_hook = keyboard.on_press(self._on_key_press, suppress=False)
            # Eliminamos keyboard.on_release por ser inestable en Windows al soltar modificadores
        except Exception as e:
            import sys
            print(f"[HotkeyListener] No se pudo registrar hotkey '{self.hotkey}': {e}", file=sys.stderr)
            self._press_hook = None

    def stop(self):
        keyboard.unhook_all()
        self._active = False

    def _matches(self, event) -> bool:
        if not event or not getattr(event, 'name', None):
            return False
            
        event_name = event.name.lower()
        
        # La librería keyboard emite nombres genéricos para las teclas izquierdas.
        # Normalizamos a explícitamente 'left' para poder distinguirlas.
        if event_name == 'ctrl': event_name = 'left ctrl'
        elif event_name == 'shift': event_name = 'left shift'
        elif event_name == 'alt': event_name = 'left alt'
        elif event_name == 'windows': event_name = 'left windows'
        
        hotkey = self.hotkey.lower()
        
        if event_name == hotkey:
            return True
            
        # Soporte por si el usuario escribe manualmente "ctrl" genérico en el config.json
        if hotkey in ('alt', 'ctrl', 'shift', 'windows'):
            if event_name in (f'left {hotkey}', f'right {hotkey}'):
                return True
                
        return False

    def _on_key_press(self, event):
        if self._matches(event) and not self._active:
            self._active = True
            self.pressed.emit()
            # Iniciamos un hilo que monitorea activamente cuándo se suelta la tecla
            self._monitor_thread = threading.Thread(target=self._monitor_release, daemon=True)
            self._monitor_thread.start()

    def _monitor_release(self):
        import keyboard
        import time
        
        # Generar lista de posibles nombres equivalentes para polling
        keys_to_check = [self.hotkey]
        if self.hotkey == 'left alt': keys_to_check.extend(['alt', 'menu'])
        elif self.hotkey == 'right alt': keys_to_check.extend(['alt gr', 'right alt', 'menu'])
        elif self.hotkey == 'left ctrl': keys_to_check.extend(['ctrl'])
        elif self.hotkey == 'left shift': keys_to_check.extend(['shift'])
        elif self.hotkey == 'left windows': keys_to_check.extend(['windows'])
        
        while True:
            time.sleep(0.05)
            try:
                is_pressed = False
                for k in keys_to_check:
                    try:
                        if keyboard.is_pressed(k):
                            is_pressed = True
                            break
                    except ValueError:
                        pass
                        
                if not is_pressed:
                    self._active = False
                    self.released.emit()
                    break
            except Exception:
                self._active = False
                self.released.emit()
                break
