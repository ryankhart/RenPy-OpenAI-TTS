# Ren'Py OpenAI TTS

This mod sends Ren'Py's built-in self-voicing text to the OpenAI speech API. The normal `V` key still turns self-voicing on and off. Ren'Py continues to extract dialogue, menus, button labels, and accessibility text. The mod only replaces the speech backend.

The runtime uses Python's standard library. It does not require the OpenAI Python package.

## Compatibility

The first release targets desktop games built with Ren'Py 7.x or 8.x. The runtime is written without known Python 3-only constructs, but the automated checker is a limited static syntax guard. This release has not yet been executed inside a Python 2-based Ren'Py 7 game.

This cannot work in every possible Ren'Py build. A game may disable self-voicing, reject loose `.rpy` files, sign its scripts, or replace `config.tts_function` after this mod loads. Android, iOS, and Ren'Py Web are not supported in version 0.1.0.

## Install

1. Extract the release ZIP.
2. Open a terminal in the extracted `RenPy-OpenAI-TTS` folder.
3. Preview the exact changes:

```console
python install.py --game-dir "C:\Path\To\Game" --dry-run
```

4. Install after the dry run points at the correct game:

```console
python install.py --game-dir "C:\Path\To\Game"
```

You may pass either the folder containing the game executable or its inner `game` folder. The installer requires an existing `.rpa`, `.rpy`, or `.rpyc` file before it will write anything. It copies only this mod's files. An existing `openai_tts_config.json` is preserved.

## Add your OpenAI API key

No API key is embedded in the source or release ZIP. Configure your key locally after installation.

Choose one method.

### Local config file

Open this file after installation:

```text
<Game>\game\openai_tts_config.json
```

Put your key between the quotes:

```json
{
  "api_key": "YOUR_KEY_HERE",
  "model": "gpt-4o-mini-tts",
  "voice": "coral",
  "instructions": "Speak naturally with clear, expressive narration.",
  "timeout_seconds": 45,
  "max_chars": 4000,
  "debounce_seconds": 0.25
}
```

The file stores the key as plain text on your PC. Do not upload or share it.

### Environment variable

Set `OPENAI_API_KEY` in the environment that launches the game. The environment value takes precedence over the config file and is never written to disk by the mod.

Do not put the key on the `install.py` command line. Command lines may be saved in shell history or process logs.

## Use

Start the game and press `V`. Ren'Py enables self-voicing and sends the text it would normally speak to this mod. Press `V` again to turn self-voicing off.

Ren'Py's other accessibility modes still use the stock backend:

- `Shift+A` opens the accessibility menu.
- Clipboard and self-voicing debug modes bypass OpenAI.
- Focus traversal and the game's accessible labels remain Ren'Py behavior.

## Settings

| Setting | Default | Purpose |
|---|---:|---|
| `model` | `gpt-4o-mini-tts` | OpenAI speech model |
| `voice` | `coral` | OpenAI built-in voice |
| `instructions` | natural, expressive narration | Voice style prompt |
| `timeout_seconds` | `45` | Network timeout, allowed range 1 to 120 |
| `max_chars` | `4000` | Maximum characters per API request, allowed range 1 to 4000 |
| `debounce_seconds` | `0.25` | Wait before sending rapidly changing focus text, allowed range 0 to 2 |

Cache keys use whitespace-normalized text. Changes only to spacing may reuse the same entry; changes to spoken text, model, voice, instructions, or chunk size create a different entry.

## Cost, privacy, and disclosure

OpenAI API use is billable. Self-voicing may read menu labels and other interface text, not only dialogue. The mod caches successful audio under `<Game>\game\openai_tts_cache` to avoid paying again for identical text and settings. Rapid focus changes are collapsed when possible.

Cancellation is cooperative at chunk boundaries. A chunk already in the HTTP transport, or being handed to it at the same moment as cancellation, may still start and be billed. It will not play or trigger fallback after cancellation. A completed cancelled render may also win the final cache-promotion race, but that cache entry is content-addressed and can only be reused for the same normalized text and voice settings.

Spoken text is sent to OpenAI over HTTPS. Certificate verification uses the bundled Certifi/Mozilla CA bundle and is never disabled. Do not use the mod for text you are not willing to send to the API.

The voice is AI-generated. OpenAI's speech guidance requires a clear disclosure to end users. This project is designed for the person who installed and configured the mod. If you redistribute it as part of a game, add an in-game disclosure.

## Failure behavior

Network calls run on one background worker. Ren'Py's main thread remains free to draw and accept input. Only the newest result may play.

If the key is missing, the API fails, audio is invalid, or the current request cannot be cached, the mod uses Ren'Py's original system TTS for that text. It does not include the API key or raw exception text in the on-screen error notice.

## Remove

Delete only these paths from the game's `game` folder:

```text
openai_tts.rpy
openai_tts.rpyc
openai_tts_mod\
openai_tts_config.json.example
openai_tts_config.json
openai_tts_cache\
```

Keep `openai_tts_config.json` somewhere private first if you plan to reuse its settings.

## Verify the source

```console
python -m unittest discover -s tests -v
python tools/check_runtime_compat.py
python tools/build_release.py
```

The automated suite uses a fake HTTP transport and a fake Ren'Py host. It proves request construction, WAV merging, cache behavior, tested latest-only playback cases, fallback behavior, installer validation and manifest boundaries, static runtime syntax checks, and deterministic packaging without making a paid API call.

A final real-game smoke test still requires a game path, a locally configured API key, and approval for a paid synthesis request.

## Technical notes

Ren'Py's self-voicing system calls `config.tts_function(text)` after it extracts and substitutes accessible text. The mod installs that callback at init priority 999. It does not edit `config.keymap`, so `V` remains Ren'Py's built-in toggle.

- Ren'Py self-voicing documentation: https://www.renpy.org/doc/html/self_voicing.html
- OpenAI text-to-speech guide: https://platform.openai.com/docs/guides/text-to-speech

## License

No license has been selected for the mod's own source code. The local project is unpublished.

The distributed `openai_tts_mod/cacert.pem` file comes from Certifi's Mozilla CA bundle. Its license text is included as `openai_tts_mod/CERTIFI_LICENSE.txt`.
