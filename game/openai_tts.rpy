# Ren'Py OpenAI TTS bootstrap.
# Deliberately does not replace the V key. Ren'Py's built-in self-voicing
# continues to own input, focus traversal, substitutions, and text extraction.

init 999 python hide:
    import renpy
    from openai_tts_mod import install

    install(renpy, config)
