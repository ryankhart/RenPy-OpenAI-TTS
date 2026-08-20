from __future__ import unicode_literals

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class GuiInstallerTests(unittest.TestCase):
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
