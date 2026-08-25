#!/usr/bin/env python3
"""Generate first-attempt.md's table of contents, between its `<!-- toc -->` markers.

A hand-maintained contents list for a 2,500-line document drifts the first time
someone adds a section, and a table of contents that silently omits a section is
worse than none — it tells a reader the section is not there.

Anchors are computed with the same rule `tools/check_spec.py` uses to validate
them, so the two cannot disagree: lowercase, drop anything outside
`[a-z0-9 -]`, then spaces to hyphens. That is GitHub's own scheme for the
heading shapes this document uses.

Depth stops at level 4. Only §7.3 and §9 go that deep, because only they are
long enough to need it; §7.3's six tables sit a level below that and are listed
by name in its satisfaction table anyway.

    python3 tools/toc.py          # rewrite the block in place
    python3 tools/toc.py --check  # fail if it is out of date
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "development" / "first-attempt.md"

START, END = "<!-- toc -->", "<!-- /toc -->"

#: Headings that are navigation themselves, and would list themselves.
SKIP = {"Contents"}


def uncoded(text: str) -> str:
    """Blank fenced blocks, keeping line structure.

    A ``# producer's native.toml`` comment inside an example is not a heading,
    and the ordinal below must not count it as one.
    """
    return re.sub(
        r"```.*?```", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S
    )


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
    """Indent by depth in the hierarchy, not by raw heading level.

    §9 is a level-2 heading whose parts are level 4, because level 3 is taken by
    the ``N.M`` sub-sections everywhere else. Indenting on the level itself
    would show those parts as grandchildren of a section that has no children.
    """
    out: list[str] = []
    ancestors: list[int] = []
    seen: dict[str, int] = {}
    # Every level is walked, because GitHub numbers a repeated heading in
    # document order over the whole file; only levels 2 to 4 are listed.
    for hashes, heading in re.findall(r"^(#{1,6}) (.+)$", uncoded(text), re.M):
        base = anchor(heading)
        nth = seen.get(base, 0)
        seen[base] = nth + 1
        target = base if nth == 0 else f"{base}-{nth}"
        level = len(hashes)
        if heading in SKIP or not 2 <= level <= 4:
            continue
        while ancestors and ancestors[-1] >= level:
            ancestors.pop()
        out.append(f"{'  ' * len(ancestors)}- [{label(heading)}](#{target})")
        ancestors.append(level)
    return "\n".join(out)


def rewrite(text: str) -> str:
    contents = build(text)
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        raise SystemExit(f"first-attempt.md has no {START} … {END} block to fill")
    return pattern.sub(f"{START}\n\n{contents}\n\n{END}", text)


def main() -> int:
    text = SPEC.read_text(encoding="utf-8")
    updated = rewrite(text)
    if "--check" in sys.argv:
        if text != updated:
            print("FAIL  first-attempt.md's table of contents is out of date")
            print("      run: python3 tools/toc.py")
            return 1
        print("ok    first-attempt.md's table of contents is current")
        return 0
    SPEC.write_text(updated, encoding="utf-8")
    print(f"wrote {len(build(text).splitlines())} entries into first-attempt.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
