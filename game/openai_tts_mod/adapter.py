from __future__ import absolute_import, unicode_literals

import os
import threading
import time


class RenPyTTSAdapter(object):
    def __init__(
        self,
        renpy_module,
        worker,
        fallback,
        game_dir,
        channel="openai_tts",
        music_module=None,
    ):
        self.renpy = renpy_module
        if music_module is None:
            music_module = getattr(renpy_module, "music", None)
        if music_module is None:
            music_module = renpy_module.audio.music
        self.music = music_module
        self.worker = worker
        self.fallback = fallback
        self.game_dir = game_dir
        self.channel = channel
        self.error_notified = False

    def speak(self, text):
        mode = self.renpy.game.preferences.self_voicing
        self.music.stop(channel=self.channel)
        if mode in ("clipboard", "debug"):
            self.worker.cancel()
            self.fallback(text)
            return
        if not text.strip():
            self.worker.cancel()
            return
        self.worker.submit(text)

    def on_success(self, token, path):
        self.renpy.invoke_in_main_thread(self._play_if_current, token, path)

    def on_error(self, token, text, error):
        self.renpy.invoke_in_main_thread(self._fallback_if_current, token, text)

    def _fallback_if_current(self, token, text):
        if not self.worker.is_current(token):
            return
        if not self.error_notified:
            self.renpy.notify("OpenAI TTS unavailable; using the system voice.")
            self.error_notified = True
        self.fallback(text)

    def _play_if_current(self, token, path):
        if not self.worker.is_current(token):
            return
        relative_path = os.path.relpath(path, self.game_dir).replace("\\", "/")
        if relative_path == ".." or relative_path.startswith("../"):
            return
        self.music.play(relative_path, channel=self.channel, loop=False)


class LatestOnlyWorker(object):
    def __init__(self, render, on_success, on_error, debounce_seconds):
        self.render = render
        self.on_success = on_success
        self.on_error = on_error
        self.debounce_seconds = debounce_seconds
        self.condition = threading.Condition()
        self.pending = None
        self.generation = 0
        self.closed = False
        self.thread = threading.Thread(target=self._run, name="RenPyOpenAITTS")
        self.thread.daemon = True
        self.thread.start()

    def submit(self, text):
        with self.condition:
            if self.closed:
                return self.generation
            self.generation += 1
            token = self.generation
            self.pending = (token, text)
            self.condition.notify()
            return token

    def is_current(self, token):
        with self.condition:
            return not self.closed and token == self.generation

    def cancel(self):
        with self.condition:
            if self.closed:
                return self.generation
            self.generation += 1
            self.pending = None
            self.condition.notify()
            return self.generation

    def close(self):
        with self.condition:
            self.closed = True
            self.pending = None
            self.condition.notify()
        self.thread.join(1.0)

    def _next_request(self):
        with self.condition:
            while self.pending is None and not self.closed:
                self.condition.wait()
            if self.closed:
                return None

            token, text = self.pending
            self.pending = None
            deadline = time.time() + self.debounce_seconds

            while self.debounce_seconds:
                remaining = deadline - time.time()
                if remaining <= 0:
                    break
                self.condition.wait(remaining)
                if self.closed:
                    return None
                if self.pending is not None:
                    token, text = self.pending
                    self.pending = None
                    deadline = time.time() + self.debounce_seconds

            return token, text

    def _run(self):
        while True:
            request = self._next_request()
            if request is None:
                return
            token, text = request
            if not self.is_current(token):
                continue
            try:
                path = self.render(text, lambda: self.is_current(token))
            except Exception as error:
                if self.is_current(token):
                    self.on_error(token, text, error)
            else:
                if self.is_current(token):
                    self.on_success(token, path)
