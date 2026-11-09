import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import main  # noqa: E402
from main import (  # noqa: E402
    line_for_user,
    parse_assignments,
    strip_blocked_comment,
)


class UserCommentTests(unittest.TestCase):
    def test_multiline_comment_round_trip(self):
        comment = "Иван\nДал ненадолго"
        line = line_for_user("user", "a" * 32, comment, False)
        self.assertEqual(len(line.splitlines()), 1)
        parsed = parse_assignments(["[access.users]", line], "access.users")
        self.assertEqual(parsed["user"]["comment"], comment)

    def test_legacy_plain_comment_is_unchanged(self):
        parsed = parse_assignments(
            ["[access.users]", 'user = "' + "a" * 32 + '" # old comment'],
            "access.users",
        )
        self.assertEqual(parsed["user"]["comment"], "old comment")

    def test_commented_user_and_unblock_keep_newlines(self):
        comment = "Первая строка\nВторая строка"
        line = line_for_user("user", "a" * 32, comment, True)
        parsed = parse_assignments(["[access.users]", line], "access.users")
        self.assertTrue(parsed["user"]["blocked"])
        self.assertEqual(strip_blocked_comment(parsed["user"]["comment"]), comment)

    def test_marker_text_is_not_mistaken_for_encoding(self):
        comment = "telemt-admin-comment: заметка"
        line = line_for_user("user", "a" * 32, comment, False)
        parsed = parse_assignments(["[access.users]", line], "access.users")
        self.assertEqual(parsed["user"]["comment"], comment)

    def test_save_and_block_preserve_multiline_comment(self):
        config = '[server]\nport = 443\n\n[access.users]\nuser = "' + "a" * 32 + '"\n'
        comment = "Иван\nДал ненадолго"
        for blocked in (False, True):
            data = main.UserInput(name="user", secret="a" * 32, comment=comment, blocked=blocked)
            with patch.object(main, "read_config", return_value=config), patch.object(main, "write_config") as write:
                main.upsert_user(data, old_name="user")
            config = write.call_args.args[0]
            self.assertEqual(parse_assignments(config.splitlines(), "access.users")["user"]["comment"], comment)
        self.assertIn("[access.user_enabled]", config)


if __name__ == "__main__":
    unittest.main()
