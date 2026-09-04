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

import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "conformance"))

import consumer  # noqa: E402
import run as harness  # noqa: E402

from native_integration import advisories  # noqa: E402

CORPUS = ROOT / "conformance"

#: What the reader does not do yet, and why. The reason is the specification's
#: name for the missing work rather than "TODO", so that the list reads as a
#: statement about coverage instead of a snooze button.
#:
#: What remains needs §9.1's `accepted.record` — the last accepted state,
#: without which no single run can show a delta.
UNIMPLEMENTED: dict[str, str] = {}


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

    # §8.5 is a SHOULD, so an advisory a case names and the reader does not
    # offer is unsupported rather than wrong, and an extra one is a consumer
    # being more helpful than the case asked for. What is checked is the reader
    # not losing an advisory it does claim.
    offered = {entry["id"] for entry in findings.as_advisories()}
    for entry in spec.get("advisories", []):
        code = entry["id"].rsplit(".", 1)[-1]
        if code in advisories.claimed():
            assert entry["id"] in offered


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


# --- the harness itself ------------------------------------------------------
# Everything above runs the consumer in-process, which skips two things a real
# conformance claim rests on: `run.py`'s own comparison of the emitted record
# against `expected/<platform>.record`, and its assertion adapters. Both live in
# the harness by design — it is the authority, and a test that reimplemented the
# record comparison would be checking the reader against a second implementation
# of the thing being tested.
#
# So this shells out to it, and pins the outcome exactly.

#: Every case run the reader cannot answer, and the assertion that stops it.
#: All six are about generated output, which a reader does not produce. Pinning
#: the set rather than a count is the point: a case that becomes unverified is a
#: regression, and one that stops being unverified needs this list shortened.
UNVERIFIED = {
    ("core/R01_dependency_closure", "sidecar_excluded_from_payload"),
    ("android/R30_view_link_passthrough", "view_link_attributes_written_through"),
    ("android/R41_artifact_feature_decided", "artifact_feature_decision_applied"),
    ("ios/R36_python_module_registered", "python_module_stubs_excluded"),
    ("ios/R37_objc_categories_union", "objc_categories_linked"),
}

SUMMARY = re.compile(
    r"^(\d+) passed, (\d+) failed, (\d+) unverified, (\d+) unsupported$", re.M
)


@pytest.mark.parametrize("profile", ("core", "android", "ios"))
def test_the_harness_reports_no_failure_and_only_the_known_unverified(profile):
    finished = subprocess.run(
        [sys.executable, str(ROOT / "conformance" / "run.py"), "--profile", profile,
         sys.executable, str(ROOT / "conformance" / "consumer.py")],
        capture_output=True, text=True, cwd=ROOT,
    )
    report = finished.stdout + finished.stderr

    summary = SUMMARY.search(report)
    assert summary, f"the harness printed no summary:\n{report}"
    passed, failed, unverified, _unsupported = (int(n) for n in summary.groups())

    assert failed == 0, report
    assert passed, "the profile ran nothing, so it proved nothing"

    # Every assertion line under every UNVERIFIED case, not the first one: a
    # case can go unverified on two assertions at once, and a regex that read
    # one line after the header counted one and lost the other. A core case
    # runs once per platform, so `core/R01` appears twice; the platform is
    # stripped so the set compares, and the run count is checked separately.
    seen: list[tuple[str, str]] = []
    runs = 0
    for block in re.finditer(
        r"^UNVERIFIED\s+(\S+)(?: \[\w+\])?[^\n]*\n((?:\s+\S[^\n]*\n)*)", report, re.M
    ):
        runs += 1
        for assertion in re.findall(r"^\s+assertion (\w+):", block.group(2), re.M):
            seen.append((block.group(1), assertion))
    unknown = sorted(set(seen) - UNVERIFIED)
    assert not unknown, f"newly unverified: {unknown}\n{report}"
    # And the other direction, which the old test never asked: a pin that no
    # longer goes unverified is a pin that should have been removed -- the
    # library learned to do something, and the list is the record of what it
    # cannot. Only the profiles this run selects can be expected here.
    stale = sorted(
        (case, assertion) for case, assertion in UNVERIFIED
        if case.startswith(f"{profile}/") or (profile != "core" and case.startswith("core/"))
        if (case, assertion) not in set(seen)
    )
    assert not stale, f"pinned as unverified but no longer is: {stale}\n{report}"
    assert unverified == runs, report

    # §8.5's note, as the harness applies it: an unverified run is not a pass.
    assert finished.returncode == (1 if unverified else 0), report


# -- what the harness says about an answer that is not one --------------------
# Found by pointing the corpus at a toy build tool that prints prose for a
# human. It failed all 41 cases, correctly, and said "stdout is not valid
# UTF-8: … byte 0xa7 in position 78" -- which sends the author of a program that
# was never answering this interface looking for an encoding bug.


class _Completed:
    def __init__(self, stdout: bytes, stderr: bytes = b"", returncode: int = 0):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


def _answer(monkeypatch, tmp, stdout: bytes, stderr: bytes = b"", code: int = 0):
    monkeypatch.setattr(
        harness.subprocess, "run",
        lambda *a, **k: _Completed(stdout, stderr, code),
    )
    case = harness.load_cases("core", {"android"})[0]
    return harness.run_consumer(["x"], case, tmp)


def test_prose_is_reported_as_prose_not_as_an_encoding_error(monkeypatch, tmp_path):
    """Console-codepage prose is not JSON *and* not UTF-8. The first is the
    headline: the second says nothing about which mistake was made."""
    _, reported = _answer(
        monkeypatch, tmp_path, ("[advisory] " + chr(0xA7) + "6.5 ok").encode("cp1252")
    )
    said = reported["_malformed"]
    assert said.startswith("this interface takes one JSON object on stdout")
    assert "advisory" in said
    assert "not valid UTF-8" in said, "the encoding defect is still reported, second"


def test_a_json_answer_in_bad_bytes_is_still_an_encoding_defect(monkeypatch, tmp_path):
    """The strict decode is deliberate: a consumer that ships non-UTF-8 in a
    field nothing reads should hear about it."""
    _, reported = _answer(
        monkeypatch, tmp_path,
        ('{"outcome": "accept", "why": "' + chr(0xA7) + '6.5"}').encode("cp1252"),
    )
    assert reported["_malformed"].startswith("stdout is not valid UTF-8")


def test_a_good_answer_is_returned_unchanged(monkeypatch, tmp_path):
    _, reported = _answer(
        monkeypatch, tmp_path, b'{"outcome": "accept", "diagnostics": []}'
    )
    assert reported == {"outcome": "accept", "diagnostics": []}


def test_what_a_consumer_wrote_is_safe_to_print():
    """The harness prints its report to a console whose encoding it does not
    choose. Echoing a consumer's bytes back verbatim turned a failed case into
    a traceback out of the harness on a cp1252 console."""
    messy = "caf" + chr(233) + " " + chr(0xFFFD) + chr(10) + "  x"
    assert harness.quoted(messy) == "caf? ? x"
    assert len(harness.quoted("a" * 500)) == 200


# -- an attestation the corpus does not define ----------------------------------
# Found by a toy consumer attesting `action_text_reaches_the_report`, a name no
# case uses. The harness ignored it. A misspelt attestation that should have
# matched a case fails that case as "unverified", for a reason its author
# cannot see from the report.


def test_an_unknown_attestation_is_refused_by_name():
    said = harness.malformed({"outcome": "accept", "assertions": {"action_text_reaches_the_report": True}})
    assert said is not None
    assert "action_text_reaches_the_report" in said


def test_a_documented_attestation_is_accepted():
    assert harness.malformed({"outcome": "accept", "assertions": {"instructions_attributed_to_producer": True}}) is None


def test_the_harness_knows_every_verified_and_attested_name():
    """The two halves of README.md's table, and nothing outside them."""
    known = set(harness.VERIFIED_ASSERTIONS) | set(harness.ATTESTED_ASSERTIONS)
    assert "record_omits" in known, "the one row that names two names two"
    assert "outcome" not in known, "a case.toml field is not an assertion"
