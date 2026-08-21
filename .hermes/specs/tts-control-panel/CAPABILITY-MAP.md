# Capability Map: Per-game TTS Control Panel

| Module id | Responsibility | Depends on |
|---|---|---|
| runtime-speed | Validate and send native speech speed; isolate cache entries by speed | — |
| control-panel | Edit one installed game's voice, speed, and instructions without exposing its API key | runtime-speed |
| installer-bundling | Embed, safely install, verify, and optionally launch the per-game control panel | control-panel |

Build order: runtime-speed → control-panel → installer-bundling

The control panel is installed beside the game executable. The Ren'Py runtime remains under the inner `game` directory. The single downloadable installer embeds the separately built control-panel executable.
