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


def test_the_widened_configuration_set_is_accepted(parse):
    """§6.5 defines four; `api` is one of them and no longer an error."""
    text = """
contract = "1"
[[android.contributes.gradle_dependencies]]
coordinate = "g:a:1.0"
configuration = "api"
"""
    _, codes, _ = parse(text)
    assert codes == []


def test_an_unimplemented_configuration_is_rejected(parse):
    """§4.4 — a value outside what this consumer implements fails closed."""
    text = """
contract = "1"
[[android.contributes.gradle_dependencies]]
coordinate = "g:a:1.0"
configuration = "wibble"
"""
    _, codes, _ = parse(text)
    assert codes == ["dependency-configuration"]


def test_a_processor_configuration_is_rejected_whatever_the_profile(parse):
    """§6.5 — a processor runs code from the artifact at build time (§2.1).

    This is the reason the configuration set stays closed while §7.3's
    extension kinds open: the value selects behaviour the *consumer performs*.
    """
    text = """
contract = "1"
[[android.contributes.gradle_dependencies]]
coordinate = "g:a:1.0"
configuration = "annotationProcessor"
"""
    _, codes, bag = parse(text)
    assert codes == ["dependency-configuration"]
    assert any("run code" in d.message for d in bag)


def test_a_manifest_placeholder_is_a_second_delivery(parse):
    """§6.3 — for a value a declared dependency's own manifest reads (Auth0)."""
    text = """
contract = "1"
[[android.requires.application_values]]
id = "auth0_domain"
reason = "Your Auth0 tenant domain"
manifest_placeholder = "auth0Domain"
"""
    sidecar, codes, _ = parse(text)
    assert codes == []
    value = sidecar.android.application_values[0]
    assert value.manifest_placeholder == "auth0Domain"
    assert value.manifest_meta_data is None


def test_both_deliveries_may_appear_on_one_value(parse):
    """The same supplied value reaching the manifest twice is legitimate."""
    text = """
contract = "1"
[[android.requires.application_values]]
id = "domain"
reason = "because"
manifest_meta_data = "com.example.Domain"
manifest_placeholder = "exampleDomain"
"""
    sidecar, codes, _ = parse(text)
    assert codes == []
    value = sidecar.android.application_values[0]
    assert (value.manifest_meta_data, value.manifest_placeholder) == (
        "com.example.Domain",
        "exampleDomain",
    )


def test_permission_attributes_are_read(parse):
    """§6.7 — maxSdkVersion and neverForLocation, both minimization."""
    text = """
contract = "1"
[[android.contributes.permissions]]
name = "android.permission.BLUETOOTH_SCAN"
reason = "Scanning for the vendor's beacons"
never_for_location = true

[[android.contributes.permissions]]
name = "android.permission.BLUETOOTH"
reason = "Legacy transport below API 31"
max_sdk_version = 30
"""
    sidecar, codes, _ = parse(text)
    assert codes == []
    scan, legacy = sidecar.android.permissions
    assert scan.never_for_location and scan.max_sdk_version is None
    assert legacy.max_sdk_version == 30 and not legacy.never_for_location


def test_core_library_desugaring_is_declarable(parse):
    """§6.2 — a floor whose axis is boolean."""
    text = """
contract = "1"
[android.requires]
core_library_desugaring = true
"""
    sidecar, codes, _ = parse(text)
    assert codes == [] and sidecar.android.core_library_desugaring


def test_contributed_meta_data_takes_three_value_types(parse):
    """§6.10 — string, integer, boolean; the consumer renders the literal."""
    text = """
contract = "1"
[[android.contributes.meta_data]]
key = "com.google.mlkit.vision.DEPENDENCIES"
value = "barcode,face"
reason = "Bundles the models rather than downloading them on first use"

[[android.contributes.meta_data]]
key = "com.example.RetryCount"
value = 3
reason = "Vendor default is 0, which drops the first event"

[[android.contributes.meta_data]]
key = "io.branch.sdk.TestMode"
value = false
reason = "Live keys, not test keys"
"""
    sidecar, codes, _ = parse(text)
    assert codes == []
    models, retries, test_mode = sidecar.android.meta_data
    assert models.rendered == "barcode,face"
    assert retries.rendered == "3"
    assert test_mode.rendered == "false"


def test_meta_data_may_not_name_a_resource(parse):
    """§6.10 — the notification-icon case, and why it stays out of reach."""
    text = """
contract = "1"
[[android.contributes.meta_data]]
key = "com.google.firebase.messaging.default_notification_icon"
value = "@drawable/ic_stat_notify"
reason = "The status bar icon"
"""
    _, codes, _ = parse(text)
    assert codes == ["meta-data-resource-reference"]


def test_meta_data_needs_a_reason(parse):
    """The key is global and its effect is invisible in Python."""
    text = """
contract = "1"
[[android.contributes.meta_data]]
key = "com.example.Flag"
value = true
"""
    _, codes, _ = parse(text)
    assert codes == ["key-required"]


def test_the_android_prerequisite_family_parses(parse):
    """§6.11 — files, resources and classes, on §7.3's common rules."""
    text = """
contract = "1"
[[android.requires.application_files]]
name = "airshipconfig.properties"
reason = "App key and secret from the Airship dashboard"

[[android.requires.resources]]
type = "drawable"
name = "ic_stat_notify"
reason = "The status bar icon; Android draws a white square without it"

[[android.requires.application_classes]]
id = "wechat_entry"
package_suffix = "wxapi"
name = "WXEntryActivity"
reason = "WeChat resolves this class by name under your own application ID"
"""
    sidecar, codes, _ = parse(text)
    assert codes == []
    kinds = [p.kind.table for p in sidecar.android.prerequisites]
    assert kinds == ["application_files", "resources", "application_classes"]
    wechat = sidecar.android.prerequisites[2]
    assert (wechat.package_suffix, wechat.class_name) == ("wxapi", "WXEntryActivity")


def test_a_declared_resource_is_the_one_thing_meta_data_may_reference(parse):
    """§6.10's rejection stops applying once the sidecar has asked for it."""
    text = """
contract = "1"
[[android.requires.resources]]
type = "drawable"
name = "ic_stat_notify"
reason = "The status bar icon"

[[android.contributes.meta_data]]
key = "com.google.firebase.messaging.default_notification_icon"
value = "@drawable/ic_stat_notify"
reason = "Points Firebase at the icon the application supplies"
"""
    _, codes, _ = parse(text)
    assert codes == []


def test_an_undeclared_resource_reference_is_still_rejected(parse):
    """The exception is exact: a different resource is still a pointer to nothing."""
    text = """
contract = "1"
[[android.requires.resources]]
type = "drawable"
name = "ic_stat_notify"
reason = "The status bar icon"

[[android.contributes.meta_data]]
key = "com.google.firebase.messaging.default_notification_color"
value = "@color/brand"
reason = "Tints the notification"
"""
    _, codes, _ = parse(text)
    assert codes == ["meta-data-resource-reference"]


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


def test_an_extension_kind_beyond_the_original_two_is_accepted(parse):
    """§7.3's `kind` is open (§4.4): Apple owns the vocabulary, not this spec."""
    text = """
contract = "1"
[[ios.requires.app_extensions]]
id = "rich_push"
kind = "notification_content"
reason = "because"
"""
    sidecar, codes, _ = parse(text, platform=Platform.IOS)
    assert codes == [] and len(sidecar.ios.prerequisites) == 1


def test_an_extension_kind_this_consumer_cannot_check_is_rejected(parse):
    """Open does not mean unchecked — the consumer fails closed on its own set."""
    text = """
contract = "1"
[[ios.requires.app_extensions]]
id = "odd"
kind = "com_example_not_an_extension_point"
reason = "because"
"""
    _, codes, _ = parse(text, platform=Platform.IOS)
    assert codes == ["extension-kind-unimplemented"]


def test_an_ios_application_value_is_declarable(parse):
    """§7.3 — the parallel table §6.3's rationale predicted."""
    text = """
contract = "1"
[[ios.requires.application_values]]
id = "facebook_app_id"
reason = "Your Meta app ID, from the App Dashboard"
info_plist_key = "FacebookAppID"
"""
    sidecar, codes, _ = parse(text, platform=Platform.IOS)
    assert codes == []
    (prerequisite,) = sidecar.ios.prerequisites
    assert prerequisite.key == "facebook_app_id"
    assert prerequisite.info_plist_key == "FacebookAppID"


def test_an_ios_application_value_needs_its_delivery_key(parse):
    """Required here, unlike §6.3: iOS has no inline reference site."""
    text = """
contract = "1"
[[ios.requires.application_values]]
id = "facebook_app_id"
reason = "Your Meta app ID"
"""
    _, codes, _ = parse(text, platform=Platform.IOS)
    assert codes == ["key-required"]


def test_an_application_value_may_not_deliver_a_purpose_string(parse):
    """An account identifier is not application-authored text."""
    text = """
contract = "1"
[[ios.requires.application_values]]
id = "why"
reason = "because"
info_plist_key = "NSCameraUsageDescription"
"""
    _, codes, _ = parse(text, platform=Platform.IOS)
    assert codes == ["plist-usage-description"]


def test_an_application_value_may_not_deliver_a_capability_key(parse):
    text = """
contract = "1"
[[ios.requires.application_values]]
id = "modes"
reason = "because"
info_plist_key = "UIBackgroundModes"
"""
    _, codes, _ = parse(text, platform=Platform.IOS)
    assert codes == ["plist-capability-key"]


def test_skadnetwork_identifiers_are_declarable(parse):
    """§7.6 — the narrow primitive, not dictionary support."""
    text = """
contract = "1"
[ios.contributes.info_plist]
skadnetwork_identifiers = ["su67r6k2v3.skadnetwork", "4fzdc2evr5.skadnetwork"]
"""
    sidecar, codes, _ = parse(text, platform=Platform.IOS)
    assert codes == []
    assert sidecar.ios.skadnetwork_identifiers == (
        "su67r6k2v3.skadnetwork",
        "4fzdc2evr5.skadnetwork",
    )


def test_a_malformed_skadnetwork_identifier_is_rejected(parse):
    """A mistyped identifier otherwise matches no network, silently."""
    text = """
contract = "1"
[ios.contributes.info_plist]
skadnetwork_identifiers = ["SU67R6K2V3.skadnetwork", "4fzdc2evr5"]
"""
    _, codes, _ = parse(text, platform=Platform.IOS)
    assert codes == ["skadnetwork-identifier-invalid", "skadnetwork-identifier-invalid"]


def test_skadnetworkitems_offered_directly_is_redirected(parse):
    """§7.6 — one destination, one merge rule, one place to look."""
    text = """
contract = "1"
[ios.contributes.info_plist.append]
SKAdNetworkItems = ["su67r6k2v3.skadnetwork"]
"""
    _, codes, _ = parse(text, platform=Platform.IOS)
    assert codes == ["skadnetwork-items-key"]


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


@pytest.mark.parametrize("mode", ["values", "append"])
@pytest.mark.parametrize("key", ["UIBackgroundModes", "UIRequiredDeviceCapabilities"])
def test_a_capability_key_may_not_be_contributed(parse, mode, key):
    """§7.6 — a producer's entry would grant a capability or restrict installation."""
    entry = '["remote-notification"]' if mode == "append" else '"x"'
    text = f'contract = "1"\n[ios.contributes.info_plist.{mode}]\n{key} = {entry}\n'
    _, codes, bag = parse(text, platform=Platform.IOS)
    assert "plist-capability-key" in codes
    assert "[[ios.requires.plist_capabilities]]" in bag.items[0].message


def test_an_ordinary_array_key_is_still_contributable(parse):
    """The line is capability, not array-valued: LSApplicationQueriesSchemes stays."""
    text = (
        'contract = "1"\n[ios.contributes.info_plist.append]\n'
        'LSApplicationQueriesSchemes = ["examplescheme"]\n'
    )
    _, codes, _ = parse(text, platform=Platform.IOS)
    assert codes == []


def test_a_capability_prerequisite_takes_a_key_from_the_closed_list(parse):
    text = """
contract = "1"
[[ios.requires.plist_capabilities]]
key = "UIFileSharingEnabled"
value = "true"
reason = "not on the closed list"
"""
    sidecar, codes, _ = parse(text, platform=Platform.IOS)
    assert sidecar is None and codes == ["type-invalid"]


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
