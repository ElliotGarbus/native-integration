"""The two things a build tool holds after `read()` that the record alone held.

Both were found by writing `src/README.md`'s consumer section against the real
surface. A caller that ran `discover()` first had to splice its findings into
`integration.findings.items`; and the merged results a build tool writes -- a
permission with the widest ceiling, minus the ones the application suppressed
-- existed only as `effective` lines in the record, so the loop the document
taught (`for p in entry.sidecar.entries("contributes", "permissions")`) would
have written a suppressed permission into the manifest.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from native_integration import (
    Answer, Application, Closure, Findings, load_registry, read, source_from_path,
)

SIDECAR = """contract = "1"

[[android.contributes.permissions]]
name = "android.permission.INTERNET"
reason = "Reaching the vendor's API"

[[android.contributes.permissions]]
name = "android.permission.ACCESS_COARSE_LOCATION"
reason = "Regional endpoint selection"

[[android.contributes.permissions]]
name = "android.permission.BLUETOOTH"
reason = "Legacy discovery"
max_sdk_version = 30
"""


@pytest.fixture
def source(tmp_path: Path):
    root = tmp_path / "pyvendor" / "_native"
    root.mkdir(parents=True)
    (root / "native.toml").write_text(SIDECAR, encoding="utf-8", newline=chr(10))
    return source_from_path(root, distribution="pyvendor", version="1.0.0")


def test_effective_is_the_merge_with_suppression_applied(source):
    """§6.5: a suppressed permission is absent from the effective merged
    manifest. `resolved` still lists it -- it was contributed -- and a consumer
    writing from `resolved` would register it anyway."""
    integration = read(
        [source], platform="android", closure=Closure.direct("pyvendor"),
        application=Application(
            android={"min_sdk": 26},
            suppressed_permissions={
                "android.permission.ACCESS_COARSE_LOCATION": Answer(date="2026-09-01"),
            },
            initial_acceptance=Answer(date="2026-09-01"),
        ),
    )
    assert integration.ok, integration.report()

    contributed = [
        p["name"]
        for entry in integration.resolved
        for p in entry.sidecar.entries("contributes", "permissions")
    ]
    assert "android.permission.ACCESS_COARSE_LOCATION" in contributed

    effective = {fact.positionals[1]: dict(fact.keyed) for fact in integration.effective("permission")}
    assert set(effective) == {"android.permission.INTERNET", "android.permission.BLUETOOTH"}
    assert effective["android.permission.BLUETOOTH"]["max-sdk"] == "30"
    assert "max-sdk" not in effective["android.permission.INTERNET"]
    assert effective["android.permission.INTERNET"]["distributions"] == "pyvendor"


def test_effective_of_an_unknown_kind_is_empty(source):
    integration = read([source], platform="android", closure=Closure.direct("pyvendor"),
                       application=Application(initial_acceptance=Answer(date="2026-09-01")))
    assert integration.effective("no-such-thing") == ()


def test_read_takes_the_callers_findings(source):
    """Discovery's findings happen before the read and belong in front of it.
    Handing `read()` the same object is what makes that true without the
    caller splicing two lists."""
    registry = load_registry()
    mine = Findings(registry)
    mine.requirement(4, "pyvendor", message="pretend discovery found something first")

    integration = read([source], platform="android", closure=Closure.direct("pyvendor"),
                       application=Application(initial_acceptance=Answer(date="2026-09-01")),
                       findings=mine)
    assert integration.findings is mine
    assert integration.findings.items[0].message == "pretend discovery found something first"
    assert len(integration.findings.items) > 1, "the read's own findings followed"


def test_read_without_findings_makes_its_own(source):
    a = read([source], platform="android", closure=Closure.direct("pyvendor"))
    b = read([source], platform="android", closure=Closure.direct("pyvendor"))
    assert a.findings is not b.findings
