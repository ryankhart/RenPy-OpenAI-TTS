# Spec: Windows GUI installer

## Objective

Package the existing safe per-game installer as a Windows `.exe` that lets a user select a Ren'Py game folder, preview the exact changes, and install the OpenAI self-voicing mod without using a terminal.

## Requirements and acceptance criteria

### REQ-GUI-001: Select and validate the game
- AC-GUI-001: Given the GUI, when the user browses for a folder, then the selected path appears in an editable field.
- AC-GUI-002: Given a game root or inner `game` folder, when validation runs, then the existing `resolve_game_dir` safety checks remain authoritative.
- AC-GUI-003: Given an unrelated, linked, junction-backed, or conflicting destination, when preview/install runs, then the GUI reports the `InstallError` and does not claim success.

### REQ-GUI-002: Preview before installing
- AC-GUI-004: Given a valid game path, when the user clicks Dry run, then the GUI lists every destination and reports that no files changed.
- AC-GUI-005: Given a valid game path, when the user clicks Install, then the GUI copies the same allowlisted runtime as `install.py` and preserves an existing `openai_tts_config.json`.

### REQ-GUI-003: Produce a verified executable
- AC-GUI-006: Given the frozen executable, when run with `--self-test`, then it verifies every bundled runtime file and writes a machine-readable success report without opening a window.
- AC-GUI-007: Given the built executable, when its self-test runs, then the process exits 0 and the report shows no missing runtime files.
- AC-GUI-008: Given a temporary Ren'Py fixture, when the executable runs `--install-test <path>`, then its bundled installer performs a real copy and exits 0 without opening a window.

## Non-goals

- Automatically finding or modifying every installed Ren'Py game.
- Storing an API key inside the executable.
- Circumventing Steam integrity checks or game script restrictions.
- Replacing the existing CLI installer.

## Tech stack

- Python/Tkinter GUI
- Existing dependency-free `install.py` controller
- PyInstaller one-file, windowed Windows executable
- `unittest` for controller behavior and packaged smoke tests

## Commands

- Focused tests: `python -m unittest tests.test_gui_installer -v`
- Full tests: `python -m unittest discover -s tests -v`
- Build: `python tools/build_gui_installer.py`
- Frozen self-test: `dist/RenPy-OpenAI-TTS-Installer.exe --self-test --report <path>`

## Boundaries

- Always: preserve existing config, use the fixed runtime manifest, show dry-run results, verify the built EXE.
- Ask first: installing into a real game other than an explicitly selected test target.
- Never: embed API keys, silently search/modify all games, bypass destination safety checks, publish or push.

## Traceability

| Criterion | Evidence |
|---|---|
| AC-GUI-001–005 | `tests/test_gui_installer.py` controller/UI contract tests |
| AC-GUI-006–007 | Frozen EXE self-test report |
| AC-GUI-008 | Frozen EXE temporary fixture installation report |

## Success criteria

The EXE launches a functional Tkinter installer, contains the complete runtime and licenses, passes its own headless bundle test, installs successfully into a temporary Ren'Py fixture, and leaves the project test suite green.
