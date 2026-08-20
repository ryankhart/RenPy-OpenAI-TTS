from __future__ import absolute_import, unicode_literals

import hashlib
import io
import json
import os
import ssl
import tempfile
import wave

try:
    string_types = (basestring,)
    text_type = unicode
except NameError:  # pragma: no cover - Python 3 branch is exercised in tests.
    string_types = (str,)
    text_type = str

try:
    from urllib.request import Request, urlopen
except ImportError:  # pragma: no cover - exercised by Ren'Py 7/Python 2.
    from urllib2 import Request, urlopen


SPEECH_ENDPOINT = "https://api.openai.com/v1/audio/speech"
CA_BUNDLE_PATH = os.path.join(os.path.dirname(__file__), "cacert.pem")

DEFAULT_SETTINGS = {
    "api_key": "",
    "model": "gpt-4o-mini-tts",
    "voice": "coral",
    "instructions": "Speak naturally with clear, expressive narration.",
    "timeout_seconds": 45,
    "max_chars": 4000,
    "debounce_seconds": 0.25,
}


class OpenAITTSError(Exception):
    pass


class ConfigurationError(OpenAITTSError):
    pass


class SpeechCancelled(OpenAITTSError):
    pass


def _valid_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def load_settings(config_path, environ=None):
    settings = dict(DEFAULT_SETTINGS)
    if os.path.isfile(config_path):
        try:
            with io.open(config_path, "r", encoding="utf-8") as config_file:
                loaded = json.load(config_file)
        except Exception as error:
            raise ConfigurationError(
                "Unable to read OpenAI TTS configuration (%s)" % error.__class__.__name__
            )
        if not isinstance(loaded, dict):
            raise ConfigurationError("OpenAI TTS configuration must be a JSON object")
        settings.update(loaded)

    environment = os.environ if environ is None else environ
    environment_key = environment.get("OPENAI_API_KEY", "").strip()
    if environment_key:
        settings["api_key"] = environment_key

    for field in ("api_key", "model", "voice", "instructions"):
        if not isinstance(settings[field], string_types):
            raise ConfigurationError("%s must be a string" % field)
    if not settings["model"].strip():
        raise ConfigurationError("model must not be empty")
    if not settings["voice"].strip():
        raise ConfigurationError("voice must not be empty")

    timeout = settings["timeout_seconds"]
    max_chars = settings["max_chars"]
    debounce = settings["debounce_seconds"]
    if not _valid_number(timeout) or not 1 <= timeout <= 120:
        raise ConfigurationError("timeout_seconds must be between 1 and 120")
    if not isinstance(max_chars, int) or isinstance(max_chars, bool) or not 1 <= max_chars <= 4000:
        raise ConfigurationError("max_chars must be an integer between 1 and 4000")
    if not _valid_number(debounce) or not 0 <= debounce <= 2:
        raise ConfigurationError("debounce_seconds must be between 0 and 2")

    return settings


def split_text(text, max_chars):
    normalized = " ".join(text.split())
    chunks = []

    while len(normalized) > max_chars:
        minimum_boundary = max_chars // 2
        cut = -1
        for marker in (". ", "? ", "! ", "; ", ": "):
            position = normalized.rfind(marker, minimum_boundary, max_chars + 1)
            if position >= 0:
                cut = max(cut, position + 1)

        if cut < 0:
            cut = normalized.rfind(" ", 0, max_chars + 1)
        if cut <= 0:
            cut = max_chars

        chunks.append(normalized[:cut].strip())
        normalized = normalized[cut:].strip()

    if normalized:
        chunks.append(normalized)

    return chunks


def merge_wav_chunks(wav_chunks, output_path):
    if not wav_chunks:
        raise OpenAITTSError("OpenAI returned no audio")

    audio_params = None
    frame_sets = []
    try:
        for wav_bytes in wav_chunks:
            source = wave.open(io.BytesIO(wav_bytes), "rb")
            try:
                current_params = (
                    source.getnchannels(),
                    source.getsampwidth(),
                    source.getframerate(),
                    source.getcomptype(),
                )
                if audio_params is None:
                    audio_params = current_params
                elif current_params != audio_params:
                    raise OpenAITTSError("OpenAI returned incompatible WAV chunks")
                frame_sets.append(source.readframes(source.getnframes()))
            finally:
                source.close()
    except OpenAITTSError:
        raise
    except Exception as error:
        raise OpenAITTSError("OpenAI returned invalid WAV audio (%s)" % error.__class__.__name__)

    destination = wave.open(output_path, "wb")
    try:
        destination.setnchannels(audio_params[0])
        destination.setsampwidth(audio_params[1])
        destination.setframerate(audio_params[2])
        destination.setcomptype(audio_params[3], "not compressed")
        for frames in frame_sets:
            destination.writeframes(frames)
    finally:
        destination.close()


def _valid_wav_file(path):
    try:
        source = wave.open(path, "rb")
        try:
            return (
                source.getnchannels() > 0
                and source.getsampwidth() > 0
                and source.getframerate() > 0
                and source.getnframes() > 0
            )
        finally:
            source.close()
    except Exception:
        return False


def _cache_digest(client, text, max_chars):
    identity = {
        "schema": 1,
        "model": client.model,
        "voice": client.voice,
        "instructions": client.instructions,
        "response_format": "wav",
        "max_chars": max_chars,
        "text": text,
    }
    encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _atomic_replace(source, target):
    if hasattr(os, "replace"):
        os.replace(source, target)
        return

    if os.name == "nt":  # pragma: no cover - Ren'Py 7/Python 2 on Windows.
        import ctypes

        movefile_replace_existing = 0x1
        movefile_write_through = 0x8
        move_file_ex = ctypes.windll.kernel32.MoveFileExW
        move_file_ex.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_ulong]
        move_file_ex.restype = ctypes.c_int
        moved = move_file_ex(
            text_type(source),
            text_type(target),
            movefile_replace_existing | movefile_write_through,
        )
        if not moved:
            raise ctypes.WinError()
        return

    os.rename(source, target)  # POSIX rename replaces atomically.


class SpeechService(object):
    def __init__(self, client, cache_dir, max_chars=4000):
        if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars < 1:
            raise ConfigurationError("max_chars must be a positive integer")
        self.client = client
        self.cache_dir = cache_dir
        self.max_chars = max_chars

    def render(self, text, is_current=None):
        def require_current():
            if is_current is not None and not is_current():
                raise SpeechCancelled("Speech request was cancelled")

        chunks = split_text(text, self.max_chars)
        if not chunks:
            raise OpenAITTSError("No speakable text was provided")

        require_current()
        if not os.path.isdir(self.cache_dir):
            os.makedirs(self.cache_dir)

        target = os.path.join(
            self.cache_dir,
            _cache_digest(self.client, " ".join(chunks), self.max_chars) + ".wav",
        )
        if os.path.isfile(target) and _valid_wav_file(target):
            require_current()
            return target

        wav_chunks = []
        for chunk in chunks:
            require_current()
            wav_chunks.append(self.client.synthesize(chunk))
        require_current()

        handle, temporary = tempfile.mkstemp(prefix="openai-tts-", suffix=".tmp", dir=self.cache_dir)
        os.close(handle)
        try:
            merge_wav_chunks(wav_chunks, temporary)
            require_current()
            _atomic_replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

        return target


def _create_ssl_context(ca_bundle_path=CA_BUNDLE_PATH):
    return ssl.create_default_context(cafile=ca_bundle_path)


def _default_transport(url, headers, body, timeout):
    request = Request(url, data=body, headers=headers)
    context = _create_ssl_context()
    response = urlopen(request, timeout=timeout, context=context)
    try:
        return response.read()
    finally:
        response.close()


class OpenAISpeechClient(object):
    def __init__(self, api_key, model, voice, instructions, timeout=45, transport=None):
        self.api_key = api_key
        self.model = model
        self.voice = voice
        self.instructions = instructions
        self.timeout = timeout
        self.transport = transport or _default_transport

    def synthesize(self, text):
        if not self.api_key or not self.api_key.strip():
            raise ConfigurationError("OpenAI API key is not configured")

        payload = {
            "model": self.model,
            "voice": self.voice,
            "input": text,
            "instructions": self.instructions,
            "response_format": "wav",
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Authorization": "Bearer " + self.api_key,
            "Content-Type": "application/json",
        }
        try:
            return self.transport(SPEECH_ENDPOINT, headers, body, self.timeout)
        except OpenAITTSError:
            raise
        except Exception as error:
            raise OpenAITTSError(
                "OpenAI speech request failed (%s)" % error.__class__.__name__
            )
