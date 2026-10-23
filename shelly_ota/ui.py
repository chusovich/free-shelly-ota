"""Terminal output with colors: yellow = warning, orange = critical warning, red = error, green = success.

Colors are added on top of the text only (the words WARNING:, NOTE:, Error:, OK: stay), and only when the output goes to a
terminal. NO_COLOR (https://no-color.org) and --color never switch them off, --color always forces them.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import textwrap
import threading
import time
from typing import Callable, Mapping

RESET = "\033[0m"
YELLOW = "\033[33m"
ORANGE = "\033[38;5;208m"
RED = "\033[31;1m"
GREEN = "\033[32m"
CYAN = "\033[36m"
DIM = "\033[2m"

# A WARNING line that contains one of these is shown in orange: it can brick a device, wipe data or leak credentials.
CRITICAL_WORDS = ("bootloader", "wipes nvs", "credentials in the image", "write to slot", "verification is off")
OK_PREFIXES = ("OK:", "Done:", "Update target slot: 0", "ESPHome config check OK", "Credential check OK",
               "all part hashes OK", "Wrote ", "Stored ")

_enabled = False


def should_color(mode: str, isatty: bool, env: Mapping[str, str]) -> bool:
    """auto: only on a terminal, not with NO_COLOR set, not on TERM=dumb. always/never are forced."""
    if mode == "never":
        return False
    if mode == "always":
        return True
    if env.get("NO_COLOR"):
        return False
    if env.get("TERM") == "dumb":
        return False
    return isatty


def is_enabled() -> bool:
    return _enabled


def why_off(mode: str, isatty: bool, env: Mapping[str, str]) -> str | None:
    """Why colors are off for this mode and environment, or None if they are on."""
    if mode == "never":
        return "--color never"
    if mode == "always":
        return None if _enabled else "the console could not be switched to ANSI colors"
    if env.get("NO_COLOR"):
        return "the NO_COLOR environment variable is set"
    if env.get("TERM") == "dumb":
        return "TERM=dumb"
    if not isatty:
        return "the output is not a terminal (redirected or piped)"
    return None if _enabled else "the console could not be switched to ANSI colors (use Windows Terminal, or --color never)"


def _enable_windows_vt() -> bool:
    """Switch on ANSI escape processing in the Windows console (Windows 10 and newer). False if it is not available."""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        ok = True
        for std in (-11, -12):  # stdout, stderr
            handle = kernel32.GetStdHandle(std)
            mode = ctypes.c_ulong()
            if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                ok = False
                continue
            ok = bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004)) and ok  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        return ok
    except (AttributeError, OSError, ImportError):
        return False


def configure(mode: str = "auto") -> bool:
    """Decide once whether to color. Returns the result."""
    global _enabled
    want = should_color(mode, sys.stdout.isatty(), os.environ)
    if want and os.name == "nt" and mode != "always":
        want = _enable_windows_vt()
    elif want and os.name == "nt":
        _enable_windows_vt()
    _enabled = want
    return _enabled


def color_for(line: str) -> str | None:
    """The color code for a message line, chosen from its prefix (and for warnings from its content)."""
    s = line.lstrip()
    if s.startswith(("Error:", "ERROR")):
        return RED
    if s.startswith(("log|", "free-shelly-ota ")):
        return DIM
    if s.startswith("WARNING"):
        low = s.lower()
        return ORANGE if any(w in low for w in CRITICAL_WORDS) else YELLOW
    if s.startswith("NOTE"):
        return CYAN
    if s.startswith(OK_PREFIXES):
        return GREEN
    return None


LABEL = re.compile(r"\s*(?:Error:|ERROR:?|WARNING:|NOTE:)")
COMMAND = re.compile(r"\s{2,}python ota\.py\b")     # a command to copy, on a line of its own
BOLD = "\033[1m"


def _block(lines: list[str], i: int) -> str:
    """The first sentence of the message that starts at lines[i], continuation lines included (it decides the color of a
    WARNING, so the color does not depend on where the terminal wrapped the line)."""
    text = [lines[i]]
    for line in lines[i + 1:]:
        if not line.strip() or not line.startswith("  ") or COMMAND.match(line) or color_for(line):
            break
        text.append(line)
    joined = " ".join(t.strip() for t in text)
    return re.split(r"(?<=[.!?])\s", joined, maxsplit=1)[0]   # the first sentence: the same whatever the line width


def paint(text: str, enabled: bool | None = None) -> str:
    """Return text with colors, line by line. Only the label of a message (Error:, WARNING:, NOTE:, OK:) is colored, the
    text stays plain, so a long message does not turn the screen red; commands to copy are bold, device log lines dim."""
    if not (_enabled if enabled is None else enabled):
        return text
    lines = text.split("\n")
    out_lines = []
    for i, line in enumerate(lines):
        if not line.strip():
            out_lines.append(line)
        elif COMMAND.match(line):
            out_lines.append(f"{BOLD}{CYAN}{line}{RESET}")
        else:
            code = color_for(_block(lines, i)) if LABEL.match(line) else color_for(line)
            if code is None:
                out_lines.append(line)
            elif code == DIM:
                out_lines.append(f"{code}{line}{RESET}")
            else:
                m = LABEL.match(line)
                if m:
                    end = m.end()
                else:
                    start = len(line) - len(line.lstrip())
                    end = start + len(next(p for p in OK_PREFIXES if line.lstrip().startswith(p)))
                start = len(line) - len(line.lstrip())
                out_lines.append(f"{line[:start]}{code}{line[start:end]}{RESET}{line[end:]}")
    return "\n".join(out_lines)


PROSE = re.compile(r"(?:NOTE|WARNING|Error):\s*")
LIST_ITEM = re.compile(r"\s*(?:[-*]|\d+\.)\s")


MAX_WIDTH = 140   # wider lines are hard to read, even on a very wide terminal
MIN_TAIL = 20     # a wrapped message does not end in a shorter last line than this, if a slightly narrower wrap avoids it


def width() -> int:
    """Line width for messages and help: the terminal's, but not wider than MAX_WIDTH and not narrower than 60."""
    return max(60, min(shutil.get_terminal_size((100, 24)).columns - 2, MAX_WIDTH))


PUNCTUATION = ".;:!?,)"   # a line prefers to end after one of these (followed by a space), if it is not much shorter
MIN_FILL = 0.55           # ... but only when the line is at least this full


def _wrap_at_punctuation(text: str, columns: int, initial_indent: str = "", subsequent_indent: str = "") -> list[str]:
    """Greedy wrap that ends a line after the last punctuation mark in its right part, so lines break between clauses."""
    kw = dict(break_long_words=False, break_on_hyphens=False)
    lines, rest, indent = [], text.strip(), initial_indent
    while rest:
        wrapped = textwrap.wrap(rest, columns, initial_indent=indent, subsequent_indent=indent, **kw)
        chunk = wrapped[0][len(indent):]
        if len(wrapped) > 1:
            cuts = [i + 1 for i, c in enumerate(chunk[:-1]) if c in PUNCTUATION and chunk[i + 1] == " "]
            cuts = [n for n in cuts if len(indent) + n >= columns * MIN_FILL]
            if cuts:
                chunk = chunk[:cuts[-1]]
        lines.append(indent + chunk)
        rest = rest[len(chunk):].lstrip()
        indent = subsequent_indent
    return lines or [""]


def _wrap(text: str, columns: int, **kw) -> list[str]:
    """Wrap at punctuation; avoids a last line of one or two words ('S).') by trying up to 25 % narrower lines first."""
    best = _wrap_at_punctuation(text, columns, **kw)
    for narrower in range(columns - 1, int(columns * 0.75), -1):
        if len(best) < 2 or len(best[-1].strip()) >= MIN_TAIL:
            break
        lines = _wrap_at_punctuation(text, narrower, **kw)
        if len(lines) <= len(best) and len(lines[-1].strip()) > len(best[-1].strip()):
            best = lines
    return best


def reflow(text: str, columns: int) -> str:
    """Wrap NOTE:/WARNING:/Error: messages to `columns`.

    A message that fits on one line stays 'NOTE: text'. A longer one (or one with a command or a list) gets its label on a
    line of its own and the text below it, indented by two. Lines that were broken by hand in the source are joined first,
    so they leave no short leftovers; a command (`python ota.py ...`) stays on one line of its own, never wrapped.
    Everything else (tables, log| lines, paths) is left alone.
    """
    out, lines, i = [], text.split("\n"), 0
    while i < len(lines):
        head = PROSE.match(lines[i])
        if not head:
            out.append(lines[i])
            i += 1
            continue
        label, first = head.group(0).strip(), lines[i][len(head.group(0)):].strip()
        end, last = i + 1, i
        while end < len(lines) and (not lines[end].strip() or lines[end].startswith("  ")) \
                and not lines[end].lstrip().startswith("log|"):
            if lines[end].strip():
                last = end
            end += 1
        parts, para = [], []                              # what follows the first line: paragraphs, commands, list items

        def flush():
            if para:
                parts.append(("para", " ".join(para)))
                para.clear()

        for line in lines[i + 1:last + 1]:
            if not line.strip():
                flush()
                parts.append(("blank", ""))
            elif COMMAND.match(line):
                flush()
                parts.append(("cmd", line.strip()))
            elif LIST_ITEM.match(line):
                flush()
                parts.append(("item", line.strip()))
            elif parts and parts[-1][0] == "item" and not para:
                parts[-1] = ("item", parts[-1][1] + " " + line.strip())
            else:
                para.append(line.strip())
        flush()
        if parts and parts[0][0] == "para":                # goes on right under the first line: one paragraph
            first = (first + " " + parts.pop(0)[1]).strip()
        i = last + 1
        if not parts and len(label) + 1 + len(first) <= columns:
            out.append(f"{label} {first}".rstrip())
            continue
        out.append(label)
        indent = "  "
        if first:
            out += _wrap(first, columns, initial_indent=indent, subsequent_indent=indent)
        for kind, value in parts:
            if kind == "blank":
                out.append("")
            elif kind == "cmd":
                out.append(indent + "  " + value)
            elif kind == "item":
                marker = value.split(" ", 1)[0]
                out += _wrap(value, columns, initial_indent=indent, subsequent_indent=indent + " " * (len(marker) + 1))
            else:
                out += _wrap(value, columns, initial_indent=indent, subsequent_indent=indent)
    return "\n".join(out)


_lock = threading.RLock()      # the device log is printed from a reader thread, messages from the main thread
_live_text: str | None = None  # the line that stays at the bottom of the screen (timer, progress), without its newline
_live_drawn = 0                # how many characters of it are on the screen
_progress_step: dict[str, int] = {}
_progress_start: dict[str, tuple[float, int]] = {}   # label -> (time, percent) of the first value of this run
_clock = time.monotonic


def _wipe() -> None:
    """Erase the live line (the caller holds the lock). Plain spaces, so it also works without ANSI."""
    global _live_drawn
    if _live_drawn:
        sys.stdout.write("\r" + " " * _live_drawn + "\r")
        _live_drawn = 0


def _draw() -> None:
    global _live_drawn
    if _live_text is not None:
        sys.stdout.write(_live_text)
        _live_drawn = len(_live_text)
        sys.stdout.flush()


def say(text: str = "", end: str = "\n") -> None:
    """print() for messages; on a terminal long NOTE/WARNING/Error messages are wrapped to its width.

    A live line is wiped before the message and drawn again below it, so it stays at the bottom.
    """
    with _lock:
        _wipe()
        if sys.stdout.isatty():
            text = reflow(text, width())
        print(paint(text), end=end)
        if end.endswith("\n"):
            _draw()


def live(text: str) -> None:
    """Show `text` as the one line at the bottom that is replaced in place. Only on a terminal; otherwise nothing."""
    global _live_text
    if not sys.stdout.isatty():
        return
    with _lock:
        _wipe()
        _live_text = text[:max(20, shutil.get_terminal_size((100, 24)).columns - 1)]
        _draw()


def live_end(final: str | None = None) -> None:
    """Remove the live line; `final` (if given) is printed in its place and stays."""
    global _live_text
    with _lock:
        _wipe()
        _live_text = None
        if final is not None:
            say(final)
        sys.stdout.flush()


def duration(seconds: float) -> str:
    """'45 s', '14 min', '1 h 5 min': a time span for people."""
    seconds = int(round(seconds))
    if seconds < 90:
        return f"{seconds} s"
    if seconds < 3600:
        return f"{round(seconds / 60)} min"
    hours, minutes = divmod(round(seconds / 60), 60)
    return f"{hours} h {minutes} min" if minutes else f"{hours} h"


def countdown(seconds: float, label: str = "Waiting", sleep: Callable[[float], None] = time.sleep,
              out: Callable[[str], None] | None = None) -> None:
    """Count down `seconds` in half-second steps (Ctrl+C works at once). On a terminal one line is updated every second;
    otherwise (or with `out`) one line every 30 s, counted from the start. Ctrl+C removes the line and goes on to the caller."""
    on_screen = out is None and sys.stdout.isatty()
    try:
        for step in range(int(seconds * 2)):
            left = max(seconds - step / 2, 0)
            text = f"{label} ... {left:.0f} s left (Ctrl+C to stop)"
            if on_screen:
                if step % 2 == 0:
                    live(text)
            elif step % 60 == 0:
                (out or say)(text)
            sleep(0.5)
    finally:
        if on_screen:
            live_end()


def progress(label: str, percent: int, out: Callable[[str], None] | None = None) -> None:
    """'label [#####---------------]  25 %': one live line on a terminal (it stays as the last line at 100 %).

    Without a terminal, or when `out` is given, it is one line per 10 % instead, so a log file or a test does not fill up.
    """
    percent = max(0, min(100, int(percent)))
    if out is None and sys.stdout.isatty():
        filled = percent * 20 // 100
        text = f"{label} [{'#' * filled}{'-' * (20 - filled)}] {percent:3d} %"
        with _lock:
            now = _clock()
            first = _progress_start.get(label)
            if first is None or percent < first[1] or _progress_step.get(label) == 11:
                first = _progress_start[label] = (now, percent)    # a new run
            elif first[1] == 0 and percent > 0:
                first = _progress_start[label] = (now, percent)    # the 0 % mark is the installer getting ready (the bootloader), not the download
            # the speed of this run so far; before 20 % are done the guess is far too high (a log showed 121 s for a real 45 s)
            if first[1] < percent < 100 and percent - first[1] >= 20 and now - first[0] >= 3:
                text += f", about {duration((now - first[0]) * (100 - percent) / (percent - first[1]))} left"
            if percent >= 100:
                if _progress_step.get(label) == 11:
                    return                               # the device logs 100 % twice: the finished line is shown once
                _progress_step[label] = 11
                live_end(text)
            else:
                _progress_step[label] = percent // 10    # a lower value after 100 % starts a new run
                live(text)
        return
    with _lock:
        step = percent // 10
        last = _progress_step.get(label)           # 0..10 = last decile shown, 11 = the 100 % line was shown
        if last is not None and percent < 100 and step < last:
            last = None                              # a new run started again from a lower value
        if last is not None and (last == 11 if percent >= 100 else step <= last):
            return
        _progress_step[label] = 11 if percent >= 100 else step
        (out or say)(f"{label}: {percent} %")


def error(message: str) -> str:
    """The 'Error: ...' text for sys.exit(), colored when stderr is a terminal and colors are on."""
    text = f"Error: {message}"
    if sys.stderr.isatty():
        text = reflow(text, width())
    return paint(text, enabled=_enabled and sys.stderr.isatty())     # label and command colored, not the whole text
