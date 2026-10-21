"""Run from ShellyOTA/: python -m unittest discover tests"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shelly_ota import logwatch, sender  # noqa: E402

SKIPPED = "2xx_ota_backend.cpp:689 Boot: cur 010003ff, new 00000000, min 010003ff, update? 0"  # issue #46 (Plus Uni)
WRITTEN = "2xx_ota_backend.cpp:689 Boot: cur 010002ff, new 00000000, min 010009ff, update? 1"  # Mini PM Gen3 report


class ParseTests(unittest.TestCase):
    def test_versions(self):
        self.assertEqual(logwatch.boot_version("010003ff"), "1.0.3")
        self.assertEqual(logwatch.boot_version("010009ff"), "1.0.9")
        self.assertEqual(logwatch.boot_version("00000000"), "0.0.0")

    def test_update_zero(self):
        self.assertEqual(logwatch.parse_boot_line("  log| " + SKIPPED), {"cur": "1.0.3", "min": "1.0.3", "update": False})

    def test_update_one(self):
        self.assertEqual(logwatch.parse_boot_line(WRITTEN), {"cur": "1.0.2", "min": "1.0.9", "update": True})

    def test_other_lines(self):
        self.assertIsNone(logwatch.parse_boot_line("Storing core dumps to app_1 (0x200000)"))
        self.assertIsNone(logwatch.parse_boot_line("Boot: cur 0103, update? 0"))

    def test_warning_text(self):
        w = logwatch.boot_skipped_warning(logwatch.parse_boot_line(SKIPPED))
        self.assertTrue(w.startswith("WARNING: ESPHome's bootloader was NOT written"))
        for part in ("1.0.3", "--boot-min-version", "1.0.9", "boot_min_version:"):
            self.assertIn(part, w)

    def test_warning_is_orange(self):
        from shelly_ota import ui
        w = logwatch.boot_skipped_warning(logwatch.parse_boot_line(SKIPPED))
        self.assertEqual(ui.color_for(w), ui.ORANGE)


class BootWatchTests(unittest.TestCase):
    def feed(self, lines, expect_new_loader=True):
        out = []
        bw = sender.BootWatch(out.append, expect_new_loader)
        for line in lines:
            bw.feed(f"  log| {line}")
        return bw, out

    def test_update_zero_warns_once(self):
        bw, out = self.feed([SKIPPED, SKIPPED])
        self.assertTrue(bw.skipped)
        self.assertEqual([m for m in out if m.startswith("WARNING")].__len__(), 1)

    def test_update_one_is_silent(self):
        bw, out = self.feed([WRITTEN])
        self.assertFalse(bw.skipped)
        self.assertFalse([m for m in out if m.startswith("WARNING")])

    def test_package_keeps_shelly_loader(self):
        bw, out = self.feed([SKIPPED], expect_new_loader=False)
        self.assertFalse(bw.skipped)
        self.assertEqual(len(out), 1)


class SettleTests(unittest.TestCase):
    """The wait after a fresh start: one live line on the command line, lines every 30 s otherwise."""

    def settle(self, uptime, answer="yes", live=False, screen=None):
        from unittest import mock
        said, sleeps = [], []
        with mock.patch.object(sender, "device_uptime", return_value=uptime):
            if screen is not None:
                with mock.patch("sys.stdout", screen):
                    sender._settle("x", {}, say=lambda level, text: said.append(text), ask=lambda prompt: answer,
                                   sleep=sleeps.append, dry_run=False, assume_yes=False, live=live)
            else:
                sender._settle("x", {}, say=lambda level, text: said.append(text), ask=lambda prompt: answer,
                               sleep=sleeps.append, dry_run=False, assume_yes=False, live=live)
        return said, sleeps

    def test_a_settled_device_is_left_alone(self):
        self.assertEqual(self.settle(300), ([], []))

    def test_saying_no_does_not_wait(self):
        said, sleeps = self.settle(57, answer="no")
        self.assertEqual(sleeps, [])
        self.assertTrue(any("Not waiting" in l for l in said), said)

    def test_on_the_command_line_the_countdown_is_one_live_line(self):
        import io

        class Tty(io.StringIO):
            def isatty(self):
                return True

        screen = Tty()
        said, sleeps = self.settle(57, live=True, screen=screen)
        text = screen.getvalue()
        self.assertIn("Waiting ... 68 s left", text)
        self.assertIn("Waiting ... 1 s left", text)
        self.assertFalse(any(l.startswith("Waiting") for l in said), said)
        self.assertEqual(len(sleeps), 136)                       # half-second steps


if __name__ == "__main__":
    unittest.main()
