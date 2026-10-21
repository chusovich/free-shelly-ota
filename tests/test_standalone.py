"""Run from ShellyOTA/: python -m unittest discover tests"""

import dataclasses
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shelly_ota import builder, firmware, profile, standalone  # noqa: E402
from shelly_ota.devicegen import parse_partitions  # noqa: E402
from test_builder import fake_app  # noqa: E402
from test_bootswap import make_factory  # noqa: E402


class StandaloneTests(unittest.TestCase):
    """The H&T Gen3 builds without Shelly's ZIP; the official ZIP is only used here to make a realistic factory image."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.profile = profile.load_profile("HTG3")
        self.official = firmware.cached_zip("HTG3")
        self.assertIsNotNone(self.official, "seed ZIP missing in fw/shelly")
        self.app = fake_app(100_000)
        (self.tmp / "app.bin").write_bytes(self.app)
        self.reference = self.tmp / "reference.zip"
        self.reference.write_bytes(standalone.reference_zip(self.profile))

    def _build(self, factory_bytes, **kw):
        (self.tmp / "factory.bin").write_bytes(factory_bytes)
        return builder.build(self.profile, self.tmp / "app.bin", self.reference, self.tmp / "out.zip",
                             factory=self.tmp / "factory.bin", pt_from_factory=True, **kw)

    def test_csv_table_matches_the_official_one(self):
        with zipfile.ZipFile(self.official) as z:
            official = parse_partitions(z.read("partition-table.bin"))
        rows = standalone.parse_csv((Path(__file__).resolve().parent.parent / "partitions" / "HTG3-stock.csv").read_text())
        self.assertEqual(rows, official)
        self.assertEqual(parse_partitions(standalone.partition_table(rows)), official)

    def test_reference_manifest_matches_the_official_one_except_hashes_and_the_fs_image(self):
        with zipfile.ZipFile(self.official) as o, zipfile.ZipFile(self.reference) as r:
            om, rm = json.loads(o.read("manifest.json")), json.loads(r.read("manifest.json"))
        for key in ("name", "platform", "version", "build_id", "build_timestamp"):
            self.assertEqual(rm[key], om[key])
        self.assertIn("src", rm["parts"]["fs"])   # the installer wants an fs image (its content is ours, see below)
        for name, part in rm["parts"].items():
            strip = lambda d: {k: v for k, v in d.items() if k not in ("size", "cs_sha256")}
            self.assertEqual(strip(part), strip(om["parts"][name]), name)

    def test_package_holds_no_file_from_shelly(self):
        # ESPHome writes its own table (same entries, other bytes: MD5 entry, padding); the helper copies Shelly's
        res = self._build(make_factory(self.official, self.app, pt_mod=lambda pt: pt.__setitem__(4095, 0x00)))
        self.assertEqual(res.replaced, ["boot", "otadata", "pt"])
        with zipfile.ZipFile(res.output) as out, zipfile.ZipFile(self.official) as off:
            self.assertEqual(set(out.read("fs.img")), {0xFF})   # erased flash, not Shelly's web UI
            for name in out.namelist():
                if name == "manifest.json":
                    continue
                self.assertTrue(name not in off.namelist() or out.read(name) != off.read(name), name)
            builder.read_official_manifest(out, "HTG3")  # every hash consistent
            self.assertEqual(out.read("HTG3.bin"), self.app)

    def test_partition_table_is_the_one_from_the_factory_image(self):
        factory = make_factory(self.official, self.app)
        res = self._build(factory)
        with zipfile.ZipFile(res.output) as out:
            self.assertEqual(out.read("partition-table.bin"), factory[self.profile.pt_offset:self.profile.pt_offset + 4096])

    def test_other_partition_layout_is_refused(self):
        def move_app0(pt):
            pt[2 * 32 + 8:2 * 32 + 12] = (0x30000).to_bytes(4, "little")
        with self.assertRaises(builder.OtaError):
            self._build(make_factory(self.official, self.app, pt_mod=move_app0))

    def test_other_flash_mode_is_refused(self):
        with self.assertRaises(builder.OtaError) as cm:
            self._build(make_factory(self.official, self.app, boot_tweak=lambda b: b.__setitem__(2, 0)))
        self.assertIn("flash mode", str(cm.exception))

    def test_profile_without_standalone_facts_is_refused(self):
        with self.assertRaises(builder.OtaError) as cm:
            standalone.reference_zip(dataclasses.replace(self.profile, standalone=None))
        self.assertIn("standalone", str(cm.exception))

    def test_pt_from_factory_needs_a_factory_image(self):
        with self.assertRaises(builder.OtaError):
            builder.build(self.profile, self.tmp / "app.bin", self.reference, self.tmp / "o.zip", pt_from_factory=True)


if __name__ == "__main__":
    unittest.main()
