# Ren'Py OpenAI TTS Implementation Plan

## T-001: Pure speech client, chunking, WAV merge, and cache
Traces to REQ-002, REQ-003, REQ-004 / AC-004–006, AC-009–010, AC-012.

- RED: Add one focused `unittest` for one behavior and run the exact test to observe the expected failure.
- GREEN: Implement the smallest Python 2/3-compatible core behavior.
- REFACTOR: Remove duplication only while focused and regression suites remain green.
- Checkpoints: request payload/header; API error redaction; text chunks; WAV validation/merge; cache identity; atomic replacement.
- Files: `tests/test_core.py`, `game/openai_tts_mod/core.py`.

## T-002: Asynchronous Ren'Py adapter and bootstrap
Traces to REQ-001, REQ-003, REQ-004 / AC-001–003, AC-007–008, AC-010–011.

- RED: Test with fake Ren'Py/config/music objects and deterministic worker hooks.
- GREEN: Implement latest-request-wins dispatch, main-thread playback/fallback, clipboard/debug delegation, and late callback installation.
- REFACTOR: Separate framework adapter from worker/controller while green.
- Checkpoints: no caller-thread render; stale success ignored; stale failure ignored; channel stopped; fallback main-thread invocation; static `.rpy` contract.
- Files: `tests/test_adapter.py`, `game/openai_tts_mod/adapter.py`, `game/openai_tts_mod/__init__.py`, `game/openai_tts.rpy`.

## T-003: Safe per-game installer and release builder
Traces to REQ-005 / AC-013–016.

- RED: Test path validation, dry-run manifest, copy behavior, existing config preservation, and package secret exclusion.
- GREEN: Add standard-library installer and deterministic ZIP builder.
- REFACTOR: Share manifest/path checks.
- Files: `tests/test_installer.py`, `install.py`, `tools/build_release.py`, example config, README.

## T-004: Compatibility, security, and delivery gates
Traces to REQ-006 / AC-017–018 and all requirements.

- Add a runtime compatibility scanner and its regression test.
- Run full tests and scanner after the final edit.
- Build ZIP twice and compare hashes for deterministic output.
- Inspect archive manifest and scan staged added lines/archive text for credentials, absolute private paths, dangerous URL overrides, and proprietary fixtures.
- Stage explicit files, record exact staged diff hash, dispatch independent read-only review, reconcile findings, rerun gates, and commit coherent local snapshots.
- No paid API call, actual game installation, remote, push, or publication without Ryan's explicit approval.
