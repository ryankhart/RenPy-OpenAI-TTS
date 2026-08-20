from __future__ import print_function, unicode_literals

import argparse
import hashlib
import os
import zipfile


RELEASE_FILES = [
    "README.md",
    "install.py",
    "game/openai_tts.rpy",
    "game/openai_tts_config.json.example",
    "game/openai_tts_mod/__init__.py",
    "game/openai_tts_mod/adapter.py",
    "game/openai_tts_mod/core.py",
    "game/openai_tts_mod/cacert.pem",
    "game/openai_tts_mod/CERTIFI_LICENSE.txt",
]
ARCHIVE_ROOT = "RenPy-OpenAI-TTS"


def build_release(output_path, project_root=None):
    if project_root is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    parent = os.path.dirname(os.path.abspath(output_path))
    if not os.path.isdir(parent):
        os.makedirs(parent)

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative_path in RELEASE_FILES:
            source = os.path.join(project_root, *relative_path.split("/"))
            with open(source, "rb") as source_file:
                content = source_file.read()

            archive_name = ARCHIVE_ROOT + "/" + relative_path
            info = zipfile.ZipInfo(archive_name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    with open(output_path, "rb") as release_file:
        return hashlib.sha256(release_file.read()).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the deterministic Ren'Py OpenAI TTS ZIP.")
    parser.add_argument(
        "--output",
        default=os.path.join("dist", "RenPy-OpenAI-TTS-0.1.0.zip"),
    )
    arguments = parser.parse_args(argv)
    digest = build_release(arguments.output)
    print("%s  %s" % (digest, arguments.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
