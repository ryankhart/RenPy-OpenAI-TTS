from __future__ import print_function, unicode_literals

import hashlib
import os


INSTALLER_NAME = "RenPy-OpenAI-TTS-Installer"


def pyinstaller_arguments(project_root):
    project_root = os.path.abspath(project_root)
    return [
        "--onefile",
        "--windowed",
        "--clean",
        "--noconfirm",
        "--name",
        INSTALLER_NAME,
        "--distpath",
        os.path.join(project_root, "dist"),
        "--workpath",
        os.path.join(project_root, "build", "gui-installer"),
        "--specpath",
        os.path.join(project_root, "build", "gui-installer"),
        "--add-data",
        os.path.join(project_root, "game") + ";game",
        os.path.join(project_root, "gui_installer.py"),
    ]


def build_installer(project_root=None):
    if project_root is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    from PyInstaller.__main__ import run

    run(pyinstaller_arguments(project_root))
    output = os.path.join(project_root, "dist", INSTALLER_NAME + ".exe")
    if not os.path.isfile(output):
        raise RuntimeError("PyInstaller did not create %s" % output)
    return output


def main():
    output = build_installer()
    with open(output, "rb") as executable:
        digest = hashlib.sha256(executable.read()).hexdigest()
    print("%s  %s" % (digest, output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
