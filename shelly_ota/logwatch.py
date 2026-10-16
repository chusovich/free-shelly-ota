"""Read a Shelly's debug log: the device sends it as UDP datagrams to this PC.

Enabled and disabled over RPC (Sys.SetConfig debug.udp.addr). The previous setting is restored.
"""

from __future__ import annotations

import re
import socket
import threading
import time
from contextlib import contextmanager
from typing import Callable

from . import rpc, ui
from .builder import OtaError


# The updater's bootloader decision, e.g. "Boot: cur 010003ff, new 00000000, min 010003ff, update? 0".
# Versions are 0xMMmmpp followed by ff (010003ff = 1.0.3); "update? 1" means it writes the package's bootloader.
BOOT_RE = re.compile(r"Boot: cur ([0-9a-fA-F]{8}), new ([0-9a-fA-F]{8}), min ([0-9a-fA-F]{8}), update\? ([01])")


def boot_version(hex8: str) -> str:
    """'010003ff' -> '1.0.3' (major, minor, patch; the last byte is not part of the version)."""
    v = int(hex8, 16)
    return f"{v >> 24 & 0xFF}.{v >> 16 & 0xFF}.{v >> 8 & 0xFF}"


def parse_boot_line(text: str) -> dict | None:
    """cur/min as versions and update as bool from a device log line, or None if it is not the Boot line."""
    m = BOOT_RE.search(text)
    if not m:
        return None
    return {"cur": boot_version(m.group(1)), "min": boot_version(m.group(3)), "update": m.group(4) == "1"}


def boot_skipped_warning(boot: dict) -> str:
    """The WARNING text for a Boot line with update? 0."""
    return (f"WARNING: ESPHome's bootloader was NOT written: the device keeps Shelly's loader (installed {boot['cur']}, package "
            f"min {boot['min']}, update? 0). Later ESPHome OTAs may not take effect or need several restarts. Build again with "
            f"a higher --boot-min-version (for example 1.0.9) or set boot_min_version: in the profile.")


@contextmanager
def udp_log(addr: str, host: str, port: int, out: Callable[[str], None] = ui.say, **auth):
    """Context manager: forward the device's debug log to out() while the block runs."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("0.0.0.0", port))
    except OSError as e:
        sock.close()
        raise OtaError(f"Cannot listen on UDP port {port}: {e}. Try --log-port.") from e
    sock.settimeout(0.5)
    stop = threading.Event()

    def reader():
        while not stop.is_set():
            try:
                data, _ = sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                return
            for line in data.decode(errors="replace").splitlines():
                out(f"  log| {line}")

    previous = None
    try:
        previous = (rpc.call(addr, "Sys.GetConfig", **auth).get("debug", {}).get("udp") or {}).get("addr")
        result = rpc.call(addr, "Sys.SetConfig", {"config": {"debug": {"udp": {"addr": f"{host}:{port}"}}}}, **auth)
        if result.get("restart_required"):
            out("NOTE: the device wants a restart for the log setting to apply.")
        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        yield
    finally:
        stop.set()
        try:  # best effort: the device may be rebooting or already reflashed
            rpc.call(addr, "Sys.SetConfig", {"config": {"debug": {"udp": {"addr": previous}}}}, **auth)
        except (OtaError, OSError):
            pass
        sock.close()


def watch(addr: str, host: str, port: int, seconds: float | None, out: Callable[[str], None] = ui.say,
          **auth) -> None:
    """Print the device log for `seconds` (until Ctrl+C if None)."""
    with udp_log(addr, host, port, out, **auth):
        out(f"Listening for the log of {addr} on {host}:{port} (Ctrl+C to stop) ...")
        try:
            if seconds is None:
                while True:
                    time.sleep(1)
            else:
                time.sleep(seconds)
        except KeyboardInterrupt:
            pass
