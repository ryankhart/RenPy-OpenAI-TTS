from __future__ import absolute_import, unicode_literals

import os

from .adapter import LatestOnlyWorker, RenPyTTSAdapter
from .core import OpenAISpeechClient, SpeechService, load_settings

__all__ = ["OpenAISpeechClient", "install"]

_runtime = None


def install(renpy_module, config, environ=None, transport=None):
    global _runtime

    music = getattr(renpy_module, "music", None)
    if music is None:
        music = renpy_module.audio.music

    if _runtime is not None:
        fallback = _runtime.fallback
        music.stop(channel="openai_tts")
        _runtime.worker.close()
    else:
        fallback = config.tts_function

    config_path = os.path.join(config.gamedir, "openai_tts_config.json")
    try:
        settings = load_settings(config_path, environ=environ)
    except Exception:
        config.tts_function = fallback
        renpy_module.notify("OpenAI TTS configuration is invalid; using the system voice.")
        _runtime = None
        return None

    client = OpenAISpeechClient(
        settings["api_key"],
        settings["model"],
        settings["voice"],
        settings["instructions"],
        timeout=settings["timeout_seconds"],
        transport=transport,
    )
    cache_dir = os.path.join(config.gamedir, "openai_tts_cache")
    service = SpeechService(client, cache_dir, max_chars=settings["max_chars"])

    adapter = RenPyTTSAdapter(
        renpy_module,
        None,
        fallback,
        config.gamedir,
        music_module=music,
    )
    worker = LatestOnlyWorker(
        service.render,
        adapter.on_success,
        adapter.on_error,
        settings["debounce_seconds"],
    )
    adapter.worker = worker

    if not music.channel_defined("openai_tts"):
        music.register_channel(
            "openai_tts",
            mixer="voice",
            loop=False,
            stop_on_mute=True,
        )

    config.tts_function = adapter.speak
    _runtime = adapter
    return adapter
