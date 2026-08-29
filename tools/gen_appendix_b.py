#!/usr/bin/env python3
"""Generate SPEC.md's Appendix B table from contract/v1.toml.

Appendix B is the contract-minor registry §4.3 rests on: a key missing from it
has no recorded revision, so the under-declaration rule cannot be applied to it.
That makes it the one table in the document where hand-maintenance is a real
hazard — a key added to §6 and forgotten here is a key no consumer can version-
gate, and nothing about reading §6 reminds anyone to come back.

So the table is derived. `contract/v1.toml` holds the mechanical properties and
Appendix B's own summary text; this writes the rows. The **rationale** — every
`> **Note:**` and `> **Caution:**` in §§4-7, and the prose above and below the
table — is untouched: this writes only between the delimiters, which is why the
appendix's introduction still says what the table is for in its own words.

    python3 tools/gen_appendix_b.py          # rewrite the block in place
    python3 tools/gen_appendix_b.py --check  # fail if it is out of date

Where this generator and SPEC.md's body disagree, the body governs and the
registry is the defect — the appendix says so itself.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "contract" / "v1.toml"
SPEC = ROOT / "SPEC.md"

START, END = "<!-- appendix-b -->", "<!-- /appendix-b -->"

#: The pseudo-group the two keys above every platform table fall into. They have
#: no container declaration because they have no container.
TOP_LEVEL = "Top level"


def heading_for(declaration_id: str, entry: dict) -> str:
    """The bold entry cell that opens a group.

    Defaults to the TOML spelling — `[x]` for a table, `[[x]]` for an array of
    tables — so that a reader can copy it straight into a sidecar. An
    `open_table` never opens a group: its key names belong to the platform, so
    it has no declared children to head and renders as a row. An explicit
    `heading` overrides where the appendix says something the shape does not,
    as `[<platform>.requires]` does in naming its rows floors.
    """
    if "heading" in entry:
        heading = entry["heading"]
    elif entry["node"] == "array_of_tables":
        heading = f"`[[{declaration_id}]]`"
    else:
        heading = f"`[{declaration_id}]`"
    return f"**{heading}**"


def section_link(entry: dict) -> str:
    return f"[§{entry['section']}](#{entry['anchor']})"


def leaf_name(declaration_id: str) -> str:
    return declaration_id.rsplit(".", maxsplit=1)[-1]


def row(entry_cell: str, description: str) -> str:
    """One table row. An empty description leaves the cell empty, not padded."""
    return f"| {entry_cell} |{' ' + description + ' ' if description else ' '}|"


def build(declarations: dict[str, dict]) -> str:
    lines = ["| Entry | Description |", "| --- | --- |"]
    group: str | None = None

    # A forbidden key — `exported`, a feature's `required` — is a row like any
    # other. A reader looking for it needs to find out why it is absent rather
    # than conclude the appendix forgot it.
    for declaration_id, entry in declarations.items():
        if entry["node"] in ("table", "array_of_tables"):
            group = declaration_id
            cell = f"{heading_for(declaration_id, entry)} {section_link(entry)}"
            if suffix := entry.get("heading_suffix"):
                cell = f"{cell} {suffix}"
            lines.append(row(cell, entry.get("description", "")))
            continue

        if group is None:
            lines.append(f"| **{TOP_LEVEL}** | |")
            group = TOP_LEVEL

        description = entry.get("description", "")
        if group == TOP_LEVEL:
            # No header row carries the section for these two, so each says it.
            description = f"{description} {section_link(entry)}"
        lines.append(row(f"`{leaf_name(declaration_id)}`", description))

    return "\n".join(lines)


def rewritten(spec: str, table: str) -> str:
    start = spec.index(START)
    end = spec.index(END)
    return spec[: start + len(START)] + "\n\n" + table + "\n\n" + spec[end:]


def main() -> int:
    declarations = tomllib.loads(REGISTRY.read_text(encoding="utf-8"))["declarations"]
    spec = SPEC.read_text(encoding="utf-8")
    if START not in spec or END not in spec:
        print(f"FAIL  SPEC.md has no {START} … {END} block to write into")
        return 1

    content = rewritten(spec, build(declarations))
    if "--check" in sys.argv:
        if spec != content:
            print("FAIL  SPEC.md's Appendix B is out of date")
            print("      run: python3 tools/gen_appendix_b.py")
            return 1
        print("ok    SPEC.md's Appendix B is current")
        return 0
    # newline="\n" explicitly: this repository pins LF (.gitattributes), and a
    # generator that emitted CRLF on Windows would fail its own --check against
    # an LF checkout while passing on Linux.
    SPEC.write_text(content, encoding="utf-8", newline="\n")
    print("wrote SPEC.md Appendix B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
