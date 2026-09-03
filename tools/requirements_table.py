#!/usr/bin/env python3
"""Generate docs/REQUIREMENTS.md from the registry and the reader's own source.

The point of a reference reader is that a consumer's obligations are code paths
rather than prose it has to remember. That claim is only worth something if the
mapping is **derived**, so nothing here is transcribed: the obligations come
from [`contract/diagnostics-v1.toml`](../src/native_integration/contract/diagnostics-v1.toml), which
`gen_error_ids.py` generates from SPEC.md §8, and the discharging code comes out
of the modules' own syntax trees.

Two things cannot be derived and are declared instead, with the reason attached
to each: an obligation a *reading* library cannot discharge because it binds a
consumer where it generates a project, and one discharged by the shape of the
API rather than by a check.

    python3 tools/requirements_table.py          # rewrite docs/REQUIREMENTS.md
    python3 tools/requirements_table.py --check  # fail if it is out of date
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from native_integration import obligations, registry  # noqa: E402

PACKAGE = ROOT / "src" / "native_integration"
OUTPUT = ROOT / "docs" / "REQUIREMENTS.md"

#: An obligation that binds a consumer where it **generates a project** —
#: compiling contributed source, writing the manifest, assembling the payload.
#: This library reads sidecars and computes a resolution; it builds nothing, so
#: these are named rather than left as a blank a later reader would mistake for
#: an oversight.
BEYOND_THE_READER = {
    6: "the payload is assembled by the build tool, not here",
    12: "the last clause: which findings a report sets apart is its layout. §5.1 "
    "asks for a declared `target_sdk` to get the prominence a repository "
    "contribution gets, and the one standing channel this reader has for that "
    "is S9's advisory — which an obligation stated as a MUST cannot use, "
    "because §8.5 lets a consumer decline an advisory",
    20: "the scaffolding clause: an acknowledgement is scaffolded into a file "
    "this reader does not write, so whether it is commented out is decided "
    "where the writing happens",
    24: "the payload again",
    28: "honoring a suppression in the merged manifest, and promoting a "
    "feature in it, are the build tool's",
    30: "the attributes are carried into the record here; writing them into the "
    "manifest is the build tool's",
    31: "the last clause: keeps are validated here and *applied* by the build "
    "tool. §6.7 conditions applying them on the application having enabled "
    "shrinking, which nothing tells this reader and which validating a pattern "
    "does not depend on",
    34: "the declaration is checked here; the privacy manifest is generated, not read",
    35: "the refusal and the conflicts are enforced here; writing the Info.plist "
    "is the build tool's",
    36: "the duplicate `name`, the identifier rule, and the `products` a "
    "registration resolves to are checked here. Linking those products into "
    "the application target, registering the module before interpreter "
    "initialization, and excluding `<name>.py` and `<name>.pyi` from the "
    "payload are all the build tool's",
    37: "the union is recorded here; linking it is the build tool's",
    39: "writing the record to disk is the tool's; producing it is `recording.py`",
    45: "the bootstrap's own activity, which this library neither writes nor sees",
    46: "the bootstrap again",
}

#: Discharged by the shape of the API rather than by a check, which is stronger
#: than a check: there is no call site at which it can be forgotten. Several of
#: §8.4's obligations are prohibitions, and the way to discharge a prohibition
#: is to have no code that could violate it.
STRUCTURAL = {
    1: "`reader.read` skips a source the `Closure` does not contain, and this "
    "library offers no way to build a `Closure` from what is installed — a "
    "convenience that evaluated markers against this interpreter would be the "
    "one code path able to violate the requirement",
    3: "nothing in this package imports a producing distribution or executes "
    "any sidecar content; a sidecar is TOML read as data",
    9: "the second sentence: `reader.read` raises `UnimplementedProfile` for a "
    "platform outside the caller's `profiles`, before a sidecar is opened, so "
    "a partial resolution for it is never produced",
    10: "`Application` is that way — one field per row of §2.2's table, joined "
    "as §2.2 joins it",
    15: "there is no code path that inspects the application's project, so an "
    "observation cannot be mistaken for an answer",
    16: "the reader produces findings and a record, and writes no "
    "application-owned artifact of any kind",
    20: "the prohibition: this library writes no file at all, so there is no "
    "code path that could modify one the application owns — which is how a "
    "prohibition is discharged",
    18: "`Finding.__post_init__` rejects a finding that names no distribution",
    19: "`discovery.py` enumerates `contract.ENTRY_POINT_GROUP` and nothing "
    "else, so a group for another major version is never read — nor named "
    "anywhere it could be",
    42: "`Credential.__repr__` keeps the locator out of a traceback, and no "
    "credential value is passed to `Record` anywhere",
}

#: Discharged by the *content* of what the reader produces rather than by a
#: check it performs. A handful of §8.4's obligations are about what a report
#: or a record has to carry, and nothing refuses a sidecar over them, so no
#: `findings.requirement` call names the number and the syntax tree cannot see
#: it. Named here with the code that does the work and the test that holds it,
#: because "the module mentions the number" is the wrong evidence for a clause
#: about content.
IN_WHAT_IT_PRODUCES = {
    11: "`integration._addressed_to_a_person` puts an action's `summary`, "
    "`instructions` and `acceptance` into the finding's detail, and "
    "`integration._floors` the declared and configured values for a floor, "
    "which carries no `reason` (`tests/test_actions.py`)",
    21: "the same lines each name the declaring distribution rather than "
    "reading as this consumer's own guidance, and `native.toml` is a hashed "
    "input of the record (`tests/test_actions.py`)",
    28: "the first clause: `semantics._permissions` merges `max_sdk_version` "
    "and `never_for_location` least-restrictively across the closure and "
    "writes one `effective permission` fact naming every distribution that "
    "asked (`conformance/android/R28_permission_attributes_merged`)",
    43: "`recording.py`'s fact vocabulary and `integration.decisions` — every "
    "value and action with its state, and each suppression, approval, feature "
    "decision and path choice with what it affected and its date "
    "(`conformance/record-format.md`)",
}

#: A requirement one of the two tables above claims *and* a check reports.
#: Ordinarily that combination is the double-counting `tests/test_requirements
#: .py` exists to catch — "structural" means there is no call site at which the
#: obligation can be forgotten, and a check is a call site. It is legitimate
#: only where the requirement has clauses of both kinds, and then it has to say
#: which clause is which.
SPLIT = {
    9: "the `platforms` key is a check on a sidecar; refusing a profile this "
    "consumer does not implement is a refusal at the API boundary, and §8.4 "
    "states them in one requirement as two sentences",
    28: "the feature clauses are checks and refuse a sidecar; the permission "
    "merge refuses nothing and is a fact in the record",
}

HEADER = """# Where each consumer obligation lives

Every obligation in [§8 of the specification](../SPEC.md#8-consuming-tool-requirements), against
the code path in [`native_integration`](../src/native_integration/) that
discharges it.

**Generated** by `python3 tools/requirements_table.py`, and CI fails if it
drifts. The obligations are read from
[`contract/diagnostics-v1.toml`](../src/native_integration/contract/diagnostics-v1.toml) and the code
paths out of the modules' syntax trees, so neither column is transcribed. An
obligation nothing discharges appears as `—` and fails
`tests/test_requirements.py`.

Four kinds of entry:

- a **module** discharges the obligation with a check that produces a finding.
- **structural** marks one discharged by the shape of the API rather than by a
  check — you cannot construct a `Finding` without naming a distribution, so
  requirement 18 has no call site at which it can be forgotten.
- **in what it produces** marks one about the *content* of a report or a
  record rather than about accepting or refusing a sidecar. Nothing fails when
  these are unmet, so no `findings.requirement` call names them and the syntax
  tree cannot see them; the note names the code and the test instead.
- **beyond this reader** marks one that binds a consumer where it *generates a
  project*. This library reads, validates, resolves and records; it builds
  nothing, and says so rather than leaving a blank.

An obligation whose clauses fall in more than one of those carries more than
one entry. Requirement 30 is split because the attributes are validated here
and written into the manifest elsewhere; requirement 9 is split because the
`platforms` key is a check and refusing an unimplemented profile is not. A row
naming a module claims **every** clause of that requirement is discharged by it,
which is why the split is worth the noise.

That claim is strong enough to be worth stating twice: 12, 20, 31 and 36 each
carried a clause about generating a project inside a row that named a module,
and a reader that validates a keep pattern has not applied it. Four entries were
added rather than four clauses implemented, because the clauses are the build
tool's — but a table that says so is the difference between a gap and a lie.

Structural validation is not listed rule by rule. `structure.py` walks a sidecar
against [`contract/v1.toml`](../src/native_integration/contract/v1.toml), so every check the registry
defines is a check it performs, and `obligations.py` maps each one to the
obligation it answers to. That mapping is the only hand-derived table in the
library, and `tests/test_obligations.py` holds it to every id the generators
emit.

| §8.4 | The obligation | Discharged by |
| --- | --- | --- |"""


def discharged() -> dict[int, set[str]]:
    """Which module reports which obligation, out of the modules' own syntax.

    A `findings.requirement(N, …)` call names its obligation directly, whether
    as a literal or through one of the module's named constants. A
    `findings.rule(…)` call resolves through the registry instead, so
    `structure.py` is credited with the whole image of the obligations mapping
    rather than with a list this tool would have to keep in step.

    An `obligation=N` keyword counts too. Where two sections state the same
    rule for different material — §6.8's `<meta-data>` and §7.4's `Info.plist`
    settle a contested key identically — the check is written once and told
    which obligation it is discharging, and the call site naming the constant
    is the module reporting it just as directly as the call inside would be.
    """
    found: dict[int, set[str]] = {}
    for path in sorted(PACKAGE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        constants = {
            target.id: node.value.value
            for node in tree.body
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
            for target in node.targets
            if isinstance(target, ast.Name) and isinstance(node.value.value, int)
        }
        helpers = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            named: list[ast.expr] = [
                keyword.value for keyword in node.keywords if keyword.arg == "obligation"
            ]
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "requirement"
                and node.args
            ):
                named.append(node.args[0])
            for argument in named:
                for number in _numbers(argument, constants, helpers):
                    found.setdefault(number, set()).add(path.stem)
    return found


def _numbers(
    node: ast.expr, constants: dict[str, int], helpers: dict[str, ast.FunctionDef]
) -> set[int]:
    """Every obligation this expression can name.

    A literal or a named constant names one. A call to a local helper names
    whichever its returns do — §4.1's two failures answer to different
    requirements and `integration.py` chooses between them in a function, which
    is the right place for the choice and would otherwise read here as a gap.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return {node.value}
    if isinstance(node, ast.Name) and node.id in constants:
        return {constants[node.id]}
    if isinstance(node, ast.IfExp):
        return _numbers(node.body, constants, helpers) | _numbers(
            node.orelse, constants, helpers
        )
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        helper = helpers.get(node.func.id)
        if helper is not None:
            return {
                number
                for statement in ast.walk(helper)
                if isinstance(statement, ast.Return) and statement.value is not None
                for number in _numbers(statement.value, constants, helpers)
            }
    return set()


def structural_image() -> set[int]:
    """Every obligation the registry-driven validator can report."""
    return (
        set(obligations.BY_CHECK.values())
        | set(obligations.BY_FAMILY.values())
        | set(obligations.BY_DECLARATION_CHECK.values())
        | set(obligations.BY_CONSTRAINT.values())
    )


def advisories_offered() -> dict[str, str]:
    """The advisory codes this reader offers, against the module reporting each."""
    from native_integration import advisories  # noqa: PLC0415

    return dict(advisories.claimed())


def build() -> str:
    contract = registry.load()
    by_module = discharged()
    for number in structural_image():
        by_module.setdefault(number, set()).add("structure")

    numbers = sorted(
        int(identifier.rsplit(".", 1)[-1])
        for identifier in contract.diagnostics
        if identifier.startswith("ni.req.")
    )

    lines = [HEADER]
    for number in numbers:
        about = contract.about(contract.requirement_id(number))
        parts = [f"`{name}.py`" for name in sorted(by_module.get(number, ()))]
        where = ", ".join(parts)
        for label, table in (
            ("structural", STRUCTURAL),
            ("in what it produces", IN_WHAT_IT_PRODUCES),
            ("beyond this reader", BEYOND_THE_READER),
        ):
            if number in table:
                note = f"*{label}* — {table[number]}"
                where = f"{where}<br>{note}" if where else note
        lines.append(f"| {number} | {_prose(about['summary'])} | {where or '—'} |")

    offered = advisories_offered()
    lines += [
        "",
        "## Advisory obligations (§8.5)",
        "",
        "Reported, never blocking. §8.5 is a **SHOULD** precisely so that a "
        "consumer can say which it offers, and most of these need something a "
        "reader does not have — a linked binary, a merged manifest, a resolved "
        "`.aar`'s contents. Claiming one this library does not offer is how a "
        "conformance claim overstates itself, so the column says *not offered* "
        "rather than leaving a gap.",
        "",
        "| §8.5 | The obligation | Offered |",
        "| --- | --- | --- |",
    ]
    codes = sorted(
        (identifier for identifier in contract.diagnostics if identifier.startswith("ni.adv.")),
        key=lambda i: int(i.rsplit(".", 1)[-1][1:]),
    )
    for identifier in codes:
        code = identifier.rsplit(".", 1)[-1]
        about = contract.about(identifier)
        state = f"`{offered[code]}.py`" if code in offered else "*not offered*"
        lines.append(f"| {code} | {_prose(about['summary'])} | {state} |")

    return "\n".join(lines) + "\n"


def _prose(text: str) -> str:
    """One cell of table prose, from a §8 summary written for SPEC.md.
    
    The summaries cite sections as `[§6.3](#63-gradle-dependencies)`, which
    resolves inside SPEC.md and nowhere else. This file lives in `docs/`, so
    every such link is repointed at `../SPEC.md` -- forty-three of them were
    dead from the day the table was first generated, and the link check never
    read this file to say so.
    """
    flat = " ".join(str(text).split()).replace("**", "").replace("|", "\\|")
    return flat.replace("](#", "](../SPEC.md#")


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
    # newline: this repository pins LF (.gitattributes) and §9.3 hashes file
    # bytes, so a generator emitting CRLF on Windows would fail its own --check
    # against an LF checkout while passing on Linux.
    OUTPUT.write_text(content, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
