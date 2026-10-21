"""Terminal output with colors: yellow = warning, orange = critical warning, red = error, green = success.

Colors are added on top of the text only (the words WARNING:, NOTE:, Error:, OK: stay), and only when the output goes to a
terminal. NO_COLOR (https://no-color.org) and --color never switch them off, --color always forces them.
"""

from __future__ import annotations

import os
import sys
import threading
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


def paint(text: str, enabled: bool | None = None) -> str:
    """Return text with colors, line by line. A continuation line (indented, no prefix of its own) keeps the color of the line above."""
    if not (_enabled if enabled is None else enabled):
        return text
    out_lines, current = [], None
    for line in text.split("\n"):
        code = color_for(line)
        if code is None and current is not None and line.startswith("  ") and line.strip():
            code = current
        current = code
        out_lines.append(f"{code}{line}{RESET}" if code and line.strip() else line)
    return "\n".join(out_lines)


_lock = threading.RLock()      # the device log is printed from a reader thread, messages from the main thread
_progress_open = False         # a progress line without its newline is on the screen
_progress_step: dict[str, int] = {}
_PROGRESS_WIDTH = 60


def _clear_progress() -> None:
    global _progress_open
    if _progress_open:
        sys.stdout.write("\r" + " " * _PROGRESS_WIDTH + "\r")
        _progress_open = False


def say(text: str = "", end: str = "\n") -> None:
    """print() for messages. A progress line that is still open is wiped first, so nothing is printed over it."""
    with _lock:
        _clear_progress()
        print(paint(text), end=end)


def progress(label: str, percent: int, out: Callable[[str], None] | None = None) -> None:
    """Show 'label [#####-----]  49 %'.

    On a terminal (out is None) this is one line that is updated in place. Without a terminal, or when out is given,
    it is one line per 10 % instead, so a log file or a test does not fill up with every step.
    """
    global _progress_open
    percent = max(0, min(100, int(percent)))
    with _lock:
        if out is None and sys.stdout.isatty():
            filled = percent * 20 // 100
            line = f"{label} [{'#' * filled}{'-' * (20 - filled)}] {percent:3d} %"
            sys.stdout.write("\r" + line.ljust(_PROGRESS_WIDTH))
            if percent >= 100:
                sys.stdout.write("\n")
                _progress_open = False
            else:
                _progress_open = True
            sys.stdout.flush()
            return
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
    return f"{RED}{text}{RESET}" if _enabled and sys.stderr.isatty() else text
