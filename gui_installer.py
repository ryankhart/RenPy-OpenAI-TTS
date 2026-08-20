from __future__ import print_function, unicode_literals

import argparse
import json
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


def run_self_test(report_path, source_dir=None):
    if source_dir is None:
        source_dir = bundled_runtime_dir()
    missing = missing_runtime_files(source_dir)
    report = {
        "ok": not missing,
        "missing": missing,
        "runtime_file_count": len(RUNTIME_FILES),
    }
    with open(report_path, "w", encoding="utf-8") as report_file:
        json.dump(report, report_file, indent=2, sort_keys=True)
    return 0 if report["ok"] else 1


def run_install_test(game_path, report_path, source_dir=None):
    try:
        actions = run_install_request(game_path, dry_run=False, source_dir=source_dir)
        report = {
            "ok": True,
            "actions": actions,
        }
        exit_code = 0
    except Exception as error:
        report = {
            "ok": False,
            "error": "%s: %s" % (error.__class__.__name__, error),
        }
        exit_code = 1
    with open(report_path, "w", encoding="utf-8") as report_file:
        json.dump(report, report_file, indent=2, sort_keys=True)
    return exit_code


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


def install_confirmation(game_path):
    return (
        "Install the OpenAI TTS mod into:\n\n%s\n\n"
        "Existing mod files will be updated; your config is preserved."
    ) % game_path


def build_argument_parser():
    parser = argparse.ArgumentParser(description="Ren'Py OpenAI TTS Windows installer")
    headless = parser.add_mutually_exclusive_group()
    headless.add_argument("--self-test", action="store_true")
    headless.add_argument("--install-test", metavar="GAME_PATH")
    parser.add_argument("--report")
    return parser


class InstallerApp(object):
    def __init__(self, root):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.root = root
        self.root.title("Ren'Py OpenAI TTS Installer")
        self.root.geometry("780x520")
        self.root.minsize(660, 440)
        self.game_path = tk.StringVar()

        outer = ttk.Frame(root, padding=18)
        outer.pack(fill="both", expand=True)
        ttk.Label(
            outer,
            text="Ren'Py OpenAI TTS Installer",
            font=("Segoe UI", 18, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(
            outer,
            text=(
                "Select the folder containing the game executable, or its inner game folder. "
                "Run the dry run first to preview every file."
            ),
            wraplength=720,
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 16))

        ttk.Label(outer, text="Ren'Py game folder").grid(row=2, column=0, sticky="w")
        self.path_entry = ttk.Entry(outer, textvariable=self.game_path)
        self.path_entry.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4, 10))
        ttk.Button(outer, text="Browse...", command=self.browse).grid(
            row=3,
            column=2,
            sticky="ew",
            padx=(8, 0),
            pady=(4, 10),
        )

        controls = ttk.Frame(outer)
        controls.grid(row=4, column=0, columnspan=3, sticky="w", pady=(0, 12))
        ttk.Button(controls, text="Dry run", command=self.dry_run).pack(side="left")
        ttk.Button(controls, text="Install", command=self.install).pack(side="left", padx=(8, 0))

        output_frame = ttk.Frame(outer)
        output_frame.grid(row=5, column=0, columnspan=3, sticky="nsew")
        self.output = tk.Text(output_frame, wrap="word", state="disabled", font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(output_frame, orient="vertical", command=self.output.yview)
        self.output.configure(yscrollcommand=scrollbar.set)
        self.output.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ttk.Label(
            outer,
            text=(
                "The installer preserves an existing openai_tts_config.json. "
                "API keys are never embedded in this installer."
            ),
            wraplength=720,
        ).grid(row=6, column=0, columnspan=3, sticky="w", pady=(12, 0))

        outer.columnconfigure(0, weight=1)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(5, weight=1)
        self._set_output("Choose a game folder, then click Dry run.")

    def browse(self):
        from tkinter import filedialog

        selected = filedialog.askdirectory(
            parent=self.root,
            title="Select Ren'Py game folder",
            mustexist=True,
        )
        if selected:
            self.game_path.set(selected)

    def dry_run(self):
        self._execute(dry_run=True)

    def install(self):
        from tkinter import messagebox

        path = self.game_path.get().strip()
        if not path:
            messagebox.showerror("Missing game folder", "Select a Ren'Py game folder first.", parent=self.root)
            return
        if not messagebox.askyesno(
            "Install OpenAI TTS mod?",
            install_confirmation(path),
            parent=self.root,
        ):
            return
        self._execute(dry_run=False)

    def _execute(self, dry_run):
        from tkinter import messagebox

        path = self.game_path.get().strip()
        if not path:
            messagebox.showerror("Missing game folder", "Select a Ren'Py game folder first.", parent=self.root)
            return
        try:
            actions = run_install_request(path, dry_run=dry_run)
            result = format_actions(actions, dry_run=dry_run)
        except Exception as error:
            result = "ERROR\n%s: %s" % (error.__class__.__name__, error)
            self._set_output(result)
            messagebox.showerror("Installation failed", str(error), parent=self.root)
            return
        self._set_output(result)
        if not dry_run:
            messagebox.showinfo(
                "Installation complete",
                "The mod was installed. Configure the API key, start the game, and press V.",
                parent=self.root,
            )

    def _set_output(self, text):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")


def main(argv=None):
    arguments = build_argument_parser().parse_args(argv)
    report_path = arguments.report or os.path.join(os.getcwd(), "installer-self-test.json")
    if arguments.self_test:
        return run_self_test(report_path)
    if arguments.install_test:
        return run_install_test(arguments.install_test, report_path)

    import tkinter as tk

    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    InstallerApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
