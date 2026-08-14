"""Reading one sidecar: the gate, the schema walk, and §§6–7's own rules."""

from __future__ import annotations

import pytest

from native_integration import ConsumerProfile, ContractVersion, Platform

ANDROID_MINIMAL = """
contract = "1"
"""


# --- §4.3 the contract gate -------------------------------------------------


def test_missing_contract_is_rejected(parse):
    sidecar, codes, _ = parse("[android.owns]\njava_namespaces = []\n")
    assert sidecar is None
    assert codes == ["contract-missing"]


def test_malformed_contract_is_rejected(parse):
    sidecar, codes, _ = parse('contract = "one"\n')
    assert sidecar is None and codes == ["contract-malformed"]


def test_a_different_major_is_rejected_without_parsing_further(parse):
    sidecar, codes, _ = parse('contract = "2"\n[android]\nnonsense = 1\n')
    assert sidecar is None
    assert codes == ["contract-major-mismatch"]  # and not the unknown key


def test_a_greater_minor_names_the_contract_that_would_work(parse):
    sidecar, codes, bag = parse('contract = "1.4"\n')
    assert sidecar is None and codes == ["contract-too-new"]
    assert "requires contract 1.4" in bag.items[0].message


def test_a_consumer_implementing_a_later_minor_accepts_an_earlier_one(parse):
    profile = ConsumerProfile(contract=ContractVersion(1, 3))
    sidecar, codes, _ = parse('contract = "1"\n', profile=profile)
    assert sidecar is not None and codes == []


def test_under_declaration_is_caught_even_when_both_are_implemented(parse, monkeypatch):
    """§4.3 — without this the gate protects only older consumers."""
    from native_integration import schema

    monkeypatch.setitem(
        schema.ANDROID.tables["owns"].fields,
        "java_namespaces",
        schema.Field(schema.nonempty_string_list, since=ContractVersion(1, 1)),
    )
    profile = ConsumerProfile(contract=ContractVersion(1, 1))
    _, codes, bag = parse(
        'contract = "1"\n[android.owns]\njava_namespaces = ["org.example"]\n', profile=profile
    )
    assert "contract-under-declared" in codes
    assert "introduced in contract 1.1" in bag.items[0].message


# --- §4.4 unknown keys ------------------------------------------------------


def test_an_unknown_key_in_the_platform_being_built_fails_closed(parse):
    sidecar, codes, _ = parse('contract = "1"\n[android.contributes]\npermisions = []\n')
    assert sidecar is None and codes == ["unknown-key"]


def test_another_platforms_table_is_not_our_concern(parse):
    _, codes, _ = parse(
        'contract = "1"\n[ios.contributes.src]\nswift = ["swift"]\n', platform=Platform.ANDROID
    )
    assert codes == []


def test_an_unrecognized_top_level_table_only_warns(parse):
    sidecar, codes, bag = parse('contract = "1"\n[windows]\nthing = 1\n')
    assert codes == ["unknown-top-level"]
    assert sidecar is not None and bag.ok


def test_a_wrong_type_names_the_key(parse):
    _, codes, bag = parse('contract = "1"\n[android.requires]\nmin_sdk = "24"\n')
    assert codes == ["type-invalid"]
    assert "android.requires.min_sdk" in bag.items[0].message


# --- §4.5 platforms ---------------------------------------------------------


def test_building_for_an_unsupported_platform_fails(parse):
    sidecar, codes, _ = parse('contract = "1"\nplatforms = ["ios"]\n', platform=Platform.ANDROID)
    assert sidecar is None and codes == ["platform-unsupported"]


def test_a_platform_table_for_an_omitted_platform_is_a_contradiction(parse):
    _, codes, _ = parse(
        'contract = "1"\nplatforms = ["ios"]\n[android.owns]\njava_namespaces = []\n',
        platform=Platform.IOS,
    )
    assert codes == ["platforms-contradiction"]


def test_omitting_platforms_makes_no_claim(parse):
    _, codes, _ = parse('contract = "1"\n', platform=Platform.IOS)
    assert codes == []


# --- §6.1 ownership ---------------------------------------------------------


def test_contributing_source_without_owning_a_namespace(parse):
    _, codes, _ = parse(
        'contract = "1"\n[android.contributes.src]\njava = ["java"]\n',
        profile=ConsumerProfile(verify_resources=False),
    )
    assert "namespace-required" in codes


def test_a_reserved_namespace_cannot_be_claimed(parse):
    _, codes, bag = parse(
        'contract = "1"\n[android.owns]\njava_namespaces = ["org.kivy.android.helpers"]\n'
    )
    assert codes == ["namespace-reserved"]
    assert "org.kivy.android" in bag.items[0].message


def test_containment_is_computed_on_segments(parse):
    """`org.kivy.androidx` is not `org.kivy.android`; `PyGMAKit` is not `PyGMA`."""
    _, codes, _ = parse('contract = "1"\n[android.owns]\njava_namespaces = ["org.kivy.androidx"]\n')
    assert codes == []


def test_a_single_label_namespace_warns_but_is_ownable(parse):
    sidecar, codes, _ = parse('contract = "1"\n[android.owns]\njava_namespaces = ["PyGMA"]\n')
    assert codes == ["namespace-single-label"] and sidecar is not None


def test_source_outside_the_owned_namespace_is_rejected(parse):
    text = """
contract = "1"
[android.owns]
java_namespaces = ["org.example"]
[android.contributes.src]
java = ["java"]
"""
    _, codes, bag = parse(
        text,
        files={"java/org/other/Bridge.java": "package org.other;\nclass Bridge {}\n"},
    )
    assert codes.count("source-outside-namespace") == 2  # the path, and the declaration
    assert any("package org.other" in d.message for d in bag)


def test_source_inside_the_owned_namespace_passes(parse):
    text = """
contract = "1"
[android.owns]
java_namespaces = ["org.example"]
[android.contributes.src]
java = ["java"]
"""
    _, codes, _ = parse(
        text, files={"java/org/example/Bridge.java": "package org.example;\nclass Bridge {}\n"}
    )
    assert codes == []


# --- §4.1 resources ---------------------------------------------------------


def test_a_symlinked_resource_is_rejected(parse, make_sidecar, tmp_path):
    text = """
contract = "1"
[android.owns]
java_namespaces = ["org.example"]
[android.contributes.src]
java = ["java"]
"""
    source = make_sidecar(text, files={"java/org/example/Real.java": "package org.example;\n"})
    outside = tmp_path / "outside.java"
    outside.write_text("package org.example;\n", encoding="utf-8")
    (source.root / "java" / "org" / "example" / "Link.java").symlink_to(outside)

    from native_integration import check_sidecar

    _, bag = check_sidecar(source, platform=Platform.ANDROID)
    assert [d.rule.code for d in bag] == ["resource-symlink"]


def test_a_path_escaping_the_sidecar_directory_is_rejected(parse):
    text = """
contract = "1"
[android.owns]
java_namespaces = ["org.example"]
[android.contributes.src]
java = ["../elsewhere"]
"""
    _, codes, _ = parse(text)
    assert codes == ["resource-escapes"]


# --- §6.3 application values ------------------------------------------------


def test_an_inline_reference_must_resolve_to_a_declared_id(parse):
    text = """
contract = "1"
[android.owns]
java_namespaces = ["org.example"]

[[android.contributes.components]]
kind = "activity"
name = "org.example.Redirect"
exported_required = true
reason = "OAuth redirect"
  [[android.contributes.components.view_links]]
  scheme = { application_value = "undeclared" }
"""
    _, codes, bag = parse(text)
    assert codes == ["application-value-unresolved-ref"]
    assert "would have no `reason`" in bag.items[0].message


def test_duplicate_application_value_ids(parse):
    text = """
contract = "1"
[[android.requires.application_values]]
id = "dsn"
reason = "one"
[[android.requires.application_values]]
id = "dsn"
reason = "two"
"""
    _, codes, _ = parse(text)
    assert codes == ["application-value-duplicate"]


# --- §6.5 dependencies ------------------------------------------------------


@pytest.mark.parametrize(
    "entry,expected",
    [
        ('coordinate = "g:a:1.0.0-SNAPSHOT"', "dependency-version-changing"),
        ('coordinate = "g:a:+"', "dependency-version-unbounded"),
        ('coordinate = "g:a:latest.release"', "dependency-version-unbounded"),
        ('coordinate = "g:a:[1.0,2.0)"', "dependency-version-unbounded"),
    ],
)
def test_changing_and_dynamic_versions_are_invalid(parse, entry, expected):
    _, codes, _ = parse(f'contract = "1"\n[[android.contributes.gradle_dependencies]]\n{entry}\n')
    assert expected in codes


def test_a_dependency_declaring_both_forms_is_rejected(parse):
    text = """
contract = "1"
[[android.contributes.gradle_dependencies]]
coordinate = "g:a:1.0"
module = "g:a"
version = { at_least = "1.0", below = "2.0" }
"""
    sidecar, codes, _ = parse(text)
    assert codes == ["dependency-form"] and sidecar is None


def test_a_dependency_declaring_neither_form_is_rejected(parse):
    text = """
contract = "1"
[[android.contributes.gradle_dependencies]]
configuration = "implementation"
"""
    sidecar, codes, _ = parse(text)
    assert codes == ["dependency-form"] and sidecar is None


def test_a_range_open_at_either_end_is_invalid(parse):
    text = """
contract = "1"
[[android.contributes.gradle_dependencies]]
module = "g:a"
version = { at_least = "1.0" }
"""
    sidecar, codes, _ = parse(text)
    assert sidecar is None and codes == ["type-invalid"]


def test_an_unimplemented_configuration_is_rejected(parse):
    text = """
contract = "1"
[[android.contributes.gradle_dependencies]]
coordinate = "g:a:1.0"
configuration = "api"
"""
    _, codes, _ = parse(text)
    assert codes == ["dependency-configuration"]


# --- §6.6 repositories ------------------------------------------------------


def test_a_repository_must_bound_its_participation(parse):
    text = """
contract = "1"
[[android.contributes.gradle_repositories]]
url = "https://example.com/maven"
reason = "hosts the shim"
"""
    _, codes, _ = parse(text)
    assert codes == ["repository-scope-missing"]


def test_url_user_info_is_a_credential_in_a_sidecar(parse):
    text = """
contract = "1"
[[android.contributes.gradle_repositories]]
url = "https://user:pass@example.com/maven"
reason = "hosts the shim"
groups = ["com.example"]
"""
    _, codes, _ = parse(text)
    assert "repository-credential-in-url" in codes


def test_a_credential_shaped_string_warns(parse):
    text = """
contract = "1"
[[android.contributes.gradle_repositories]]
url = "https://example.com/maven"
reason = "use the token = \\"sk.abcdefgh12345\\" as the password"
groups = ["com.example"]
"""
    _, codes, _ = parse(text)
    assert "repository-credential-shaped" in codes


# --- §6.7 features ----------------------------------------------------------


def test_a_producer_may_not_set_required_on_a_feature(parse):
    text = """
contract = "1"
[[android.contributes.features]]
name = "android.hardware.bluetooth_le"
required = true
"""
    sidecar, codes, _ = parse(text)
    assert codes == ["feature-required-forbidden"] and sidecar is None


# --- §6.8 components --------------------------------------------------------


def test_view_links_need_an_exported_activity(parse):
    text = """
contract = "1"
[android.owns]
java_namespaces = ["org.example"]
[[android.contributes.components]]
kind = "service"
name = "org.example.Svc"
  [[android.contributes.components.view_links]]
  scheme = "myapp"
"""
    _, codes, _ = parse(text)
    assert "view-links-invalid" in codes


def test_intent_filters_are_only_valid_on_an_unexported_component(parse):
    text = """
contract = "1"
[android.owns]
java_namespaces = ["org.example"]
[[android.contributes.components]]
kind = "activity"
name = "org.example.Redirect"
exported_required = true
reason = "redirect"
  [[android.contributes.components.intent_filters]]
  action = "com.vendor.ACTION"
"""
    _, codes, _ = parse(text)
    assert "intent-filter-invalid" in codes


def test_from_dependency_must_name_a_declared_dependency(parse):
    text = """
contract = "1"
[[android.contributes.components]]
kind = "receiver"
name = "com.vendor.sdk.Receiver"
from_dependency = "com.vendor:sdk"
"""
    _, codes, _ = parse(text)
    assert codes == ["component-dependency-undeclared"]


def test_a_from_dependency_component_is_exempt_from_the_namespace_rule(parse):
    text = """
contract = "1"
[[android.contributes.gradle_dependencies]]
coordinate = "com.vendor:sdk:1.0.0"
[[android.contributes.components]]
kind = "receiver"
name = "com.vendor.sdk.Receiver"
from_dependency = "com.vendor:sdk"
"""
    _, codes, _ = parse(text)
    assert codes == []


# --- §6.9 keeps -------------------------------------------------------------


def test_keep_classes_must_be_within_an_owned_namespace(parse):
    text = """
contract = "1"
[android.owns]
java_namespaces = ["org.example"]
[android.contributes.r8]
keep_classes = ["okhttp3.**"]
"""
    _, codes, bag = parse(text)
    assert codes == ["keep-outside-namespace"]
    assert "[[android.contributes.r8.keep]]" in bag.items[0].message


def test_a_dependency_keep_must_name_a_declared_dependency(parse):
    text = """
contract = "1"
[[android.contributes.r8.keep]]
pattern = "okhttp3.**"
from_dependency = "com.squareup.okhttp3:okhttp"
"""
    _, codes, _ = parse(text)
    assert codes == ["keep-dependency-undeclared"]


# --- §7.3 prerequisites -----------------------------------------------------


def test_a_prerequisite_needs_a_reason(parse):
    text = """
contract = "1"
[[ios.requires.entitlements]]
key = "aps-environment"
"""
    sidecar, codes, _ = parse(text, platform=Platform.IOS)
    assert sidecar is None and codes == ["key-required"]


def test_duplicate_producer_local_ids_cannot_be_answered_separately(parse):
    text = """
contract = "1"
[[ios.requires.url_schemes]]
id = "callback"
reason = "one"
[[ios.requires.url_schemes]]
id = "callback"
reason = "two"
"""
    _, codes, _ = parse(text, platform=Platform.IOS)
    assert codes == ["prerequisite-id-duplicate"]


def test_several_url_schemes_are_allowed_when_their_ids_differ(parse):
    """§7.3 — a package needing several declares one entry each."""
    text = """
contract = "1"
[[ios.requires.url_schemes]]
id = "oauth_callback"
reason = "OAuth return"
[[ios.requires.url_schemes]]
id = "payment_return"
reason = "payment return"
"""
    sidecar, codes, _ = parse(text, platform=Platform.IOS)
    assert codes == [] and len(sidecar.ios.prerequisites) == 2


def test_an_unknown_app_extension_kind_is_rejected(parse):
    text = """
contract = "1"
[[ios.requires.app_extensions]]
id = "widget"
kind = "widget"
reason = "because"
"""
    sidecar, codes, _ = parse(text, platform=Platform.IOS)
    assert sidecar is None and codes == ["type-invalid"]


def test_a_conditional_reason_should_state_the_condition(parse):
    text = """
contract = "1"
[[ios.requires.usage_descriptions]]
key = "NSLocationAlwaysAndWhenInUseUsageDescription"
conditional = true
reason = "Location, always"
"""
    _, codes, _ = parse(text, platform=Platform.IOS)
    assert codes == ["prerequisite-condition-unstated"]


# --- §7.4 / §7.6 / §7.7 -----------------------------------------------------


def test_a_branch_requirement_is_rejected(parse):
    text = """
contract = "1"
[[ios.contributes.swift_packages]]
name = "Shim"
url = "https://example.com/shim"
requirement = { branch = "main" }
products = ["Shim"]
"""
    _, codes, _ = parse(text, platform=Platform.IOS)
    assert codes == ["swift-branch-requirement"]


def test_two_swift_packages_may_not_share_a_local_handle(parse):
    text = """
contract = "1"
[[ios.contributes.swift_packages]]
name = "Shim"
url = "https://example.com/a"
requirement = { exact = "1.0.0" }
products = ["A"]
[[ios.contributes.swift_packages]]
name = "Shim"
url = "https://example.com/b"
requirement = { exact = "1.0.0" }
products = ["B"]
"""
    _, codes, _ = parse(text, platform=Platform.IOS)
    assert codes == ["swift-package-duplicate-name"]


def test_a_usage_description_may_not_be_contributed_as_a_plist_value(parse):
    text = """
contract = "1"
[ios.contributes.info_plist.values]
NSCameraUsageDescription = "We need your camera"
"""
    _, codes, bag = parse(text, platform=Platform.IOS)
    assert codes == ["plist-usage-description"]
    assert "[[ios.requires.usage_descriptions]]" in bag.items[0].message


@pytest.mark.parametrize(
    "value", ["1979-05-27T07:32:00Z", "{ nested = 1 }", '["a", 1]']
)
def test_plist_values_reject_types_with_no_unambiguous_form(parse, value):
    text = f'contract = "1"\n[ios.contributes.info_plist.values]\nKey = {value}\n'
    sidecar, codes, _ = parse(text, platform=Platform.IOS)
    assert sidecar is None and codes == ["type-invalid"]


def test_a_dotted_python_module_name_is_rejected(parse):
    text = """
contract = "1"
[[ios.contributes.swift_packages]]
name = "PyWebViews"
url = "https://example.com/wv"
requirement = { exact = "1.0.0" }
products = ["PyWebViews"]
[[ios.contributes.python_modules]]
name = "web.views"
swift_package = "PyWebViews"
"""
    _, codes, _ = parse(text, platform=Platform.IOS)
    assert codes == ["python-module-name-invalid"]


def test_a_python_module_must_name_a_declared_package(parse):
    text = """
contract = "1"
[[ios.contributes.python_modules]]
name = "web_views"
swift_package = "PyWebViews"
"""
    _, codes, _ = parse(text, platform=Platform.IOS)
    assert codes == ["python-module-package-undeclared"]
