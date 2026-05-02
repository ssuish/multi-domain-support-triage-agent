import os
import unittest

import agent_triager.tools.get_file_content as get_file_content_mod
from agent_triager.tools.get_file_content import get_file_content
from config import CHARACTER_LIMIT

_REPO_DATA = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data")
)


class TestGetFileContent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_working_dir = get_file_content_mod.WORKING_DIR
        get_file_content_mod.WORKING_DIR = _REPO_DATA

    @classmethod
    def tearDownClass(cls):
        get_file_content_mod.WORKING_DIR = cls._orig_working_dir

    def test_truncation_message_when_file_exceeds_character_limit(self):
        print("Results for current directory")
        result = get_file_content("visa/support.md")
        content = result.split("[...")[0] if "[..." in result else result

        self.assertEqual(len(content), CHARACTER_LIMIT)
        if "[..." in result:
            self.assertIn("truncated", result)

    def test_short_file_returns_full_content_without_truncation(self):
        print("Results for current directory")
        result = get_file_content(
            "visa/support/small-business/dispute-resolution.md",
        )

        content = result.split("[...")[0] if "[..." in result else result

        self.assertNotEqual(len(content), CHARACTER_LIMIT)
        if "[..." in result:
            self.assertIn("truncated", result)

    def test_file_in_nested_path_returns_content_below_limit(self):
        print("Results for current directory")
        result = get_file_content(
            "visa/support/small-business/dispute-resolution.md",
        )
        content = result.split("[...")[0] if "[..." in result else result

        self.assertNotEqual(len(content), CHARACTER_LIMIT)
        if "[..." in result:
            self.assertIn("truncated", result)

    def test_raises_when_file_path_outside_working_directory(self):
        print("Results for current directory")

        with self.assertRaises(Exception) as ctx:
            get_file_content("../code/something.txt")
        print(ctx.exception, "\n")
        self.assertIn("Error:", str(ctx.exception))

    def test_raises_when_file_does_not_exist(self):
        print("Results for current directory")
        with self.assertRaises(Exception) as ctx:
            get_file_content("visa/does_not_exist.py")
        print(ctx.exception, "\n")
        self.assertIn("Error:", str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
