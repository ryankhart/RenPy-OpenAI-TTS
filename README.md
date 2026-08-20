# Ren'Py OpenAI TTS

Local, unpublished work in progress: a dependency-free mod that routes Ren'Py's built-in self-voicing text to OpenAI speech while preserving Ren'Py's normal `V` toggle and accessibility navigation.

## Current status

Specification and implementation plan are complete. Runtime code and release artifacts are not yet implemented.

## Safety and compatibility goals

- No API key in source control or release ZIPs.
- No proprietary game files.
- No main-thread network request.
- Cached speech to reduce repeated API charges.
- Original Ren'Py TTS fallback on configuration or API failure.
- Desktop Ren'Py 7.x/8.x first, with Python 2.7-compatible runtime syntax.

See `.hermes/specs/renpy-openai-tts/SPEC.md` for acceptance criteria.
