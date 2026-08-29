#!/usr/bin/env python3
"""Generate contract/diagnostics-v1.toml — the stable diagnostic ID list.

**Why IDs at all.** A failure that says *`configuration` must be one of …* tells
an author what is wrong and not which paragraph decides it. An ID turns the
failure into a retrievable rule: `native-integration explain` resolves it to the
rule text, the section anchor, and a minimal correct fragment, so an author —
human or agent — repairs against one paragraph instead of re-reading §6.

**Why generated.** Hand-written IDs drift from the rules they name, and two
consumers that invent their own cannot compare findings. These are derived from
`contract/v1.toml` and from SPEC.md §8, so a rule cannot exist without an ID and
an ID cannot outlive its rule.

**Why these IDs are stable.** Every ID is keyed to a *name* — a declaration id, a
requirement number, an advisory identifier — never to a position. Inserting a
declaration renumbers nothing, which is the property an ID has to have before
anyone can cite one in a bug report.

Three families:

* `ni.decl.<declaration-id>.<check>` — structural, from the registry;
* `ni.constraint.<scope>.<field>.<rule>.<other>` — the between-key rules, named
  by both keys because one field can carry two of them;
* `ni.req.<n>` and `ni.adv.<Sn>` — §8's numbered requirements and its SHOULD
  list, which is where the semantic rules a schema cannot reach are counted.

    python3 tools/gen_error_ids.py          # write the list
    python3 tools/gen_error_ids.py --check  # fail if it is out of date
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "contract" / "v1.toml"
SPEC = ROOT / "SPEC.md"
OUTPUT = ROOT / "contract" / "diagnostics-v1.toml"

BLOCKING, ADVISORY = "blocking", "advisory"

#: One check per registry property that can fail on its own, with the summary
#: `explain` renders. `{id}` is the declaration id.
DECLARATION_CHECKS: tuple[tuple[str, str, str], ...] = (
    ("required", "missing", "`{id}` is required and is absent"),
    ("type", "type", "`{id}` is not of the type this declaration takes"),
    ("values", "value", "`{id}` names a value outside its closed vocabulary"),
    ("pattern", "pattern", "`{id}` does not match the form this declaration fixes"),
    ("min_items", "empty", "`{id}` is empty, and an empty list is invalid here"),
    ("only_true", "false", "`{id}` is declared `false`, and only `true` says anything"),
    ("forbidden", "forbidden", "`{id}` must not be declared by a producer"),
    ("unique_within", "duplicate", "`{id}` repeats a value that must be unique"),
    ("resolves_to", "unresolved", "`{id}` names something the same sidecar does not declare"),
    ("scheme", "scheme", "`{id}` is not an `https` URL"),
    ("valid_when", "invalid-context", "`{id}` is declared where it is not valid"),
    ("value_platforms", "wrong-platform", "`{id}` names a value belonging to the other platform"),
)

CONTAINER_CHECKS: tuple[tuple[str, str, str], ...] = (
    ("exactly_one_of", "exactly-one-of", "`{id}` declares both or neither of {choices}"),
    ("at_least_one_of", "at-least-one-of", "`{id}` declares neither of {choices}"),
)

CONSTRAINT_SUMMARY = {
    "required_unless_equals": "`{field}` is required unless `{other}` is `{value}`",
    "forbidden_if_equals": "`{field}` must be absent when `{other}` is `{value}`",
    "required_if_present": "`{field}` is required when `{other}` is declared",
    "forbidden_if_present": "`{field}` must be absent when `{other}` is declared",
    "requires_equals": "`{field}` is valid only where `{other}` is `{value}`",
}


def requirement_text() -> dict[int, str]:
    """§8.4's numbered requirements, from SPEC.md itself."""
    spec = SPEC.read_text(encoding="utf-8")
    block = spec.split("A conforming consumer **MUST**:")[1].split("### 8.5")[0]
    found: dict[int, str] = {}
    for match in re.finditer(r"^(\d+)\.\s(.*?)(?=^\d+\.\s|\Z)", block, re.M | re.S):
        body = re.split(r"\n\s*>", match.group(2))[0]
        found[int(match.group(1))] = " ".join(body.split()).replace("**", "")
    return found


def advisory_text() -> dict[str, tuple[str, str]]:
    """§8.5's SHOULD list, which is a table rather than a bullet list."""
    spec = SPEC.read_text(encoding="utf-8")
    block = spec.split("### 8.5 Advisory obligations")[1].split("\n## ")[0]
    found: dict[str, tuple[str, str]] = {}
    for line in block.splitlines():
        match = re.match(r"^\|\s*\*\*(S\d+)\*\*\s*\|\s*(.+?)\s*\|\s*\[§([\d.]+)\]", line)
        if match:
            found[match.group(1)] = (
                " ".join(match.group(2).split()).replace("**", ""),
                match.group(3),
            )
    return found


def profiles() -> dict[int, str]:
    """§8.1's profile table, so a diagnostic knows which profile owns it."""
    spec = SPEC.read_text(encoding="utf-8")
    block = spec.split("### 8.1 Conformance is per platform")[1].split("### 8.2")[0]
    found: dict[int, str] = {}
    for line in block.splitlines():
        match = re.match(r"^\|\s*\*\*(Core|Android|iOS)\*\*.*?\|\s*([\d,\s–-]+)\s*\|", line)
        if not match:
            continue
        for span in match.group(2).split(","):
            span = span.strip().replace("–", "-")
            if "-" in span:
                low, high = (int(x) for x in span.split("-"))
                found.update({n: match.group(1).lower() for n in range(low, high + 1)})
            elif span:
                found[int(span)] = match.group(1).lower()
    return found


def anchor_of(section: str, spec: str) -> str:
    """The anchor SPEC.md's own headings produce for a section number."""
    match = re.search(rf"^#{{2,3}} {re.escape(section)}\.? (.+)$", spec, re.M)
    if not match:
        return ""
    text = f"{section} {match.group(1)}".lower()
    return re.sub(r"[^a-z0-9 -]", "", text).replace(" ", "-")


def escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def build() -> str:
    registry = tomllib.loads(REGISTRY.read_text(encoding="utf-8"))
    spec = SPEC.read_text(encoding="utf-8")
    lines = [
        "# Stable diagnostic IDs for contract 1. GENERATED — do not edit.",
        "#",
        "# Written by tools/gen_error_ids.py from contract/v1.toml and SPEC.md §8.",
        "# Every ID is keyed to a name rather than a position, so adding a rule",
        "# renumbers nothing and an ID stays citable across revisions.",
        "#",
        "# `native-integration explain <id>` resolves each of these to its rule",
        "# text, its section anchor, and a minimal correct fragment.",
        "",
    ]

    seen: set[str] = set()

    def emit(identifier: str, **fields: object) -> None:
        # Two rules sharing an ID would make `explain` ambiguous and a cited
        # failure unresolvable, which is the one thing these IDs exist to avoid.
        if identifier in seen:
            raise SystemExit(f"duplicate diagnostic id {identifier!r}")
        seen.add(identifier)
        lines.append(f'[diagnostics."{identifier}"]')
        for key, value in fields.items():
            if isinstance(value, str):
                lines.append(f'{key} = "{escape(value)}"')
            else:
                lines.append(f"{key} = {str(value).lower()}")
        lines.append("")

    for declaration_id, entry in registry["declarations"].items():
        checks = DECLARATION_CHECKS if entry["node"] == "field" else CONTAINER_CHECKS
        for prop, check, summary in checks:
            # A falsy property is not a rule: `required = false` says a key is
            # optional, which nothing can violate.
            if not entry.get(prop):
                continue
            choices = entry[prop] if isinstance(entry[prop], list) else []
            emit(
                f"ni.decl.{declaration_id}.{check}",
                declaration=declaration_id,
                section=entry["section"],
                anchor=entry["anchor"],
                severity=BLOCKING,
                summary=summary.format(
                    id=declaration_id, choices=", ".join(f"`{c}`" for c in choices)
                ),
            )
        if entry["node"] in ("table", "array_of_tables"):
            emit(
                f"ni.decl.{declaration_id}.unknown-key",
                declaration=declaration_id,
                section="4.4",
                anchor="44-unknown-declarations-fail-closed",
                severity=BLOCKING,
                summary=f"`{declaration_id}` carries a key this specification does not define",
            )

    for rule in registry["constraints"]:
        emit(
            f"ni.constraint.{rule['scope']}.{rule['field']}"
            f".{rule['rule'].replace('_', '-')}.{rule['other']}",
            declaration=f"{rule['scope']}.{rule['field']}",
            section=rule["section"],
            anchor=anchor_of(rule["section"], spec),
            severity=BLOCKING,
            summary=CONSTRAINT_SUMMARY[rule["rule"]].format(
                field=rule["field"], other=rule["other"], value=rule.get("value")
            ),
        )

    profile = profiles()
    for number, text in sorted(requirement_text().items()):
        emit(
            f"ni.req.{number}",
            requirement=number,
            profile=profile.get(number, ""),
            section="8.4",
            anchor="84-requirements",
            severity=BLOCKING,
            summary=text,
        )

    for identifier, (text, section) in sorted(advisory_text().items()):
        emit(
            f"ni.adv.{identifier}",
            advisory=identifier,
            section=section,
            anchor=anchor_of(section, spec),
            severity=ADVISORY,
            summary=text,
        )

    return "\n".join(lines).rstrip("\n") + "\n"


def main() -> int:
    content = build()
    if "--check" in sys.argv:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != content:
            print(f"FAIL  {OUTPUT.relative_to(ROOT)} is out of date")
            print("      run: python3 tools/gen_error_ids.py")
            return 1
        print(f"ok    {OUTPUT.relative_to(ROOT)} is current")
        return 0
    # newline="\n" explicitly: this repository pins LF (.gitattributes), and a
    # generator that emitted CRLF on Windows would fail its own --check against
    # an LF checkout while passing on Linux.
    OUTPUT.write_text(content, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
