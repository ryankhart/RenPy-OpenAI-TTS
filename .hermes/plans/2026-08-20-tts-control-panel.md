# Plan: Per-game TTS Control Panel

Date: 2026-08-20

## Assumptions

- The installed panel belongs to one game and sits beside that game's executable.
- Voice, speed, and instructions apply on the next game launch.
- The installer launch checkbox defaults on, but automated/headless installs never launch the GUI.
- The panel supports current built-in string voices only; custom voice objects remain out of scope.

## Tasks

- [ ] T1: Native speed request and cache isolation
  - Traces to: REQ-SPEED-001/002, AC-SPEED-001–005
  - RED: Add focused settings, payload, and cache tests; run `python -m unittest tests.test_core -v`.
  - GREEN: Add default/validation, client field/payload, cache identity, and constructor plumbing.
  - REFACTOR: Keep one numeric validator and Python 2-compatible syntax.
  - Regression: full suite plus compatibility checker.

- [ ] T2: Safe per-game configuration controller
  - Traces to: REQ-PANEL-001/002, AC-PANEL-001–007
  - RED: Add path resolution, malformed config, atomic save, preservation, and rejection tests.
  - GREEN: Implement `control_panel.py` controller functions.
  - REFACTOR: Separate controller errors and GUI concerns.
  - Regression: `python -m unittest tests.test_control_panel -v`.

- [ ] T3: Control-panel GUI and frozen verification
  - Traces to: REQ-PANEL-003, AC-PANEL-008/009
  - RED: Add CLI contract and build-argument tests.
  - GREEN: Add Tkinter interface, headless modes, and `tools/build_control_panel.py`.
  - REFACTOR: Keep GUI callbacks thin.
  - Regression: source tests, build EXE, frozen self/config tests.

- [ ] T4: Safe outer-root panel installation
  - Traces to: REQ-BUNDLE-001, AC-BUNDLE-001–004
  - RED: Add dry-run/copy/preflight/preservation tests.
  - GREEN: Add game-layout resolver and optional allowlisted panel source/destination.
  - REFACTOR: Preserve `resolve_game_dir` compatibility.
  - Regression: installer tests.

- [ ] T5: GUI launch option and nested packaging
  - Traces to: REQ-BUNDLE-002/003, AC-BUNDLE-005–009
  - RED: Add launch command, bundle report, and PyInstaller argument tests.
  - GREEN: Add checked option, launch helper, nested build order, and reports.
  - REFACTOR: Distinguish install result from launch warning.
  - Regression: full tests and both frozen headless paths.

- [ ] T6: Documentation, final verification, and review
  - Traces to: all requirements
  - Update README and example config.
  - Run full suite, compatibility checker, builds, executable self-tests, fixture install/config test, secret/path scan, and staged-diff review.

## Risks and Mitigations

- Nested PyInstaller executable increases size: retain one outer download and verify both hashes/executables.
- An existing running panel may block replacement: report copy failure honestly and leave config preserved.
- Outer-root writes widen installer scope: resolve and preflight the root separately, reject links/reparse points, and test both root and inner-game selections.
- Secret leakage during panel saves/reports: reports contain booleans/counts only; tests use unmistakably synthetic keys and assert preservation without output.

## Verification Checkpoints

1. Runtime speed focused tests and compatibility pass.
2. Source control-panel tests pass.
3. Installer source tests pass.
4. Panel EXE passes self/config tests.
5. Outer installer EXE passes self-test and installs a fixture containing a working panel.
6. Final full suite and exact-candidate review pass.
