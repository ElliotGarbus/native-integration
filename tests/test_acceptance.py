"""§9.1's gate, and the first build in particular.

The corpus covers both outcomes through `core/R38_first_build_unaccepted` and
`core/R38_unaccepted_change`. What it cannot express is the interaction between
the gate and a build that is already failing, which is a reading of §9.1 rather
than a line of it, so it is pinned here.
"""

from __future__ import annotations

import pytest

from native_integration import acceptance
from native_integration.application import Answer, Application
from native_integration.findings import Findings
from native_integration.recording import Record
from native_integration.registry import load as load_registry


@pytest.fixture
def findings() -> Findings:
    return Findings(load_registry())


def a_record() -> Record:
    record = Record()
    record.add("dist", "pyexample", "contributes", "permission",
               "android.permission.ACCESS_FINE_LOCATION")
    return record


def numbers(findings: Findings) -> list[str]:
    return [found.obligation for found in findings]


def test_a_first_build_nobody_accepted_is_refused(findings):
    """The reading §9.1 forecloses: "no record yet" is not implicit approval."""
    delta = acceptance.check(a_record(), None, findings=findings, application=Application())
    assert numbers(findings) == ["ni.req.38"]
    assert delta, "everything is new on a first build, so everything is the delta"


def test_the_whole_effective_set_is_reported_rather_than_the_fact_of_a_change(findings):
    """§9.1 asks for the set, not a notification. An application accepting one
    line at a time is the workflow the bootstrap action exists to avoid."""
    acceptance.check(a_record(), None, findings=findings, application=Application())
    detail = findings.items[0].detail
    assert any("android.permission.ACCESS_FINE_LOCATION" in line for line in detail)


def test_the_bootstrap_action_satisfies_it(findings):
    """"A single bootstrap action covering the initial set satisfies this.\""""
    application = Application(initial_acceptance=Answer(date="2026-08-24"))
    delta = acceptance.check(a_record(), None, findings=findings, application=application)
    assert numbers(findings) == []
    assert not delta


def test_the_gate_names_the_distributions_the_surface_came_from(findings):
    acceptance.check(a_record(), None, findings=findings, application=Application())
    assert findings.items[0].distributions == ("pyexample",)


def test_a_build_already_failing_is_not_told_twice(findings):
    """§9.1's lifecycle starts by computing the resolution, and the gate is step
    4 of it. A resolution that failed to compute is not one an application can
    accept, and the author has a diagnostic to act on already."""
    findings.requirement(12, "pyexample", message="the floor is unmet")
    acceptance.check(a_record(), None, findings=findings, application=Application())
    assert numbers(findings) == ["ni.req.12"]


def test_an_empty_first_build_still_needs_accepting(findings):
    """A closure contributing nothing is still a closure the application has not
    seen. Cheap to exempt and wrong: the next dependency added is then the first
    build too, and by then the exemption is load-bearing."""
    acceptance.check(Record(), None, findings=findings, application=Application())
    assert numbers(findings) == ["ni.req.38"]


# -- §9.1's two halves ------------------------------------------------------
# `core/R38_answer_is_not_a_change` covers the outcome end to end. These pin the
# projection itself, line by line, because the split runs through the middle of
# a value or an action rather than around it and that is the part a rewrite is
# likeliest to flatten.

@pytest.mark.parametrize(
    "line, gated",
    [
        # The accepted resolution: every contribution, the inputs, the graphs.
        ("dist pyx contributes permission android.permission.INTERNET",
         "dist pyx contributes permission android.permission.INTERNET"),
        ("dist pyx input native.toml sha256=" + "a" * 64,
         "dist pyx input native.toml sha256=" + "a" * 64),
        ("dist pyx artifact com.vendor:sdk:1.0.0 sha256=" + "b" * 64,
         "dist pyx artifact com.vendor:sdk:1.0.0 sha256=" + "b" * 64),
        # The application's answers, which §9.1 keeps out of the gate.
        ("decision suppress-permission android.permission.ACCESS_FINE_LOCATION"
         " date=2026-08-24 withdrew=pyx", None),
        ("decision approve-export org.pyx.Activity date=2026-08-24"
         " distribution=pyx state=approved", None),
        ("decision artifact-feature android.hardware.camera artifact=com.vendor:sdk:1.0.0"
         " date=2026-08-24 distribution=pyx keep=optional", None),
        ("decision collision META-INF/LICENSE artifacts=com.a:x:1.0.0,com.b:y:2.0.0"
         " chosen=com.a:x:1.0.0 date=2026-08-24 decided=application distributions=pya,pyb",
         None),
        # Not an answer: that a repository needs a credential is a fact about a
        # producer's declaration (§9.5), and a producer newly requiring one is a
        # change the application has to see.
        ("decision credential-required https://maven.vendor.com/releases kind=repository",
         "decision credential-required https://maven.vendor.com/releases kind=repository"),
        # Derived from facts that are gated already, and moved by an answer.
        ("effective permission android.permission.INTERNET distributions=pyx", None),
        # The split runs through the line: the demand is the producer's, the
        # state is the application's.
        ("dist pyx value vendor_key key=com.vendor.KEY kind=manifest_meta_data state=supplied",
         "dist pyx value vendor_key key=com.vendor.KEY kind=manifest_meta_data"),
        ("dist pyx action enable_dashboard date=2026-08-24 state=acknowledged version=1.0.0",
         "dist pyx action enable_dashboard"),
    ],
)
def test_the_gate_sees_the_resolution_and_not_the_answers(line, gated):
    assert acceptance.resolution_only(line) == gated


def test_answering_a_declared_value_is_not_a_delta(findings):
    """The confirmation dialog §9.1's note forbids, as two record states."""
    declared = ("dist pyx value vendor_key key=com.vendor.KEY"
                " kind=manifest_meta_data state=%s")
    record = Record()
    record.extend([declared % "supplied", "dist pyx contract 1"])
    stored = "\n".join(sorted([declared % "unresolved", "dist pyx contract 1"])) + "\n"

    delta = acceptance.check(record, stored, findings=findings, distributions=["pyx"])
    assert not delta
    assert findings.ok


def test_a_producer_adding_a_demand_is_a_delta(findings):
    """The same line, moving for the other reason."""
    record = Record()
    record.extend(["dist pyx contract 1",
                   "dist pyx value vendor_key key=com.vendor.KEY"
                   " kind=manifest_meta_data state=unresolved"])
    delta = acceptance.check(record, "dist pyx contract 1\n",
                             findings=findings, distributions=["pyx"])
    assert delta.added == ("dist pyx value vendor_key key=com.vendor.KEY"
                           " kind=manifest_meta_data",)
    assert not findings.ok
