#!/usr/bin/env python3
"""Generate docs/REQUIREMENTS.md from SPEC.md §8 and the library's rule registry.

The point of the reference reader is that a consumer's obligations are code
paths rather than prose it has to remember. That claim is only worth something
if the mapping is derived rather than asserted, so this reads the requirement
text out of the specification and the discharging code out of
``native_integration.rules`` — neither by hand.

    python3 tools/requirements_table.py          # rewrite docs/REQUIREMENTS.md
    python3 tools/requirements_table.py --check  # fail if it is out of date
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from native_integration.rules import RULES, STRUCTURAL  # noqa: E402

OUTPUT = ROOT / "docs" / "REQUIREMENTS.md"

HEADER = """# Where each consumer obligation lives

Every requirement in [§8 of the specification](../SPEC.md#8-consuming-tool-requirements),
against the code path in [`native_integration`](../src/native_integration/) that
discharges it.

**Generated** by `python3 tools/requirements_table.py` from SPEC.md and
`native_integration.rules`; CI fails if it drifts. A requirement that appears in
neither column fails `tests/test_integration.py::test_every_requirement_is_discharged_somewhere`.

Two kinds of entry:

- a **rule code** is a check that produces a diagnostic. Every rule names its
  section and severity once, in `rules.py`, so "MUST fail" cannot decay into a
  warning through an edit at a call site.
- a **structural** entry is an obligation discharged by the shape of the API
  rather than by a check — you cannot construct a `Diagnostic` without naming a
  distribution, so requirement 8.15 has no rule and cannot be forgotten either.

Four requirements need something only a build tool has: a resolved dependency
graph, an archive listing, the manifest inside a resolved `.aar`. Those are
[ports](../src/native_integration/ports.py), and a sidecar that needs one when
the consumer supplied none raises `UnimplementedObligation` rather than
returning a clean result.

| §8 | The requirement | Discharged by |
| --- | --- | --- |"""


def requirement_text() -> dict[int, str]:
    spec = (ROOT / "SPEC.md").read_text(encoding="utf-8")
    block = spec.split("A conforming consumer **MUST**:")[1].split(
        "A conforming consumer **SHOULD**:"
    )[0]
    found: dict[int, str] = {}
    for match in re.finditer(r"^(\d+)\.\s(.*?)(?=^\d+\.\s|\Z)", block, re.M | re.S):
        # A trailing block quote is rationale attached to the list, not part of
        # the requirement it happens to follow.
        body = re.split(r"\n\s*>", match.group(2))[0]
        text = " ".join(body.split())
        text = text.replace("**", "").replace("|", "\\|")
        found[int(match.group(1))] = text
    return found


def build() -> str:
    requirements = requirement_text()
    lines = [HEADER]
    for number in sorted(requirements):
        codes = sorted(r.code for r in RULES.values() if number in r.requirements)
        where = ", ".join(f"`{c}`" for c in codes)
        if number in STRUCTURAL:
            structural = f"*structural* — {STRUCTURAL[number]}"
            where = f"{where}<br>{structural}" if where else structural
        lines.append(f"| 8.{number} | {requirements[number]} | {where or '—'} |")
    lines.append("")
    lines.append("## Rules with no requirement number")
    lines.append("")
    lines.append(
        "Checks the specification states in §§3–9 without giving them a numbered "
        "line in §8. They are enforced the same way."
    )
    lines.append("")
    lines.append("| Rule | Section | Severity |")
    lines.append("| --- | --- | --- |")
    for rule in sorted(RULES.values(), key=lambda r: (r.section, r.code)):
        if not rule.requirements:
            lines.append(f"| `{rule.code}` | {rule.section} | {rule.severity} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    content = build()
    if "--check" in sys.argv:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != content:
            print(f"FAIL  {OUTPUT.relative_to(ROOT)} is out of date")
            print("      run: python3 tools/requirements_table.py")
            return 1
        print(f"ok    {OUTPUT.relative_to(ROOT)} is current")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
