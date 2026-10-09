#!/usr/bin/env python3
"""Check every skills/*/SKILL.md against the Agent Skills frontmatter rules.

Rules enforced: frontmatter present; `name` matches the directory, is 1-64
characters of [a-z0-9-], has no leading/trailing/double hyphen;
`description` is 1-1024 characters; `compatibility`, when present, is at
most 500 characters; no unknown top-level keys. Exits 1 on any failure.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ALLOWED_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def parse_frontmatter(text: str) -> dict[str, str] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    fields: dict[str, str] = {}
    current = None
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        if line.startswith((" ", "\t")):
            if current is None:
                raise ValueError(f"indented line outside a key: {line!r}")
            fields[current] += "\n" + line.strip()
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"line is not `key: value`: {line!r}")
        current = key.strip()
        fields[current] = value.strip().strip('"').strip("'")
    return fields


def check(skill_md: Path) -> list[str]:
    problems: list[str] = []
    text = skill_md.read_text(encoding="utf-8")
    try:
        fm = parse_frontmatter(text)
    except ValueError as exc:
        return [str(exc)]
    if fm is None:
        return ["missing YAML frontmatter (--- ... ---)"]
    unknown = set(fm) - ALLOWED_KEYS
    if unknown:
        problems.append(f"unknown frontmatter keys: {sorted(unknown)}")
    name = fm.get("name", "")
    if not name:
        problems.append("missing `name`")
    else:
        if not 1 <= len(name) <= 64:
            problems.append(f"`name` must be 1-64 characters, got {len(name)}")
        if not NAME_RE.match(name):
            problems.append(f"`name` must be lowercase [a-z0-9-] without leading/trailing/double hyphens: {name!r}")
        if name != skill_md.parent.name:
            problems.append(f"`name` {name!r} does not match directory {skill_md.parent.name!r}")
    description = fm.get("description", "")
    if not description:
        problems.append("missing `description`")
    elif len(description) > 1024:
        problems.append(f"`description` exceeds 1024 characters ({len(description)})")
    compat = fm.get("compatibility")
    if compat is not None and not 1 <= len(compat) <= 500:
        problems.append("`compatibility` must be 1-500 characters when present")
    body = text[text.find("\n---\n", 4) + 5 :].strip()
    if not body:
        problems.append("empty body after frontmatter")
    return problems


def main() -> int:
    root = Path(__file__).resolve().parent.parent / "skills"
    skill_dirs = sorted(p for p in root.iterdir() if p.is_dir())
    failures = 0
    for skill_dir in skill_dirs:
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            print(f"{skill_dir}: missing SKILL.md")
            failures += 1
            continue
        problems = check(skill_md)
        for problem in problems:
            print(f"{skill_md}: {problem}")
        failures += len(problems)
    print(f"{len(skill_dirs)} skills checked, {failures} problem(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
