from __future__ import unicode_literals

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class GuiInstallerTests(unittest.TestCase):
    def test_entrypoint_exposes_headless_modes_and_gui_actions(self):
        from gui_installer import InstallerApp, build_argument_parser

        parser = build_argument_parser()
        arguments = parser.parse_args(["--self-test", "--report", "report.json"])

        self.assertTrue(arguments.self_test)
        self.assertEqual(arguments.report, "report.json")
        self.assertTrue(hasattr(InstallerApp, "browse"))
        self.assertTrue(hasattr(InstallerApp, "dry_run"))
        self.assertTrue(hasattr(InstallerApp, "install"))

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

    def test_headless_install_test_performs_real_copy(self):
        from gui_installer import run_install_test

        with tempfile.TemporaryDirectory() as directory:
            game_root = os.path.join(directory, "FixtureGame")
            game_dir = os.path.join(game_root, "game")
            os.makedirs(game_dir)
            with open(os.path.join(game_dir, "archive.rpa"), "wb") as marker:
                marker.write(b"fixture")
            report_path = os.path.join(directory, "install-test.json")

            exit_code = run_install_test(
                game_root,
                report_path,
                source_dir=os.path.join(ROOT, "game"),
            )
            with open(report_path, "r", encoding="utf-8") as report_file:
                report = json.load(report_file)

            self.assertEqual(exit_code, 0)
            self.assertTrue(report["ok"])
            self.assertTrue(os.path.isfile(os.path.join(game_dir, "openai_tts.rpy")))
            self.assertTrue(os.path.isfile(os.path.join(game_dir, "openai_tts_mod", "cacert.pem")))
            self.assertTrue(os.path.isfile(os.path.join(game_dir, "openai_tts_config.json")))

    def test_headless_self_test_writes_complete_bundle_report(self):
        from gui_installer import run_self_test

        with tempfile.TemporaryDirectory() as directory:
            report_path = os.path.join(directory, "self-test.json")

            exit_code = run_self_test(
                report_path,
                source_dir=os.path.join(ROOT, "game"),
            )
            with open(report_path, "r", encoding="utf-8") as report_file:
                report = json.load(report_file)

        self.assertEqual(exit_code, 0)
        self.assertTrue(report["ok"])
        self.assertEqual(report["missing"], [])
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

        self.assertIn("--onefile", arguments)
        self.assertIn("--windowed", arguments)
        self.assertIn("RenPy-OpenAI-TTS-Installer", arguments)
        self.assertEqual(len(add_data_values), len(RUNTIME_FILES))
        self.assertNotIn(os.path.join(ROOT, "game") + ";game", add_data_values)
        for relative_path in RUNTIME_FILES:
            source = os.path.join(ROOT, "game", *relative_path.split("/"))
            relative_parent = os.path.dirname(relative_path).replace("\\", "/")
            destination = "game" if not relative_parent else "game/" + relative_parent
            self.assertIn(source + ";" + destination, add_data_values)
        self.assertEqual(arguments[-1], os.path.join(ROOT, "gui_installer.py"))

    def test_project_runtime_bundle_is_complete(self):
        from gui_installer import bundled_runtime_dir, missing_runtime_files

        source_dir = bundled_runtime_dir(ROOT)

        self.assertEqual(source_dir, os.path.join(ROOT, "game"))
        self.assertEqual(missing_runtime_files(source_dir), [])

    def test_controller_dry_run_formats_plan_without_copying(self):
        from gui_installer import format_actions, run_install_request

        with tempfile.TemporaryDirectory() as game_root:
            game_dir = os.path.join(game_root, "game")
            os.makedirs(game_dir)
            with open(os.path.join(game_dir, "archive.rpa"), "wb") as marker:
                marker.write(b"fixture")

            actions = run_install_request(
                game_root,
                dry_run=True,
                source_dir=os.path.join(ROOT, "game"),
            )
            output = format_actions(actions, dry_run=True)

            self.assertIn("DRY RUN", output)
            self.assertIn("would_copy openai_tts.rpy", output)
            self.assertIn("No files were changed.", output)
            self.assertEqual(sorted(os.listdir(game_dir)), ["archive.rpa"])


if __name__ == "__main__":
    unittest.main()
