"""The one hand-written table in the reader, held total.

`obligations.py` maps a generated check id to the §8.4 requirement it
discharges. Nothing derives it — Phase 1 put mechanical properties in the
registry and left §8 as prose — so the guard against it drifting is here: every
id any generator emits must resolve, and must resolve somewhere §8.1 admits.
"""

from __future__ import annotations

import pytest

from native_integration import obligations, registry


@pytest.fixture(scope="module")
def contract() -> registry.Registry:
    return registry.load()


@pytest.fixture(scope="module")
def checks(contract) -> list[str]:
    return [
        identifier
        for identifier in contract.diagnostics
        if identifier.startswith(("ni.decl.", "ni.constraint."))
    ]


def test_there_are_checks_to_attribute(checks):
    """A vacuous pass here would make every assertion below meaningless."""
    assert len(checks) > 150


def test_every_generated_check_resolves_to_a_requirement(contract, checks):
    unattributed = []
    for identifier in checks:
        try:
            number = obligations.for_identifier(identifier, contract)
        except obligations.UnattributedCheck:
            unattributed.append(identifier)
            continue
        assert number in contract.requirements(), identifier
    assert not unattributed


#: A declaration shared by both platform tables answers to a core requirement,
#: with one exception §8.4 states outright: requirement 35 rejects a capability,
#: external-reach or consumer-managed key "wherever it arrives, in those three
#: channels alike", and one of the three is a `kind = "info_plist"` value. The
#: kind is iOS-only (§5.5's Platform column), so the check reaches no Android
#: build despite hanging off a shared declaration.
SHARED_BUT_PLATFORM_SPECIFIC = {
    "ni.constraint.<platform>.requires.application_value.key"
    ".registers-forbidden-if-equals.kind",
}


def _platform_of(contract, identifier):
    """Which platform table a check can fire in.

    A constraint entry names its target in `declaration` too, but that target
    may be a platform table rather than a declaration row, so the head of the
    dotted name is what decides.
    """
    target = str(contract.about(identifier)["declaration"])
    if identifier.startswith("ni.constraint."):
        head = target.split(".")[0]
        return head if head in registry.PLATFORMS else "both"
    return contract.declaration(target)["platform"]


def test_no_check_is_attributed_outside_its_own_profile(contract, checks):
    """§8.1 gives each requirement one profile. An Android declaration answering
    to an iOS requirement would hand a case to a consumer that never owed it."""
    wrong = []
    for identifier in checks:
        number = obligations.for_identifier(identifier, contract)
        profile = contract.profile_of(number)
        platform = _platform_of(contract, identifier)
        if profile == "core":
            continue
        if platform == "both" and identifier in SHARED_BUT_PLATFORM_SPECIFIC:
            continue
        if profile != platform:
            wrong.append(f"{identifier} → ni.req.{number} ({profile}, not {platform})")
    assert not wrong


def test_a_shared_declaration_answers_to_a_core_requirement(contract, checks):
    stray = []
    for identifier in checks:
        if identifier in SHARED_BUT_PLATFORM_SPECIFIC:
            continue
        if _platform_of(contract, identifier) != "both":
            continue
        if contract.profile_of(obligations.for_identifier(identifier, contract)) != "core":
            stray.append(identifier)
    assert not stray


# -- the attributions the conformance corpus pins ---------------------------


@pytest.mark.parametrize(
    "identifier, number",
    [
        ("ni.decl.<platform>.requires.application_value.id.duplicate", 22),
        ("ni.decl.android.contributes.features.required.forbidden", 28),
        ("ni.decl.ios.contributes.swift_packages.name.duplicate", 33),
        ("ni.decl.ios.contributes.info_plist.values.refuses.usage-description-suffix", 35),
        ("ni.decl.ios.contributes.info_plist.append.refuses.capability-keys", 35),
        ("ni.constraint.ios.contributes.accessed_api_types.requires-present.src.swift", 34),
        ("ni.decl.android.contributes.components.unknown-key", 8),
        ("ni.constraint.android.platform-table-requires-listing.platforms", 9),
    ],
)
def test_the_corpus_attributions(contract, identifier, number):
    assert obligations.for_identifier(identifier, contract) == number


def test_a_view_links_combination_and_its_content_differ(contract):
    """§6.6 splits between requirement 29 and requirement 30, and so must we."""
    combination = (
        "ni.constraint.android.contributes.components.view_links.requires-equals.kind"
    )
    content = "ni.decl.android.contributes.components.view_links.open-key-pattern"
    assert obligations.for_identifier(combination, contract) == 29
    assert obligations.for_identifier(content, contract) == 30


def test_an_unrecorded_check_raises_rather_than_defaulting(contract):
    with pytest.raises(obligations.UnattributedCheck):
        obligations.for_declaration("something.nobody.declares", "type")
    with pytest.raises(obligations.UnattributedCheck):
        obligations.for_identifier("ni.req.12", contract)
