from __future__ import unicode_literals

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class GuiInstallerTests(unittest.TestCase):
    @staticmethod
    def make_control_panel_source(directory):
        path = os.path.join(directory, "OpenAI TTS Control Panel.exe")
        with open(path, "wb") as panel_file:
            panel_file.write(b"synthetic panel executable")
        return path

    def test_entrypoint_exposes_headless_modes_and_gui_actions(self):
        from gui_installer import DEFAULT_LAUNCH_CONTROL_PANEL, InstallerApp, build_argument_parser

        parser = build_argument_parser()
        arguments = parser.parse_args(["--self-test", "--report", "report.json"])

        self.assertTrue(arguments.self_test)
        self.assertEqual(arguments.report, "report.json")
        self.assertTrue(hasattr(InstallerApp, "browse"))
        self.assertTrue(hasattr(InstallerApp, "dry_run"))
        self.assertTrue(hasattr(InstallerApp, "install"))
        self.assertTrue(DEFAULT_LAUNCH_CONTROL_PANEL)

    def test_headless_modes_are_mutually_exclusive(self):
        from gui_installer import build_argument_parser

        parser = build_argument_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "--self-test",
                    "--install-test",
                    "C:/Fixture",
                    "--report",
                    "report.json",
                ]
            )

    def test_install_confirmation_contains_exact_selected_path(self):
        from gui_installer import install_confirmation

        selected = r"D:\Games\Example RenPy Game"
        confirmation = install_confirmation(selected)

        self.assertIn(selected, confirmation)
        self.assertIn("config is preserved", confirmation.lower())

    def test_headless_install_test_performs_real_copy(self):
        from gui_installer import run_install_test

        with tempfile.TemporaryDirectory() as directory:
            game_root = os.path.join(directory, "FixtureGame")
            game_dir = os.path.join(game_root, "game")
            os.makedirs(game_dir)
            with open(os.path.join(game_dir, "archive.rpa"), "wb") as marker:
                marker.write(b"fixture")
            report_path = os.path.join(directory, "install-test.json")
            panel_source = self.make_control_panel_source(directory)

            exit_code = run_install_test(
                game_root,
                report_path,
                source_dir=os.path.join(ROOT, "game"),
                control_panel_path=panel_source,
            )
            with open(report_path, "r", encoding="utf-8") as report_file:
                report = json.load(report_file)

            self.assertEqual(exit_code, 0)
            self.assertTrue(report["ok"])
            self.assertTrue(os.path.isfile(os.path.join(game_dir, "openai_tts.rpy")))
            self.assertTrue(os.path.isfile(os.path.join(game_dir, "openai_tts_mod", "cacert.pem")))
            self.assertTrue(os.path.isfile(os.path.join(game_dir, "openai_tts_config.json")))
            self.assertTrue(os.path.isfile(os.path.join(game_root, "OpenAI TTS Control Panel.exe")))
            self.assertTrue(report["panel_present"])

    def test_headless_self_test_writes_complete_bundle_report(self):
        from gui_installer import run_self_test

        with tempfile.TemporaryDirectory() as directory:
            report_path = os.path.join(directory, "self-test.json")
            panel_source = self.make_control_panel_source(directory)

            exit_code = run_self_test(
                report_path,
                source_dir=os.path.join(ROOT, "game"),
                control_panel_path=panel_source,
            )
            with open(report_path, "r", encoding="utf-8") as report_file:
                report = json.load(report_file)

        self.assertEqual(exit_code, 0)
        self.assertTrue(report["ok"])
        self.assertEqual(report["missing"], [])
        self.assertTrue(report["license_present"])
        self.assertTrue(report["control_panel_present"])
        self.assertGreater(report["runtime_file_count"], 0)

    def test_pyinstaller_arguments_embed_complete_runtime(self):
        from install import RUNTIME_FILES

        tools_dir = os.path.join(ROOT, "tools")
        sys.path.insert(0, tools_dir)
        try:
            from build_gui_installer import pyinstaller_arguments
        finally:
            sys.path.pop(0)

        arguments = pyinstaller_arguments(ROOT)
        add_data_values = [
            arguments[index + 1]
            for index, argument in enumerate(arguments)
            if argument == "--add-data"
        ]
        add_binary_values = [
            arguments[index + 1]
            for index, argument in enumerate(arguments)
            if argument == "--add-binary"
        ]

        self.assertIn("--onefile", arguments)
        self.assertIn("--windowed", arguments)
        self.assertIn("RenPy-OpenAI-TTS-Installer", arguments)
        self.assertEqual(len(add_data_values), len(RUNTIME_FILES) + 1)
        self.assertNotIn(os.path.join(ROOT, "game") + ";game", add_data_values)
        self.assertIn(os.path.join(ROOT, "LICENSE") + ";.", add_data_values)
        self.assertEqual(
            add_binary_values,
            [os.path.join(ROOT, "dist", "OpenAI TTS Control Panel.exe") + ";."],
        )
        for relative_path in RUNTIME_FILES:
            source = os.path.join(ROOT, "game", *relative_path.split("/"))
            relative_parent = os.path.dirname(relative_path).replace("\\", "/")
            destination = "game" if not relative_parent else "game/" + relative_parent
            self.assertIn(source + ";" + destination, add_data_values)
        self.assertEqual(arguments[-1], os.path.join(ROOT, "gui_installer.py"))

    def test_pyinstaller_excludes_unlisted_live_config(self):
        from install import RUNTIME_FILES

        tools_dir = os.path.join(ROOT, "tools")
        sys.path.insert(0, tools_dir)
        try:
            from build_gui_installer import pyinstaller_arguments
        finally:
            sys.path.pop(0)

        with tempfile.TemporaryDirectory() as project_root:
            for relative_path in RUNTIME_FILES:
                path = os.path.join(project_root, "game", *relative_path.split("/"))
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as runtime_file:
                    runtime_file.write("allowlisted")
            live_config = os.path.join(project_root, "game", "openai_tts_config.json")
            with open(live_config, "w", encoding="utf-8") as config_file:
                config_file.write('{"api_key":"credential-shaped-sentinel"}')
            with open(os.path.join(project_root, "gui_installer.py"), "w", encoding="utf-8") as entrypoint:
                entrypoint.write("pass")

            arguments = pyinstaller_arguments(project_root)
            add_data_sources = [
                arguments[index + 1].split(";", 1)[0]
                for index, argument in enumerate(arguments)
                if argument == "--add-data"
            ]

        self.assertNotIn(live_config, add_data_sources)
        self.assertNotIn("credential-shaped-sentinel", "\n".join(arguments))

    def test_project_runtime_bundle_is_complete(self):
        from gui_installer import bundled_runtime_dir, missing_runtime_files

        source_dir = bundled_runtime_dir(ROOT)

        self.assertEqual(source_dir, os.path.join(ROOT, "game"))
        self.assertEqual(missing_runtime_files(source_dir), [])

    def test_controller_dry_run_formats_plan_without_copying(self):
        from gui_installer import format_actions, run_install_request

        with tempfile.TemporaryDirectory() as game_root, tempfile.TemporaryDirectory() as source_directory:
            game_dir = os.path.join(game_root, "game")
            os.makedirs(game_dir)
            with open(os.path.join(game_dir, "archive.rpa"), "wb") as marker:
                marker.write(b"fixture")
            panel_source = self.make_control_panel_source(source_directory)

            actions = run_install_request(
                game_root,
                dry_run=True,
                source_dir=os.path.join(ROOT, "game"),
                control_panel_source=panel_source,
            )
            output = format_actions(actions, dry_run=True)

            self.assertIn("DRY RUN", output)
            self.assertIn("would_copy openai_tts.rpy", output)
            self.assertIn("would_copy OpenAI TTS Control Panel.exe", output)
            self.assertIn("No files were changed.", output)
            self.assertEqual(sorted(os.listdir(game_dir)), ["archive.rpa"])

    def test_launch_control_panel_uses_installed_executable_and_selected_game(self):
        from gui_installer import launch_control_panel

        calls = []

        def fake_popen(command, **kwargs):
            calls.append((command, kwargs))
            return object()

        with tempfile.TemporaryDirectory() as game_root:
            game_dir = os.path.join(game_root, "game")
            os.makedirs(game_dir)
            with open(os.path.join(game_dir, "archive.rpa"), "wb") as marker:
                marker.write(b"fixture")
            panel_path = os.path.join(game_root, "OpenAI TTS Control Panel.exe")
            with open(panel_path, "wb") as panel_file:
                panel_file.write(b"synthetic panel")

            launch_control_panel(game_root, popen=fake_popen)

        self.assertEqual(calls[0][0], [panel_path, "--game-dir", os.path.abspath(game_root)])
        self.assertEqual(
            calls[0][1].get("creationflags", 0),
            getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def test_post_install_launch_failure_returns_warning_without_changing_install_result(self):
        from gui_installer import launch_after_install

        def failing_launch(game_path):
            raise OSError("synthetic launch failure")

        warning = launch_after_install("C:/Fixture", True, launch=failing_launch)

        self.assertEqual(warning, "OSError: synthetic launch failure")
        self.assertIsNone(launch_after_install("C:/Fixture", False, launch=failing_launch))

    def test_control_panel_verifier_runs_self_and_config_headless_modes(self):
        from gui_installer import verify_control_panel_executable

        commands = []

        class Result(object):
            returncode = 0

        def fake_runner(command, **kwargs):
            commands.append(command)
            report_path = command[command.index("--report") + 1]
            with open(report_path, "w", encoding="utf-8") as report_file:
                json.dump({"ok": True}, report_file)
            return Result()

        result = verify_control_panel_executable(
            "C:/Fixture/OpenAI TTS Control Panel.exe",
            "C:/Fixture",
            runner=fake_runner,
        )

        self.assertEqual(result, {"panel_self_test": True, "panel_config_test": True})
        self.assertIn("--self-test", commands[0])
        self.assertEqual(commands[1][1:3], ["--config-test", "C:/Fixture"])


if __name__ == "__main__":
    unittest.main()
