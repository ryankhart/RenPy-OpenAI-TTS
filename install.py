from __future__ import print_function, unicode_literals

import argparse
import os
import shutil
import stat
import sys


RUNTIME_FILES = [
    "openai_tts.rpy",
    "openai_tts_config.json.example",
    "openai_tts_mod/__init__.py",
    "openai_tts_mod/adapter.py",
    "openai_tts_mod/core.py",
]


class InstallError(Exception):
    pass


def _is_link_or_reparse(path):
    if os.path.islink(path):
        return True
    try:
        attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    except OSError:
        return False
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def _assert_beneath(root, path):
    root_real = os.path.normcase(os.path.realpath(root))
    path_real = os.path.normcase(os.path.realpath(path))
    try:
        common = os.path.commonpath([root_real, path_real])
    except ValueError:
        raise InstallError("Installer destination escapes the selected game directory")
    if common != root_real:
        raise InstallError("Installer destination escapes the selected game directory")


def _preflight_destination(game_dir, relative_path):
    parts = relative_path.split("/")
    current = game_dir
    for part in parts[:-1]:
        current = os.path.join(current, part)
        if os.path.lexists(current):
            if _is_link_or_reparse(current):
                raise InstallError("Installer destination parent is a link or reparse point: %s" % relative_path)
            if not os.path.isdir(current):
                raise InstallError("Installer destination parent is not a directory: %s" % relative_path)

    destination = os.path.join(game_dir, *parts)
    _assert_beneath(game_dir, os.path.dirname(destination))
    _assert_beneath(game_dir, destination)
    if os.path.lexists(destination):
        if _is_link_or_reparse(destination):
            raise InstallError("Installer destination is a link or reparse point: %s" % relative_path)
        if not os.path.isfile(destination):
            raise InstallError("Installer destination is not a regular file: %s" % relative_path)
    return destination


def _looks_like_renpy_game(directory):
    try:
        names = os.listdir(directory)
    except OSError:
        return False
    return any(
        name.lower().endswith((".rpa", ".rpy", ".rpyc"))
        and os.path.isfile(os.path.join(directory, name))
        and not _is_link_or_reparse(os.path.join(directory, name))
        for name in names
    )


def resolve_game_dir(path):
    requested = os.path.abspath(os.path.expanduser(path))
    nested = os.path.join(requested, "game")

    if os.path.lexists(requested) and _is_link_or_reparse(requested):
        raise InstallError("The selected game directory is a link or reparse point")
    if os.path.lexists(nested) and _is_link_or_reparse(nested):
        raise InstallError("The selected game's 'game' directory is a link or reparse point")
    if os.path.isdir(nested) and _looks_like_renpy_game(nested):
        return nested

    if os.path.isdir(requested) and _looks_like_renpy_game(requested):
        return requested

    raise InstallError(
        "Not a Ren'Py game directory. Select the game folder or its 'game' subfolder."
    )


def install_game(path, dry_run=False, source_dir=None):
    game_dir = resolve_game_dir(path)
    if source_dir is None:
        source_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game")

    actions = []
    destinations = {}
    for relative_path in RUNTIME_FILES:
        source = os.path.join(source_dir, *relative_path.split("/"))
        if not os.path.isfile(source):
            raise InstallError("Installer runtime is incomplete: %s" % relative_path)
        actions.append({"destination": relative_path, "status": "would_copy"})

    for relative_path in RUNTIME_FILES + ["openai_tts_config.json"]:
        destinations[relative_path] = _preflight_destination(game_dir, relative_path)

    config_path = destinations["openai_tts_config.json"]
    actions.append(
        {
            "destination": "openai_tts_config.json",
            "status": "preserved" if os.path.exists(config_path) else "would_copy",
        }
    )

    if dry_run:
        return actions

    for index, relative_path in enumerate(RUNTIME_FILES):
        source = os.path.join(source_dir, *relative_path.split("/"))
        destination = destinations[relative_path]
        parent = os.path.dirname(destination)
        if not os.path.isdir(parent):
            os.makedirs(parent)
        shutil.copy2(source, destination)
        actions[index]["status"] = "copied"

    if not os.path.exists(config_path):
        shutil.copy2(
            os.path.join(source_dir, "openai_tts_config.json.example"),
            config_path,
        )
        actions[-1]["status"] = "copied"

    return actions


def main(argv=None, stdout=None):
    output = stdout or sys.stdout
    parser = argparse.ArgumentParser(
        description="Install the OpenAI self-voicing mod into one Ren'Py game."
    )
    parser.add_argument(
        "--game-dir",
        required=True,
        help="Game folder, or the game's inner 'game' folder.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and show the exact files without changing anything.",
    )
    arguments = parser.parse_args(argv)

    try:
        actions = install_game(arguments.game_dir, dry_run=arguments.dry_run)
    except InstallError as error:
        print("ERROR: %s" % error, file=output)
        return 2

    print("DRY RUN" if arguments.dry_run else "INSTALL COMPLETE", file=output)
    for action in actions:
        print("%-10s %s" % (action["status"], action["destination"]), file=output)

    if arguments.dry_run:
        print("No files were changed.", file=output)
    else:
        print("Configure OPENAI_API_KEY or edit openai_tts_config.json locally.", file=output)
        print("Start the game and press V to toggle Ren'Py self-voicing.", file=output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
