import json
from datetime import datetime
from pathlib import Path

HISTORY_PATH = Path.home() / ".dictum" / "history.json"
MAX_ENTRIES = 200


def save(text: str):
    entries = load()
    entries.insert(0, {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "text": text,
    })
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(entries[:MAX_ENTRIES], f, ensure_ascii=False, indent=2)


def load() -> list:
    if HISTORY_PATH.exists():
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            pass
    return []


def clear():
    if HISTORY_PATH.exists():
        HISTORY_PATH.unlink()
