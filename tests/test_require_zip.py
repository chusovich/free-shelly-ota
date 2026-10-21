"""Run from ShellyOTA/: python -m unittest discover tests

A file that is not an OTA ZIP (most often a DevKit flash image) gets a message that says what it is, not a traceback.
"""

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shelly_ota import builder, profile, sender  # noqa: E402


class RequireZipTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def file(self, name, data=b"\xe9\x03\x02\x30" + b"\x00" * 100):
        path = self.dir / name
        path.write_bytes(data)
        return path

    def test_a_zip_passes(self):
        path = self.dir / "a.zip"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("manifest.json", "{}")
        self.assertEqual(builder.require_zip(path), path)

    def test_a_devkit_image_is_named_as_one_and_the_command_is_on_its_own_line(self):
        with self.assertRaises(builder.OtaError) as cm:
            builder.require_zip(self.file("Mini1G4-devkit-2.0.1.bin"))
        text = str(cm.exception)
        self.assertIn("flash image for a dev board", text)
        self.assertIn("\n\n  python ota.py devkit Mini1G4\n\n", text)

    def test_another_bin_is_called_a_flash_image_without_a_profile_guess(self):
        with self.assertRaises(builder.OtaError) as cm:
            builder.require_zip(self.file("app.ota.bin"))
        self.assertIn("looks like a flash image", str(cm.exception))
        self.assertIn("python ota.py devkit <profile>", str(cm.exception))

    def test_any_other_file_is_just_not_a_zip(self):
        with self.assertRaises(builder.OtaError) as cm:
            builder.require_zip(self.file("notes.txt", b"hello"))
        self.assertEqual(str(cm.exception), "notes.txt is not a ZIP file, so it is not an OTA package.")

    def test_a_missing_file_is_said_to_be_missing(self):
        with self.assertRaises(builder.OtaError) as cm:
            builder.require_zip(self.dir / "nothere.zip", "official ZIP")
        self.assertIn("official ZIP", str(cm.exception))
        self.assertIn("does not exist", str(cm.exception))

    def test_send_and_inspect_refuse_a_devkit_image_before_they_talk_to_anything(self):
        image = self.file("PlugMG3-devkit-2.0.1.bin")
        p = profile.load_profile("PlugMG3")
        with self.assertRaises(builder.OtaError) as cm:
            sender.send(p, image, "192.0.2.1", out=lambda m: None)    # nothing listens there: the check comes first
        self.assertIn("python ota.py devkit PlugMG3", str(cm.exception))
        with self.assertRaises(builder.OtaError):
            builder.inspect_zip(image)


if __name__ == "__main__":
    unittest.main()
