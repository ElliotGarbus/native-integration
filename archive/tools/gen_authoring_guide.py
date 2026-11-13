#!/usr/bin/env python3
"""Copy §12.2 into the package, so `authoring-guide` can emit it from a wheel.

**Why a copy at all.** The people who most need the authoring procedure are
working in another package's repository. They will not have this one checked
out, and `SPEC.md` is not in the wheel — so a command that read the
specification off disk would work here and nowhere else, which is the failure
`contract/` had until Phase 4 found it.

**Why it cannot drift.** This is generated, byte for byte, from `SPEC.md`, and
`--check` fails the build when the two disagree. The copy is a transport, not a
second statement: §12.2 says it introduces nothing, and a copy that had started
saying something else would be the one place nobody would look.

    python3 tools/gen_authoring_guide.py           # write
    python3 tools/gen_authoring_guide.py --check   # fail if it has drifted
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "SPEC.md"
OUTPUT = ROOT / "src" / "native_integration" / "contract" / "authoring-guide.md"

HEADING = "### 12.2 Sidecar authoring procedure"

PREAMBLE = """<!-- GENERATED from SPEC.md §12.2 by tools/gen_authoring_guide.py. -->
<!-- Do not edit: the specification is the original and this is a copy. -->

"""


def build() -> str:
    text = SPEC.read_text(encoding="utf-8")
    start = text.index(HEADING)
    end = text.index("\n---\n", start)
    body = text[start:end].rstrip("\n")
    return PREAMBLE + body + "\n"


def main() -> int:
    rendered = build()
    if "--check" in sys.argv:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != rendered:
            print(f"FAIL  {OUTPUT.relative_to(ROOT)} has drifted from SPEC.md §12.2; "
                  "run python3 tools/gen_authoring_guide.py")
            return 1
        print("ok    the packaged authoring guide matches SPEC.md")
        return 0
    # newline: this repository pins LF, and a generated file that differed by
    # line ending would fail its own drift check on the next checkout.
    OUTPUT.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
