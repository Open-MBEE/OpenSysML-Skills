#!/usr/bin/env python3
"""Fail on relative Markdown links that do not resolve inside the repository."""
from __future__ import annotations

import re
import sys
from pathlib import Path

LINK_RE = re.compile(r"\]\(([^)\s#]+)(#[^)]*)?\)")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    broken = 0
    for md in sorted(root.rglob("*.md")):
        if ".git" in md.parts:
            continue
        for match in LINK_RE.finditer(md.read_text(encoding="utf-8")):
            target = match.group(1)
            if "://" in target or target.startswith("mailto:"):
                continue
            if not (md.parent / target).exists():
                print(f"{md.relative_to(root)}: broken link {target}")
                broken += 1
    print(f"{broken} broken link(s)")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
