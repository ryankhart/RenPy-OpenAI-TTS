# Spec: Native TTS Speed

Module: `runtime-speed`

## Objective

Let installed Ren'Py games request OpenAI speech at a configurable native speed while preserving existing behavior, Python 2.7 compatibility, and deterministic cache isolation.

## Requirements and Acceptance Criteria

### REQ-SPEED-001: Validate speed configuration
- AC-SPEED-001: Given no configured speed, when settings load, then speed defaults to `1.0`.
- AC-SPEED-002: Given a finite numeric speed from `0.25` through `4.0`, when settings load, then it is accepted.
- AC-SPEED-003: Given a boolean, non-number, non-finite number, or value outside `0.25` through `4.0`, when settings load, then a redacted `ConfigurationError` is raised.

### REQ-SPEED-002: Apply speed safely
- AC-SPEED-004: Given a valid speed, when speech is synthesized, then the JSON request includes that speed.
- AC-SPEED-005: Given identical text and other voice settings at different speeds, when speech is rendered, then separate cache entries are used.

## Non-Goals

- Post-processing audio with FFmpeg.
- Changing speed while an already generated utterance is playing.
- Character-specific speed selection.

## Tech Stack

Python 2.7/3.x-compatible standard library runtime and OpenAI `POST /v1/audio/speech`.

## Commands

- Focused tests: `python -m unittest tests.test_core -v`
- Full tests: `python -m unittest discover -s tests -v`
- Compatibility: `python tools/check_runtime_compat.py`

## Project Structure

- `game/openai_tts_mod/core.py`: settings, API payload, cache identity.
- `game/openai_tts_mod/__init__.py`: client construction.
- `game/openai_tts_config.json.example`: documented default.
- `tests/test_core.py`: behavioral evidence.

## Code Style

Keep runtime code compatible with Python 2.7: no annotations, f-strings, pathlib, dataclasses, or Python-3-only imports.

## Testing Strategy

Strict RED → GREEN tests cover default, valid boundaries, malformed values, request payload, and cache separation.

## Boundaries

- Always: include every voice-affecting field in the cache identity; redact configuration failures.
- Ask first: paid live synthesis.
- Never: weaken TLS or log an API key.

## Traceability

| Acceptance criterion | Test evidence |
|---|---|
| AC-SPEED-001–003 | `tests.test_core` settings tests |
| AC-SPEED-004 | `test_synthesize_posts_authenticated_wav_request` |
| AC-SPEED-005 | speed cache-isolation test |

## Success Criteria

Focused and full tests pass, compatibility check passes, and the mocked request contains native speed without requiring an external audio tool.
