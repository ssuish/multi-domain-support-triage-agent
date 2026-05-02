import os
import unittest

import agent_triager.tools.get_files_info as get_files_info_mod
from agent_triager.tools.get_files_info import get_files_info

_REPO_DATA = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data")
)


class TestGetFilesInfo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_working_dir = get_files_info_mod.WORKING_DIR
        get_files_info_mod.WORKING_DIR = _REPO_DATA

    @classmethod
    def tearDownClass(cls):
        get_files_info_mod.WORKING_DIR = cls._orig_working_dir

    def test_current_dir(self):
        result = get_files_info(".")
        self.assertIsNotNone(result)
        self.assertIn("visa", result)
        self.assertIn("hackerrank", result)
        self.assertIn("claude", result)

    def test_visa_dir(self):
        result = get_files_info("visa")
        self.assertIsNotNone(result)
        self.assertIn("support.md", result)
        self.assertIn("index.md", result)
        self.assertIn("support", result)

    def test_file_path_raises_not_a_directory(self):
        with self.assertRaises(Exception) as ctx:
            get_files_info("visa/support.md")
        self.assertIn("is not a directory", str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
