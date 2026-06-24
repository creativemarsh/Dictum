import json
import os
import sys
from pathlib import Path
import config

def get_base_path():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent

class I18n:
    def __init__(self):
        self._locales = {}
        self._lang = "en"
        self.load_translations()

    def load_translations(self):
        cfg = config.load()
        self._lang = cfg.get("ui_language", "en")
        
        locales_dir = get_base_path() / "locales"
        file_path = locales_dir / f"{self._lang}.json"
        
        if not file_path.exists():
            # Fallback to English
            file_path = locales_dir / "en.json"
            
        try:
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    self._locales = json.load(f)
        except Exception as e:
            print(f"Error loading translation file {file_path}: {e}")
            self._locales = {}

    def t(self, key: str, default: str = None) -> str:
        return self._locales.get(key, default or key)

# Singleton
_i18n_instance = I18n()

def t(key: str, default: str = None) -> str:
    return _i18n_instance.t(key, default)
