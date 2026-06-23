# Project Scope

This document defines what Dictum is, what it isn't, and where it's headed. It exists so contributors and users know what to expect.

---

## What Dictum is

A local, privacy-first voice transcription tool for desktop. You hold a key, speak, and the text appears where your cursor is. No accounts, no mandatory cloud.

The core use case: replacing manual typing for quick text input — notes, messages, commands — using your voice.

---

## What Dictum is not

- A full dictation suite (not competing with Dragon or similar)
- A speech-to-text API or library
- A cloud service
- A mobile app

---

## Current state

Dictum works but is a personal tool being opened to the community. Expect rough edges. The core flow (record → transcribe → paste) is stable. Configuration, packaging, and cross-platform support are areas that need work.

---

## Planned improvements

- [x] Proper config UI (currently uses `config.json` and PyQt6 tabs)
- [ ] Windows and macOS testing and support
- [ ] Installable package (pip or standalone binary)
- [ ] More Whisper model options exposed in config
- [ ] Better error messages when backends are unavailable

---

## Out of scope (for now)

- Web interface
- Multi-user support
- Real-time streaming transcription
- Speaker diarization

If you want to build any of these, consider forking. If there's enough interest, scope can always expand.
