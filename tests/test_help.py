"""Run from ShellyOTA/: python -m unittest discover tests

The help of ota.py: every command is listed in a group, every command has a working -h, the device list is shown once
and no line is wider than the terminal.
"""

import argparse
import contextlib
import io
import os
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ota  # noqa: E402
from shelly_ota import profile  # noqa: E402

COLUMNS = 100


def help_of(*argv):
    """(exit code, text) of `ota.py <argv> -h` in a terminal COLUMNS wide."""
    out = io.StringIO()
    with mock.patch.dict(os.environ, {"COLUMNS": str(COLUMNS)}), contextlib.redirect_stdout(out):
        try:
            ota.build_parser().parse_args([*argv, "-h"])
        except SystemExit as e:
            return e.code, out.getvalue()
    raise AssertionError("-h did not exit")


class HelpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code, cls.top = help_of()
        sub = next(a for a in ota.build_parser()._actions if isinstance(a, argparse._SubParsersAction))
        cls.commands = list(sub.choices)

    def test_every_command_is_in_exactly_one_group(self):
        listed = [name for _, items in ota.COMMANDS for name, _ in items]
        self.assertEqual(sorted(listed), sorted(self.commands))
        self.assertEqual(len(listed), len(set(listed)))

    def test_top_help_shows_the_groups_and_commands(self):
        self.assertEqual(self.code, 0)
        for group, items in ota.COMMANDS:
            self.assertRegex(self.top, rf"(?m)^  {group}$")
            for name, _ in items:
                self.assertRegex(self.top, rf"(?m)^    {re.escape(name)}\s")

    def test_top_help_lists_every_device(self):
        tail = self.top[self.top.index("devices:"):]
        for name in profile.list_devices():
            self.assertIn(name, tail)

    def test_every_command_has_a_working_help(self):
        for name in self.commands:
            code, text = help_of(name)
            self.assertEqual(code, 0, name)
            self.assertTrue(text.startswith(f"usage: ota.py {name}"), name)

    def test_command_help_does_not_repeat_the_device_list(self):
        for name in ("fetch", "build", "send", "restore", "partition-csv"):
            _, text = help_of(name)
            self.assertNotIn("Mini1PMG4ZB", text, name)

    def test_send_options_are_in_groups(self):
        _, text = help_of("send")
        for title in ("the Shelly:", "this PC:", "what to do:"):
            self.assertIn(title, text)

    def test_nothing_is_wider_than_the_terminal(self):
        for argv in [()] + [(name,) for name in self.commands]:
            _, text = help_of(*argv)
            for line in text.splitlines():
                self.assertLessEqual(len(line), COLUMNS, f"{argv}: {line}")


if __name__ == "__main__":
    unittest.main()
