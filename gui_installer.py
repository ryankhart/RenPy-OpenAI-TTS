from __future__ import print_function, unicode_literals

import os
import sys

from install import RUNTIME_FILES


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
