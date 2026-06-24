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
        try:
            # 1. Cargar inglés como base
            base_path = locales_dir / "en.json"
            if base_path.exists():
                with open(base_path, "r", encoding="utf-8") as f:
                    self._locales = json.load(f)
            
            # 2. Cargar español para rellenar cualquier llave que falte en inglés
            es_path = locales_dir / "es.json"
            if es_path.exists():
                with open(es_path, "r", encoding="utf-8") as f:
                    es_dict = json.load(f)
                    for k, v in es_dict.items():
                        if k not in self._locales:
                            self._locales[k] = v
            
            # 3. Finalmente, sobreescribir todo con el idioma que el usuario eligió
            if self._lang != "en":
                target_path = locales_dir / f"{self._lang}.json"
                if target_path.exists():
                    with open(target_path, "r", encoding="utf-8") as f:
                        target_locales = json.load(f)
                        self._locales.update(target_locales)
        except Exception as e:
            pass # Ignorar para no crashear pythonw.exe

    def t(self, key: str, default: str = None) -> str:
        return self._locales.get(key, default or key)

# Singleton
_i18n_instance = I18n()

def t(key: str, default: str = None) -> str:
    return _i18n_instance.t(key, default)
