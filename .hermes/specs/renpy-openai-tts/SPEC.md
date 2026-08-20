# Spec: Ren'Py OpenAI Self-Voicing Mod

## Assumptions

1. The first supported target is desktop Ren'Py 7.x and 8.x, including older Python 2-based Ren'Py 7 games such as a supported Ren'Py game.
2. Installation is per game by copying loose files into that game's `game` directory. No proprietary game files are redistributed.
3. The existing `V` key remains owned by Ren'Py. The mod replaces Ren'Py's TTS callback, not the keymap, so built-in self-voicing navigation remains intact.
4. One configurable OpenAI voice is used for all spoken content in version 1. Character-specific casting is a non-goal.
5. Speech requests are billable. A deterministic disk cache and latest-request-wins queue minimize repeated calls, but cannot guarantee zero cost for a request already in flight.
6. No API key is available in the current environment. The implementation and mocked API path can be fully tested, but a live paid OpenAI synthesis requires the user to configure a key locally.

## Objective

Build an installable mod that routes Ren'Py's built-in self-voicing output to OpenAI's higher-quality speech API while preserving the normal `V` toggle, accessibility focus behavior, clipboard/debug modes, and a safe operating-system TTS fallback.

## Requirements and Acceptance Criteria

### REQ-001: Preserve Ren'Py self-voicing behavior
- AC-001: Given an installed supported game, when the player presses `V`, then Ren'Py toggles its existing self-voicing mode without a replacement key binding.
- AC-002: Given self-voicing text, when Ren'Py calls `config.tts_function`, then the mod receives the already-extracted accessible text.
- AC-003: Given clipboard or debug self-voicing mode, when text is emitted, then the original Ren'Py TTS function handles it and no OpenAI request is made.

### REQ-002: Generate high-quality OpenAI speech
- AC-004: Given a valid key and uncached text, when speech is requested, then the client sends an authenticated JSON `POST` to `https://api.openai.com/v1/audio/speech` using configurable model, voice, instructions, and WAV output.
- AC-005: Given text longer than the configured per-request limit, when rendered, then it is split at sensible boundaries and every non-empty chunk is synthesized in order.
- AC-006: Given successful WAV chunks, when rendering finishes, then they are combined into one valid WAV file without changing audio parameters.

### REQ-003: Remain responsive and avoid stale speech
- AC-007: Given rapid focus/text changes, when multiple utterances arrive, then the game thread does not perform network I/O and only the latest completed request is eligible to play.
- AC-008: Given a new utterance, when older mod speech is playing, then the dedicated TTS channel is stopped before the replacement is generated.
- AC-009: Given identical settings and text already cached, when requested again, then no API call is made and cached audio is reused.

### REQ-004: Fail safely
- AC-010: Given no API key, malformed settings, network failure, HTTP error, or invalid audio, when speech is requested, then the key is never logged and the original Ren'Py TTS function is invoked on the main thread.
- AC-011: Given a stale failed request followed by newer text, when the stale failure arrives, then it cannot speak its fallback over the newer request.
- AC-012: Given a partial download or process interruption, when a cache entry is written, then readers never observe it as a completed cache file.

### REQ-005: Install and configure without embedding secrets
- AC-013: Given a game directory, when the installer runs, then it copies only the mod runtime and a non-secret example config into the game's `game` directory.
- AC-014: Given a key in `OPENAI_API_KEY`, when the mod loads, then it uses the environment value without writing it to disk.
- AC-015: Given a local `openai_tts_config.json` containing an API key, when the mod loads, then it can use that key while repository rules exclude the file from Git and packages exclude configured secrets.
- AC-016: Given a missing or invalid game directory, when installation is attempted, then it fails without modifying unrelated paths.

### REQ-006: Broad version compatibility
- AC-017: Given CPython 3.11 tests, when the suite runs, then all core and adapter behaviors pass without third-party runtime dependencies.
- AC-018: Given the shipped runtime source, when checked for Python 2.7-incompatible syntax/features, then it contains no annotations, f-strings, dataclasses, pathlib dependency, or Python-3-only urllib imports.

## Non-Goals

- One installation that automatically modifies every game on the machine.
- Character detection, per-character voices, voice cloning, or game-specific dialogue parsing.
- Android, iOS, or Ren'Py Web support in version 1.
- Circumventing game integrity checks, anti-cheat, DRM, script signing, or a game that deliberately disables loose scripts/self-voicing.
- Bundling an OpenAI key, charging account, OpenAI SDK, or proprietary game content.
- Guaranteed lip-sync or synchronization with existing recorded voice acting.

## Tech Stack

- Ren'Py `.rpy` bootstrap using the existing `config.tts_function` hook.
- Python 2.7/3.x-compatible standard-library runtime (`threading`, `json`, `hashlib`, `wave`, `urllib2`/`urllib.request`).
- OpenAI REST endpoint `POST /v1/audio/speech`, default `gpt-4o-mini-tts`, configurable voice, WAV output.
- Python 3.11 `unittest` for local tests. No runtime package install.

## Commands

- Focused test: `python -m unittest tests.test_core.<TestClass>.<test_method> -v`
- Full test: `python -m unittest discover -s tests -v`
- Syntax/compatibility check: `python tools/check_runtime_compat.py`
- Package: `python tools/build_release.py`
- Installer dry run: `python install.py --game-dir <path> --dry-run`

## Project Structure

- `game/openai_tts.rpy` → late-init Ren'Py bootstrap.
- `game/openai_tts_mod/` → dependency-free runtime package.
- `game/openai_tts_config.json.example` → non-secret settings example.
- `tests/` → unit/integration tests with fake Ren'Py and HTTP boundaries.
- `tools/` → compatibility and deterministic packaging checks.
- `dist/` → generated ZIP release, ignored by Git.
- `.hermes/specs/` and `.hermes/plans/` → durable specification and execution plan.

## Code Style

Python runtime uses four-space indentation, explicit imports, `%`/`.format()` string formatting, and classes/functions that remain importable under Python 2.7. Tests may use modern Python 3 syntax when it improves clarity.

## Testing Strategy

Each behavioral slice follows strict RED → GREEN → REFACTOR. HTTP and Ren'Py are injected boundaries. Tests use a real temporary filesystem, valid synthetic WAV bytes, a recording fake Ren'Py object, and a fake transport. No paid API call is part of the automated suite.

## Boundaries

- Always: keep network work off the Ren'Py main thread; preserve clipboard/debug behavior; cache by text plus all voice-affecting settings; redact credentials; stage explicit paths; run the complete suite before commits.
- Ask first: paid live synthesis; installation into an actual game directory; adding dependencies; publishing or pushing a repository.
- Never: commit or package an API key; edit/redistribute proprietary game archives; suppress accessibility fallback; claim universal compatibility without a game-level smoke test.

## Traceability

| Acceptance criteria | Planned test evidence | Task |
|---|---|---|
| AC-001–003 | Adapter and bootstrap integration tests | T-002 |
| AC-004–006 | Client payload, chunking, WAV merge tests | T-001 |
| AC-007–012 | Worker coalescing, cache, stale result, fallback, atomic write tests | T-001/T-002 |
| AC-013–016 | Installer dry-run/copy/safety/package tests | T-003 |
| AC-017–018 | Full unittest suite and compatibility scanner | T-004 |

## Success Criteria

A deterministic ZIP is produced containing the mod, installer, example configuration, and documentation; all automated tests and compatibility checks pass; no configured API key or machine-specific path is packaged; a mocked end-to-end call proves extracted text → OpenAI request → cache → main-thread Ren'Py playback; and the only remaining unverified boundary is a paid live call inside a real game after the user supplies a key.

## Open Questions

- Which exact a supported Ren'Py game installation/version will receive the first real-game smoke test?
- Which OpenAI voice should be the long-term default after listening tests? Version 1 uses `coral` as a configurable starting point.
