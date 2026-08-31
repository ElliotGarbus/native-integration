"""The whole corpus, run against the reader.

`conformance/run.py` is the authority and drives a consumer as a subprocess.
This runs the same reference consumer in-process, over every case, so that a
regression is a named test rather than a line in a harness report — and so that
what is *not* yet implemented is a list rather than a feeling.

A case this reader cannot yet answer is listed in `UNIMPLEMENTED` with the
reason. §8.5's note is the standard being held to here: an obligation quietly
skipped is how a conformance claim overstates itself, so the list is asserted to
be exactly the set that fails, and a case that starts passing fails this file
until it is removed from the list.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "conformance"))

import consumer  # noqa: E402

CORPUS = ROOT / "conformance"

#: What the reader does not do yet, and why. The reason is the specification's
#: name for the missing work rather than "TODO", so that the list reads as a
#: statement about coverage instead of a snooze button.
#:
#: What remains needs §9.1's `accepted.record` — the last accepted state,
#: without which no single run can show a delta.
UNIMPLEMENTED: dict[str, str] = {
    "R26_artifact_checksum_mismatch": "§9.1 compares a resolved digest against "
    "the last accepted record",
    "R38_unaccepted_change": "§9.1's acceptance gate needs the last accepted record",
    "R40_stored_digest_malformed": "§9.3 rejects a stored digest that is not 64 "
    "lowercase hexadecimal characters, which needs the stored record",
}


def cases() -> list[tuple[Path, str]]:
    found = []
    for case in sorted(CORPUS.glob("*/*/case.toml")):
        profile = case.parent.parent.name
        platforms = ("android", "ios") if profile == "core" else (profile,)
        found.extend((case.parent, platform) for platform in platforms)
    return found


def identify(value) -> str:
    return value if isinstance(value, str) else value.name


@pytest.fixture(scope="module")
def corpus():
    return {case: tomllib.loads((case / "case.toml").read_text(encoding="utf-8"))
            for case, _ in cases()}


def expected_ids(spec, key: str) -> set[str]:
    return {entry["id"] for entry in spec.get(key, [])}


@pytest.mark.parametrize("case, platform", cases(), ids=identify)
def test_every_case_reports_exactly_what_it_expects(case, platform, corpus):
    spec = corpus[case]
    base = consumer.input_directory(case, platform)
    if not (base / "closure.toml").exists():
        pytest.skip("the case states no closure for this platform")

    outcome, findings, _ = consumer.run(base, platform)
    reported = {entry["id"] for entry in findings.as_diagnostics()}
    wanted = expected_ids(spec, "diagnostics")

    if case.name in UNIMPLEMENTED:
        if reported == wanted and outcome == spec.get("outcome"):
            pytest.fail(
                f"{case.name} now passes; remove it from UNIMPLEMENTED "
                f"({UNIMPLEMENTED[case.name]})"
            )
        pytest.xfail(UNIMPLEMENTED[case.name])

    assert reported == wanted
    assert outcome == spec.get("outcome")


@pytest.mark.parametrize("case, platform", cases(), ids=identify)
def test_every_diagnostic_names_the_distribution_the_case_names(case, platform, corpus):
    """Requirement 18. Naming the wrong distribution, or none, is the failure the
    requirement exists to prevent — a finding nobody can act on."""
    spec = corpus[case]
    base = consumer.input_directory(case, platform)
    if not (base / "closure.toml").exists() or case.name in UNIMPLEMENTED:
        pytest.skip("not answerable yet")

    reported = {entry["id"]: set(entry["distributions"])
                for entry in consumer.run(base, platform)[1].as_diagnostics()}
    for entry in spec.get("diagnostics", []):
        if entry["id"] in reported:
            assert reported[entry["id"]] == set(entry["distributions"])
