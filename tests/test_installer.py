from __future__ import unicode_literals

import io
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class InstallerTests(unittest.TestCase):
    def test_cli_dry_run_prints_plan_and_returns_success(self):
        from install import main

        with tempfile.TemporaryDirectory() as game_root:
            game_dir = os.path.join(game_root, "game")
            os.makedirs(game_dir)
            with open(os.path.join(game_dir, "archive.rpa"), "wb") as file:
                file.write(b"marker")
            output = io.StringIO()

            code = main(["--game-dir", game_root, "--dry-run"], stdout=output)

        self.assertEqual(code, 0)
        self.assertIn("DRY RUN", output.getvalue())
        self.assertIn("openai_tts.rpy", output.getvalue())
        self.assertIn("No files were changed.", output.getvalue())

    def test_compatibility_checker_rejects_python3_only_runtime_syntax(self):
        tools_dir = os.path.join(ROOT, "tools")
        sys.path.insert(0, tools_dir)
        try:
            from check_runtime_compat import compatibility_errors
        finally:
            sys.path.pop(0)

        self.assertEqual(compatibility_errors("def compatible(value):\n    return value\n"), [])
        errors = compatibility_errors(
            "from pathlib import Path\n"
            "def incompatible(value: str) -> str:\n"
            "    return f'{value}'\n"
        )
        self.assertTrue(any("annotation" in error for error in errors))
        self.assertTrue(any("f-string" in error for error in errors))
        self.assertTrue(any("pathlib" in error for error in errors))

    def test_dry_run_lists_files_without_modifying_game(self):
        from install import install_game

        with tempfile.TemporaryDirectory() as game_root:
            game_dir = os.path.join(game_root, "game")
            os.makedirs(game_dir)
            with open(os.path.join(game_dir, "script.rpyc"), "wb") as file:
                file.write(b"marker")

            actions = install_game(game_root, dry_run=True)

            self.assertEqual(
                [action["destination"] for action in actions],
                [
                    "openai_tts.rpy",
                    "openai_tts_config.json.example",
                    "openai_tts_mod/__init__.py",
                    "openai_tts_mod/adapter.py",
                    "openai_tts_mod/core.py",
                    "openai_tts_mod/cacert.pem",
                    "openai_tts_mod/CERTIFI_LICENSE.txt",
                    "openai_tts_config.json",
                ],
            )
            self.assertTrue(all(action["status"] == "would_copy" for action in actions))
            self.assertEqual(sorted(os.listdir(game_dir)), ["script.rpyc"])

    def test_install_copies_runtime_and_preserves_existing_config(self):
        from install import install_game

        with tempfile.TemporaryDirectory() as game_root:
            game_dir = os.path.join(game_root, "game")
            os.makedirs(game_dir)
            with open(os.path.join(game_dir, "script.rpyc"), "wb") as file:
                file.write(b"marker")
            config_path = os.path.join(game_dir, "openai_tts_config.json")
            with open(config_path, "w", encoding="utf-8") as file:
                file.write('{"voice": "onyx"}')

            actions = install_game(game_root)

            self.assertEqual(actions[-1]["status"], "preserved")
            with open(config_path, "r", encoding="utf-8") as file:
                self.assertEqual(file.read(), '{"voice": "onyx"}')
            self.assertTrue(os.path.isfile(os.path.join(game_dir, "openai_tts.rpy")))
            self.assertTrue(os.path.isfile(os.path.join(game_dir, "openai_tts_mod", "core.py")))

    def test_install_preflights_all_destinations_before_copying(self):
        from install import InstallError, install_game

        with tempfile.TemporaryDirectory() as game_root:
            game_dir = os.path.join(game_root, "game")
            os.makedirs(game_dir)
            with open(os.path.join(game_dir, "script.rpyc"), "wb") as file:
                file.write(b"marker")
            bootstrap_path = os.path.join(game_dir, "openai_tts.rpy")
            with open(bootstrap_path, "w", encoding="utf-8") as file:
                file.write("keep old bootstrap")
            with open(os.path.join(game_dir, "openai_tts_mod"), "w", encoding="utf-8") as file:
                file.write("parent conflict")

            with self.assertRaises(InstallError):
                install_game(game_root)

            with open(bootstrap_path, "r", encoding="utf-8") as file:
                self.assertEqual(file.read(), "keep old bootstrap")
            self.assertFalse(os.path.exists(os.path.join(game_dir, "openai_tts_config.json.example")))

    def test_install_rejects_selected_wrapper_root_junction(self):
        from install import InstallError, install_game

        with tempfile.TemporaryDirectory() as links, tempfile.TemporaryDirectory() as real_wrapper:
            real_game = os.path.join(real_wrapper, "game")
            os.makedirs(real_game)
            with open(os.path.join(real_game, "script.rpyc"), "wb") as file:
                file.write(b"marker")
            selected = os.path.join(links, "selected-game")
            try:
                os.symlink(real_wrapper, selected, target_is_directory=True)
            except (OSError, NotImplementedError) as error:
                if os.name != "nt":
                    self.skipTest("directory links unavailable: %s" % error)
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                result = subprocess.run(
                    ["cmd.exe", "/c", "mklink", "/J", selected, real_wrapper],
                    capture_output=True,
                    creationflags=creationflags,
                )
                if result.returncode:
                    self.skipTest("directory links unavailable: %s" % error)

            with self.assertRaises(InstallError):
                install_game(selected)

            self.assertEqual(sorted(os.listdir(real_game)), ["script.rpyc"])

    def test_install_rejects_game_directory_root_junction(self):
        from install import InstallError, install_game

        with tempfile.TemporaryDirectory() as outer, tempfile.TemporaryDirectory() as outside:
            with open(os.path.join(outside, "script.rpyc"), "wb") as file:
                file.write(b"marker")
            link = os.path.join(outer, "game")
            try:
                os.symlink(outside, link, target_is_directory=True)
            except (OSError, NotImplementedError) as error:
                if os.name != "nt":
                    self.skipTest("directory links unavailable: %s" % error)
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                result = subprocess.run(
                    ["cmd.exe", "/c", "mklink", "/J", link, outside],
                    capture_output=True,
                    creationflags=creationflags,
                )
                if result.returncode:
                    self.skipTest("directory links unavailable: %s" % error)

            with self.assertRaises(InstallError):
                install_game(outer)

            self.assertEqual(sorted(os.listdir(outside)), ["script.rpyc"])

    def test_install_rejects_linked_module_destination(self):
        from install import InstallError, install_game

        with tempfile.TemporaryDirectory() as game_root, tempfile.TemporaryDirectory() as outside:
            game_dir = os.path.join(game_root, "game")
            os.makedirs(game_dir)
            with open(os.path.join(game_dir, "script.rpyc"), "wb") as file:
                file.write(b"marker")
            link = os.path.join(game_dir, "openai_tts_mod")
            try:
                os.symlink(outside, link, target_is_directory=True)
            except (OSError, NotImplementedError) as error:
                if os.name != "nt":
                    self.skipTest("directory links unavailable: %s" % error)
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                result = subprocess.run(
                    ["cmd.exe", "/c", "mklink", "/J", link, outside],
                    capture_output=True,
                    creationflags=creationflags,
                )
                if result.returncode:
                    self.skipTest("directory links unavailable: %s" % error)

            with self.assertRaises(InstallError):
                install_game(game_root)

            self.assertEqual(os.listdir(outside), [])

    def test_install_rejects_config_path_that_is_not_a_file(self):
        from install import InstallError, install_game

        with tempfile.TemporaryDirectory() as game_root:
            game_dir = os.path.join(game_root, "game")
            os.makedirs(game_dir)
            with open(os.path.join(game_dir, "script.rpyc"), "wb") as file:
                file.write(b"marker")
            os.makedirs(os.path.join(game_dir, "openai_tts_config.json"))

            with self.assertRaises(InstallError):
                install_game(game_root)

            self.assertFalse(os.path.exists(os.path.join(game_dir, "openai_tts.rpy")))

    def test_release_zip_is_deterministic_and_contains_no_live_config(self):
        tools_dir = os.path.join(ROOT, "tools")
        sys.path.insert(0, tools_dir)
        try:
            from build_release import build_release
        finally:
            sys.path.pop(0)

        import zipfile
        with tempfile.TemporaryDirectory() as directory:
            first = os.path.join(directory, "first.zip")
            second = os.path.join(directory, "second.zip")
            build_release(first, ROOT)
            build_release(second, ROOT)

            with open(first, "rb") as file:
                first_bytes = file.read()
            with open(second, "rb") as file:
                second_bytes = file.read()
            with zipfile.ZipFile(first, "r") as archive:
                names = archive.namelist()

        self.assertEqual(first_bytes, second_bytes)
        self.assertIn("RenPy-OpenAI-TTS/install.py", names)
        self.assertIn("RenPy-OpenAI-TTS/game/openai_tts_config.json.example", names)
        self.assertIn("RenPy-OpenAI-TTS/game/openai_tts_mod/cacert.pem", names)
        self.assertIn("RenPy-OpenAI-TTS/game/openai_tts_mod/CERTIFI_LICENSE.txt", names)
        self.assertNotIn("RenPy-OpenAI-TTS/game/openai_tts_config.json", names)
        self.assertFalse(any("__pycache__" in name for name in names))

    def test_resolve_game_dir_rejects_marker_named_directory(self):
        from install import InstallError, resolve_game_dir

        with tempfile.TemporaryDirectory() as unrelated:
            os.makedirs(os.path.join(unrelated, "fake.rpy"))
            with self.assertRaises(InstallError):
                resolve_game_dir(unrelated)

    def test_resolve_game_dir_rejects_unrelated_directory(self):
        from install import InstallError, resolve_game_dir

        with tempfile.TemporaryDirectory() as unrelated:
            marker = os.path.join(unrelated, "must-remain.txt")
            with open(marker, "w", encoding="utf-8") as file:
                file.write("untouched")

            with self.assertRaises(InstallError):
                resolve_game_dir(unrelated)

            with open(marker, "r", encoding="utf-8") as file:
                self.assertEqual(file.read(), "untouched")
            self.assertEqual(sorted(os.listdir(unrelated)), ["must-remain.txt"])


if __name__ == "__main__":
    unittest.main()
