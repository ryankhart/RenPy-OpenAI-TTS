from __future__ import unicode_literals

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "game"))


class ControlPanelTests(unittest.TestCase):
    def make_game(self, directory, config=None):
        game_root = os.path.join(directory, "FixtureGame")
        game_dir = os.path.join(game_root, "game")
        os.makedirs(game_dir)
        config_path = os.path.join(game_dir, "openai_tts_config.json")
        if config is not None:
            with open(config_path, "w", encoding="utf-8") as config_file:
                json.dump(config, config_file)
        return game_root, game_dir, config_path

    def test_resolve_config_path_uses_panel_location_or_explicit_game(self):
        from control_panel import resolve_config_path

        with tempfile.TemporaryDirectory() as directory:
            game_root, game_dir, config_path = self.make_game(directory, {})
            panel_path = os.path.join(game_root, "OpenAI TTS Control Panel.exe")

            self.assertEqual(resolve_config_path(executable_path=panel_path), config_path)
            self.assertEqual(resolve_config_path(game_path=game_root), config_path)
            self.assertEqual(resolve_config_path(game_path=game_dir), config_path)

    def test_load_panel_settings_rejects_missing_malformed_and_non_object_configs(self):
        from control_panel import PanelConfigurationError, load_panel_settings

        with tempfile.TemporaryDirectory() as directory:
            missing = os.path.join(directory, "missing.json")
            with self.assertRaises(PanelConfigurationError):
                load_panel_settings(missing)

            malformed = os.path.join(directory, "malformed.json")
            with open(malformed, "w", encoding="utf-8") as config_file:
                config_file.write("{not valid json")
            with self.assertRaises(PanelConfigurationError) as caught:
                load_panel_settings(malformed)
            self.assertNotIn("not valid json", str(caught.exception))

            non_object = os.path.join(directory, "list.json")
            with open(non_object, "w", encoding="utf-8") as config_file:
                json.dump([], config_file)
            with self.assertRaises(PanelConfigurationError):
                load_panel_settings(non_object)

    def test_save_panel_settings_preserves_key_and_unknown_fields(self):
        from control_panel import load_panel_settings, save_panel_settings
        from openai_tts_mod.core import load_settings

        synthetic_key = "test-" + "key-control-panel-not-real"
        with tempfile.TemporaryDirectory() as directory:
            game_root, game_dir, config_path = self.make_game(
                directory,
                {
                    "api_key": synthetic_key,
                    "model": "gpt-4o-mini-tts",
                    "voice": "coral",
                    "instructions": "Original instructions.",
                    "speed": 1.0,
                    "unknown_future_setting": {"enabled": True},
                },
            )

            saved = save_panel_settings(
                config_path,
                voice="cedar",
                speed=1.25,
                instructions="Read clearly and warmly.",
            )

            with open(config_path, "r", encoding="utf-8") as config_file:
                raw = json.load(config_file)
            runtime = load_settings(config_path, {})

            self.assertEqual(saved["voice"], "cedar")
            self.assertEqual(saved["speed"], 1.25)
            self.assertEqual(load_panel_settings(config_path)["instructions"], "Read clearly and warmly.")
            self.assertEqual(raw["api_key"], synthetic_key)
            self.assertEqual(raw["unknown_future_setting"], {"enabled": True})
            self.assertEqual(runtime["voice"], "cedar")
            self.assertEqual(runtime["speed"], 1.25)
            self.assertEqual(sorted(os.listdir(game_dir)), ["openai_tts_config.json"])

    def test_save_panel_settings_rejects_invalid_values_without_changing_file(self):
        from control_panel import PanelConfigurationError, save_panel_settings

        invalid_values = [
            {"voice": "unknown-voice", "speed": 1.0, "instructions": "Valid"},
            {"voice": "coral", "speed": True, "instructions": "Valid"},
            {"voice": "coral", "speed": "1.25", "instructions": "Valid"},
            {"voice": "coral", "speed": float("nan"), "instructions": "Valid"},
            {"voice": "coral", "speed": 4.01, "instructions": "Valid"},
            {"voice": "coral", "speed": 1.0, "instructions": None},
        ]
        with tempfile.TemporaryDirectory() as directory:
            game_root, game_dir, config_path = self.make_game(
                directory,
                {"api_key": "test-key-not-real", "voice": "coral", "speed": 1.0},
            )
            with open(config_path, "rb") as config_file:
                original = config_file.read()

            for values in invalid_values:
                with self.subTest(values=values):
                    with self.assertRaises(PanelConfigurationError):
                        save_panel_settings(config_path, **values)
                    with open(config_path, "rb") as config_file:
                        self.assertEqual(config_file.read(), original)

    def test_headless_self_test_reports_supported_configuration(self):
        from control_panel import BUILT_IN_VOICES, run_self_test

        with tempfile.TemporaryDirectory() as directory:
            report_path = os.path.join(directory, "panel-self-test.json")
            exit_code = run_self_test(report_path)
            with open(report_path, "r", encoding="utf-8") as report_file:
                report = json.load(report_file)

        self.assertEqual(exit_code, 0)
        self.assertTrue(report["ok"])
        self.assertEqual(report["voice_count"], len(BUILT_IN_VOICES))
        self.assertEqual(report["voices"], list(BUILT_IN_VOICES))
        self.assertEqual(report["default_speed"], 1.0)
        self.assertNotIn("api_key", report)

    def test_headless_config_test_performs_real_secret_preserving_save(self):
        from control_panel import run_config_test

        synthetic_key = "test-" + "key-headless-not-real"
        with tempfile.TemporaryDirectory() as directory:
            game_root, game_dir, config_path = self.make_game(
                directory,
                {
                    "api_key": synthetic_key,
                    "voice": "coral",
                    "speed": 1.0,
                    "instructions": "Fixture instructions.",
                    "future": 42,
                },
            )
            report_path = os.path.join(directory, "panel-config-test.json")

            exit_code = run_config_test(game_root, report_path)

            with open(report_path, "r", encoding="utf-8") as report_file:
                report = json.load(report_file)
            with open(config_path, "r", encoding="utf-8") as config_file:
                saved = json.load(config_file)

        self.assertEqual(exit_code, 0)
        self.assertTrue(report["ok"])
        self.assertTrue(report["api_key_preserved"])
        self.assertTrue(report["unknown_fields_preserved"])
        self.assertNotEqual(saved["voice"], "coral")
        self.assertNotEqual(saved["speed"], 1.0)
        self.assertEqual(saved["api_key"], synthetic_key)
        self.assertEqual(saved["future"], 42)
        self.assertNotIn(synthetic_key, json.dumps(report))

    def test_entrypoint_and_build_expose_headless_modes_and_windowed_exe(self):
        from control_panel import ControlPanelApp, build_argument_parser

        parser = build_argument_parser()
        arguments = parser.parse_args(["--self-test", "--report", "report.json"])
        self.assertTrue(arguments.self_test)
        self.assertTrue(hasattr(ControlPanelApp, "save"))
        self.assertTrue(hasattr(ControlPanelApp, "reset_defaults"))

        tools_dir = os.path.join(ROOT, "tools")
        sys.path.insert(0, tools_dir)
        try:
            from build_control_panel import pyinstaller_arguments
        finally:
            sys.path.pop(0)
        build_arguments = pyinstaller_arguments(ROOT)
        self.assertIn("--onefile", build_arguments)
        self.assertIn("--windowed", build_arguments)
        self.assertIn("OpenAI TTS Control Panel", build_arguments)
        self.assertIn(os.path.join(ROOT, "game"), build_arguments)
        self.assertEqual(build_arguments[-1], os.path.join(ROOT, "control_panel.py"))


if __name__ == "__main__":
    unittest.main()
