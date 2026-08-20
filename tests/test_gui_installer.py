from __future__ import unicode_literals

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class GuiInstallerTests(unittest.TestCase):
    def test_project_runtime_bundle_is_complete(self):
        from gui_installer import bundled_runtime_dir, missing_runtime_files

        source_dir = bundled_runtime_dir(ROOT)

        self.assertEqual(source_dir, os.path.join(ROOT, "game"))
        self.assertEqual(missing_runtime_files(source_dir), [])


if __name__ == "__main__":
    unittest.main()
