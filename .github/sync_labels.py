"""Create, rename and update the issue labels of the repository from .github/labels.yml.

Dry run by default: it prints what would change and writes nothing. `--apply` runs `gh label create` and
`gh label edit`. It needs the GitHub CLI and `gh auth login`; `--from-json FILE` reads the labels GitHub has
today from a file (the output of `gh label list --json name,color,description --limit 200`), so the plan can be
checked without a login.

It never deletes: labels that are not in the file are only listed, and the `delete:` entries of the file are
printed as commands for you to run.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

LABELS_FILE = Path(__file__).with_name("labels.yml")


def load_wanted(path: Path = LABELS_FILE) -> tuple[list[dict], list[str]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data["labels"], data.get("delete") or []


def plan(wanted: list[dict], existing: list[dict], delete: list[str] = ()) -> list[dict]:
    """Compare the file with GitHub. Each action has a `verb`: create, rename, edit, conflict, remove or unlisted.

    GitHub treats label names case-insensitively, so the comparison does too.
    """
    have = {label["name"].casefold(): label for label in existing}
    wanted_names = {w["name"].casefold() for w in wanted}
    consumed = set()  # names on GitHub that the file accounts for
    actions = []
    for w in wanted:
        key = w["name"].casefold()
        change = {"name": w["name"], "color": w["color"], "description": w["description"]}
        aliases = [a for a in w.get("aliases", []) if a.casefold() in have]
        consumed.update(a.casefold() for a in aliases)
        if key in have:
            consumed.add(key)
            current = have[key]
            for alias in aliases:
                actions.append({"verb": "conflict", "name": w["name"], "old": alias})
            if current["name"] != w["name"]:
                actions.append({"verb": "rename", "old": current["name"], **change})
            elif current["color"].casefold() != w["color"].casefold() or (current.get("description") or "") != w["description"]:
                actions.append({"verb": "edit", **change})
        elif aliases:
            actions.append({"verb": "rename", "old": aliases[0], **change})
            for alias in aliases[1:]:
                actions.append({"verb": "conflict", "name": w["name"], "old": alias})
        else:
            actions.append({"verb": "create", **change})
    to_delete = {d.casefold() for d in delete}
    for key, label in have.items():
        if key in consumed or key in wanted_names:
            continue
        actions.append({"verb": "remove" if key in to_delete else "unlisted", "name": label["name"]})
    return actions


def gh_command(action: dict, repo: str | None) -> list[str]:
    """The `gh` call for a create, rename or edit action."""
    verb = action["verb"]
    settings = ["--color", action["color"], "--description", action["description"]]
    if verb == "create":
        cmd = ["gh", "label", "create", action["name"], *settings]
    elif verb == "rename":
        cmd = ["gh", "label", "edit", action["old"], "--name", action["name"], *settings]
    else:
        cmd = ["gh", "label", "edit", action["name"], *settings]
    return cmd + (["--repo", repo] if repo else [])


def describe(action: dict) -> str:
    verb, name = action["verb"], action["name"]
    if verb == "create":
        return f"create    {name}"
    if verb == "rename":
        return f"rename    {action['old']}  ->  {name}"
    if verb == "edit":
        return f"edit      {name}  (colour or description differs)"
    if verb == "conflict":
        return f"conflict  {action['old']} and {name} both exist: move the issues by hand, then delete {action['old']}"
    if verb == "remove":
        return f"remove    {name}  (listed under delete; not done by this script)"
    return f"unlisted  {name}  (on GitHub, not in the file; left alone)"


def read_existing(from_json: str | None, repo: str | None) -> list[dict]:
    if from_json:
        return json.loads(Path(from_json).read_text(encoding="utf-8"))
    cmd = ["gh", "label", "list", "--json", "name,color,description", "--limit", "200"] + (["--repo", repo] if repo else [])
    done = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if done.returncode:
        raise SystemExit(f"{' '.join(cmd)} failed (is the GitHub CLI installed and logged in with `gh auth login`?):\n{done.stderr.strip()}")
    return json.loads(done.stdout)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Make the labels on GitHub match .github/labels.yml (dry run unless --apply).")
    ap.add_argument("--apply", action="store_true", help="run the creates, renames and edits (default: only print them)")
    ap.add_argument("--repo", metavar="OWNER/NAME", help="repository (default: the one of the current directory)")
    ap.add_argument("--from-json", metavar="FILE", help="labels GitHub has today, from a file instead of `gh` (dry run only)")
    args = ap.parse_args(argv)
    if args.apply and args.from_json:
        ap.error("--apply needs the live labels: leave out --from-json")

    wanted, delete = load_wanted()
    actions = plan(wanted, read_existing(args.from_json, args.repo), delete)
    for action in actions:
        print(describe(action))
    todo = [a for a in actions if a["verb"] in ("create", "rename", "edit")]
    print(f"{len(todo)} change(s), {len(wanted) - len(todo)} label(s) already as in the file.")
    if not args.apply:
        print("Dry run, nothing written. Run again with --apply to make the changes.")
        return 0
    for action in todo:
        cmd = gh_command(action, args.repo)
        done = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if done.returncode:
            print(f"failed: {' '.join(cmd)}\n{done.stderr.strip()}", file=sys.stderr)
            return 1
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
