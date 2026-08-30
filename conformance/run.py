#!/usr/bin/env python3
"""Run the conformance corpus against an external consumer.

    python3 conformance/run.py --profile android -- mytool build --conformance-record

For each case in the profile this invokes the consumer once, with the case's
`input/` directory as the application's resolved dependency closure, and
compares what came back against what the case says the specification requires.

**This is not a consumer.** It imports none, implements none, and knows nothing
about sidecars beyond how to compare two records. The reference reader under
`src/` is a separate thing and is not used here — a harness that shared code
with an implementation would be measuring agreement with that implementation,
which is the failure `README.md` opens by naming.

Three axes are checked, per `conformance/README.md`:

* `outcome`     — accept or blocking, the build's fate;
* `diagnostics` — the finding IDs the consumer reported;
* `assertions`  — postconditions on what the consumer produced.

Exit status is 0 when every case passed, 1 when any failed. An assertion the
consumer says it cannot observe is reported **unsupported** and does not pass.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROFILES = ("core", "android", "ios")

PASS, FAIL, UNSUPPORTED = "pass", "fail", "unsupported"


@dataclass
class Case:
    name: str
    profile: str
    directory: Path
    spec: dict

    @property
    def requirement(self) -> str:
        return str(self.spec.get("requirement", "?"))

    @property
    def outcome(self) -> str:
        return self.spec.get("outcome", "accept")

    @property
    def expected_record(self) -> Path | None:
        named = self.spec.get("record")
        if named:
            return self.directory / "expected" / named
        default = self.directory / "expected" / f"{self.spec.get('platform', self.profile)}.record"
        return default if default.exists() else None


@dataclass
class Result:
    case: Case
    status: str
    detail: list[str] = field(default_factory=list)


def load_cases(profile: str) -> list[Case]:
    cases: list[Case] = []
    for path in sorted((ROOT / profile).glob("*/case.toml")):
        cases.append(
            Case(
                name=path.parent.name,
                profile=profile,
                directory=path.parent,
                spec=tomllib.loads(path.read_text(encoding="utf-8")),
            )
        )
    return cases


FACTS = tomllib.loads((ROOT / "record-facts.toml").read_text(encoding="utf-8"))["facts"]

DIGEST = re.compile(r"[0-9a-f]{64}")
DIGEST_KEYS = ("sha256", "checksum")


def read_record(raw: bytes) -> tuple[list[str], list[str]]:
    """The file rules of record-format.md §1, checked rather than assumed.

    A harness that silently repaired CRLF, blank lines or a missing final
    newline would let two consumers disagree about the bytes while agreeing
    about the facts — which is the one thing a byte-comparable format exists to
    prevent.
    """
    problems: list[str] = []
    if raw.startswith(b"\xef\xbb\xbf"):
        problems.append("the record starts with a BOM")
        raw = raw[3:]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return [], [f"the record is not valid UTF-8: {exc}"]
    if "\r" in text:
        problems.append("the record contains a carriage return; lines end with a bare newline")
    if text and not text.endswith("\n"):
        problems.append("the record has no final newline")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            problems.append(f"line {index} is blank; the file is facts and nothing else")
    return lines, problems


BARE = re.compile(r"[A-Za-z0-9._:/@+~*-]+")
KEY = re.compile(r"[a-z0-9_-]+")
ESCAPES = {'"': '"', "\\": "\\", "n": "\n", "t": "\t", "r": "\r"}


class LexError(Exception):
    pass


def scan_scalar(line: str, i: int) -> tuple[str, str, int]:
    """One scalar from `line` at `i`. Returns (decoded, raw, next index).

    Canonicalization is checked here rather than after the fact: the format's
    claim is that one value has one spelling, and a lexer that accepted two
    would let two consumers emit files that differ in bytes and agree in facts.
    """
    if line[i] == '"':
        out: list[str] = []
        j = i + 1
        while True:
            if j >= len(line):
                raise LexError("a quoted value is never closed")
            char = line[j]
            if char == '"':
                j += 1
                break
            if char == "\\":
                if j + 1 >= len(line):
                    raise LexError("a quoted value ends inside an escape")
                marker = line[j + 1]
                if marker in ESCAPES:
                    out.append(ESCAPES[marker])
                    j += 2
                    continue
                if marker == "u":
                    digits = line[j + 2 : j + 6]
                    if len(digits) != 4 or any(d not in "0123456789abcdef" for d in digits):
                        raise LexError(
                            f"`\\u{digits}` is not four lowercase hexadecimal digits"
                        )
                    out.append(chr(int(digits, 16)))
                    j += 6
                    continue
                raise LexError(f"`\\{marker}` is not an escape this format defines")
            if ord(char) < 0x20 or ord(char) == 0x7F:
                raise LexError("a control character is written as an escape, never literally")
            out.append(char)
            j += 1
        decoded = "".join(out)
        if decoded and BARE.fullmatch(decoded):
            raise LexError(f'`{decoded}` is bare, so it is never quoted')
        return decoded, line[i:j], j

    match = BARE.match(line, i)
    if not match:
        raise LexError(f"`{line[i]}` begins no value this format defines")
    return match.group(0), match.group(0), match.end()


def scan_value(line: str, i: int) -> tuple[list[str], int]:
    """A scalar, or a list of two or more of them."""
    members: list[str] = []
    while True:
        decoded, _, i = scan_scalar(line, i)
        members.append(decoded)
        if i < len(line) and line[i] == ",":
            i += 1
            continue
        break
    if len(members) > 1:
        if members != sorted(members):
            raise LexError("a list is sorted bytewise")
        if len(set(members)) != len(members):
            raise LexError("a list is de-duplicated")
    return members, i


def lex(line: str) -> tuple[list[str], dict[str, list[str]]]:
    """A fact as its positional operands and its keyed ones."""
    positional: list[str] = []
    keyed: dict[str, list[str]] = {}
    order: list[str] = []
    i = 0
    while i < len(line):
        if line[i] == " ":
            raise LexError("operands are separated by exactly one space")
        key_match = KEY.match(line, i)
        if key_match and line[key_match.end() : key_match.end() + 1] == "=":
            key = key_match.group(0)
            if key in keyed:
                raise LexError(f"`{key}` appears more than once")
            values, i = scan_value(line, key_match.end() + 1)
            keyed[key] = values
            order.append(key)
        else:
            if keyed:
                raise LexError("a positional operand follows a keyed one")
            decoded, _, i = scan_scalar(line, i)
            positional.append(decoded)
        if i < len(line):
            if line[i] != " ":
                raise LexError("operands are separated by exactly one space")
            i += 1
            if i >= len(line):
                raise LexError("the fact ends in a space")
    if order != sorted(order):
        raise LexError("keyed operands are sorted bytewise by key")
    return positional, keyed


def match_template(positional: list[str]) -> tuple[str, dict, dict[str, str]] | None:
    """The fact type these positionals satisfy, and its placeholder bindings."""
    for name, spec in FACTS.items():
        tokens = spec["template"].split(" ")
        if len(tokens) != len(positional):
            continue
        bindings = {}
        for want, got in zip(tokens, positional):
            if want.startswith("<"):
                bindings[want.strip("<>")] = got
            elif want != got:
                break
        else:
            return name, spec, bindings
    return None


def satisfied(condition: dict, bound: dict[str, list[str]]) -> bool:
    """Whether a conditional rule's `if` half holds for this fact."""
    present = bound.get(condition["key"])
    if present is None:
        return False
    if "values" in condition:
        return any(v in condition["values"] for v in present)
    if "not_values" in condition:
        return all(v not in condition["not_values"] for v in present)
    return True


def validate_fact(line: str) -> list[str]:
    try:
        positional, keyed = lex(line)
    except LexError as problem:
        return [f"{problem}: {line}"]

    matched = match_template(positional)
    if matched is None:
        return [f"no fact type in record-facts.toml has this form: {line}"]
    name, spec, bindings = matched

    problems: list[str] = []
    # Placeholder bindings and keyed operands share one namespace, so a
    # conditional rule may test either.
    bound: dict[str, list[str]] = {k: [v] for k, v in bindings.items()}
    bound.update(keyed)

    allowed = set(spec.get("required", [])) | set(spec.get("optional", []))
    if not spec.get("open_keys"):
        for key in sorted(set(keyed) - allowed):
            problems.append(f"{name} does not take `{key}`: {line}")
    for key in sorted(set(spec.get("required", [])) - set(keyed)):
        problems.append(f"{name} requires `{key}`: {line}")

    for key, allowed_values in spec.get("values", {}).items():
        for value in bound.get(key, []):
            if value not in allowed_values:
                problems.append(
                    f"{name} takes {key}={'|'.join(allowed_values)}, not {value}: {line}"
                )

    for rule in spec.get("rules", []):
        field = rule["field"]
        if "required_if" in rule and satisfied(rule["required_if"], bound) and field not in keyed:
            problems.append(f"{name} requires `{field}` here: {line}")
        if "forbidden_if" in rule and satisfied(rule["forbidden_if"], bound) and field in keyed:
            problems.append(f"{name} does not take `{field}` here: {line}")

    for key in DIGEST_KEYS:
        for value in keyed.get(key, []):
            if not DIGEST.fullmatch(value):
                problems.append(
                    f"{key} is not 64 lowercase hexadecimal characters, "
                    f"which §9.3 requires: {line}"
                )
    return problems


def elide_digests(lines: list[str]) -> list[str]:
    """Drop digest *content*, never digest syntax.

    `ignore_digests` exists so that a case about namespace collision is not also
    a test of file hashing. It is not a licence to emit `sha256=garbage`, so the
    syntax is validated in `validate_fact` before anything is elided here.
    """
    out = []
    for line in lines:
        out.append(
            " ".join(
                f"{token.split('=', 1)[0]}=<digest>"
                if token.split("=", 1)[0] in DIGEST_KEYS and "=" in token
                else token
                for token in line.split(" ")
            )
        )
    return out


def compare_records(expected: bytes, actual: bytes, *, ignore_digests: bool) -> list[str]:
    """The whole comparison: two sorted sets of valid facts, diffed."""
    want, problems = read_record(expected)
    if problems:
        return [f"the case's own expected record is malformed: {p}" for p in problems]
    got, problems = read_record(actual)
    if problems:
        return problems

    for line in got:
        problems.extend(validate_fact(line))
    if problems:
        return problems

    if got != sorted(got):
        return ["the record is not in sorted order, which record-format.md §1 requires"]
    if len(set(got)) != len(got):
        return ["the record repeats a fact; each is stated exactly once"]

    if ignore_digests:
        want, got = elide_digests(want), elide_digests(got)

    for line in sorted(set(want) - set(got)):
        problems.append(f"missing: {line}")
    for line in sorted(set(got) - set(want)):
        problems.append(f"unexpected: {line}")
    return problems


def run_consumer(command: list[str], case: Case) -> tuple[int, dict]:
    """Invoke the consumer for one case, and read what it reported.

    The consumer is handed the case directory and is expected to answer on
    stdout as JSON: its outcome, the diagnostic IDs it raised, the assertions it
    can vouch for, and its conformance record.
    """
    completed = subprocess.run(
        [*command, str(case.directory / "input")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    try:
        return completed.returncode, json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        return completed.returncode, {
            "_malformed": completed.stdout[:400] or completed.stderr[:400]
        }


def check(case: Case, exit_code: int, reported: dict) -> Result:
    problems: list[str] = []
    unsupported: list[str] = []

    if "_malformed" in reported:
        return Result(case, FAIL, [f"the consumer did not answer in JSON: {reported['_malformed']}"])

    # Axis 1 — the build's fate.
    actual_outcome = reported.get("outcome", "blocking" if exit_code else "accept")
    if actual_outcome != case.outcome:
        problems.append(f"outcome: expected {case.outcome}, got {actual_outcome}")

    # Axis 2 — findings.
    for key in ("diagnostics", "advisories"):
        want = set(case.spec.get(key, []))
        got = set(reported.get(key, []))
        for missing in sorted(want - got):
            problems.append(f"{key}: expected {missing}, not reported")
        if key == "diagnostics":
            # An unexpected advisory is a consumer being more helpful than the
            # case asked for; an unexpected blocking diagnostic is not.
            for extra in sorted(got - want):
                problems.append(f"{key}: reported {extra}, which this case does not expect")

    # Axis 3 — postconditions.
    vouched = reported.get("assertions", {})
    for assertion in case.spec.get("assertions", []):
        state = vouched.get(assertion)
        if state is True:
            continue
        if state is None:
            unsupported.append(f"assertion {assertion}: the consumer cannot observe it")
        else:
            problems.append(f"assertion {assertion}: the consumer reports it unmet")

    expected_record = case.expected_record
    if expected_record is not None:
        problems.extend(
            compare_records(
                expected_record.read_bytes(),
                reported.get("record", "").encode("utf-8"),
                ignore_digests=bool(case.spec.get("ignore_digests")),
            )
        )

    if problems:
        return Result(case, FAIL, problems + unsupported)
    if unsupported:
        return Result(case, UNSUPPORTED, unsupported)
    return Result(case, PASS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, action="append", required=True)
    parser.add_argument("--list", action="store_true", help="list cases and exit")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    cases = [case for profile in args.profile for case in load_cases(profile)]
    if not cases:
        print("no cases found for the selected profile(s)")
        return 1

    if args.list:
        for case in cases:
            print(f"{case.profile}/{case.name}  §{case.spec.get('section', '?')}  "
                  f"requirement {case.requirement}  {case.outcome}")
        return 0

    command = [part for part in args.command if part != "--"]
    if not command:
        parser.error("a consumer command is required: … -- mytool build …")

    results = [check(case, *run_consumer(command, case)) for case in cases]

    for result in results:
        print(f"{result.status.upper():12} {result.case.profile}/{result.case.name}"
              f"  (requirement {result.case.requirement})")
        for line in result.detail:
            print(f"             {line}")

    failed = [r for r in results if r.status == FAIL]
    unsupported = [r for r in results if r.status == UNSUPPORTED]
    print(
        f"\n{len(results) - len(failed) - len(unsupported)} passed, "
        f"{len(failed)} failed, {len(unsupported)} unsupported"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
