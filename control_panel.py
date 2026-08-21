from __future__ import print_function, unicode_literals

import argparse
import json
import os
import stat
import sys
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
GAME_SOURCE_DIR = os.path.join(PROJECT_ROOT, "game")
if os.path.isdir(GAME_SOURCE_DIR) and GAME_SOURCE_DIR not in sys.path:
    sys.path.insert(0, GAME_SOURCE_DIR)

from openai_tts_mod.core import ConfigurationError, DEFAULT_SETTINGS, load_settings


BUILT_IN_VOICES = (
    "alloy",
    "ash",
    "ballad",
    "coral",
    "echo",
    "fable",
    "onyx",
    "nova",
    "sage",
    "shimmer",
    "verse",
    "marin",
    "cedar",
)


class PanelConfigurationError(Exception):
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


def resolve_config_path(game_path=None, executable_path=None):
    if game_path:
        selected = os.path.abspath(os.path.expanduser(game_path))
        if os.path.basename(selected).lower() == "game":
            game_dir = selected
        else:
            game_dir = os.path.join(selected, "game")
    else:
        if executable_path is None:
            executable_path = sys.executable if getattr(sys, "frozen", False) else __file__
        game_dir = os.path.join(os.path.dirname(os.path.abspath(executable_path)), "game")
    return os.path.join(game_dir, "openai_tts_config.json")


def _read_config_object(config_path):
    game_dir = os.path.dirname(config_path)
    if _is_link_or_reparse(game_dir):
        raise PanelConfigurationError("The game directory must not be a link or reparse point")
    if not os.path.isfile(config_path) or _is_link_or_reparse(config_path):
        raise PanelConfigurationError("OpenAI TTS configuration was not found as a regular file")
    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            raw = json.load(config_file)
    except PanelConfigurationError:
        raise
    except Exception as error:
        raise PanelConfigurationError(
            "Unable to read OpenAI TTS configuration (%s)" % error.__class__.__name__
        )
    if not isinstance(raw, dict):
        raise PanelConfigurationError("OpenAI TTS configuration must be a JSON object")
    return raw


def load_panel_settings(config_path):
    _read_config_object(config_path)
    try:
        settings = load_settings(config_path, {})
    except ConfigurationError as error:
        raise PanelConfigurationError(str(error))
    if settings["voice"] not in BUILT_IN_VOICES:
        raise PanelConfigurationError("voice must be a supported built-in voice")
    return settings


def _validate_panel_values(voice, speed, instructions):
    if voice not in BUILT_IN_VOICES:
        raise PanelConfigurationError("voice must be a supported built-in voice")
    if (
        not isinstance(speed, (int, float))
        or isinstance(speed, bool)
        or not 0.25 <= speed <= 4.0
    ):
        raise PanelConfigurationError("speed must be between 0.25 and 4.0")
    if not isinstance(instructions, str):
        raise PanelConfigurationError("instructions must be a string")


def save_panel_settings(config_path, voice, speed, instructions):
    _validate_panel_values(voice, speed, instructions)
    existing = _read_config_object(config_path)
    updated = dict(existing)
    updated["voice"] = voice
    updated["speed"] = speed
    updated["instructions"] = instructions

    directory = os.path.dirname(config_path)
    handle, temporary = tempfile.mkstemp(prefix="openai-tts-config-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as config_file:
            json.dump(updated, config_file, indent=2, sort_keys=True)
            config_file.write("\n")
            config_file.flush()
            os.fsync(config_file.fileno())
        try:
            load_settings(temporary, {})
        except ConfigurationError as error:
            raise PanelConfigurationError(str(error))
        os.replace(temporary, config_path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)

    return load_panel_settings(config_path)


def _write_report(report_path, report):
    parent = os.path.dirname(os.path.abspath(report_path))
    if not os.path.isdir(parent):
        os.makedirs(parent)
    with open(report_path, "w", encoding="utf-8") as report_file:
        json.dump(report, report_file, indent=2, sort_keys=True)


def run_self_test(report_path):
    report = {
        "ok": DEFAULT_SETTINGS.get("speed") == 1.0 and "coral" in BUILT_IN_VOICES,
        "default_speed": DEFAULT_SETTINGS.get("speed"),
        "voice_count": len(BUILT_IN_VOICES),
        "voices": list(BUILT_IN_VOICES),
    }
    _write_report(report_path, report)
    return 0 if report["ok"] else 1


def run_config_test(game_path, report_path):
    config_path = resolve_config_path(game_path=game_path)
    try:
        before = _read_config_object(config_path)
        before_key = before.get("api_key")
        known_fields = {"voice", "speed", "instructions"}
        before_unknown = dict((key, value) for key, value in before.items() if key not in known_fields)
        current = load_panel_settings(config_path)
        next_voice = "cedar" if current["voice"] != "cedar" else "coral"
        next_speed = 1.25 if current["speed"] != 1.25 else 1.5
        save_panel_settings(
            config_path,
            voice=next_voice,
            speed=next_speed,
            instructions=current["instructions"],
        )
        after = _read_config_object(config_path)
        after_unknown = dict((key, value) for key, value in after.items() if key not in known_fields)
        report = {
            "ok": True,
            "api_key_preserved": after.get("api_key") == before_key,
            "unknown_fields_preserved": after_unknown == before_unknown,
            "voice_changed": after.get("voice") == next_voice,
            "speed_changed": after.get("speed") == next_speed,
        }
        report["ok"] = all(report.values())
        exit_code = 0 if report["ok"] else 1
    except Exception as error:
        report = {"ok": False, "error_type": error.__class__.__name__}
        exit_code = 1
    _write_report(report_path, report)
    return exit_code


def build_argument_parser():
    parser = argparse.ArgumentParser(description="OpenAI TTS settings for one Ren'Py game")
    headless = parser.add_mutually_exclusive_group()
    headless.add_argument("--self-test", action="store_true")
    headless.add_argument("--config-test", metavar="GAME_PATH")
    parser.add_argument("--game-dir")
    parser.add_argument("--report")
    return parser


class ControlPanelApp(object):
    def __init__(self, root, config_path):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.root = root
        self.config_path = config_path
        self.root.title("OpenAI TTS Control Panel")
        self.root.geometry("700x560")
        self.root.minsize(620, 500)

        settings = load_panel_settings(config_path)
        self.voice = tk.StringVar(value=settings["voice"])
        self.speed = tk.DoubleVar(value=settings["speed"])
        self.status = tk.StringVar(value="Settings loaded. Changes apply the next time the game starts.")

        outer = ttk.Frame(root, padding=20)
        outer.pack(fill="both", expand=True)
        ttk.Label(
            outer,
            text="OpenAI TTS Control Panel",
            font=("Segoe UI", 18, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(
            outer,
            text="Change the OpenAI voice and speaking speed for this game.",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 18))

        ttk.Label(outer, text="Voice").grid(row=2, column=0, sticky="w")
        self.voice_box = ttk.Combobox(
            outer,
            textvariable=self.voice,
            values=BUILT_IN_VOICES,
            state="readonly",
        )
        self.voice_box.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(4, 14))

        ttk.Label(outer, text="Speaking speed").grid(row=4, column=0, sticky="w")
        self.speed_scale = ttk.Scale(
            outer,
            from_=0.25,
            to=4.0,
            variable=self.speed,
            orient="horizontal",
        )
        self.speed_scale.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(4, 4))
        self.speed_box = ttk.Spinbox(
            outer,
            from_=0.25,
            to=4.0,
            increment=0.05,
            textvariable=self.speed,
            width=8,
        )
        self.speed_box.grid(row=5, column=2, sticky="e", padx=(12, 0), pady=(4, 4))
        ttk.Label(outer, text="0.25× slowest   •   1.0× normal   •   4.0× fastest").grid(
            row=6, column=0, columnspan=3, sticky="w", pady=(0, 14)
        )

        ttk.Label(outer, text="Voice instructions").grid(row=7, column=0, sticky="w")
        self.instructions = tk.Text(outer, height=7, wrap="word")
        self.instructions.grid(row=8, column=0, columnspan=3, sticky="nsew", pady=(4, 14))
        self.instructions.insert("1.0", settings["instructions"])

        controls = ttk.Frame(outer)
        controls.grid(row=9, column=0, columnspan=3, sticky="w")
        ttk.Button(controls, text="Save settings", command=self.save).pack(side="left")
        ttk.Button(controls, text="Reset defaults", command=self.reset_defaults).pack(
            side="left", padx=(8, 0)
        )

        ttk.Label(outer, textvariable=self.status, wraplength=650).grid(
            row=10, column=0, columnspan=3, sticky="w", pady=(14, 4)
        )
        ttk.Label(
            outer,
            text="API key and advanced runtime fields are preserved and are not displayed here.",
            wraplength=650,
        ).grid(row=11, column=0, columnspan=3, sticky="w")
        ttk.Label(outer, text=config_path, wraplength=650).grid(
            row=12, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )

        outer.columnconfigure(0, weight=1)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(8, weight=1)

    def save(self):
        from tkinter import messagebox

        try:
            speed = float(self.speed.get())
            settings = save_panel_settings(
                self.config_path,
                voice=self.voice.get(),
                speed=speed,
                instructions=self.instructions.get("1.0", "end-1c"),
            )
        except Exception as error:
            self.status.set("Settings were not changed.")
            messagebox.showerror("Unable to save settings", str(error), parent=self.root)
            return
        self.speed.set(settings["speed"])
        self.status.set("Settings saved. They will apply the next time the game starts.")
        messagebox.showinfo("Settings saved", self.status.get(), parent=self.root)

    def reset_defaults(self):
        self.voice.set(DEFAULT_SETTINGS["voice"])
        self.speed.set(DEFAULT_SETTINGS["speed"])
        self.instructions.delete("1.0", "end")
        self.instructions.insert("1.0", DEFAULT_SETTINGS["instructions"])
        self.status.set("Defaults selected. Click Save settings to apply them.")


def main(argv=None):
    arguments = build_argument_parser().parse_args(argv)
    report_path = arguments.report or os.path.join(os.getcwd(), "control-panel-self-test.json")
    if arguments.self_test:
        return run_self_test(report_path)
    if arguments.config_test:
        return run_config_test(arguments.config_test, report_path)

    import tkinter as tk
    from tkinter import messagebox

    config_path = resolve_config_path(game_path=arguments.game_dir)
    root = tk.Tk()
    try:
        ControlPanelApp(root, config_path)
    except Exception as error:
        root.withdraw()
        messagebox.showerror("OpenAI TTS Control Panel", str(error), parent=root)
        root.destroy()
        return 1
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
