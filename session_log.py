"""
session_log.py
Log por sesión y fecha en ~/.dictum/logs/YYYY-MM-DD.log
"""
from datetime import datetime
from pathlib import Path

LOG_DIR = Path.home() / ".dictum" / "logs"


def _log_file() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"


def _w(line: str):
    with open(_log_file(), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def session_start(cfg: dict):
    now = datetime.now()
    mode = cfg.get("whisper_mode", "?")
    _w("")
    _w("=" * 58)
    _w(f"SESIÓN  {now.strftime('%Y-%m-%d  %H:%M:%S')}")
    _w(f"  whisper_mode  : {mode}")
    _w(f"  whisper_model : {cfg.get('whisper_model', '?')}")
    _w(f"  idioma        : {cfg.get('language', '?')}")
    _w(f"  llm_provider  : {cfg.get('llm_provider', '?')}")
    if mode == "local":
        _w(f"  ollama_model  : {cfg.get('ollama_model', '?')}")
    elif mode == "api":
        _w(f"  api_url       : {cfg.get('whisper_api_url', '?')}")
        _w(f"  api_model     : {cfg.get('whisper_api_model', 'whisper-large-v3')}")
    _w("=" * 58)


def transcription(device: str, model: str, dur_s: float, text: str):
    ts = datetime.now().strftime("%H:%M:%S")
    snippet = text[:120].replace("\n", " ") + ("…" if len(text) > 120 else "")
    _w(f"[{ts}] OK   device={device}  model={model}  {dur_s:.1f}s")
    _w(f"         → {snippet}")


def error(context: str, msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    _w(f"[{ts}] ERR  [{context}] {msg}")
