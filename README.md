# Dictum 🎙️

Dictum is an open source desktop app for **intelligent voice dictation with AI semantic rewriting**.

Speak naturally — with filler words, hesitations, self-corrections — and Dictum will transcribe your voice, clean it up with an LLM, and drop the result straight into your clipboard. No cloud required if you don't want it.

---

## How it works

1. Hold **Alt** (or your configured key) and speak into your mic
2. Release the key
3. Dictum transcribes your audio locally with **faster-whisper**
4. An LLM rewrites the raw transcription — removing fillers, fixing grammar, applying your custom technical vocabulary
5. The clean text lands in your clipboard, ready to paste anywhere

---

## Features

- 🌐 **Universal push-to-talk** — works globally across any active window
- ⚡ **Local transcription** via faster-whisper with GPU acceleration (CUDA)
- 🤖 **AI rewriting** via Ollama (local/private) or OpenRouter (cloud)
- 👤 **Custom profiles** — tell Dictum your profession and technical terms so the AI doesn't mangle them
- 🔇 **Silent background mode** — runs without a terminal window via `Dictum.bat`
- 📋 **Clipboard integration** — processed text is always one `Ctrl+V` away
- 🔒 **Privacy-first** — fully local setup possible with Ollama + faster-whisper

---

## Requirements

- Python 3.10+
- NVIDIA GPU with CUDA 11.8+ (recommended — CPU works but slower)
- [Ollama](https://ollama.com/) (optional, for local AI rewriting)

---

## Installation

```bash
# Clone the repository
git clone https://github.com/creativemarsh/Dictum.git
cd Dictum
```

**Option A — Automatic (recommended):**

Run `setup.bat`. It will create the virtual environment, activate it, and install dependencies. It will also ask if you want to install PyTorch (a ~2.5GB download) to automatically get the CUDA DLLs required for GPU acceleration.

**Option B — Manual:**

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# Install base dependencies
pip install -r requirements.txt

# Optional: Install PyTorch with CUDA support (If you don't have CUDA Toolkit installed globally)
# This is an easy way to get the CUDA DLLs required by ctranslate2 to use your GPU.
# If you already have CUDA installed, you can skip this.
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

---

## Running

```bash
python main.py
```

Or use the included scripts:

| Script | Description |
|---|---|
| `setup.bat` | First-time setup — creates venv and installs all dependencies |
| `Dictum.bat` | Silent launcher — runs the app without a terminal window |
| `dev.bat` | Development mode — auto-restarts on any `.py` file change |
| `build.bat` | Builds a standalone `.exe` via PyInstaller |

---

## Configuration

On first launch, open the **Settings** tab:

- **Whisper:** Choose Local (GPU) or configure an alternative. For NVIDIA GPUs, `medium` model is the recommended balance of speed and accuracy.
- **AI Rewriting:**
  - **Ollama** — install Ollama, pull a model (`ollama pull mistral`), hit "Refresh Models" in Dictum
  - **OpenRouter** — create an account at [openrouter.ai](https://openrouter.ai), generate an API key, paste it in settings
- **Profiles** — set your profession and technical vocabulary so the AI handles domain-specific terms correctly (e.g. "React", "KQL", "FastAPI")

All settings are saved automatically to `~/.dictum/config.json`.

---

## Architecture

```
Dictum/
├── core/
│   ├── audio_capture.py   # Global hotkey + mic recording (keyboard + sounddevice)
│   ├── transcriber.py     # faster-whisper integration, GPU acceleration
│   └── rewriter.py        # LLM rewriting via Ollama or OpenRouter (httpx)
└── gui/                   # PyQt6 interface, QRunnable/QThreadPool for async processing
```

The app separates logic (`core/`) from the UI (`gui/`) — keep that structure when contributing.

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) to get started.

---

## Built with Dictum?

The best way to improve Dictum is to contribute directly — bug fixes, new features, platform support. Check the [open issues](https://github.com/creativemarsh/Dictum/issues) and the [contributing guide](CONTRIBUTING.md) to get started.

That said, Dictum is intentionally fork-friendly. The architecture is simple and modular enough that you can take it as a base and build something completely different — a profession-specific tool, a different UI, a headless version, whatever makes sense for your use case.

If you build something with Dictum as a base, share it in [Discussions](https://github.com/creativemarsh/Dictum/discussions/7) — we'd love to see where you take it.

---

## License

GPL v3 — see [LICENSE](LICENSE).

You can use, modify, and distribute Dictum freely. If you publish a modified version, it must also be open source under the same license.

---

## Credits

Built by [@creativemarsh](https://github.com/creativemarsh) with AI assistance (Claude and Antigravity) for code generation and structure. The author acted as architect, reviewer, and tester. Community refactoring and improvements are warmly welcome.
