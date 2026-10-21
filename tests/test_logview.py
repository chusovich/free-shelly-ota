"""The device log made readable: entries, rules, levels, progress and the log file.

The fixture is the log of a real update of a Multicolor Bulb Gen3 (device ID, MAC and addresses replaced). Run from ShellyOTA/:
python -m unittest discover tests
"""

import io
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shelly_ota import logview, ui  # noqa: E402
from shelly_ota.logview import Level  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "rgbcct_update.devlog.txt"
DEVICE = "shellycolorblbg3-aabbccddeeff"


def datagrams() -> list[str]:
    return [line[len("  log| "):] for line in FIXTURE.read_text(encoding="utf-8").splitlines() if line.strip()]


def records() -> list[logview.LogRecord]:
    items = [item for text in datagrams() for item in logview.split_records(text, DEVICE)]
    assert all(isinstance(i, logview.LogRecord) for i in items), "the fixture has text that is not an entry"
    return items


def replay_into(level: Level, **kw):
    lines: list[str] = []
    session = logview.Session(level=level, out=lines.append, **kw)
    for text in datagrams():
        session.device(text)
    return session, lines


class SplitTests(unittest.TestCase):
    def test_every_datagram_is_cut_into_its_entries(self):
        for text in datagrams():
            items = logview.split_records(text, DEVICE)
            self.assertTrue(items)
            self.assertTrue(all(isinstance(i, logview.LogRecord) for i in items), text)
            self.assertEqual(len(items), text.count(DEVICE + " "), text)
            self.assertEqual("".join(i.raw for i in items), text.strip())     # nothing lost, nothing added

    def test_numbers_run_through_the_whole_log(self):
        seqs = [r.seq for r in records()]
        self.assertEqual(seqs, sorted(seqs))
        self.assertEqual((seqs[0], seqs[-1]), (94, 176))
        self.assertEqual(len(seqs), 75)                       # the real log has gaps: UDP drops datagrams

    def test_fields_of_an_entry(self):
        r = logview.split_records(datagrams()[0], DEVICE)[0]
        self.assertEqual((r.seq, r.uptime, r.severity, r.source), (94, 105.130, 2, "shos_rpc_inst.c:241"))
        self.assertTrue(r.message.startswith("Sys.SetConfig [1@] via HTTP_in POST from 192.0.2.10"))
        self.assertTrue(r.message.endswith("via ws0"))          # the next entry was cut off exactly there

    def test_text_that_is_not_an_entry_is_kept(self):
        self.assertEqual(logview.split_records("hello", DEVICE), ["hello"])
        self.assertEqual(logview.split_records("  \n", DEVICE), [])
        entry = f"{DEVICE} 1 1.000 2 2|a.c:1 hi"
        items = logview.split_records("junk " + entry, DEVICE)
        self.assertEqual(items[0], "junk")
        self.assertIsInstance(items[1], logview.LogRecord)

    def test_the_device_id_is_learned_from_the_first_entry(self):
        session = logview.Session(level=Level.debug, out=lambda t: None)
        self.assertIsNone(session.device_id)
        session.device(datagrams()[0])
        self.assertEqual(session.device_id, DEVICE)


class RuleTests(unittest.TestCase):
    def setUp(self):
        self.entries = [(r, logview.classify(r)) for r in records()]

    def texts(self, kind):
        return [e.text for _, e in self.entries if e.kind == kind]

    def test_progress_runs_from_0_to_100(self):
        percents = [e.percent for _, e in self.entries if e.kind == "progress"]
        self.assertEqual((percents[0], percents[-1]), (0, 100))
        self.assertEqual(percents, sorted(percents))
        self.assertEqual({0, 1, 6, 49, 94, 99, 100} - set(percents), set())

    def test_the_lines_the_device_pages_ask_for(self):
        milestones = self.texts("milestone")
        self.assertIn("The installer writes to slot 0", milestones)
        self.assertIn("The bootloader will be replaced (current 010002ff, minimum 010009ff)", milestones)
        self.assertIn("Installing the bootloader (20960 bytes)", milestones)
        self.assertIn("The installer's target slot: 0", milestones)

    def test_the_efuse_lines_are_a_known_note_and_not_errors(self):
        self.assertEqual([e.kind for r, e in self.entries if "efuse" in r.source.lower() or "EFUSE" in r.message
                          or "FW signatures: want" in r.message], ["known"] * 5)
        self.assertFalse([r.message for r, e in self.entries if e.kind in ("error", "warn")])
        self.assertTrue(all(e.key == "efuse" for _, e in self.entries if e.kind == "known"))

    def test_the_result_is_a_success(self):
        self.assertEqual(sum(e.kind == "result_ok" for _, e in self.entries), 1)
        self.assertEqual(sum(e.kind == "result_error" for _, e in self.entries), 0)

    def test_rpc_requests_of_other_clients_are_recognised_and_readable(self):
        rpc = self.texts("rpc")
        self.assertIn("RPC Shelly.GetStatus <- 192.0.2.30:47470", rpc)
        self.assertEqual(len(rpc), 17)

    def test_a_bootloader_that_is_not_replaced_is_a_warning(self):
        r = logview.split_records(f"{DEVICE} 5 9.000 2 2|2xx_ota_backend.cpp:689 Boot: cur 010003ff, new 00000000, "
                                  f"min 010002ff, update? 0", DEVICE)[0]
        e = logview.classify(r)
        self.assertEqual((e.kind, e.level), ("warn", Level.normal))
        self.assertIn("NOT be replaced", e.text)

    def test_unknown_entries_follow_the_severity(self):
        def kind(sev):
            r = logview.split_records(f"{DEVICE} 5 9.000 2 {sev}|x.c:1 something new", DEVICE)[0]
            return logview.classify(r)
        self.assertEqual(kind(0).kind, "error")
        self.assertEqual(kind(1).kind, "warn")
        self.assertEqual((kind(2).kind, kind(2).level), ("info", Level.debug))
        self.assertIn("x.c:1: something new", kind(0).text)

    def test_an_error_event_is_an_error(self):
        """The name ota_error is an assumption (not seen yet); any event with 'error' in it counts."""
        for body in ('{"event":"ota_error","msg":"flash write failed"}', '{"event":"ota_progress","msg":"error"}'):
            r = logview.split_records(f'{DEVICE} 5 9.000 2 2|y_notifications.cpp:213 Event from sys: {body}', DEVICE)[0]
            self.assertEqual(logview.classify(r).kind, "result_error")


class LevelTests(unittest.TestCase):
    def setUp(self):
        ui._progress_step.clear()

    def test_quiet_shows_nothing_when_all_went_well(self):
        session, lines = replay_into(Level.quiet)
        self.assertEqual(lines, [])
        self.assertEqual(session.result, "ok")

    def test_normal_shows_the_key_lines_and_the_progress_once_each(self):
        session, lines = replay_into(Level.normal)
        self.assertEqual([l for l in lines if l.startswith("Update:")],
                         [f"Update: {p} %" for p in (0, 11, 21, 31, 41, 54, 64, 74, 84, 94, 100)])
        self.assertIn("Device: The update started", lines)
        self.assertIn("Device: The installer writes to slot 0", lines)
        self.assertIn("Device: The bootloader will be replaced (current 010002ff, minimum 010009ff)", lines)
        self.assertEqual(sum(l.startswith("NOTE: The installer logs refused eFuse writes") for l in lines), 1)
        self.assertFalse([l for l in lines if l.startswith("  log|")], "no raw entries at normal")
        self.assertFalse([l for l in lines if "RPC" in l])
        session.summary()
        self.assertTrue(lines[-1].startswith("Device log: ") and "more entries hidden" in lines[-1], lines[-1])

    def test_verbose_adds_every_step_of_the_update_but_not_the_noise(self):
        session, lines = replay_into(Level.verbose)
        for text in ("Device: The device starts downloading the ZIP", "Device: The installer's target slot: 0",
                     "Device: The device sees the package RGBCCTBulbG3 2.0.1",
                     "Device: The installer reports success; the device reboots", "Device: The device reboots in 1000 ms",
                     "Device: The device restarts in 756 ms"):
            self.assertIn(text, lines)
        self.assertFalse([l for l in lines if "RPC" in l or l.startswith("  log|")])
        session.summary()
        self.assertIn("hidden 17 RPC requests", lines[-1])

    def test_debug_shows_every_entry_on_its_own_line(self):
        session, lines = replay_into(Level.debug)
        self.assertEqual(len(lines), len(records()))
        self.assertTrue(all(l.startswith("  log| ") for l in lines))
        boot = next(l for l in lines if "Boot: cur" in l)
        self.assertEqual(re.sub(r" +", " ", boot), " log| 110.324 2xx_ota_backend.cpp:689 Boot: cur 010002ff, new 00000000, "
                                                   "min 010009ff, update? 1")
        self.assertTrue(any("RPC Shelly.GetStatus <- 192.0.2.30:47470" in l for l in lines))
        self.assertEqual(sum(" ERR " in l for l in lines), 4)        # the four eFuse errors
        self.assertEqual(sum(" WRN " in l for l in lines), 1)        # "FW signatures: want 07 got 00"

    def test_raw_is_the_old_output(self):
        session, lines = replay_into(Level.raw)
        self.assertEqual(lines, [f"  log| {t}" for t in datagrams()])
        self.assertEqual(session.result, "ok")             # the result is recognised all the same

    def test_tool_messages_follow_the_level(self):
        for level, shown in ((Level.quiet, ["q"]), (Level.normal, ["q", "n"]), (Level.verbose, ["q", "n", "v"]),
                             (Level.debug, ["q", "n", "v", "d"]), (Level.raw, ["q", "n", "v", "d"])):
            lines = []
            session = logview.Session(level=level, out=lines.append)
            for lv, text in ((Level.quiet, "q"), (Level.normal, "n"), (Level.verbose, "v"), (Level.debug, "d")):
                session.say(lv, text)
            self.assertEqual(lines, shown, level)


class FailureTests(unittest.TestCase):
    ERROR = f'{DEVICE} 200 160.000 2 2|y_notifications.cpp:213 Event from sys: {{"event":"ota_error","msg":"flash write failed"}}'

    def test_an_error_event_ends_the_run_and_the_tail_is_printed_even_when_quiet(self):
        lines = []
        session = logview.Session(level=Level.quiet, out=lines.append)
        for text in datagrams()[:12]:
            session.device(text)
        session.device(self.ERROR)
        self.assertTrue(session.finished.is_set())
        self.assertEqual(session.result, "error")
        self.assertIn("flash write failed", session.error_text)
        self.assertEqual(lines, [])                           # nothing shown while it went on
        session.dump_tail()
        self.assertEqual(lines[0], "Last lines of the device log:")
        self.assertTrue(any("flash write failed" in l for l in lines), lines)
        self.assertLessEqual(len(lines), 31)
        lines.clear()
        session.dump_tail()
        self.assertEqual(lines, [])                           # shown once

    def test_an_unknown_error_entry_is_shown_even_when_quiet(self):
        lines = []
        session = logview.Session(level=Level.quiet, out=lines.append)
        session.device(f"{DEVICE} 7 9.000 2 0|flash.c:9 write failed at 0x1000")
        self.assertEqual(lines, ["ERROR: device log: flash.c:9: write failed at 0x1000"])


class FileTests(unittest.TestCase):
    def setUp(self):
        ui._progress_step.clear()
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_the_file_holds_everything_one_entry_per_line_whatever_the_level(self):
        path = self.tmp / "logs" / "run.send.log"                 # the folder is created
        logfile = logview.LogFile(path)
        session, lines = replay_into(Level.quiet, logfile=logfile)
        session.say(Level.verbose, "ZIP: t.zip")
        session.close()
        self.assertEqual(lines, [])
        text = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(sum(re.match(r"\d\d:\d\d:\d\d\.\d{3} dev \| ", l) is not None for l in text), len(records()))
        self.assertTrue(any(re.match(r"\d\d:\d\d:\d\d\.\d{3} tool\| ZIP: t.zip$", l) for l in text))
        self.assertTrue(any(l.endswith("Update succeeded (OK), will reboot, uba=3, cd=90/ct=0 s") for l in text))

    def test_a_saved_file_can_be_replayed(self):
        path = self.tmp / "run.send.log"
        logfile = logview.LogFile(path)
        replay_into(Level.quiet, logfile=logfile)[0].close()
        _, original = replay_into(Level.normal)
        replayed = []
        session = logview.Session(level=Level.normal, out=replayed.append)
        ui._progress_step.clear()
        logview.replay(path, session)
        self.assertEqual(replayed, original)
        self.assertEqual(session.result, "ok")

    def test_the_output_of_raw_can_be_replayed_too(self):
        replayed = []
        session = logview.Session(level=Level.normal, out=replayed.append)
        logview.replay(FIXTURE, session)
        self.assertEqual(session.result, "ok")
        self.assertIn("Device: The installer writes to slot 0", replayed)

    def test_dump_tail_names_the_file(self):
        logfile = logview.LogFile(self.tmp / "x.send.log")
        self.addCleanup(logfile.close)
        lines = []
        session = logview.Session(level=Level.quiet, out=lines.append, logfile=logfile)
        session.dump_tail()
        self.assertEqual(lines, [f"Log file: {logfile.path}"])


class _Tty(io.StringIO):
    def isatty(self):
        return True


class ProgressTests(unittest.TestCase):
    def setUp(self):
        ui._progress_step.clear()
        ui._live_text, ui._live_drawn = None, 0

    def test_on_a_terminal_it_is_one_line_that_is_updated(self):
        out = _Tty()
        old, sys.stdout = sys.stdout, out
        try:
            for p in (0, 49, 100):
                ui.progress("Update", p)
        finally:
            sys.stdout = old
        text = out.getvalue()
        self.assertEqual(text.count("\n"), 1)                       # only the 100 % line is ended
        self.assertIn("Update [#########-----------]  49 %", text)
        self.assertTrue(text.endswith("Update [####################] 100 %\n"))

    def test_a_message_wipes_the_progress_line_and_it_is_drawn_again_below(self):
        out = _Tty()
        old, sys.stdout = sys.stdout, out
        try:
            ui.progress("Update", 49)
            self.assertIsNotNone(ui._live_text)
            out.seek(0)
            out.truncate()
            ui.say("WARNING: something")
        finally:
            sys.stdout = old
        text = out.getvalue()
        self.assertTrue(text.startswith("\r"))
        self.assertIn("WARNING: something\n", text)
        self.assertTrue(text.endswith("Update [#########-----------]  49 %"))

    def test_without_a_terminal_it_is_one_line_per_ten_percent(self):
        lines = []
        for p in (0, 3, 9, 10, 15, 99, 100, 100):
            ui.progress("Update", p, lines.append)
        self.assertEqual(lines, ["Update: 0 %", "Update: 10 %", "Update: 99 %", "Update: 100 %"])

    def test_a_second_run_starts_again(self):
        lines = []
        for p in (0, 50, 100, 0, 50, 100):
            ui.progress("Update", p, lines.append)
        self.assertEqual(lines, ["Update: 0 %", "Update: 50 %", "Update: 100 %"] * 2)


if __name__ == "__main__":
    unittest.main()
