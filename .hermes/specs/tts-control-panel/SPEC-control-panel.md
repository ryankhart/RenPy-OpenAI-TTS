# Spec: Per-game TTS Control Panel

Module: `control-panel`

## Objective

Provide a separate Windows GUI installed in each Ren'Py game root so players can change that game's OpenAI TTS voice, speed, and instructions without locating or editing JSON manually.

## Requirements and Acceptance Criteria

### REQ-PANEL-001: Locate one game's configuration
- AC-PANEL-001: Given a panel installed beside the game executable, when launched without arguments, then it targets `<panel-dir>\game\openai_tts_config.json`.
- AC-PANEL-002: Given `--game-dir` pointing to a game root or inner `game` directory, when launched, then it resolves the same config safely.
- AC-PANEL-003: Given a missing, linked, malformed, or non-object config, when loaded or saved, then the panel reports an error and does not overwrite it.

### REQ-PANEL-002: Edit supported settings safely
- AC-PANEL-004: Given a valid config, when it is loaded, then the GUI exposes the current built-in voice, speed, and instructions.
- AC-PANEL-005: Given a supported built-in voice, speed from `0.25` through `4.0`, and string instructions, when Save is used, then only those fields change while the API key and unknown fields are preserved.
- AC-PANEL-006: Given an invalid voice, speed, or instructions value, when Save is attempted, then no file changes.
- AC-PANEL-007: Given a successful save, when the file is read back, then it is valid JSON and valid runtime configuration.

### REQ-PANEL-003: Produce a verifiable executable
- AC-PANEL-008: Given the frozen panel, when `--self-test --report <path>` runs, then it exits zero and reports a complete built-in voice list and valid default speed without opening a window.
- AC-PANEL-009: Given a temporary installed-game fixture, when `--config-test <path> --report <path>` runs, then it performs an atomic real save, preserves the synthetic key and unknown fields, and reports success without opening a window.

## Non-Goals

- Live reloading inside a running Ren'Py process.
- Managing multiple games from one panel instance.
- Storing keys outside each game's config.
- Paid voice previews in the first release.
- Clearing audio caches in the first release.

## Tech Stack

Python 3.11, Tkinter/ttk, standard-library JSON and atomic file replacement, PyInstaller one-file/windowed executable.

## Commands

- Focused tests: `python -m unittest tests.test_control_panel -v`
- Build: `python tools/build_control_panel.py`
- Frozen self-test: `dist/"OpenAI TTS Control Panel.exe" --self-test --report <path>`

## Project Structure

- `control_panel.py`: controller, persistence, CLI, and Tkinter GUI.
- `tools/build_control_panel.py`: deterministic PyInstaller invocation.
- `tests/test_control_panel.py`: controller and packaging contracts.

## Code Style

Follow existing installer style: four-space indentation, explicit imports, controller functions outside Tk widgets, and dependency injection at process boundaries.

## Testing Strategy

Strict RED → GREEN controller tests use temporary real files. GUI tests inspect exposed actions and CLI modes without requiring an interactive desktop. Frozen headless modes exercise the built executable.

## Boundaries

- Always: preserve keys and unknown settings; atomically replace validated JSON; avoid secret-bearing report fields.
- Ask first: paid API calls or installation into a real game.
- Never: print, centralize, or package a configured API key.

## Traceability

| Acceptance criterion | Test evidence |
|---|---|
| AC-PANEL-001–003 | config-path and malformed-config tests |
| AC-PANEL-004–007 | load/save preservation and rejection tests |
| AC-PANEL-008–009 | source and frozen headless-mode tests |

## Success Criteria

The source tests and frozen executable tests pass, a fixture config is updated atomically, and secret/unknown fields remain unchanged.
