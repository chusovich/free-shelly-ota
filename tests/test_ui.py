"""Colored messages: when colors are used, and which line gets which color."""

import io
import sys
import threading
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shelly_ota import ui  # noqa: E402


class ShouldColorTests(unittest.TestCase):
    def test_auto_colors_only_on_a_terminal(self):
        self.assertTrue(ui.should_color("auto", True, {}))
        self.assertFalse(ui.should_color("auto", False, {}))

    def test_no_color_and_dumb_terminal_switch_it_off(self):
        self.assertFalse(ui.should_color("auto", True, {"NO_COLOR": "1"}))
        self.assertFalse(ui.should_color("auto", True, {"TERM": "dumb"}))

    def test_always_and_never_are_forced(self):
        self.assertTrue(ui.should_color("always", False, {"NO_COLOR": "1"}))
        self.assertFalse(ui.should_color("never", True, {}))


class ColorForTests(unittest.TestCase):
    def test_levels(self):
        cases = {
            "Error: something broke": ui.RED,
            "WARNING: the update target slot could not be read": ui.YELLOW,
            "  WARNING: Credentials were not checked (give --esphome-yaml ...)": ui.YELLOW,
            "WARNING: this package replaces Shelly's bootloader. If it does not suit the device": ui.ORANGE,
            "WARNING: this wipes NVS (Wi-Fi credentials and settings) and replaces the firmware.": ui.ORANGE,
            "  WARNING: BOOTLOADER REPLACED: the package carries ESPHome's bootloader": ui.ORANGE,
            "WARNING: the installer will write to slot 1, but ESPHome's bootloader starts app_0": ui.ORANGE,
            "WARNING: TLS certificate verification is OFF for this download.": ui.ORANGE,
            "NOTE: ESPHome's bootloader starts app_0": ui.CYAN,
            "OK: I:\\x\\y.zip": ui.GREEN,
            "Update target slot: 0 (the slot ESPHome's bootloader starts).": ui.GREEN,
            "ESPHome config check OK (x.yaml)": ui.GREEN,
            "  Credential check OK: none of 2 known values found in the image": ui.GREEN,
            "  all part hashes OK": ui.GREEN,
            "  log| shellyplugx 0 41.093 2 2|shos_rpc_inst.c:243 Sys.SetConfig": ui.DIM,
            "Device 192.168.33.1: app=PlugMG3": None,
            "Waiting for the device to download the ZIP ...": None,
        }
        for line, code in cases.items():
            self.assertEqual(ui.color_for(line), code, line)


class PaintTests(unittest.TestCase):
    def test_disabled_returns_the_text_unchanged(self):
        text = "WARNING: x\nplain"
        self.assertEqual(ui.paint(text, enabled=False), text)

    def test_enabled_wraps_colored_lines_and_keeps_the_words(self):
        out = ui.paint("OK: done", enabled=True)
        self.assertEqual(out, f"{ui.GREEN}OK:{ui.RESET} done")      # only the label has a color
        self.assertIn("WARNING:", ui.paint("WARNING: careful", enabled=True))

    def test_only_the_label_is_colored_and_the_text_stays_plain(self):
        text = "NOTE: first line\n      continued here\nplain again"
        lines = ui.paint(text, enabled=True).split("\n")
        self.assertEqual(lines[0], f"{ui.CYAN}NOTE:{ui.RESET} first line")
        self.assertEqual(lines[1], "      continued here")
        self.assertEqual(lines[2], "plain again")

    def test_the_color_of_a_warning_follows_its_first_sentence_not_where_the_line_wrapped(self):
        wrapped = "WARNING: this package is special and\n         replaces the bootloader. It is fine."
        self.assertTrue(ui.paint(wrapped, enabled=True).startswith(ui.ORANGE))
        later = "WARNING: this package is fine.\n         It replaces the bootloader."
        self.assertTrue(ui.paint(later, enabled=True).startswith(ui.YELLOW))

    def test_a_command_line_is_bold_and_the_device_log_is_dim(self):
        out = ui.paint("Error: x\n\n         python ota.py restore X\nlog| y", enabled=True).split("\n")
        self.assertEqual(out[2], f"{ui.BOLD}{ui.CYAN}         python ota.py restore X{ui.RESET}")
        self.assertEqual(out[3], f"{ui.DIM}log| y{ui.RESET}")

    def test_blank_lines_are_not_wrapped(self):
        self.assertEqual(ui.paint("NOTE: a\n\nb", enabled=True).split("\n")[1], "")

    def test_an_error_colors_its_label_and_command_but_not_the_whole_text(self):
        with mock.patch("sys.stderr", _Tty()), mock.patch.object(ui, "_enabled", True):
            lines = ui.error("it failed:\n\n  python ota.py restore X\n\n  Then again.").split("\n")
        self.assertEqual(lines[:2], [f"{ui.RED}Error:{ui.RESET}", "  it failed:"])
        self.assertEqual(lines[3], f"{ui.BOLD}{ui.CYAN}    python ota.py restore X{ui.RESET}")
        self.assertEqual(lines[5], "  Then again.")

    def test_error_text_is_plain_without_a_terminal(self):
        self.assertEqual(ui.error("boom"), "Error: boom")   # stderr is not a terminal under the test runner


class ReflowTests(unittest.TestCase):
    def test_a_short_message_stays_on_one_line_with_its_label(self):
        self.assertEqual(ui.reflow("NOTE: the device has been running for only 57 s.", 80),
                         "NOTE: the device has been running for only 57 s.")

    def test_a_long_message_gets_its_label_alone_and_the_text_indented_below(self):
        lines = ui.reflow("NOTE: " + "word " * 30, 40).split("\n")
        self.assertEqual(lines[0], "NOTE:")
        self.assertGreater(len(lines), 3)
        self.assertTrue(all(len(l) <= 40 for l in lines), lines)
        self.assertTrue(all(l.startswith("  ") and not l.startswith("   ") for l in lines[1:]), lines)

    def test_warning_and_error_work_the_same_way(self):
        self.assertEqual(ui.reflow("WARNING: " + "ab " * 40, 40).split("\n")[0], "WARNING:")
        self.assertEqual(ui.reflow("Error: " + "ab " * 40, 40).split("\n")[0], "Error:")

    def test_hand_broken_lines_are_joined_without_short_leftovers(self):
        text = "NOTE: first part of a sentence\n      second part\n      end."
        self.assertEqual(ui.reflow(text, 80), "NOTE: first part of a sentence second part end.")

    def test_a_blank_line_starts_a_new_message(self):
        out = ui.reflow("NOTE: one\n      more\n\nNOTE: two", 80).split("\n")
        self.assertEqual(out, ["NOTE: one more", "", "NOTE: two"])

    def test_list_items_stay_separate_and_are_wrapped_under_the_dash(self):
        text = "Error: check failed:\n  - " + "long " * 20 + "\n  - short"
        lines = ui.reflow(text, 40).split("\n")
        self.assertEqual(lines[:2], ["Error:", "  check failed:"])
        self.assertTrue(lines[2].startswith("  - "))
        self.assertTrue(lines[3].startswith("    ") and not lines[3].startswith("  - "))
        self.assertEqual(lines[-1], "  - short")

    def test_tables_and_device_log_lines_are_left_alone(self):
        text = "  boot     size=  20384  ptn=boot\nlog| " + "x" * 200
        self.assertEqual(ui.reflow(text, 40), text)

    def test_the_last_line_is_not_left_with_a_word_or_two(self):
        text = ("NOTE: ESPHome's bootloader starts app_0 (the installer overwrites otadata), so the installer must write to "
                "slot 0; otherwise the old app in app_0 starts instead (seen on the Power Strip Gen4 and the Plus Plug S).")
        for columns in range(80, 111):
            lines = ui.reflow(text, columns).split("\n")
            self.assertTrue(all(len(l) <= columns for l in lines), columns)
            self.assertGreaterEqual(len(lines[-1].strip()), ui.MIN_TAIL, (columns, lines[-1]))

    def test_lines_break_after_punctuation_when_possible(self):
        text = ("NOTE: first clause is here, second clause follows here, third clause comes after, fourth clause ends "
                "this sentence. Another sentence starts and runs on for a while longer than the line.")
        lines = ui.reflow(text, 60).split("\n")
        self.assertTrue(lines[1].endswith(","), lines)       # not "... second clause follows"
        self.assertTrue(all(len(l) <= 60 for l in lines), lines)

    def test_a_command_stays_on_its_own_line_and_the_text_goes_on_below_it(self):
        text = ("Error: The installer would write to slot 1, so the old firmware would start again. Do this first:\n\n"
                "    python ota.py restore DimmerG4 --ip 192.168.33.1 --option-that-is-long\n\n"
                "  Then send again.")
        lines = ui.reflow(text, 50).split("\n")
        self.assertEqual(lines[0], "Error:")
        self.assertIn("    python ota.py restore DimmerG4 --ip 192.168.33.1 --option-that-is-long", lines)
        self.assertEqual(lines[-1], "  Then send again.")
        self.assertEqual(lines[lines.index("") + 1].strip().split()[0], "python")

    def test_a_long_url_is_not_broken(self):
        url = "http://192.168.33.82:8000/Dimmer0110VPMG4-esphome-softap.ota.zip"
        self.assertIn(url, ui.reflow("NOTE: download from " + url, 40))

    def test_say_does_not_wrap_when_the_output_is_not_a_terminal(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            ui.say("NOTE: " + "word " * 60)
        self.assertEqual(buf.getvalue().count("\n"), 1)

    def test_the_restore_note_fits_a_narrow_terminal(self):
        import ota
        for columns in (60, 80, 120):
            lines = ui.reflow(ota.RESTORE_NOTE, columns).split("\n")
            self.assertTrue(all(len(l) <= columns for l in lines), columns)
            for line in lines:      # a short note on one line, a label alone, or text indented under it: no column-0 leftovers
                self.assertTrue(not line.strip() or line.startswith(("NOTE:", "  ")), (columns, line))
                if line.startswith("NOTE: "):
                    self.assertGreater(len(line), len("NOTE: x"))      # a label is never followed by a fragment


class _Tty(io.StringIO):
    def isatty(self):
        return True


class LiveLineTests(unittest.TestCase):
    def setUp(self):
        ui._live_text, ui._live_drawn = None, 0
        ui._progress_step.clear()
        ui._progress_start.clear()
        self.addCleanup(lambda: (setattr(ui, "_live_text", None), setattr(ui, "_live_drawn", 0), ui._progress_step.clear(), ui._progress_start.clear()))

    def tty(self):
        fake = _Tty()
        patcher = mock.patch("sys.stdout", fake)
        patcher.start()
        self.addCleanup(patcher.stop)
        return fake

    def test_live_replaces_the_line_in_place_without_a_newline(self):
        out = self.tty()
        ui.live("Waiting ... 9 s left")
        ui.live("Waiting ... 8 s left")
        text = out.getvalue()
        self.assertNotIn("\n", text)
        self.assertEqual(text.count("\r"), 2)       # the second call wipes first: \r + spaces + \r, then draws
        self.assertTrue(text.endswith("Waiting ... 8 s left"))

    def test_a_message_wipes_the_line_and_draws_it_again_below(self):
        out = self.tty()
        ui.live("Update [#---] 5 %")
        out.seek(0), out.truncate()
        ui.say("log| something")
        text = out.getvalue()
        self.assertTrue(text.startswith("\r"))
        self.assertIn("log| something\n", text)
        self.assertTrue(text.endswith("Update [#---] 5 %"))

    def test_live_end_leaves_nothing_or_the_final_line(self):
        out = self.tty()
        ui.live("working")
        ui.live_end()
        self.assertIsNone(ui._live_text)
        out.seek(0), out.truncate()
        ui.say("later")
        self.assertEqual(out.getvalue(), "later\n")
        ui.live("again")
        ui.live_end("done: 100 %")
        self.assertTrue(out.getvalue().endswith("done: 100 %\n"))

    def test_live_is_silent_without_a_terminal(self):
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            ui.live("anything")
        self.assertEqual(out.getvalue(), "")

    def test_countdown_updates_one_line_each_second_on_a_terminal(self):
        out = self.tty()
        waited = []
        ui.countdown(5, "Waiting", sleep=waited.append)
        self.assertEqual(waited, [0.5] * 10)
        text = out.getvalue()
        self.assertNotIn("\n", text)
        for left in (5, 4, 3, 2, 1):
            self.assertIn(f"Waiting ... {left} s left", text)
        self.assertIsNone(ui._live_text)

    def test_countdown_without_a_terminal_prints_a_line_per_30_seconds(self):
        lines = []
        ui.countdown(65, "Waiting", sleep=lambda s: None, out=lines.append)
        self.assertEqual(lines, ["Waiting ... 65 s left (Ctrl+C to stop)", "Waiting ... 35 s left (Ctrl+C to stop)",
                                 "Waiting ... 5 s left (Ctrl+C to stop)"])

    def test_ctrl_c_removes_the_countdown_line(self):
        self.tty()

        def stop(_):
            raise KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            ui.countdown(5, "Waiting", sleep=stop)
        self.assertIsNone(ui._live_text)

    def test_progress_without_a_terminal_is_one_line_per_ten_percent(self):
        lines = []
        for pct in (0, 1, 6, 9, 11, 16, 21, 50, 55, 100, 100):
            ui.progress("Update", pct, lines.append)
        self.assertEqual(lines, ["Update: 0 %", "Update: 11 %", "Update: 21 %", "Update: 50 %", "Update: 100 %"])

    def test_a_new_run_after_100_percent_starts_again(self):
        lines = []
        for pct in (100, 0, 100):
            ui.progress("Update", pct, lines.append)
        self.assertEqual(lines, ["Update: 100 %", "Update: 0 %", "Update: 100 %"])

    def test_progress_on_a_terminal_is_a_bar_and_the_100_percent_line_stays(self):
        out = self.tty()
        ui.progress("Update", 50)
        self.assertIn("Update [##########----------]  50 %", out.getvalue())
        ui.progress("Update", 100)
        self.assertTrue(out.getvalue().endswith("Update [####################] 100 %\n"))
        self.assertIsNone(ui._live_text)

    def test_progress_on_a_terminal_estimates_the_time_left_from_its_own_speed(self):
        out = self.tty()
        clock = iter([0.0, 1.0, 10.0, 30.0])
        with mock.patch.object(ui, "_clock", lambda: next(clock)):
            for pct in (10, 12, 30, 60):
                ui.progress("Update", pct)
        text = out.getvalue()
        self.assertNotIn("left", text.split("30 %")[0])           # too early: under 3 s, then under 5 %
        self.assertIn(" 30 %, about 35 s left", text)               # 20 % in 10 s: the 70 % to go take 35 s
        self.assertIn(" 60 %, about 24 s left", text)               # 50 % in 30 s: the 40 % to go take 24 s

    def test_the_device_logging_100_percent_twice_shows_the_finished_line_once(self):
        out = self.tty()
        for pct in (50, 100, 100):
            ui.progress("Update", pct)
        self.assertEqual(out.getvalue().count("100 %"), 1)
        ui.progress("Update", 0)                     # a new run is drawn again
        ui.progress("Update", 100)
        self.assertEqual(out.getvalue().count("100 %"), 2)

    def test_two_threads_do_not_mix_their_output(self):
        out = self.tty()

        def talk(name):
            for i in range(200):
                ui.say(f"{name} line {i:03d}")

        def tick():
            for i in range(200):
                ui.live(f"Update {i:03d}")

        threads = [threading.Thread(target=talk, args=("a",)), threading.Thread(target=talk, args=("b",)),
                   threading.Thread(target=tick)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        ui.live_end()
        full = [l for l in out.getvalue().replace("\r", "\n").split("\n") if l.strip().startswith(("a line", "b line"))]
        self.assertEqual(len(full), 400)
        self.assertTrue(all(len(l.strip()) == len("a line 000") for l in full))


class ColorsCommandTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parent.parent

    def _run(self, *args):
        import os
        import subprocess
        env = {k: v for k, v in os.environ.items() if k not in ("NO_COLOR", "TERM")}   # do not depend on the caller's setup
        return subprocess.run([sys.executable, str(self.ROOT / "ota.py"), *args], capture_output=True, text=True,
                              encoding="utf-8", cwd=self.ROOT, env=env)

    def test_forced_colors_show_every_level(self):
        done = self._run("--color", "always", "colors")
        self.assertEqual(done.returncode, 0, done.stderr)
        for code in (ui.GREEN, ui.CYAN, ui.YELLOW, ui.ORANGE, ui.RED, ui.DIM):
            self.assertIn(code, done.stdout)
        self.assertIn("Colors are ON", done.stdout)

    def test_piped_output_has_no_codes_and_says_why(self):
        done = self._run("colors")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertNotIn("\x1b", done.stdout)
        self.assertIn("Colors are OFF: the output is not a terminal", done.stdout)

    def test_why_off_names_the_reason(self):
        self.assertEqual(ui.why_off("never", True, {}), "--color never")
        self.assertIn("NO_COLOR", ui.why_off("auto", True, {"NO_COLOR": "1"}))
        self.assertIn("TERM=dumb", ui.why_off("auto", True, {"TERM": "dumb"}))
        self.assertIn("not a terminal", ui.why_off("auto", False, {}))

    def test_the_sources_are_plain_ascii(self):
        """A Windows console (cp1252) cannot print characters like arrows; a message with one would crash the command."""
        for path in [self.ROOT / "ota.py", *sorted((self.ROOT / "shelly_ota").glob("*.py"))]:
            try:
                path.read_bytes().decode("ascii")
            except UnicodeDecodeError as e:
                self.fail(f"{path.name} contains a non-ASCII character at byte {e.start}")


if __name__ == "__main__":
    unittest.main()
