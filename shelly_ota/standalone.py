"""Build a package without Shelly's official ZIP.

An ESPHome package needs from the official ZIP only facts: the manifest layout, the partition table entries and the
first bytes of Shelly's bootloader header (to check that ESPHome's bootloader suits the hardware). None of Shelly's
files is needed, and none ends up in the package: bootloader and otadata come from the ESPHome factory image, so does
the partition table, and the filesystem image (Shelly's web UI) is replaced by an erased one (all 0xFF), so fs_0 is wiped.

`reference_zip` assembles a stand-in for the official ZIP from the profile's `standalone:` block and
partitions/<Device>-stock.csv. It carries the facts only (a bootloader header, a table generated from the CSV, filler),
and `builder.build` then works on it exactly as on a real one.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

from . import MODULE_DIR
from .builder import OtaError
from .devicegen import ENTRY, MAGIC, _SUBTYPES
from .profile import Profile

REQUIRED_KEYS = ("version", "build_id", "build_timestamp", "boot_header", "boot_min_version")
_TYPES = {"app": 0, "data": 1}
_SUBTYPE_NUMBERS = {(t, name): sub for (t, sub), name in _SUBTYPES.items()}


def parse_csv(text: str) -> list[dict]:
    """Rows of an ESP-IDF partitions CSV as {name, type, subtype, offset, size}."""
    rows = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        cols = [c.strip() for c in line.split(",")]
        if len(cols) < 5:
            raise OtaError(f"Partitions CSV: cannot read the line {line!r}.")
        name, kind, sub, offset, size = cols[:5]
        if kind not in _TYPES:
            raise OtaError(f"Partitions CSV: unknown type {kind!r} in {line!r}.")
        ptype = _TYPES[kind]
        subtype = _SUBTYPE_NUMBERS.get((ptype, sub))
        if subtype is None:
            try:
                subtype = int(sub, 0)
            except ValueError:
                raise OtaError(f"Partitions CSV: unknown subtype {sub!r} in {line!r}.") from None
        rows.append({"name": name, "type": ptype, "subtype": subtype, "offset": int(offset, 0), "size": int(size, 0)})
    return rows


def partition_table(rows: list[dict]) -> bytes:
    """Binary table with the entries only (no MD5), padded to 4 KB. Used for comparing; ESPHome's own table is shipped."""
    out = b"".join(ENTRY.pack(MAGIC, r["type"], r["subtype"], r["offset"], r["size"], r["name"].encode(), 0)
                   for r in rows)
    if len(out) > 4096:
        raise OtaError("Too many partitions for a 4 KB table.")
    return out + b"\xff" * (4096 - len(out))


def _check_profile(profile: Profile) -> dict:
    facts = profile.standalone
    if not facts:
        raise OtaError(f"{profile.name} has no 'standalone:' section in its profile, so it cannot be built without "
                       f"Shelly's ZIP. Use the official ZIP (python ota.py fetch {profile.name}, or --official).")
    missing = [k for k in REQUIRED_KEYS if k not in facts]
    if missing:
        raise OtaError(f"devices/{profile.name}.yaml: 'standalone:' lacks {', '.join(missing)}.")
    try:
        header = bytes.fromhex(str(facts["boot_header"]))
    except ValueError:
        raise OtaError(f"devices/{profile.name}.yaml: standalone.boot_header is not a hex string.") from None
    if len(header) != 16 or header[0] != 0xE9:
        raise OtaError(f"devices/{profile.name}.yaml: standalone.boot_header must be the 16 header bytes of the "
                       f"bootloader (starting with E9).")
    return facts


def reference_zip(profile: Profile, csv_path: Path | None = None) -> bytes:
    """A stand-in for the official ZIP, built from the profile's facts. Contains no Shelly file."""
    facts = _check_profile(profile)
    csv_path = csv_path or MODULE_DIR / "partitions" / f"{profile.name}-stock.csv"
    if not csv_path.is_file():
        raise OtaError(f"Missing {csv_path}; it holds the partition layout the standalone build checks against.")
    rows = parse_csv(csv_path.read_text(encoding="utf-8"))
    by_name = {r["name"]: r for r in rows}
    for need in ("otadata", "nvs", profile.app_ptn):
        if need not in by_name:
            raise OtaError(f"{csv_path.name} has no '{need}' partition.")

    boot = bytes.fromhex(str(facts["boot_header"]))   # header only: it is compared, then replaced
    pt = partition_table(rows)
    otadata = b"\xff" * by_name["otadata"]["size"]
    app = b"\0"                                       # replaced by the real app
    files = {"bootloader.bin": boot, "partition-table.bin": pt, "boot_state.bin": otadata, f"{profile.name}.bin": app}
    if "fs_0" in by_name:
        # The installer aborts with "Missing a part" without an fs image (seen on the H&T Gen3, also with a fill-only fs
        # part). Shelly's image (its web UI) is not shipped: this one is erased flash, so fs_0 is wiped (ESPHome ignores it).
        files["fs.img"] = b"\xff" * by_name["fs_0"]["size"]

    def part(kind: str, src: str, **extra) -> dict:
        data = files[src]
        return {"type": kind, "src": src, "size": len(data), "cs_sha256": hashlib.sha256(data).hexdigest(),
                "encrypt": True, **extra}

    manifest = {
        "name": profile.name, "platform": profile.platform, "version": str(facts["version"]),
        "build_id": facts["build_id"], "build_timestamp": facts["build_timestamp"],
        "parts": {
            "boot": part("boot", "bootloader.bin", addr=0, min_version=str(facts["boot_min_version"])),
            "pt": part("pt", "partition-table.bin", addr=profile.pt_offset),
            "otadata": part("otadata", "boot_state.bin", ptn="otadata"),
            "nvs": {"type": "nvs", "size": by_name["nvs"]["size"], "fill": 255, "ptn": "nvs"},
            "app": part("app", f"{profile.name}.bin", ptn=profile.app_ptn),
        },
    }
    if "fs.img" in files:
        manifest["parts"]["fs"] = part("fs", "fs.img", ptn="fs_0", fs_size=len(files["fs.img"]))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as z:
        z.writestr("manifest.json", json.dumps(manifest, separators=(",", ":")))
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()
