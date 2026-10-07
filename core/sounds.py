"""
sounds.py
Pitidos de feedback. winsound.Beep bloquea el hilo que lo llama, así que se
reproduce en un hilo aparte para no congelar la GUI. En plataformas sin
winsound simplemente no suena.
"""
import threading

import config

try:
    import winsound
except ImportError:   # Linux / macOS
    winsound = None

# (frecuencia Hz, duración ms)
START  = (600, 100)
DONE   = (1200, 150)
ERROR  = (300, 300)
CANCEL = (400, 120)


def play(tone: tuple[int, int]):
    if winsound is None:
        return
    if not config.load().get("play_sounds", True):
        return
    freq, ms = tone
    threading.Thread(target=winsound.Beep, args=(freq, ms), daemon=True).start()
