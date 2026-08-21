# Spec: Single-installer Control Panel Bundling

Module: `installer-bundling`

## Objective

Keep one downloadable installer while deploying a separately launchable `OpenAI TTS Control Panel.exe` beside each selected game's executable.

## Requirements and Acceptance Criteria

### REQ-BUNDLE-001: Install the embedded panel safely
- AC-BUNDLE-001: Given a valid game root or inner `game` selection, when installation is previewed, then the panel destination in the outer game root is listed and no files change.
- AC-BUNDLE-002: Given a complete bundled source, when installation runs, then the panel is copied beside the game executable and runtime files are copied under the inner `game` directory.
- AC-BUNDLE-003: Given a missing panel source, linked/reparse game root, linked panel destination, or non-file conflict, when installation runs, then preflight fails before any destination changes.
- AC-BUNDLE-004: Given a reinstall, when installation runs, then the panel and runtime are updated while `openai_tts_config.json` is preserved.

### REQ-BUNDLE-002: Offer post-install launch
- AC-BUNDLE-005: Given the installer GUI, when displayed, then `Launch TTS Control Panel after installation` is selected by default.
- AC-BUNDLE-006: Given a successful install with the option selected, when completion handling runs, then the installed panel is launched with the selected game path.
- AC-BUNDLE-007: Given a panel launch failure, when installation has succeeded, then installation remains successful and a separate launch warning is shown.

### REQ-BUNDLE-003: Verify the nested executable
- AC-BUNDLE-008: Given the outer frozen installer, when `--self-test` runs, then it verifies the embedded panel is present in addition to the runtime and license.
- AC-BUNDLE-009: Given the outer frozen installer and temporary fixture, when `--install-test` runs, then the installed panel exists and passes its own headless self-test/config test.

## Non-Goals

- Installing the panel globally or into Program Files.
- Creating Start-menu or desktop shortcuts.
- Downloading a panel executable at runtime.
- Automatically launching anything after a dry run.

## Tech Stack

Existing Tkinter installer, safe allowlisted installer controller, PyInstaller one-file nesting, and subprocess launch after confirmed copy.

## Commands

- Focused tests: `python -m unittest tests.test_installer tests.test_gui_installer -v`
- Build: `python tools/build_gui_installer.py`
- Frozen verification: `dist/RenPy-OpenAI-TTS-Installer.exe --self-test --report <path>` and `--install-test <fixture> --report <path>`

## Project Structure

- `install.py`: root/game layout resolution and allowlisted destinations.
- `gui_installer.py`: launch option and frozen test modes.
- `tools/build_gui_installer.py`: embeds the already built panel EXE.
- `tests/test_installer.py`, `tests/test_gui_installer.py`: safety and bundle evidence.

## Code Style

Match existing controller-first Tkinter design and keep filesystem/process boundaries injectable for tests.

## Testing Strategy

Strict RED → GREEN tests cover destination selection, full preflight, launch command, launch failure, PyInstaller arguments, and frozen end-to-end installation.

## Boundaries

- Always: preflight every destination before copying; preserve existing config; distinguish install success from launch success.
- Ask first: install into a real game, signing, publishing, or pushing.
- Never: download or execute an unverified payload, package configured secrets, or write outside the selected validated game root.

## Traceability

| Acceptance criterion | Test evidence |
|---|---|
| AC-BUNDLE-001–004 | installer controller tests |
| AC-BUNDLE-005–007 | GUI/controller launch tests |
| AC-BUNDLE-008–009 | PyInstaller argument, self-test, and frozen fixture verification |

## Success Criteria

One outer installer EXE contains the panel, installs it into a temporary game root, preserves config, optionally launches it, and both frozen executables pass headless verification.
