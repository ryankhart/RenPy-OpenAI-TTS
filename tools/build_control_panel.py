from __future__ import print_function, unicode_literals

import hashlib
import os


CONTROL_PANEL_NAME = "OpenAI TTS Control Panel"


def pyinstaller_arguments(project_root):
    project_root = os.path.abspath(project_root)
    return [
        "--onefile",
        "--windowed",
        "--clean",
        "--noconfirm",
        "--name",
        CONTROL_PANEL_NAME,
        "--distpath",
        os.path.join(project_root, "dist"),
        "--workpath",
        os.path.join(project_root, "build", "control-panel"),
        "--specpath",
        os.path.join(project_root, "build", "control-panel"),
        "--paths",
        os.path.join(project_root, "game"),
        os.path.join(project_root, "control_panel.py"),
    ]


def build_control_panel(project_root=None):
    if project_root is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    from PyInstaller.__main__ import run

    run(pyinstaller_arguments(project_root))
    output = os.path.join(project_root, "dist", CONTROL_PANEL_NAME + ".exe")
    if not os.path.isfile(output):
        raise RuntimeError("PyInstaller did not create %s" % output)
    return output


def main():
    output = build_control_panel()
    with open(output, "rb") as executable:
        digest = hashlib.sha256(executable.read()).hexdigest()
    print("%s  %s" % (digest, output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
