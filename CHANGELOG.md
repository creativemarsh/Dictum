# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### UI redesign
- New colour system (`gui/theme.py`): layered neutral surfaces, a single
  accent colour, and red/amber/green only for states. No colour is
  hard-coded outside the theme any more
- Accent colour picker in Settings (Indigo, Blue, Teal, Rose, Graphite).
  Text on the accent is adjusted to meet WCAG AA contrast, checked by a test
- Changing the accent or the interface language offers to restart Dictum
  instead of asking you to restart it by hand
- Native dark title bar instead of the fake one, which doubled the
  Windows title bar. Closing the window keeps Dictum running in the tray
- Big animated microphone button on the Transcription tab: pulses with your
  voice while recording, spins while processing, shows a check when done.
  Click it to start or stop a dictation
- Contextual instruction under the button ("Hold Alt and speak", "Release
  Alt to finish"…); errors and AI warnings in their own banner; the result
  can be edited before copying
- Pill-style tab navigation, toggle switches in Settings, aligned settings
  labels, a save bar that is always visible, compact icon buttons
- Statistics: highlighted "time saved" card and coloured metric cards
- History: friendly timestamps ("Today 10:02") and compact cards
- Drawn app and tray icon
- Settings fit the minimum window width (combos used to push content off-screen)

### Also
- A second launch brings the running window forward instead of starting
  another instance (which registered the hotkey twice)
- Auto-paste is skipped when Dictum itself is the active window
- Background settings threads are awaited on quit

### Added
- Floating overlay during dictation showing recording / processing / done / error,
  with a live level meter and timer. Always on top, never steals focus, hides
  itself when done. Can be turned off in Settings (#3)
- Press **Esc** anywhere to cancel an active dictation (recording or processing).
  Can be turned off in Settings (#4)
- "copied ✓" confirmation on copy buttons, in the Transcription and History tabs (#5)
- Confirmation dialog before clearing the history
- "No speech detected" feedback when Whisper returns an empty transcription
- Automated tests for the dictation flow (`tests/`), run in CI on every PR

### Changed
- The Whisper model is loaded once and reused between dictations instead of
  being reloaded every time (much faster transcriptions after the first one)
- Accidental taps of the hotkey (< 0.35 s) are ignored instead of being sent
  to Whisper or reported as "no audio captured"
- Cancelling is immediate: results that arrive after a cancel are discarded
- Feedback sounds no longer freeze the UI, and no longer crash on non-Windows systems
- Tray icon is now a round dot
- Settings tab is fully translated (it had many hard-coded Spanish strings)
- Statistics: recording time shows seconds under a minute, dictation speed is
  computed from seconds, "time saved" subtracts the time spent dictating, and
  "last transcription" is actually filled in

### Fixed
- The active AI profile (role and custom terms) was never sent to Whisper or
  the LLM: both read a `user_profile` key that the profile migration removes
- Old single-profile configs were never migrated to the multi-profile format
- Labels inside cards and settings sections were drawn with their own border box
- "AI corrections" stat was incremented even when the AI step failed
- Statistics were refreshed before the new words were counted
- An empty reply from the LLM was copied as an empty result; it now falls
  back to the raw transcription
- Clicking "Refresh models" twice while Ollama was slow could crash the app
  (its background thread was destroyed while still running)

## [0.1.0] - 2026-06-24
- Initial public release
