"""Run from ShellyOTA/: python -m unittest discover tests

Keeps the README (and the device overview next to the device pages) in step with the profiles.
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shelly_ota import profile  # noqa: E402

ROOT = profile.MODULE_DIR
README = ROOT / "README.md"
DEVICE_OVERVIEW = ROOT / "docs" / "devices" / "README.md"
STATES = ("✅", "🟡", "🧪")


def _slug(heading: str) -> str:
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def _anchors(path: Path) -> set:
    found = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"#{1,6}\s+(.*)", line)
        if m:
            found.add(_slug(m.group(1)))
    return found


def _table_states(path: Path, state_cell: str) -> dict:
    """{profile: state symbol} from the rows that link a profile as [`Name`](...)."""
    states = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|[^|]*\|\s*\[`(\w+)`\]\([^)]*\)\s*\|", line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        symbol = cells[state_cell].split(" ")[0]
        states[m.group(1)] = symbol
    return states


class ReadmeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = README.read_text(encoding="utf-8")
        cls.states = _table_states(README, state_cell=3)  # Device | Profile | Chip | State | Note

    def test_every_profile_is_in_the_device_table_and_nothing_else(self):
        self.assertEqual(sorted(self.states), profile.list_devices())

    def test_states_are_known_symbols(self):
        for name, symbol in self.states.items():
            self.assertIn(symbol, STATES, name)

    def test_summary_line_matches_the_table(self):
        m = re.search(r"\*\*(\d+) profiles:\*\* ✅ (\d+) confirmed · 🟡 (\d+) partly checked · 🧪 (\d+) untested", self.text)
        self.assertIsNotNone(m, "summary line above the device table is missing or changed its form")
        symbols = list(self.states.values())
        expected = (len(symbols), symbols.count("✅"), symbols.count("🟡"), symbols.count("🧪"))
        self.assertEqual(tuple(int(g) for g in m.groups()), expected)

    def test_device_overview_has_the_same_states(self):
        overview = _table_states(DEVICE_OVERVIEW, state_cell=5)  # Device | Profile | Chip | Table | Slot | State
        self.assertEqual(overview, self.states)

    def test_relative_links_and_images_exist(self):
        for m in re.finditer(r"\]\(([^)\s]+)\)", self.text):
            url = m.group(1)
            if re.match(r"[a-z]+://", url):
                continue
            path, _, frag = url.partition("#")
            target = ROOT / path if path else README
            self.assertTrue(target.exists(), url)
            if frag and target.suffix == ".md":
                self.assertIn(frag, _anchors(target), url)
        for m in re.finditer(r'<img [^>]*src="([^"]+)"', self.text):
            if not re.match(r"[a-z]+://", m.group(1)):
                self.assertTrue((ROOT / m.group(1)).is_file(), m.group(1))


SECTIONS = ("Before you start", "ESPHome config", "Pins", "Flash it", "What to expect", "Notes for this device", "Way back")
BADGE = {"✅": "state-confirmed-", "🟡": "state-partly%20checked-", "🧪": "state-untested-"}


class DevicePageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = sorted(p for p in (ROOT / "docs" / "devices").glob("*.md") if p.name != "README.md")
        cls.states = _table_states(README, state_cell=3)

    def _profiles(self, text):
        m = re.search(r"(?m)^\| Profile \| (.+) \|$", text)
        self.assertIsNotNone(m, "no Profile row")
        return re.findall(r"`(\w+)`", m.group(1))

    def test_every_profile_has_a_page(self):
        named = set()
        for page in self.pages:
            named.update(self._profiles(page.read_text(encoding="utf-8")))
        self.assertEqual(sorted(named), profile.list_devices())

    def test_pages_have_the_standard_sections_in_order(self):
        for page in self.pages:
            heads = re.findall(r"(?m)^## (.+)$", page.read_text(encoding="utf-8"))
            core = [h for h in heads if h in SECTIONS]
            self.assertEqual(core, [s for s in SECTIONS if s in heads], page.name)
            for needed in ("Before you start", "Flash it", "What to expect", "Notes for this device", "Way back"):
                self.assertIn(needed, heads, page.name)

    def test_state_badge_matches_the_readme(self):
        for page in self.pages:
            text = page.read_text(encoding="utf-8")
            for name in self._profiles(text):
                self.assertIn(BADGE[self.states[name]], text, f"{page.name}: {name}")

    def test_flash_commands_use_the_profile_of_the_page(self):
        for page in self.pages:
            text = page.read_text(encoding="utf-8")
            first = self._profiles(text)[0]
            self.assertIn(f"python ota.py fetch {first} --insecure", text, page.name)
            self.assertIn(f"python ota.py restore {first}", text, page.name)

    def test_relative_links_exist(self):
        for page in self.pages + [DEVICE_OVERVIEW]:
            text = page.read_text(encoding="utf-8")
            for m in re.finditer(r"\]\(([^)\s]+)\)", text):
                url = m.group(1)
                if re.match(r"[a-z]+://", url):
                    continue
                path, _, frag = url.partition("#")
                target = (page.parent / path) if path else page
                self.assertTrue(target.exists(), f"{page.name}: {url}")
                if frag and target.suffix == ".md":
                    self.assertIn(frag, _anchors(target), f"{page.name}: {url}")


if __name__ == "__main__":
    unittest.main()
