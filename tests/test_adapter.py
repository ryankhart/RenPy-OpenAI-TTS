from __future__ import unicode_literals

import importlib
import io
import json
import os
import sys
import threading
import unittest
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))


class InstallationTests(unittest.TestCase):
    def setUp(self):
        import openai_tts_mod
        self.mod = importlib.reload(openai_tts_mod)

    def test_install_with_malformed_config_keeps_system_tts(self):
        class Music(object):
            registrations = []

            @classmethod
            def channel_defined(cls, channel):
                return False

            @classmethod
            def register_channel(cls, *args, **kwargs):
                cls.registrations.append((args, kwargs))

        class RenPy(object):
            music = Music()
            notices = []

            @classmethod
            def notify(cls, text):
                cls.notices.append(text)

        class Config(object):
            pass

        fallback_calls = []
        config = Config()
        config.tts_function = fallback_calls.append

        import tempfile
        with tempfile.TemporaryDirectory() as game_dir:
            config.gamedir = game_dir
            with open(os.path.join(game_dir, "openai_tts_config.json"), "w", encoding="utf-8") as file:
                file.write("{not valid json")

            result = self.mod.install(RenPy(), config, environ={})

        self.assertIsNone(result)
        config.tts_function("fallback text")
        self.assertEqual(fallback_calls, ["fallback text"])
        self.assertEqual(Music.registrations, [])
        self.assertEqual(RenPy.notices, ["OpenAI TTS configuration is invalid; using the system voice."])

    def test_mocked_end_to_end_request_caches_and_plays_audio(self):
        class Music(object):
            def __init__(self):
                self.played = []

            def channel_defined(self, channel):
                return False

            def register_channel(self, *args, **kwargs):
                pass

            def stop(self, channel):
                pass

            def play(self, filename, channel, loop):
                self.played.append((filename, channel, loop))

        class Preferences(object):
            self_voicing = True

        class Game(object):
            preferences = Preferences()

        class RenPy(object):
            music = Music()
            game = Game()
            scheduled = []
            scheduled_event = threading.Event()

            @classmethod
            def invoke_in_main_thread(cls, function, *args):
                cls.scheduled.append((function, args))
                cls.scheduled_event.set()

            @classmethod
            def notify(cls, text):
                pass

        class Config(object):
            pass

        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(1)
            wav_file.setframerate(8000)
            wav_file.writeframes(b"A")
        wav_bytes = wav_buffer.getvalue()
        requests = []

        def transport(url, headers, body, timeout):
            requests.append((url, headers, json.loads(body.decode("utf-8"))))
            return wav_bytes

        import tempfile
        with tempfile.TemporaryDirectory() as game_dir:
            with open(os.path.join(game_dir, "openai_tts_config.json"), "w", encoding="utf-8") as file:
                json.dump({"api_key": "synthetic-test-value", "debounce_seconds": 0}, file)
            config = Config()
            config.gamedir = game_dir
            config.tts_function = lambda text: None
            adapter = self.mod.install(RenPy(), config, environ={}, transport=transport)
            try:
                config.tts_function("Read this line")
                self.assertTrue(RenPy.scheduled_event.wait(1.0))
                for function, args in RenPy.scheduled:
                    function(*args)

                self.assertEqual(len(requests), 1)
                self.assertEqual(requests[0][2]["input"], "Read this line")
                self.assertEqual(len(RenPy.music.played), 1)
                relative_path, channel, loop = RenPy.music.played[0]
                self.assertTrue(relative_path.startswith("openai_tts_cache/"))
                self.assertEqual((channel, loop), ("openai_tts", False))
                self.assertTrue(os.path.isfile(os.path.join(game_dir, *relative_path.split("/"))))
            finally:
                adapter.worker.close()

    def test_reinstall_stops_old_channel_and_closes_old_worker(self):
        class Music(object):
            def __init__(self):
                self.stops = []

            def channel_defined(self, channel):
                return True

            def register_channel(self, *args, **kwargs):
                pass

            def stop(self, channel):
                self.stops.append(channel)

        class Preferences(object):
            self_voicing = True

        class Game(object):
            preferences = Preferences()

        class RenPy(object):
            music = Music()
            game = Game()

        class Config(object):
            pass

        import tempfile
        with tempfile.TemporaryDirectory() as game_dir:
            config = Config()
            config.gamedir = game_dir
            config.tts_function = lambda text: None
            first = self.mod.install(RenPy(), config, environ={})
            second = self.mod.install(RenPy(), config, environ={})
            try:
                self.assertTrue(first.worker.closed)
                self.assertEqual(RenPy.music.stops, ["openai_tts"])
            finally:
                second.worker.close()

    def test_rpy_bootstrap_installs_late_without_rebinding_v(self):
        bootstrap_path = os.path.join(ROOT, "game", "openai_tts.rpy")
        with open(bootstrap_path, "r", encoding="utf-8") as bootstrap_file:
            source = bootstrap_file.read()

        self.assertIn("init 999 python hide:", source)
        self.assertIn("install(renpy, config)", source)
        self.assertNotIn("config.keymap", source)
        self.assertNotIn("K_v", source)

    def test_install_registers_voice_channel_and_replaces_only_tts_callback(self):
        install = self.mod.install

        class Music(object):
            def __init__(self):
                self.registrations = []

            def channel_defined(self, channel):
                return False

            def register_channel(self, channel, mixer, loop, stop_on_mute):
                self.registrations.append((channel, mixer, loop, stop_on_mute))

        class Preferences(object):
            self_voicing = True

        class Game(object):
            preferences = Preferences()

        class RenPy(object):
            music = Music()
            game = Game()

        class Config(object):
            gamedir = None
            tts_function = None

        fallback_calls = []
        config = Config()
        config.tts_function = fallback_calls.append

        import tempfile
        with tempfile.TemporaryDirectory() as game_dir:
            config.gamedir = game_dir
            adapter = install(RenPy(), config, environ={})
            try:
                self.assertIs(config.tts_function.__self__, adapter)
                self.assertEqual(config.tts_function.__func__, adapter.speak.__func__)
                adapter.fallback("fallback probe")
                self.assertEqual(fallback_calls, ["fallback probe"])
                self.assertEqual(
                    RenPy.music.registrations,
                    [("openai_tts", "voice", False, True)],
                )
            finally:
                adapter.worker.close()


class LatestOnlyWorkerTests(unittest.TestCase):
    def test_adapter_delegates_clipboard_and_debug_modes_to_renpy(self):
        from openai_tts_mod.adapter import RenPyTTSAdapter

        class Music(object):
            def __init__(self):
                self.stops = 0

            def stop(self, channel):
                self.stops += 1

        class Worker(object):
            def __init__(self):
                self.submissions = []
                self.cancellations = 0

            def submit(self, text):
                self.submissions.append(text)

            def cancel(self):
                self.cancellations += 1

        class Preferences(object):
            self_voicing = None

        class Game(object):
            preferences = Preferences()

        class RenPy(object):
            music = Music()
            game = Game()

        worker = Worker()
        fallback_calls = []
        adapter = RenPyTTSAdapter(RenPy(), worker, fallback_calls.append, "C:/game/game")

        for mode in ("clipboard", "debug"):
            RenPy.game.preferences.self_voicing = mode
            adapter.speak(mode + " text")

        self.assertEqual(fallback_calls, ["clipboard text", "debug text"])
        self.assertEqual(worker.submissions, [])
        self.assertEqual(worker.cancellations, 2)
        self.assertEqual(RenPy.music.stops, 2)

    def test_adapter_falls_back_only_for_current_failure_on_main_thread(self):
        from openai_tts_mod.adapter import RenPyTTSAdapter

        class Worker(object):
            def is_current(self, token):
                return token == 2

        class Preferences(object):
            self_voicing = True

        class Game(object):
            preferences = Preferences()

        class RenPy(object):
            game = Game()
            scheduled = []
            notices = []

            @classmethod
            def invoke_in_main_thread(cls, function, *args):
                cls.scheduled.append((function, args))

            @classmethod
            def notify(cls, text):
                cls.notices.append(text)

        fallback_calls = []
        adapter = RenPyTTSAdapter(RenPy(), Worker(), fallback_calls.append, "C:/game/game")

        adapter.on_error(1, "stale text", RuntimeError("secret detail"))
        adapter.on_error(2, "current text", RuntimeError("secret detail"))
        for function, args in RenPy.scheduled:
            function(*args)

        self.assertEqual(fallback_calls, ["current text"])
        self.assertEqual(RenPy.notices, ["OpenAI TTS unavailable; using the system voice."])

    def test_adapter_plays_only_current_result_on_renpy_main_thread(self):
        from openai_tts_mod.adapter import RenPyTTSAdapter

        class Music(object):
            def __init__(self):
                self.played = []

            def play(self, filename, channel, loop):
                self.played.append((filename, channel, loop))

        class Worker(object):
            def is_current(self, token):
                return token == 2

        class Preferences(object):
            self_voicing = True

        class Game(object):
            preferences = Preferences()

        class RenPy(object):
            music = Music()
            game = Game()
            scheduled = []

            @classmethod
            def invoke_in_main_thread(cls, function, *args):
                cls.scheduled.append((function, args))

        adapter = RenPyTTSAdapter(RenPy(), Worker(), lambda text: None, "C:/game/game")

        adapter.on_success(1, "C:/game/game/openai_tts_cache/old.wav")
        adapter.on_success(2, "C:/game/game/openai_tts_cache/new.wav")

        self.assertEqual(RenPy.music.played, [])
        for function, args in RenPy.scheduled:
            function(*args)
        self.assertEqual(
            RenPy.music.played,
            [("openai_tts_cache/new.wav", "openai_tts", False)],
        )

    def test_adapter_stops_audio_but_does_not_submit_blank_text(self):
        from openai_tts_mod.adapter import RenPyTTSAdapter

        class Music(object):
            stopped = []

            @classmethod
            def stop(cls, channel):
                cls.stopped.append(channel)

        class Worker(object):
            submissions = []
            cancellations = 0

            @classmethod
            def submit(cls, text):
                cls.submissions.append(text)

            @classmethod
            def cancel(cls):
                cls.cancellations += 1

        class Preferences(object):
            self_voicing = True

        class Game(object):
            preferences = Preferences()

        class RenPy(object):
            music = Music()
            game = Game()

        adapter = RenPyTTSAdapter(RenPy(), Worker(), lambda text: None, "C:/game/game")
        adapter.speak("   ")

        self.assertEqual(Music.stopped, ["openai_tts"])
        self.assertEqual(Worker.submissions, [])
        self.assertEqual(Worker.cancellations, 1)

    def test_adapter_stops_current_audio_and_submits_without_rendering(self):
        from openai_tts_mod.adapter import RenPyTTSAdapter

        class FakeMusic(object):
            def __init__(self):
                self.stopped = []

            def stop(self, channel):
                self.stopped.append(channel)

        class FakeWorker(object):
            def __init__(self):
                self.submitted = []

            def submit(self, text):
                self.submitted.append(text)
                return 1

        class Preferences(object):
            self_voicing = True

        class Game(object):
            preferences = Preferences()

        class FakeRenPy(object):
            music = FakeMusic()
            game = Game()

        worker = FakeWorker()
        fallback_calls = []
        adapter = RenPyTTSAdapter(FakeRenPy(), worker, fallback_calls.append, "C:/game/game")

        adapter.speak("A line of dialogue")

        self.assertEqual(FakeRenPy.music.stopped, ["openai_tts"])
        self.assertEqual(worker.submitted, ["A line of dialogue"])
        self.assertEqual(fallback_calls, [])

    def test_worker_cancel_drops_pending_request(self):
        from openai_tts_mod.adapter import LatestOnlyWorker

        rendered = threading.Event()

        def render(text, is_current):
            rendered.set()
            return "unexpected.wav"

        worker = LatestOnlyWorker(
            render,
            lambda token, path: None,
            lambda token, text, error: None,
            0.1,
        )
        try:
            token = worker.submit("pending")
            cancelled_token = worker.cancel()
            self.assertGreater(cancelled_token, token)
            self.assertFalse(rendered.wait(0.2))
        finally:
            worker.close()

    def test_worker_cancel_suppresses_in_flight_result(self):
        from openai_tts_mod.adapter import LatestOnlyWorker

        started = threading.Event()
        release = threading.Event()
        successes = []

        def render(text, is_current):
            started.set()
            release.wait(1.0)
            return "stale.wav"

        worker = LatestOnlyWorker(
            render,
            lambda token, path: successes.append((token, path)),
            lambda token, text, error: None,
            0,
        )
        try:
            worker.submit("in flight")
            self.assertTrue(started.wait(1.0))
            worker.cancel()
            release.set()
            worker.thread.join(0.2)
            self.assertEqual(successes, [])
        finally:
            worker.close()

    def test_worker_close_suppresses_in_flight_result(self):
        from openai_tts_mod.adapter import LatestOnlyWorker

        started = threading.Event()
        release = threading.Event()
        successes = []

        def render(text, is_current):
            started.set()
            release.wait(1.0)
            return "stale.wav"

        worker = LatestOnlyWorker(
            render,
            lambda token, path: successes.append((token, path)),
            lambda token, text, error: None,
            0,
        )
        worker.submit("in flight")
        self.assertTrue(started.wait(1.0))
        timer = threading.Timer(0.05, release.set)
        timer.start()
        worker.close()
        timer.join()

        self.assertEqual(successes, [])

    def test_worker_coalesces_rapid_requests_before_rendering(self):
        from openai_tts_mod.adapter import LatestOnlyWorker

        render_calls = []
        successes = []
        completed = threading.Event()

        def render(text, is_current):
            render_calls.append(text)
            return text + ".wav"

        def on_success(token, path):
            successes.append((token, path))
            completed.set()

        worker = LatestOnlyWorker(render, on_success, lambda token, error: None, 0.05)
        try:
            first_token = worker.submit("old text")
            second_token = worker.submit("new text")
            self.assertTrue(completed.wait(1.0))
        finally:
            worker.close()

        self.assertLess(first_token, second_token)
        self.assertEqual(render_calls, ["new text"])
        self.assertEqual(successes, [(second_token, "new text.wav")])


if __name__ == "__main__":
    unittest.main()
