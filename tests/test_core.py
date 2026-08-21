from __future__ import unicode_literals

import io
import json
import os
import sys
import tempfile
import unittest
import wave
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))


class OpenAISpeechClientTests(unittest.TestCase):
    @staticmethod
    def make_wav(frames):
        output = io.BytesIO()
        with wave.open(output, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(1)
            wav_file.setframerate(8000)
            wav_file.writeframes(frames)
        return output.getvalue()

    def test_load_settings_uses_environment_key_and_file_voice_options(self):
        from openai_tts_mod.core import load_settings

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "openai_tts_config.json")
            with open(path, "w", encoding="utf-8") as config_file:
                json.dump(
                    {
                        "api_key": "file-key",
                        "voice": "shimmer",
                        "instructions": "Read dramatically.",
                        "timeout_seconds": 22,
                    },
                    config_file,
                )

            settings = load_settings(path, {"OPENAI_API_KEY": "environment-key"})

        self.assertEqual(settings["api_key"], "environment-key")
        self.assertEqual(settings["model"], "gpt-4o-mini-tts")
        self.assertEqual(settings["voice"], "shimmer")
        self.assertEqual(settings["instructions"], "Read dramatically.")
        self.assertEqual(settings["timeout_seconds"], 22)
        self.assertEqual(settings["max_chars"], 4000)
        self.assertEqual(settings["speed"], 1.0)

    def test_load_settings_accepts_speed_boundaries(self):
        from openai_tts_mod.core import load_settings

        for speed in (0.25, 1, 4.0):
            with self.subTest(speed=speed), tempfile.TemporaryDirectory() as directory:
                path = os.path.join(directory, "openai_tts_config.json")
                with open(path, "w", encoding="utf-8") as config_file:
                    json.dump({"speed": speed}, config_file)

                settings = load_settings(path, {})

                self.assertEqual(settings["speed"], speed)

    def test_load_settings_normalizes_invalid_json_as_configuration_error(self):
        from openai_tts_mod.core import ConfigurationError, load_settings

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "openai_tts_config.json")
            with open(path, "w", encoding="utf-8") as config_file:
                config_file.write("{not valid json")

            with self.assertRaises(ConfigurationError) as caught:
                load_settings(path, {})

        self.assertNotIn("not valid json", str(caught.exception))

    def test_load_settings_rejects_non_string_speech_fields(self):
        from openai_tts_mod.core import ConfigurationError, load_settings

        invalid_settings = [
            {"api_key": 123},
            {"model": None},
            {"voice": []},
            {"instructions": False},
        ]

        for config in invalid_settings:
            with self.subTest(config=config), tempfile.TemporaryDirectory() as directory:
                path = os.path.join(directory, "openai_tts_config.json")
                with open(path, "w", encoding="utf-8") as config_file:
                    json.dump(config, config_file)
                with self.assertRaises(ConfigurationError):
                    load_settings(path, {})

    def test_load_settings_rejects_unsafe_numeric_values(self):
        from openai_tts_mod.core import ConfigurationError, load_settings

        invalid_settings = [
            {"timeout_seconds": "forever"},
            {"timeout_seconds": True},
            {"max_chars": 0},
            {"max_chars": 4001},
            {"debounce_seconds": -1},
            {"speed": True},
            {"speed": "fast"},
            {"speed": 0.24},
            {"speed": 4.01},
            {"speed": float("inf")},
            {"speed": float("nan")},
        ]

        for config in invalid_settings:
            with self.subTest(config=config), tempfile.TemporaryDirectory() as directory:
                path = os.path.join(directory, "openai_tts_config.json")
                with open(path, "w", encoding="utf-8") as config_file:
                    json.dump(config, config_file)
                with self.assertRaises(ConfigurationError):
                    load_settings(path, {})

    def test_render_stops_before_starting_later_chunks_after_cancellation(self):
        from openai_tts_mod.core import SpeechCancelled, SpeechService

        active = [True]

        class FakeClient(object):
            model = "model"
            voice = "voice"
            instructions = "instructions"

            def __init__(self, owner):
                self.owner = owner
                self.calls = []

            def synthesize(self, text):
                self.calls.append(text)
                active[0] = False
                return self.owner.make_wav(b"A")

        with tempfile.TemporaryDirectory() as cache_dir:
            client = FakeClient(self)
            service = SpeechService(client, cache_dir, max_chars=8)

            with self.assertRaises(SpeechCancelled):
                service.render("Alpha. Beta.", lambda: active[0])

            self.assertEqual(client.calls, ["Alpha."])
            self.assertFalse(any(name.endswith(".wav") for name in os.listdir(cache_dir)))

    def test_render_synthesizes_chunks_into_one_valid_wav(self):
        from openai_tts_mod.core import SpeechService

        class FakeClient(object):
            model = "model"
            voice = "voice"
            instructions = "instructions"

            def __init__(self, owner):
                self.owner = owner
                self.calls = []

            def synthesize(self, text):
                self.calls.append(text)
                return self.owner.make_wav(bytes([len(self.calls)]))

        with tempfile.TemporaryDirectory() as cache_dir:
            client = FakeClient(self)
            service = SpeechService(client, cache_dir, max_chars=8)

            path = service.render("Alpha. Beta.")

            self.assertEqual(client.calls, ["Alpha.", "Beta."])
            self.assertTrue(os.path.isfile(path))
            with wave.open(path, "rb") as wav_file:
                self.assertEqual(wav_file.getparams()[:4], (1, 1, 8000, 2))
                self.assertEqual(wav_file.readframes(2), b"\x01\x02")

    def test_render_replaces_corrupt_cache_entry(self):
        from openai_tts_mod.core import SpeechService

        class FakeClient(object):
            model = "model"
            voice = "voice"
            instructions = "instructions"

            def __init__(self, audio):
                self.audio = audio
                self.calls = []

            def synthesize(self, text):
                self.calls.append(text)
                return self.audio

        with tempfile.TemporaryDirectory() as cache_dir:
            client = FakeClient(self.make_wav(b"A"))
            service = SpeechService(client, cache_dir, max_chars=100)
            path = service.render("Repair me")
            with open(path, "wb") as cache_file:
                cache_file.write(b"not a wav")

            repaired = service.render("Repair me")

            self.assertEqual(repaired, path)
            self.assertEqual(client.calls, ["Repair me", "Repair me"])
            with wave.open(repaired, "rb") as wav_file:
                self.assertEqual(wav_file.readframes(1), b"A")

    def test_render_reuses_cached_audio_for_same_text_and_settings(self):
        from openai_tts_mod.core import SpeechService

        class FakeClient(object):
            model = "model"
            voice = "voice"
            instructions = "instructions"

            def __init__(self, audio):
                self.audio = audio
                self.calls = []

            def synthesize(self, text):
                self.calls.append(text)
                return self.audio

        with tempfile.TemporaryDirectory() as cache_dir:
            client = FakeClient(self.make_wav(b"A"))
            service = SpeechService(client, cache_dir, max_chars=100)

            first = service.render("Cache me")
            second = service.render("Cache me")

            self.assertEqual(first, second)
            self.assertEqual(client.calls, ["Cache me"])

    def test_render_uses_separate_cache_entries_for_different_speeds(self):
        from openai_tts_mod.core import SpeechService

        class FakeClient(object):
            model = "model"
            voice = "voice"
            instructions = "instructions"

            def __init__(self, speed, audio):
                self.speed = speed
                self.audio = audio
                self.calls = []

            def synthesize(self, text):
                self.calls.append(text)
                return self.audio

        with tempfile.TemporaryDirectory() as cache_dir:
            normal = FakeClient(1.0, self.make_wav(b"A"))
            faster = FakeClient(1.25, self.make_wav(b"B"))

            normal_path = SpeechService(normal, cache_dir).render("Cache by speed")
            faster_path = SpeechService(faster, cache_dir).render("Cache by speed")

            self.assertNotEqual(normal_path, faster_path)
            self.assertEqual(normal.calls, ["Cache by speed"])
            self.assertEqual(faster.calls, ["Cache by speed"])

    def test_service_rejects_non_positive_max_chars(self):
        from openai_tts_mod.core import ConfigurationError, SpeechService

        with tempfile.TemporaryDirectory() as cache_dir:
            with self.assertRaises(ConfigurationError):
                SpeechService(object(), cache_dir, max_chars=0)

    def test_ssl_context_uses_explicit_ca_bundle(self):
        from openai_tts_mod.core import _create_ssl_context

        with mock.patch("openai_tts_mod.core.ssl.create_default_context") as create_context:
            context = _create_ssl_context("C:/trusted/cacert.pem")

        self.assertIs(context, create_context.return_value)
        create_context.assert_called_once_with(cafile="C:/trusted/cacert.pem")

    def test_split_text_prefers_sentence_boundaries_and_honors_limit(self):
        from openai_tts_mod.core import split_text

        chunks = split_text("Alpha sentence.  Beta sentence? Gamma.", 18)

        self.assertEqual(chunks, ["Alpha sentence.", "Beta sentence?", "Gamma."])
        self.assertTrue(all(len(chunk) <= 18 for chunk in chunks))
        self.assertEqual(" ".join(chunks), "Alpha sentence. Beta sentence? Gamma.")

    def test_synthesize_posts_authenticated_wav_request(self):
        from openai_tts_mod.core import OpenAISpeechClient

        calls = []

        def transport(url, headers, body, timeout):
            calls.append((url, headers, json.loads(body.decode("utf-8")), timeout))
            return b"synthetic wav"

        client = OpenAISpeechClient(
            api_key="test-" + "key-not-real",
            model="gpt-4o-mini-tts",
            voice="coral",
            instructions="Speak naturally.",
            speed=1.25,
            timeout=12,
            transport=transport,
        )

        result = client.synthesize("Hello, Rowan.")

        self.assertEqual(result, b"synthetic wav")
        self.assertEqual(len(calls), 1)
        url, headers, payload, timeout = calls[0]
        self.assertEqual(url, "https://api.openai.com/v1/audio/speech")
        self.assertEqual(headers["Authorization"], "Bearer test-key-not-real")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(timeout, 12)
        self.assertEqual(
            payload,
            {
                "model": "gpt-4o-mini-tts",
                "voice": "coral",
                "input": "Hello, Rowan.",
                "instructions": "Speak naturally.",
                "speed": 1.25,
                "response_format": "wav",
            },
        )

    def test_synthesize_rejects_missing_api_key_without_network_call(self):
        from openai_tts_mod.core import ConfigurationError, OpenAISpeechClient

        calls = []

        def transport(url, headers, body, timeout):
            calls.append(url)
            return b"unused"

        client = OpenAISpeechClient("", "model", "voice", "instructions", transport=transport)

        with self.assertRaises(ConfigurationError):
            client.synthesize("Hello")
        self.assertEqual(calls, [])

    def test_synthesize_redacts_key_when_transport_fails(self):
        from openai_tts_mod.core import OpenAISpeechClient, OpenAITTSError

        secret = "sk-" + "test-secret-never-log"

        def transport(url, headers, body, timeout):
            raise RuntimeError("connection failed while using " + secret)

        client = OpenAISpeechClient(secret, "model", "voice", "instructions", transport=transport)

        with self.assertRaises(OpenAITTSError) as caught:
            client.synthesize("Hello")

        message = str(caught.exception)
        self.assertNotIn(secret, message)
        self.assertEqual(message, "OpenAI speech request failed (RuntimeError)")


if __name__ == "__main__":
    unittest.main()
