"""Resolving a sidecar against an application (§5.1–§5.4, §6.1, §9.3).

The corpus fixture is the test wherever it can be. `core/R01_dependency_closure`
ships a real sidecar, a real application configuration and the record a
conforming consumer must produce for each platform, so reproducing that file
byte for byte from the fixture's own bytes is worth more than any assertion
about an intermediate structure.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from native_integration import document, integration, registry
from native_integration.application import Answer, Application, Approval, Credential
from native_integration.discovery import source_from_path
from native_integration.findings import Findings
from native_integration.recording import Record

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "conformance"
R01 = CORPUS / "core" / "R01_dependency_closure"


def application_for(path: Path) -> Application:
    """The corpus's neutral spelling, adapted — which is what §2.2 asks of any
    consumer, and the shape of what a build tool writes once."""
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    build = raw.get("build", {})
    answers = raw.get("answers", {})
    return Application(
        android={k: v for k, v in build.items() if isinstance(v, int) and not isinstance(v, bool)},
        deployment_target=str(build.get("deployment_target", "")),
        core_library_desugaring=bool(build.get("core_library_desugaring", False)),
        values={
            tuple(key.split(".", 1)): value  # type: ignore[misc]
            for key, value in answers.get("values", {}).items()
        },
        acknowledged={
            (distribution, identifier): Answer()
            for distribution, listed in answers.get("acknowledged", {}).items()
            for identifier in listed
        },
        exported_components={
            component: Approval(date=held.get("date", ""), approved=bool(held.get("approved")))
            for component, held in answers.get("exported_components", {}).items()
        },
        suppressed_permissions={
            permission: Answer(date=held.get("date", ""))
            for permission, held in answers.get("suppressed_permissions", {}).items()
        },
        credentials={
            url: Credential(kind=held.get("kind", "env"), locator=held.get("locator", ""))
            for url, held in answers.get("credentials", {}).items()
        },
    )


def input_directory(case: Path, platform: str) -> Path:
    """A case is either per-platform or shared, which is what `core/` buys."""
    per_platform = case / "input" / platform
    return per_platform if per_platform.is_dir() else case / "input"


def sidecar_root(base: Path, distribution: str) -> Path:
    found = sorted((base / distribution).rglob("native.toml"))
    assert found, f"no sidecar for {distribution} under {base}"
    return found[0].parent


def resolve_case(case: Path, platform: str):
    """Every in-closure distribution of one case, resolved onto one record.

    The closure is read rather than assumed, so a distribution marked
    `not-in-closure` is skipped here exactly as requirement 1 says it must be.
    """
    base = input_directory(case, platform)
    closure = tomllib.loads((base / "closure.toml").read_text(encoding="utf-8"))
    application = application_for(base / "application.toml")
    log = Findings(registry.load())
    record = Record()
    integration.build_facts(record, contract="1.0", platform=platform)

    resolved = []
    for entry in closure.get("distribution", []):
        if entry.get("origin") == "not-in-closure":
            continue
        root = sidecar_root(base, entry["name"])
        source = source_from_path(
            root,
            distribution=entry["name"],
            version=entry.get("version", ""),
            module=entry.get("entry_point", ""),
        )
        parsed = document.read(source, platform=platform, findings=log)
        if parsed is None:
            continue
        resolved.append(
            integration.resolve(
                parsed,
                application=application,
                findings=log,
                record=record,
                origin=entry.get("origin", "direct"),
                via=entry.get("via", ()),
            )
        )
    integration.decisions(resolved, application=application, findings=log, record=record)
    return resolved, log, record


@pytest.mark.parametrize("platform", ["android", "ios"])
def test_r01_is_reproduced_byte_for_byte_from_its_own_fixture(platform):
    _, log, record = resolve_case(R01, platform)
    expected = (R01 / "expected" / f"{platform}.record").read_text(
        encoding="utf-8", newline=""
    )
    assert record.render() == expected
    assert not list(log)


def _cases_with_records():
    for record in sorted(CORPUS.glob("*/*/expected/*.record")):
        yield record.parent.parent, record.stem


@pytest.mark.parametrize(
    "case, platform",
    list(_cases_with_records()),
    ids=lambda v: v if isinstance(v, str) else v.name,
)
def test_every_expected_record_the_sidecars_alone_can_explain(case, platform):
    """A case whose record needs only what a sidecar declares must reproduce now.

    One that needs the resolved graph — an artifact digest, a locked package, a
    §9.4 attribution — cannot, because nothing here resolves anything, and it
    says so rather than being quietly skipped.
    """
    if (input_directory(case, platform) / "resolved.toml").exists():
        pytest.skip("needs a stated resolution, which is not wired up yet")
    _, _, record = resolve_case(case, platform)
    expected = (case / "expected" / f"{platform}.record").read_text(
        encoding="utf-8", newline=""
    )
    assert record.render() == expected


@pytest.mark.parametrize("platform", ["android", "ios"])
def test_a_distribution_outside_the_closure_contributes_nothing(platform):
    """`pyunrelated` is installed beside the application and ships a sidecar.
    Requirement 1: a consumer never accepts a contribution from it."""
    _, _, record = resolve_case(R01, platform)
    assert not any("pyunrelated" in line for line in record)
    assert (input_directory(R01, platform) / "pyunrelated").is_dir()


@pytest.mark.parametrize("platform", ["android", "ios"])
def test_the_digests_are_the_real_bytes(platform):
    """"A fixture's `input` digests are the SHA-256 of the bytes in its own
    `input/` directory, so they are real and a consumer computes the same ones"."""
    import hashlib

    _, _, record = resolve_case(R01, platform)
    root = sidecar_root(input_directory(R01, platform), "examplytics")
    inputs = [line.split(" ") for line in record if " input " in line]
    assert inputs
    for parts in inputs:
        digest = parts[4].removeprefix("sha256=")
        assert digest == hashlib.sha256((root / parts[3]).read_bytes()).hexdigest()


# -- §5.4's table, one line at a time ---------------------------------------


def test_a_placeholder_read_back_is_not_an_answer():
    """`core/R13_placeholder_not_an_answer`: the scaffold, unedited. A consumer
    that accepted its own placeholder would report a value as answered on the
    strength of text it printed itself."""
    case = CORPUS / "core" / "R13_placeholder_not_an_answer"
    _, log, record = resolve_case(case, "android")
    assert {f.obligation for f in log} == {"ni.req.13"}
    assert any("state=unresolved" in line for line in record)
    assert any("placeholder" in " ".join(f.detail) for f in log)


def test_an_acknowledged_action_is_held_open_by_an_unsupplied_value():
    """`core/R14_action_held_by_unsupplied_value`. The value is *conditional*, so
    on its own it never fails the build — which is exactly why §5.3 needs the
    second conjunct, and why requirement 14 is the only finding."""
    case = CORPUS / "core" / "R14_action_held_by_unsupplied_value"
    _, log, _ = resolve_case(case, "android")
    assert {f.obligation for f in log} == {"ni.req.14"}
    held = next(iter(log))
    assert "app_group_entitlement" in held.message
    assert "app_group_id" in " ".join(held.detail)


def test_a_floor_the_application_is_below_fails_with_both_values():
    """`core/R12_floor_unmet`: a floor carries no `reason`, so the declared and
    configured values are the whole of what a report can say."""
    case = CORPUS / "core" / "R12_floor_unmet"
    for platform in ("android", "ios"):
        _, log, record = resolve_case(case, platform)
        assert {f.obligation for f in log} == {"ni.req.12"}
        detail = " ".join(next(iter(log)).detail)
        assert "declared" in detail and "configured" in detail
        assert any("state=unmet" in line for line in record)


def test_a_consumer_never_raises_the_configuration_to_meet_a_floor():
    """Requirement 12, and the reason the record carries both numbers."""
    _, _, record = resolve_case(CORPUS / "core" / "R12_floor_unmet", "android")
    floors = [line for line in record if " floor " in line]
    assert floors
    for line in floors:
        assert "configured=" in line


# -- §2.2's answers joined by a name rather than an id ----------------------


def test_an_unapproved_export_fails_rather_than_falling_back():
    """`android/R29_export_without_approval`, the case with two wrong answers.

    The record still carries the request and its pending state, because §9.6
    wants "the approval's absence where a component is still pending" to stay
    recoverable rather than looking like a component nobody asked to export.
    """
    case = CORPUS / "android" / "R29_export_without_approval"
    _, log, record = resolve_case(case, "android")
    assert {f.obligation for f in log} == {"ni.req.29"}
    pending = [line for line in record if line.startswith("decision approve-export")]
    assert pending and all("state=pending" in line for line in pending)
    assert all("date=" not in line for line in pending)
    assert not any("exported-required=false" in line for line in record)


def test_an_authenticated_repository_without_credentials_fails_by_name():
    """`android/R27_authenticated_no_credentials`. A bare 401 names a host, and
    not the distribution that added the repository or where to get a credential."""
    case = CORPUS / "android" / "R27_authenticated_no_credentials"
    _, log, record = resolve_case(case, "android")
    assert {f.obligation for f in log} == {"ni.req.27"}
    reported = next(iter(log))
    assert reported.distributions == ("pymapbox",)
    assert any(line.startswith("decision credential-required") for line in record)


def test_a_credential_never_reaches_the_record():
    """§9.5: that one is required is a fact about the integration; it is not."""
    case = CORPUS / "android" / "R27_authenticated_no_credentials"
    _, _, record = resolve_case(case, "android")
    for line in record:
        if line.startswith("decision credential-required"):
            assert line.endswith("kind=repository")


@pytest.mark.parametrize(
    "declared, configured, expected",
    [
        ("15.0", "16.0", True),
        ("16.0", "16.0", True),
        ("16.1", "16.0", False),
        ("16", "16.0.0", True),
        ("16.0.0", "16", True),
        ("9.0", "10.0", True),
    ],
)
def test_a_deployment_target_is_compared_component_wise_and_numerically(
    declared, configured, expected
):
    """"9.0" is below "10.0", which a lexical comparison gets backwards."""
    from native_integration.application import meets

    assert meets(declared, configured, "deployment_target") is expected


def test_an_unconfigured_floor_is_unmet_rather_than_ignored():
    from native_integration.application import meets

    assert meets(24, None, "min_sdk") is False
