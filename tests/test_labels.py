"""Run from ShellyOTA/: python -m unittest discover tests

Keeps .github/labels.yml, the issue forms and the profiles in step, and checks the plan of .github/sync_labels.py.
"""

import importlib.util
import re
import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shelly_ota import profile  # noqa: E402

ROOT = profile.MODULE_DIR
GITHUB = ROOT / ".github"
FORMS = sorted((GITHUB / "ISSUE_TEMPLATE").glob("*.yml"))
GROUPS = ("type", "tester", "status", "area", "device", "risk")
UNGROUPED = {"help wanted", "good first issue", "duplicate", "wontfix", "out of scope"}

_spec = importlib.util.spec_from_file_location("sync_labels", GITHUB / "sync_labels.py")
sync_labels = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync_labels)


def _label(name, color="aaaaaa", description="d", **extra):
    return {"name": name, "color": color, "description": description, **extra}


class LabelFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wanted, cls.delete = sync_labels.load_wanted()
        cls.names = [w["name"] for w in cls.wanted]

    def test_names_are_unique_and_short(self):
        folded = [n.casefold() for n in self.names]
        self.assertEqual(len(folded), len(set(folded)))
        for name in self.names:
            self.assertLessEqual(len(name), 50, name)

    def test_colour_and_description_fit_what_github_accepts(self):
        for w in self.wanted:
            self.assertIsInstance(w["color"], str, w["name"])
            self.assertRegex(w["color"], r"^[0-9a-f]{6}$", w["name"])
            self.assertTrue(w["description"].strip(), w["name"])
            self.assertLessEqual(len(w["description"]), 100, w["name"])

    def test_every_label_is_in_a_group_or_a_known_plain_name(self):
        for name in self.names:
            group = name.partition(": ")[0] if ": " in name else None
            if group is None:
                self.assertIn(name, UNGROUPED, name)
            else:
                self.assertIn(group, GROUPS, name)

    def test_aliases_do_not_collide_with_a_label_name(self):
        folded = {n.casefold() for n in self.names}
        aliases = [a.casefold() for w in self.wanted for a in w.get("aliases", [])]
        self.assertEqual(len(aliases), len(set(aliases)))
        self.assertFalse(folded & set(aliases))
        self.assertFalse(folded & {d.casefold() for d in self.delete})

    def test_device_labels_are_profiles_or_other(self):
        for name in self.names:
            if name.startswith("device: "):
                self.assertTrue(name[len("device: "):] in profile.list_devices() or name == "device: other", name)

    def test_issue_forms_use_labels_that_exist(self):
        self.assertTrue(FORMS)
        for path in FORMS:
            form = yaml.safe_load(path.read_text(encoding="utf-8"))
            for label in form.get("labels", []):
                self.assertIn(label, self.names, f"{path.name}: label {label!r} is not in labels.yml")

    def test_every_form_with_a_type_label_sets_exactly_one(self):
        for path in FORMS:
            form = yaml.safe_load(path.read_text(encoding="utf-8"))
            if "body" in form:
                types = [lb for lb in form["labels"] if lb.startswith("type: ")]
                self.assertEqual(len(types), 1, path.name)

    def test_tester_labels_match_the_answers_of_the_new_device_form(self):
        form = yaml.safe_load((GITHUB / "ISSUE_TEMPLATE" / "new-device.yml").read_text(encoding="utf-8"))
        options = next(b for b in form["body"] if b.get("id") == "help")["attributes"]["options"]
        self.assertEqual(len(options), len([n for n in self.names if n.startswith("tester: ")]))
        self.assertEqual(len([o for o in options if re.match(r"Yes", o)]), 2)


class PlanTests(unittest.TestCase):
    def verbs(self, wanted, existing, delete=()):
        return [(a["verb"], a["name"]) for a in sync_labels.plan(wanted, existing, delete)]

    def test_missing_label_is_created(self):
        self.assertEqual(self.verbs([_label("type: bug")], []), [("create", "type: bug")])

    def test_label_that_is_already_right_is_left_alone(self):
        self.assertEqual(self.verbs([_label("a")], [_label("a")]), [])

    def test_colour_is_compared_without_case_and_description_exactly(self):
        self.assertEqual(self.verbs([_label("a", "ABCDEF")], [_label("a", "abcdef")]), [])
        self.assertEqual(self.verbs([_label("a", description="new")], [_label("a", description="old")]), [("edit", "a")])
        self.assertEqual(self.verbs([_label("a")], [_label("a", description=None)]), [("edit", "a")])

    def test_alias_is_renamed_not_created(self):
        actions = sync_labels.plan([_label("type: bug", aliases=["bug"])], [_label("bug")])
        self.assertEqual([(a["verb"], a["old"], a["name"]) for a in actions], [("rename", "bug", "type: bug")])

    def test_both_names_existing_is_a_conflict_that_is_not_touched(self):
        actions = sync_labels.plan([_label("type: bug", aliases=["bug"])], [_label("bug"), _label("type: bug")])
        self.assertEqual([(a["verb"], a["name"]) for a in actions], [("conflict", "type: bug")])

    def test_names_differing_only_in_case_are_a_rename(self):
        self.assertEqual(self.verbs([_label("Bug")], [_label("bug")]), [("rename", "Bug")])

    def test_labels_missing_from_the_file_are_never_removed(self):
        self.assertEqual(self.verbs([_label("a")], [_label("a"), _label("x")]), [("unlisted", "x")])
        self.assertEqual(self.verbs([_label("a")], [_label("a"), _label("x")], delete=["X"]), [("remove", "x")])

    def test_rename_command_carries_the_new_settings(self):
        action = sync_labels.plan([_label("type: bug", "d73a4a", "text", aliases=["bug"])], [_label("bug")])[0]
        self.assertEqual(
            sync_labels.gh_command(action, "o/r"),
            ["gh", "label", "edit", "bug", "--name", "type: bug", "--color", "d73a4a", "--description", "text", "--repo", "o/r"],
        )

    def test_the_real_file_against_todays_labels_renames_and_creates(self):
        today = [_label(n, c, "x") for n, c in (
            ("bug", "d73a4a"), ("documentation", "0075ca"), ("enhancement", "a2eeef"), ("question", "d876e3"), ("new-device", "5ab8b9"),
            ("invalid", "e4e669"), ("accessibility", "f143ab"), ("help wanted", "008672"), ("good first issue", "7057ff"),
            ("duplicate", "cfd3d7"), ("wontfix", "ffffff"))]
        wanted, delete = sync_labels.load_wanted()
        actions = sync_labels.plan(wanted, today, delete)
        renames = {a["old"]: a["name"] for a in actions if a["verb"] == "rename"}
        self.assertEqual(renames, {"bug": "type: bug", "documentation": "type: docs", "enhancement": "type: enhancement",
                                   "question": "type: question", "new-device": "type: device-request", "invalid": "out of scope"})
        self.assertIn(("remove", "accessibility"), [(a["verb"], a["name"]) for a in actions])
        self.assertNotIn("conflict", {a["verb"] for a in actions})


if __name__ == "__main__":
    unittest.main()
