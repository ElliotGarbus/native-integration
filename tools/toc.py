#!/usr/bin/env python3
"""Generate SPEC.md's table of contents, between its `<!-- toc -->` markers.

A hand-maintained contents list for a 2,500-line document drifts the first time
someone adds a section, and a table of contents that silently omits a section is
worse than none — it tells a reader the section is not there.

Anchors are computed with the same rule `tools/check_spec.py` uses to validate
them, so the two cannot disagree: lowercase, drop anything outside
`[a-z0-9 -]`, then spaces to hyphens. That is GitHub's own scheme for the
heading shapes this document uses.

    python3 tools/toc.py          # rewrite the block in place
    python3 tools/toc.py --check  # fail if it is out of date
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "SPEC.md"

START, END = "<!-- toc -->", "<!-- /toc -->"

#: Headings that are navigation themselves, and would list themselves.
SKIP = {"Contents"}


def anchor(heading: str) -> str:
    return re.sub(r"[^a-z0-9 -]", "", heading.lower()).replace(" ", "-")


def label(heading: str) -> str:
    """The heading without its table path.

    ``6.7 Permissions and features: `[[android.contributes.permissions]]`, …``
    is an accurate entry and a poor one — a reader scanning for a concept does
    not want the TOML path, and Appendix D already maps keys to sections. The
    link still targets the full heading's anchor.
    """
    return heading.split(": `", 1)[0]


def build(text: str) -> str:
    out: list[str] = []
    for level, heading in re.findall(r"^(#{2,3}) (.+)$", text, re.M):
        if heading in SKIP:
            continue
        indent = "  " * (len(level) - 2)
        out.append(f"{indent}- [{label(heading)}](#{anchor(heading)})")
    return "\n".join(out)


def rewrite(text: str) -> str:
    contents = build(text)
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        raise SystemExit(f"SPEC.md has no {START} … {END} block to fill")
    return pattern.sub(f"{START}\n\n{contents}\n\n{END}", text)


def main() -> int:
    text = SPEC.read_text(encoding="utf-8")
    updated = rewrite(text)
    if "--check" in sys.argv:
        if text != updated:
            print("FAIL  SPEC.md's table of contents is out of date")
            print("      run: python3 tools/toc.py")
            return 1
        print("ok    SPEC.md's table of contents is current")
        return 0
    SPEC.write_text(updated, encoding="utf-8")
    print(f"wrote {len(build(text).splitlines())} entries into SPEC.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
