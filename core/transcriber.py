"""
transcriber.py
Transcribe audio WAV usando faster-whisper (CUDA) con fallback a API.
"""
import io
import time
import httpx
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool
import config
import session_log


class TranscribeTask(QRunnable):
    def __init__(self, wav_bytes: bytes, signals, lang: str = "es"):
        super().__init__()
        self.wav_bytes = wav_bytes
        self.signals   = signals
        self.lang      = lang

    def run(self):
        cfg  = config.load()
        mode = cfg.get("whisper_mode", "local")
        t0   = time.monotonic()

        try:
            if mode == "local":
                text, device = self._local(cfg)
            else:
                text   = self._api(cfg)
                device = "api"
            dur = time.monotonic() - t0
            model_id = cfg.get("whisper_model") if mode == "local" else cfg.get("whisper_api_model", "whisper-large-v3")
            session_log.transcription(device, model_id, dur, text)
            self.signals.done.emit(text)
        except Exception as e:
            session_log.error("transcriber", str(e))
            if mode == "local":
                try:
                    text   = self._api(cfg)
                    dur    = time.monotonic() - t0
                    model_id = cfg.get("whisper_api_model", "whisper-large-v3")
                    session_log.transcription("api-fallback", model_id, dur, text)
                    self.signals.done.emit(text)
                    return
                except Exception as e2:
                    session_log.error("api-fallback", str(e2))
            self.signals.error.emit(str(e))

    def _local(self, cfg: dict) -> tuple:
        """Devuelve (text, device_name)."""
        from faster_whisper import WhisperModel
        model_size   = cfg.get("whisper_model", "medium")
        device_pref  = cfg.get("whisper_device", "auto")
        audio_array  = self._wav_to_float32()

        try:
            import ctranslate2
            cuda_ok = ctranslate2.get_cuda_device_count() > 0
        except ImportError:
            cuda_ok = False

        use_cuda = (device_pref == "cuda") or (device_pref == "auto" and cuda_ok)

        profile = cfg.get("user_profile", {})
        initial_prompt = profile.get("custom_terms", "").strip() or None

        if use_cuda:
            try:
                model = WhisperModel(model_size, device="cuda", compute_type="float16")
                segments, _ = model.transcribe(audio_array, language=self.lang, beam_size=5, initial_prompt=initial_prompt)
                return " ".join(s.text.strip() for s in segments), "cuda"
            except Exception as e:
                if device_pref == "cuda":
                    raise RuntimeError(f"CUDA no disponible: {e}") from e
                # auto → caer a CPU

        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio_array, language=self.lang, beam_size=5, initial_prompt=initial_prompt)
        return " ".join(s.text.strip() for s in segments), "cpu"

    def _api(self, cfg: dict) -> str:
        """Groq Whisper (free tier) o cualquier endpoint OpenAI-compatible."""
        api_url = cfg.get("whisper_api_url", "")
        api_key = cfg.get("whisper_api_key", "")
        model   = cfg.get("whisper_api_model", "whisper-large-v3")

        if not api_url or not api_key:
            raise ValueError("Whisper API no configurada. Ve a Ajustes.")

        with httpx.Client(timeout=30) as client:
            resp = client.post(
                api_url,
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": ("audio.wav", self.wav_bytes, "audio/wav")},
                data={"model": model, "language": self.lang},
            )
        resp.raise_for_status()
        return resp.json().get("text", "")

    def _wav_to_float32(self):
        import wave, numpy as np
        buf = io.BytesIO(self.wav_bytes)
        with wave.open(buf, "rb") as wf:
            raw = wf.readframes(wf.getnframes())
        arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        return arr


class TranscribeSignals(QObject):
    done  = pyqtSignal(str)
    error = pyqtSignal(str)


class Transcriber(QObject):
    done  = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pool = QThreadPool.globalInstance()
        self._sigs = None  # Evita que se elimine por recolección de basura

    def transcribe(self, wav_bytes: bytes):
        cfg  = config.load()
        lang = cfg.get("language", "es")
        self._sigs = TranscribeSignals()
        self._sigs.done.connect(self.done)
        self._sigs.error.connect(self.error)
        task = TranscribeTask(wav_bytes, self._sigs, lang)
        task.setAutoDelete(True)
        self._pool.start(task)
