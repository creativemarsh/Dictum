# Contributing to Dictum

Thanks for your interest in contributing. Every bug report, idea, and pull request helps.

---

## Getting started

### 1. Fork and clone

Fork the repository on GitHub, then clone your fork locally:

```bash
git clone https://github.com/YOUR_USERNAME/Dictum.git
cd Dictum
```

### 2. Set up the environment

Run `setup.bat` — it creates the virtual environment and installs all dependencies including PyTorch with CUDA support automatically.

### 3. Run in development mode

Use `dev.bat`. It starts Dictum with auto-restart — any change you save to a `.py` file will reload the app instantly.

### 4. Create a branch

Use a descriptive name:

```bash
git checkout -b feature/profile-import
# or
git checkout -b bugfix/audio-capture-crash
```

---

## Code rules

- **Keep the separation:** logic lives in `core/`, UI lives in `gui/`. Don't mix them.
- **Keep it lean:** Dictum is fast, silent, and privacy-focused. Don't add heavy dependencies unless strictly necessary.
- **Test before submitting:** Run the app from terminal and verify your changes work end to end.
- **No hardcoded secrets:** API keys and paths go through `~/.dictum/config.json` or environment variables, never in source code.

---

## Submitting changes

1. Commit with a clear message describing what changed and why
2. Push your branch to your fork

```bash
git push origin your-branch-name
```

3. Open a **Pull Request** against the `main` branch of this repository
4. Fill out the PR template that will appear automatically — it's short, just the essentials

---

## Ways to contribute

- 🐛 **Report bugs** — open an Issue using the bug report template
- 💡 **Suggest features** — open an Issue using the feature request template
- 🌍 **Add language support** — help test Whisper accuracy for non-English profiles
- 🖥️ **Cross-platform testing** — Linux and macOS support needs community help
- 🔧 **Refactoring** — the codebase was largely AI-assisted; clean, optimized code is always welcome

Check the [Issues](https://github.com/creativemarsh/Dictum/issues) tab for open tasks. `good first issue` labels are a good starting point.

---

## License

By contributing, you agree your code will be released under GPL v3, the same license as this project.
