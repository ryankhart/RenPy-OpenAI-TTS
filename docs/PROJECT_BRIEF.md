# Project brief

## Problem

Ren'Py's built-in self-voicing preserves accessibility semantics but usually uses an operating-system voice. The desired mod keeps that extraction/navigation behavior and replaces only the speech backend with a higher-quality OpenAI voice.

## Known integration point

Current Ren'Py source queues accessible text and calls `config.tts_function(text)`. The stock `V` key toggles self-voicing. The mod can therefore avoid game-specific dialogue parsing and keymap replacement.

## Deliverables

1. Copy-in Ren'Py runtime.
2. Safe local configuration and installer.
3. Mocked end-to-end automated tests.
4. Deterministic release ZIP.
5. Documentation for per-game install, cost, disclosure, fallback, and removal.

## Required user input for final live verification

- An actual game directory and approval to install into it.
- A locally configured OpenAI API key (not sent through chat).
- Approval for one paid synthesis request.
- Preferred voice after listening.
