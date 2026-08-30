"""The registry loader — what the reader is driven by.

These tests are about the loader, not about the vocabulary: that
`contract/v1.toml` agrees with SPEC.md is `tools/check_spec.py`'s job, and
duplicating it here would make a second place to update when a declaration
changes. What is checked here is that the loader presents the file faithfully
and refuses to invent anything it cannot find.
"""

from __future__ import annotations

import pytest

from native_integration import registry


@pytest.fixture(scope="module")
def contract() -> registry.Registry:
    return registry.load()


def test_the_registry_is_found_and_parsed(contract):
    assert contract.contract == "1.0"
    assert contract.entry_point_group == "native_integration.v1"
    assert contract.declarations
    assert contract.diagnostics


def test_loading_twice_returns_one_registry():
    assert registry.load() is registry.load()


# -- the vocabulary --------------------------------------------------------


@pytest.mark.parametrize("platform", registry.PLATFORMS)
def test_a_platform_tree_holds_the_top_level_keys_and_one_platform_table(contract, platform):
    tree = contract.tree(platform)
    assert sorted(tree.children) == sorted(["contract", "platforms", platform])


@pytest.mark.parametrize(
    "platform, absent", [("android", "ios"), ("ios", "android")]
)
def test_the_other_platforms_table_is_absent_rather_than_empty(contract, platform, absent):
    """§4.5 makes a table for an unlisted platform a contradiction, not a shape."""
    assert contract.tree(platform).child(absent) is None


def test_an_unknown_platform_is_refused(contract):
    with pytest.raises(registry.RegistryError):
        contract.tree("windows")


def test_a_shared_declaration_keeps_its_token_and_resolves_its_path(contract):
    """A diagnostic id is built from the registry's spelling, a walk from the path."""
    value = (
        contract.tree("android").child("android").child("requires").child("application_value")
    )
    assert value.id == "<platform>.requires.application_value"
    assert value.path == ("android", "requires", "application_value")
    assert value.node == "array_of_tables"
    assert contract.tree("ios").child("ios").child("requires").child(
        "application_value"
    ).id == value.id


def test_a_container_the_registry_does_not_name_is_still_a_node(contract):
    """`[android.contributes]` carries no properties; `[ios.contributes]` does."""
    android = contract.tree("android").child("android").child("contributes")
    assert android is not None and not android.declared
    assert android.child("permissions") is not None

    ios = contract.tree("ios").child("ios").child("contributes")
    assert ios.declared
    assert ios.child("objc_categories") is not None


def test_open_keys_are_marked_where_the_platform_owns_the_names(contract):
    contributes = contract.tree("ios").child("ios").child("contributes")
    assert contributes.child("info_plist").child("values").open_keys
    links = (
        contract.tree("android")
        .child("android")
        .child("contributes")
        .child("components")
        .child("view_links")
    )
    assert links.open_keys
    assert not links.child("scheme").open_keys


def test_a_register_is_read_from_the_registry(contract):
    assert "UIBackgroundModes" in contract.register("capability_keys")
    with pytest.raises(registry.RegistryError):
        contract.register("invented_register")


# -- the identifiers -------------------------------------------------------


def test_every_constraint_resolves_to_a_generated_id(contract):
    for rule in contract.constraints:
        assert contract.constraint_id(rule).startswith("ni.constraint.")


def test_every_requirement_and_advisory_resolves(contract):
    assert contract.requirements() == tuple(range(1, 47))
    for number in contract.requirements():
        assert contract.profile_of(number) in ("core", "android", "ios")
    for advisory in contract.advisories():
        assert contract.advisory_id(advisory)


@pytest.mark.parametrize(
    "identifier",
    [
        # The ids the conformance corpus expects, resolved rather than spelled.
        "ni.decl.<platform>.requires.application_value.id.duplicate",
        "ni.decl.ios.contributes.swift_packages.name.duplicate",
        "ni.decl.android.contributes.features.required.forbidden",
        "ni.decl.ios.contributes.info_plist.values.refuses.usage-description-suffix",
        "ni.decl.ios.contributes.info_plist.append.refuses.capability-keys",
        "ni.constraint.ios.contributes.accessed_api_types.requires-present.src.swift",
    ],
)
def test_the_corpus_ids_are_produced_by_lookup(contract, identifier):
    about = contract.about(identifier)
    assert about["section"] and about["severity"] in ("blocking", "advisory")


def test_a_check_the_registry_cannot_name_raises(contract):
    """A reader that fell back to a hand-written string is a second source of truth."""
    with pytest.raises(registry.RegistryError):
        contract.declaration_id("android.contributes.permissions.name", "invented")
    with pytest.raises(registry.RegistryError):
        contract.requirement_id(999)
    with pytest.raises(registry.RegistryError):
        contract.refusal_id("ios.contributes.info_plist.values", "invented_register")
