from __future__ import print_function, unicode_literals

import os
import sys

from install import RUNTIME_FILES, install_game


def bundled_runtime_dir(base_dir=None):
    if base_dir is None:
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "game")


def missing_runtime_files(source_dir):
    missing = []
    for relative_path in RUNTIME_FILES:
        path = os.path.join(source_dir, *relative_path.split("/"))
        if not os.path.isfile(path):
            missing.append(relative_path)
    return missing


def run_install_request(game_path, dry_run, source_dir=None):
    if source_dir is None:
        source_dir = bundled_runtime_dir()
    return install_game(game_path, dry_run=dry_run, source_dir=source_dir)


def format_actions(actions, dry_run):
    lines = ["DRY RUN" if dry_run else "INSTALL COMPLETE"]
    for action in actions:
        lines.append("%-10s %s" % (action["status"], action["destination"]))
    if dry_run:
        lines.append("No files were changed.")
    else:
        lines.append("Existing openai_tts_config.json was preserved when present.")
        lines.append("Add an OpenAI API key, start the game, and press V.")
    return "\n".join(lines)
