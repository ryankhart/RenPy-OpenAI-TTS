from __future__ import print_function, unicode_literals

import hashlib
import os
import sys

MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODULE_ROOT not in sys.path:
    sys.path.insert(0, MODULE_ROOT)

from install import RUNTIME_FILES


INSTALLER_NAME = "RenPy-OpenAI-TTS-Installer"


def pyinstaller_arguments(project_root):
    project_root = os.path.abspath(project_root)
    arguments = [
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
    ]
    for relative_path in RUNTIME_FILES:
        source = os.path.join(project_root, "game", *relative_path.split("/"))
        relative_parent = os.path.dirname(relative_path).replace("\\", "/")
        destination = "game" if not relative_parent else "game/" + relative_parent
        arguments.extend(["--add-data", source + ";" + destination])
    arguments.extend(["--add-data", os.path.join(project_root, "LICENSE") + ";."])
    arguments.append(os.path.join(project_root, "gui_installer.py"))
    return arguments


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
