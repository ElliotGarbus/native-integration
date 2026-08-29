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


def parse_record(text: str) -> list[str]:
    return [line for line in text.replace("\r\n", "\n").split("\n") if line]


def compare_records(expected: str, actual: str, *, ignore_digests: bool) -> list[str]:
    """The whole comparison: two sorted sets of facts, diffed."""

    def normalize(lines: list[str]) -> list[str]:
        if not ignore_digests:
            return lines
        out = []
        for line in lines:
            parts = [
                p.split("=", 1)[0] + "=<digest>"
                if p.split("=", 1)[0] in ("sha256", "checksum")
                else p
                for p in line.split(" ")
            ]
            out.append(" ".join(parts))
        return out

    want = normalize(parse_record(expected))
    got = normalize(parse_record(actual))

    if got != sorted(got):
        return ["the record is not in sorted order, which §1 of record-format.md requires"]
    if len(set(got)) != len(got):
        return ["the record repeats a fact; each is stated exactly once"]

    problems = []
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
                expected_record.read_text(encoding="utf-8"),
                reported.get("record", ""),
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
