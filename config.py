import json
import os
from pathlib import Path

CONFIG_PATH = Path.home() / ".dictum" / "config.json"

DEFAULTS = {
    "hotkey": "alt",
    "hotkey_mode": "hold",            # "hold" | "toggle"
    "auto_paste": False,              # Simular Ctrl+V
    "play_sounds": True,              # Sonidos de feedback
    "whisper_mode": "local",          # "local" | "api"
    "whisper_model": "medium",        # tiny, base, small, medium, large-v2
    "whisper_device": "auto",         # "auto" | "cuda" | "cpu"
    "whisper_api_url": "https://api.openai.com/v1/audio/transcriptions",
    "whisper_api_key": "",
    "llm_provider": "ollama",         # "ollama" | "openrouter"
    "ollama_model": "",               # se llena dinámicamente
    "ollama_base_url": "http://localhost:11434",
    "openrouter_model": "",           # se llena dinámicamente
    "openrouter_api_key": "",
    "openrouter_custom_models": [],   # lista de modelos que el usuario ha introducido
    "ui_language": "en",              # Idioma de la interfaz ("en" o "es")
    "language": "es",
    "stats": {
        "words_total": 0,
        "sessions_total": 0,
        "time_recorded_s": 0,
        "ai_corrections": 0,
    },
    "profiles": [{
        "id": "default",
        "name": "Predeterminado",
        "role": "",
        "custom_terms": "",
    }],
    "active_profile_id": "default",
}

OPENROUTER_FREE_MODELS = [
    {"id": "openrouter/free", "label": "OpenRouter Auto (Recomendado - evita saturación)"},
]

WHISPER_API_FREE = [
    {"id": "groq_whisper", "label": "Groq — Whisper Large v3 (free tier)", "url": "https://api.groq.com/openai/v1/audio/transcriptions", "model": "whisper-large-v3"},
]


def load() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # merge con defaults para claves nuevas
            for k, v in DEFAULTS.items():
                if k not in data:
                    data[k] = v
            # Migración de perfil antiguo a multi-perfil
            if "user_profile" in data and "profiles" not in data:
                old_prof = data.pop("user_profile")
                data["profiles"] = [{
                    "id": "default",
                    "name": "Predeterminado",
                    "role": old_prof.get("role", ""),
                    "custom_terms": old_prof.get("custom_terms", "")
                }]
                data["active_profile_id"] = "default"
                save(data)
            return data
        except (json.JSONDecodeError, ValueError):
            pass  # archivo vacío o corrupto — usar defaults
    return dict(DEFAULTS)


def save(cfg: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def update_stat(key: str, delta):
    cfg = load()
    cfg["stats"][key] = cfg["stats"].get(key, 0) + delta
    save(cfg)
