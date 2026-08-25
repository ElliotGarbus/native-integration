"""Discovery, the application's answers, the ports, and the §9 record."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib.metadata import EntryPoint
from pathlib import Path

import pytest

from native_integration import (
    Application,
    ArtifactManifest,
    Closure,
    ConsumerProfile,
    CredentialReference,
    Diagnostic,
    DiagnosticBag,
    GradleGraph,
    IntegrationError,
    IntegrationRecord,
    ManifestComponent,
    ManifestFeature,
    MappingAnswers,
    Origin,
    Platform,
    ResolutionFailure,
    ResolvedArtifact,
    ResolvedSwiftPackage,
    Resolvers,
    SwiftGraph,
    UnimplementedObligation,
    discover,
    read,
)
from native_integration.naming import Module
from native_integration.rules import (
    BEYOND_THE_READER,
    RULES,
    STRUCTURAL,
    rules_for_requirement,
)

PROFILE = ConsumerProfile(verify_resources=False)


# --- doubles ----------------------------------------------------------------


class FakeDistribution:
    def __init__(self, name, version, entries, root):
        self.metadata = {"Name": name}
        self.version = version
        self.entry_points = entries
        self._root = Path(root)

    def locate_file(self, relative):
        return self._root / relative


def fake_dist(tmp_path, name, module="pkg._native", body='contract = "1"\n', entries=None):
    root = tmp_path / name
    (root / module.replace(".", "/")).mkdir(parents=True, exist_ok=True)
    (root / module.replace(".", "/") / "native.toml").write_text(body, encoding="utf-8")
    if entries is None:
        entries = [EntryPoint("native", module, "native_integration.v1")]
    return FakeDistribution(name, "1.0.0", entries, root)


@dataclass
class FakeGradle:
    graph: GradleGraph
    fail: bool = False

    def resolve(self, requests, repositories, locked=None):
        self.locked = locked
        if self.fail:
            raise ResolutionFailure("Could not find com.example:widget:9.9.9")
        return self.graph


@dataclass
class FakeSwift:
    graph: SwiftGraph

    def resolve(self, requests, locked=None):
        self.locked = locked
        return self.graph


@dataclass
class FakeArtifacts:
    manifests: dict
    classes: dict
    classpath: list
    files: dict = field(default_factory=dict)

    def files_of(self, artifact):
        return self.files.get(artifact.coordinate, [])

    def manifest_of(self, artifact):
        return self.manifests.get(artifact.coordinate)

    def classes_of(self, artifact):
        return self.classes.get(artifact.coordinate, [])

    def classpath_classes(self):
        return self.classpath


# --- §3 discovery -----------------------------------------------------------


def test_the_entry_point_name_is_ignored(tmp_path):
    """§3.3 — a name-keyed lookup silently skips a distribution that labelled it differently."""
    dist = fake_dist(
        tmp_path,
        "oddly-named",
        entries=[EntryPoint("something-else", "pkg._native", "native_integration.v1")],
    )
    bag = DiagnosticBag()
    found = discover(closure=Closure.direct("oddly-named"), bag=bag, distributions=[dist])
    assert [s.distribution for s in found] == ["oddly-named"]


def test_a_distribution_outside_the_closure_is_not_read(tmp_path):
    dist = fake_dist(tmp_path, "debug-tool")
    bag = DiagnosticBag()
    found = discover(closure=Closure.direct("something-else"), bag=bag, distributions=[dist])
    assert found == [] and len(bag) == 0


def test_an_isolated_environment_may_treat_everything_as_a_candidate(tmp_path):
    dist = fake_dist(tmp_path, "anything")
    bag = DiagnosticBag()
    found = discover(closure=Closure.isolated_environment(), bag=bag, distributions=[dist])
    assert [s.distribution for s in found] == ["anything"]


def test_multiple_entries_fail_rather_than_being_merged(tmp_path):
    dist = fake_dist(
        tmp_path,
        "two-entries",
        entries=[
            EntryPoint("native", "pkg._native", "native_integration.v1"),
            EntryPoint("also", "pkg._other", "native_integration.v1"),
        ],
    )
    bag = DiagnosticBag()
    found = discover(closure=Closure.direct("two-entries"), bag=bag, distributions=[dist])
    assert found == []
    assert [d.rule.code for d in bag] == ["multiple-entry-points"]


def test_an_entry_point_with_an_attr_suffix_is_invalid(tmp_path):
    dist = fake_dist(
        tmp_path,
        "attr-suffix",
        entries=[EntryPoint("native", "pkg._native:thing", "native_integration.v1")],
    )
    bag = DiagnosticBag()
    assert discover(closure=Closure.direct("attr-suffix"), bag=bag, distributions=[dist]) == []
    assert [d.rule.code for d in bag] == ["entry-point-value-invalid"]


def test_a_named_directory_without_a_sidecar_fails(tmp_path):
    dist = fake_dist(tmp_path, "no-sidecar")
    (tmp_path / "no-sidecar" / "pkg" / "_native" / "native.toml").unlink()
    bag = DiagnosticBag()
    assert discover(closure=Closure.direct("no-sidecar"), bag=bag, distributions=[dist]) == []
    assert [d.rule.code for d in bag] == ["sidecar-missing"]


def test_a_real_installed_distribution_is_read_without_importing_it(tmp_path):
    """The metadata path, not a double: dist-info on disk, read by importlib.metadata."""
    import sys
    from importlib.metadata import PathDistribution

    site = tmp_path / "site-packages"
    (site / "demo_pkg" / "_native").mkdir(parents=True)
    (site / "demo_pkg" / "__init__.py").write_text(
        "raise RuntimeError('§3.2 forbids importing this on a build host')", encoding="utf-8"
    )
    (site / "demo_pkg" / "_native" / "native.toml").write_text(
        'contract = "1"\n[[android.contributes.permissions]]\n'
        'name = "android.permission.INTERNET"\nreason = "demo"\n',
        encoding="utf-8",
    )
    info = site / "demo_native_pkg-2.1.0.dist-info"
    info.mkdir()
    (info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: demo-native-pkg\nVersion: 2.1.0\n", encoding="utf-8"
    )
    (info / "entry_points.txt").write_text(
        "[native_integration.v1]\nnative = demo_pkg._native\n", encoding="utf-8"
    )

    bag = DiagnosticBag()
    found = discover(
        closure=Closure.direct("demo-native-pkg"),
        bag=bag,
        distributions=[PathDistribution(info)],
    )
    assert len(found) == 1 and found[0].version == "2.1.0"
    assert "demo_pkg" not in sys.modules

    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("demo-native-pkg"),
        application=Application(),
        sources=found,
        accept_current_surface=True,
    )
    assert integration.ok, integration.diagnostics.render()
    assert integration.effective.permissions()[0].name == "android.permission.INTERNET"
    assert integration.payload_exclusions() == ("demo_pkg/_native/",)


def test_the_closure_records_how_a_distribution_entered_it():
    closure = Closure.of({"analytics-shim": Origin(via=("some-ui-lib",))})
    assert closure.origin("analytics_shim").render() == "via some-ui-lib"
    assert Closure.direct("map-sdk").origin("map-sdk").render() == "direct dependency"


# --- diagnostics ------------------------------------------------------------


def test_a_diagnostic_cannot_be_built_without_attribution():
    """Requirement 8.15, discharged by the constructor."""
    with pytest.raises(ValueError, match="8.15"):
        Diagnostic(RULES["unknown-key"], "something", ())


# --- §2.2 answers, §6, §7 ---------------------------------------------------

SIDE = """
contract = "1"

[android.owns]
java_namespaces = ["org.pystripe"]

[android.contributes.src]
java = ["java"]

[android.requires]
min_sdk = 21
compile_sdk = 34

[[android.requires.application_values]]
id = "stripe_return_scheme"
reason = "The URL scheme you registered with Stripe"

[[android.contributes.permissions]]
name = "android.permission.INTERNET"
reason = "Stripe API calls"

[[android.contributes.components]]
kind = "activity"
name = "org.pystripe.PaymentReturnActivity"
exported_required = true
reason = "Receives the 3D Secure redirect"

  [[android.contributes.components.view_links]]
  scheme = { application_value = "stripe_return_scheme" }
  host = "stripe-redirect"
"""


#: SIDE registers `org.pystripe.PaymentReturnActivity`, which §6.8 requires the
#: sidecar to contribute, so every source built from it carries the class.
PAYMENT_ACTIVITY = {"java/org/pystripe/PaymentReturnActivity.java": "package org.pystripe;"}


def build(
    tmp_path, body=SIDE, *, name="pystripe", module="pystripe._native", files=None
):
    from native_integration import source_from_path

    root = tmp_path / name / module.replace(".", "/")
    root.mkdir(parents=True, exist_ok=True)
    (root / "native.toml").write_text(body, encoding="utf-8")
    for relative, content in {**PAYMENT_ACTIVITY, **(files or {})}.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return source_from_path(root, distribution=name, version="1.0.0", module=module)


def answered():
    return Application(
        android_sdk={"min_sdk": 24, "compile_sdk": 35},
        answers=MappingAnswers(
            application_values={"pystripe": {"stripe_return_scheme": "trailmap-pay"}},
            allow_exported={"pystripe": ["org.pystripe.PaymentReturnActivity"]},
        ),
    )


def test_an_unanswered_integration_blocks_and_says_what_is_missing(tmp_path):
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pystripe"),
        application=Application(android_sdk={"min_sdk": 24, "compile_sdk": 35}),
        profile=PROFILE,
        sources=[build(tmp_path)],
    )
    codes = {d.rule.code for d in integration.diagnostics}
    assert "application-value-unsupplied" in codes
    assert "component-export-unapproved" in codes
    assert not integration.ok


def test_an_answered_integration_substitutes_and_exports(tmp_path):
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pystripe"),
        application=answered(),
        profile=PROFILE,
        sources=[build(tmp_path)],
        accept_current_surface=True,
    )
    assert integration.ok, integration.diagnostics.render()
    component = integration.effective.exported_components()[0]
    assert component.view_links[0].scheme == "trailmap-pay"
    assert "android.intent.category.BROWSABLE" in component.view_links[0].categories


def test_an_unmet_floor_is_never_raised_for_you(tmp_path):
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pystripe"),
        application=Application(android_sdk={"min_sdk": 19, "compile_sdk": 34}),
        profile=PROFILE,
        sources=[build(tmp_path)],
    )
    floors = [d for d in integration.diagnostics if d.rule.code == "floor-unmet"]
    assert len(floors) == 1 and "min_sdk ≥ 21" in floors[0].message


def test_a_suppressed_permission_leaves_the_effective_manifest(tmp_path):
    application = Application(
        android_sdk={"min_sdk": 24, "compile_sdk": 35},
        answers=MappingAnswers(
            application_values={"pystripe": {"stripe_return_scheme": "x"}},
            allow_exported={"pystripe": ["org.pystripe.PaymentReturnActivity"]},
            suppressed_permissions=["android.permission.INTERNET"],
        ),
    )
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pystripe"),
        application=application,
        profile=PROFILE,
        sources=[build(tmp_path)],
        accept_current_surface=True,
    )
    assert integration.effective.permissions() == ()
    # Omitting it from the generated manifest is not sufficient: an .aar can
    # bring the same permission back through the merger.
    assert integration.effective.manifest_removals() == ("android.permission.INTERNET",)


def test_a_repository_needing_credentials_blocks_before_a_bare_401(tmp_path):
    body = """
contract = "1"
[[android.contributes.gradle_repositories]]
url = "https://api.mapbox.com/downloads/v2/releases/maven"
reason = "Needs a Mapbox token scoped DOWNLOADS:READ"
groups = ["com.mapbox"]
credentials_required = true
"""
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pymapbox"),
        application=Application(),
        profile=PROFILE,
        sources=[build(tmp_path, body, name="pymapbox", module="pymapbox._native")],
    )
    assert "repository-credentials-missing" in {d.rule.code for d in integration.diagnostics}


def test_a_credential_supplied_by_indirection_never_reaches_the_record(tmp_path):
    body = """
contract = "1"
[[android.contributes.gradle_repositories]]
url = "https://api.mapbox.com/downloads/v2/releases/maven"
reason = "Needs a Mapbox token scoped DOWNLOADS:READ"
groups = ["com.mapbox"]
credentials_required = true
"""
    secret = "sk.dont-record-me"
    application = Application(
        answers=MappingAnswers(
            credentials={
                "https://api.mapbox.com/downloads/v2/releases/maven": CredentialReference.from_env(
                    "MAPBOX_DOWNLOADS_TOKEN", username="mapbox"
                )
            }
        )
    )
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pymapbox"),
        application=application,
        profile=PROFILE,
        sources=[build(tmp_path, body, name="pymapbox", module="pymapbox._native")],
        accept_current_surface=True,
    )
    assert integration.ok
    dumped = integration.record.dumps()
    assert secret not in dumped and "MAPBOX_DOWNLOADS_TOKEN" not in dumped
    assert "authenticated — credentials configured" in dumped


# --- §7.3 satisfaction ------------------------------------------------------

IOS_SIDE = """
contract = "1"

[ios.requires]
deployment_target = "15.0"

[[ios.requires.usage_descriptions]]
key = "NSLocationWhenInUseUsageDescription"
reason = "requestWhenInUseAuthorization() traps if this key is absent"

[[ios.requires.url_schemes]]
id = "stripe_3ds_callback"
conditional = true
reason = "Required only if the 3D Secure webview fallback is reached"

[[ios.requires.app_extensions]]
id = "onesignal_nse"
kind = "notification_service"
reason = "Confirmed delivery and image attachments"
"""


def ios_read(tmp_path, application, **kwargs):
    return read(
        platform=Platform.IOS,
        closure=Closure.direct("pyios"),
        application=application,
        profile=PROFILE,
        sources=[build(tmp_path, IOS_SIDE, name="pyios", module="pyios._native")],
        **kwargs,
    )


def test_an_unconditional_prerequisite_fails_the_build(tmp_path):
    integration = ios_read(tmp_path, Application(deployment_target="16.0"))
    unsatisfied = [d for d in integration.diagnostics if d.rule.code == "prerequisite-unsatisfied"]
    assert {d.message.split("`")[1] for d in unsatisfied} == {
        "NSLocationWhenInUseUsageDescription",
        "onesignal_nse",
    }


def test_a_conditional_prerequisite_is_recorded_and_does_not_block(tmp_path):
    integration = ios_read(tmp_path, Application(deployment_target="16.0"))
    conditional = [d for d in integration.diagnostics if d.rule.code == "prerequisite-conditional"]
    assert len(conditional) == 1 and not conditional[0].blocking
    entries = integration.record.distributions[0].entries
    assert "requires url_schemes stripe_3ds_callback (conditional, unresolved)" in entries


def test_an_extension_needs_both_a_target_and_an_acknowledgement(tmp_path):
    """§7.3 — one existing target cannot be assumed to serve two producers."""
    only_target = Application(
        deployment_target="16.0",
        answers=MappingAnswers(
            usage_descriptions={"NSLocationWhenInUseUsageDescription": "Shows trails near you."},
            extension_targets=["notification_service"],
        ),
    )
    integration = ios_read(tmp_path, only_target)
    assert any(
        d.rule.code == "prerequisite-unsatisfied" and "onesignal_nse" in d.message
        for d in integration.diagnostics
    )

    both = Application(
        deployment_target="16.0",
        answers=MappingAnswers(
            usage_descriptions={"NSLocationWhenInUseUsageDescription": "Shows trails near you."},
            extension_targets=["notification_service"],
            acknowledged_ids={"pyios": ["onesignal_nse"]},
        ),
    )
    integration = ios_read(tmp_path, both, accept_current_surface=True)
    assert not any(d.rule.code == "prerequisite-unsatisfied" for d in integration.diagnostics)


CAPABILITY_SIDE = """
contract = "1"
[[ios.requires.plist_capabilities]]
key = "UIBackgroundModes"
value = "remote-notification"
reason = "Silent pushes wake the application to fetch content"
"""


def test_a_capability_is_a_prerequisite_the_application_grants(tmp_path):
    """§7.3 — the producer states the need; the application's own plist grants it."""
    unanswered = read(
        platform=Platform.IOS,
        closure=Closure.direct("pypush"),
        application=Application(),
        profile=PROFILE,
        sources=[build(tmp_path, CAPABILITY_SIDE, name="pypush", module="pypush._native")],
    )
    blocked = [d for d in unanswered.diagnostics if d.rule.code == "prerequisite-unsatisfied"]
    assert len(blocked) == 1 and "UIBackgroundModes" in blocked[0].message

    granted = read(
        platform=Platform.IOS,
        closure=Closure.direct("pypush"),
        application=Application(
            answers=MappingAnswers(
                plist_capabilities={"UIBackgroundModes": ["remote-notification"]}
            )
        ),
        profile=PROFILE,
        sources=[build(tmp_path, CAPABILITY_SIDE, name="pypush", module="pypush._native")],
        accept_current_surface=True,
    )
    assert granted.ok, granted.diagnostics.render()


def test_one_application_answer_satisfies_every_producer_that_asked(tmp_path):
    """Joined by (key, value), not by distribution: the plist key is app-wide."""
    a = build(tmp_path, CAPABILITY_SIDE, name="pypush-a", module="pypush_a._native")
    b = build(tmp_path, CAPABILITY_SIDE, name="pypush-b", module="pypush_b._native")
    integration = read(
        platform=Platform.IOS,
        closure=Closure.direct("pypush-a", "pypush-b"),
        application=Application(
            answers=MappingAnswers(
                plist_capabilities={"UIBackgroundModes": ["remote-notification"]}
            )
        ),
        profile=PROFILE,
        sources=[a, b],
        accept_current_surface=True,
    )
    assert integration.ok, integration.diagnostics.render()
    assert len(integration.effective.prerequisites()) == 2


def test_a_capability_a_different_value_does_not_satisfy(tmp_path):
    integration = read(
        platform=Platform.IOS,
        closure=Closure.direct("pypush"),
        application=Application(
            answers=MappingAnswers(plist_capabilities={"UIBackgroundModes": ["location"]})
        ),
        profile=PROFILE,
        sources=[build(tmp_path, CAPABILITY_SIDE, name="pypush", module="pypush._native")],
    )
    assert any(d.rule.code == "prerequisite-unsatisfied" for d in integration.diagnostics)


def test_an_ios_floor_is_compared_numerically(tmp_path):
    integration = ios_read(tmp_path, Application(deployment_target="14.0"))
    assert any(d.rule.code == "floor-unmet" for d in integration.diagnostics)


# --- cross-distribution -----------------------------------------------------


def test_two_distributions_claiming_overlapping_namespaces_fail_naming_both(tmp_path):
    a = build(
        tmp_path,
        'contract = "1"\n[android.owns]\njava_namespaces = ["org.example"]\n',
        name="pkg-a",
        module="pkg_a._native",
    )
    b = build(
        tmp_path,
        'contract = "1"\n[android.owns]\njava_namespaces = ["org.example.sub"]\n',
        name="pkg-b",
        module="pkg_b._native",
    )
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pkg-a", "pkg-b"),
        application=Application(),
        profile=PROFILE,
        sources=[a, b],
    )
    overlap = [d for d in integration.diagnostics if d.rule.code == "namespace-overlap"]
    assert len(overlap) == 1
    assert set(overlap[0].distributions) == {"pkg-a", "pkg-b"}


def test_contested_repository_scopes_name_both_and_the_coordinates(tmp_path):
    repo = """
contract = "1"
[[android.contributes.gradle_repositories]]
url = "https://repo-{n}.example/maven"
reason = "hosts com.example"
groups = ["com.example"]
"""
    a = build(tmp_path, repo.format(n="a"), name="package-a", module="package_a._native")
    b = build(tmp_path, repo.format(n="b"), name="package-b", module="package_b._native")
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("package-a", "package-b"),
        application=Application(),
        profile=PROFILE,
        sources=[a, b],
    )
    overlap = [d for d in integration.diagnostics if d.rule.code == "repository-scope-overlap"]
    assert len(overlap) == 1
    assert set(overlap[0].distributions) == {"package-a", "package-b"}
    assert "com.example may resolve from two repositories" in overlap[0].message


def test_the_same_repository_url_twice_is_not_a_conflict(tmp_path):
    repo = """
contract = "1"
[[android.contributes.gradle_repositories]]
url = "https://repo.example/maven"
reason = "hosts com.example"
groups = ["com.example"]
"""
    a = build(tmp_path, repo, name="package-a", module="package_a._native")
    b = build(tmp_path, repo, name="package-b", module="package_b._native")
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("package-a", "package-b"),
        application=Application(),
        profile=PROFILE,
        sources=[a, b],
        accept_current_surface=True,
    )
    assert integration.ok


def test_two_distributions_delivering_different_meta_data_values_fail(tmp_path):
    body = """
contract = "1"
[[android.requires.application_values]]
id = "app_id"
reason = "your id"
manifest_meta_data = "com.vendor.APPLICATION_ID"
"""
    a = build(tmp_path, body, name="wrap-a", module="wrap_a._native")
    b = build(tmp_path, body, name="wrap-b", module="wrap_b._native")
    application = Application(
        answers=MappingAnswers(
            application_values={"wrap-a": {"app_id": "one"}, "wrap-b": {"app_id": "two"}}
        )
    )
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("wrap-a", "wrap-b"),
        application=application,
        profile=PROFILE,
        sources=[a, b],
    )
    conflict = [d for d in integration.diagnostics if d.rule.code == "meta-data-conflict"]
    assert len(conflict) == 1 and set(conflict[0].distributions) == {"wrap-a", "wrap-b"}


def test_equal_meta_data_values_coalesce(tmp_path):
    body = """
contract = "1"
[[android.requires.application_values]]
id = "app_id"
reason = "your id"
manifest_meta_data = "com.vendor.APPLICATION_ID"
"""
    a = build(tmp_path, body, name="wrap-a", module="wrap_a._native")
    b = build(tmp_path, body, name="wrap-b", module="wrap_b._native")
    application = Application(
        answers=MappingAnswers(
            application_values={"wrap-a": {"app_id": "same"}, "wrap-b": {"app_id": "same"}}
        )
    )
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("wrap-a", "wrap-b"),
        application=application,
        profile=PROFILE,
        sources=[a, b],
        accept_current_surface=True,
    )
    assert integration.ok
    # Both provenance records survive: one entry per distribution.
    assert sum(len(c.meta_data) for c in integration.effective.contributions) == 2


# --- ports ------------------------------------------------------------------

WITH_DEPENDENCY = """
contract = "1"
[android.owns]
java_namespaces = ["org.example"]
[[android.contributes.gradle_dependencies]]
coordinate = "com.example:widget:1.2.3"
[android.contributes.r8]
keep_classes = ["org.example.**"]
[[android.contributes.r8.keep]]
pattern = "okhttp3.**"
from_dependency = "com.example:widget"
"""


def widget_graph(version="1.2.3", checksum="sha256:aaa"):
    return GradleGraph(
        (
            ResolvedArtifact(
                Module("com.example", "widget"), version, checksum, declared_by=("pkg-dep",)
            ),
        )
    )


def dep_read(tmp_path, resolvers, **kwargs):
    return read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pkg-dep"),
        application=Application(shrinking_enabled=True),
        profile=PROFILE,
        resolvers=resolvers,
        sources=[build(tmp_path, WITH_DEPENDENCY, name="pkg-dep", module="pkg_dep._native")],
        **kwargs,
    )


def test_a_missing_resolver_raises_rather_than_passing_quietly(tmp_path):
    with pytest.raises(UnimplementedObligation) as exc:
        dep_read(tmp_path, Resolvers())
    assert "requirements 8.12, 8.16" in str(exc.value)
    assert "pkg-dep" in str(exc.value)


def test_a_missing_artifact_inspector_raises(tmp_path):
    with pytest.raises(UnimplementedObligation) as exc:
        dep_read(tmp_path, Resolvers(gradle=FakeGradle(widget_graph())))
    assert "ArtifactInspector" in str(exc.value)


def test_resolution_failure_names_every_declared_coordinate(tmp_path):
    integration = dep_read(
        tmp_path,
        Resolvers(
            gradle=FakeGradle(GradleGraph(), fail=True),
            artifacts=FakeArtifacts({}, {}, []),
        ),
    )
    failure = [d for d in integration.diagnostics if d.rule.code == "resolution-failed"][0]
    assert failure.distributions == ("pkg-dep",)
    assert "com.example:widget:1.2.3  ← pkg-dep" in failure.detail


def test_a_higher_resolved_version_is_shown_alongside_the_request(tmp_path):
    resolvers = Resolvers(
        gradle=FakeGradle(widget_graph(version="1.4.0")),
        artifacts=FakeArtifacts({"com.example:widget:1.4.0": None}, {}, []),
    )
    integration = dep_read(tmp_path, resolvers, accept_current_surface=True)
    substituted = [
        d for d in integration.diagnostics if d.rule.code == "dependency-version-substituted"
    ]
    assert "requested 1.2.3 → resolved 1.4.0" in substituted[0].message
    assert any("requested 1.2.3 → resolved 1.4.0" in e for e in integration.record.distributions[0].entries)


def test_a_keep_pattern_matching_a_foreign_class_is_rejected(tmp_path):
    """§6.9 — checked against the classpath, not only the named artifact."""
    resolvers = Resolvers(
        gradle=FakeGradle(widget_graph()),
        artifacts=FakeArtifacts(
            manifests={"com.example:widget:1.2.3": None},
            classes={"com.example:widget:1.2.3": ["okhttp3.OkHttpClient"]},
            classpath=["okhttp3.OkHttpClient", "okhttp3.extra.Bar"],
        ),
    )
    integration = dep_read(tmp_path, resolvers)
    stray = [d for d in integration.diagnostics if d.rule.code == "keep-matches-foreign-class"]
    assert len(stray) == 1 and "okhttp3.extra.Bar" in stray[0].message


def test_a_keep_pattern_within_the_named_artifact_passes(tmp_path):
    resolvers = Resolvers(
        gradle=FakeGradle(widget_graph()),
        artifacts=FakeArtifacts(
            manifests={"com.example:widget:1.2.3": None},
            classes={"com.example:widget:1.2.3": ["okhttp3.OkHttpClient", "okhttp3.extra.Bar"]},
            classpath=["okhttp3.OkHttpClient", "okhttp3.extra.Bar", "org.other.Thing"],
        ),
    )
    integration = dep_read(tmp_path, resolvers, accept_current_surface=True)
    assert integration.ok, integration.diagnostics.render()


def test_a_checksum_mismatch_fails_the_next_build(tmp_path):
    resolvers = Resolvers(
        gradle=FakeGradle(widget_graph()),
        artifacts=FakeArtifacts({"com.example:widget:1.2.3": None}, {}, []),
    )
    first = dep_read(tmp_path, resolvers, accept_current_surface=True)
    record_path = tmp_path / "record.json"
    first.accept(record_path)

    moved = Resolvers(
        gradle=FakeGradle(widget_graph(checksum="sha256:bbb")),
        artifacts=FakeArtifacts({"com.example:widget:1.2.3": None}, {}, []),
    )
    second = dep_read(tmp_path, moved, record_path=record_path)
    codes = {d.rule.code for d in second.diagnostics}
    assert "dependency-checksum-mismatch" in codes


def test_the_recorded_graph_is_handed_back_to_the_resolver(tmp_path):
    """§6.5 — resolve *from the record* on subsequent builds, so the lock is an input."""
    record_path = tmp_path / "record.json"
    dep_read(
        tmp_path,
        Resolvers(
            gradle=FakeGradle(widget_graph()),
            artifacts=FakeArtifacts({"com.example:widget:1.2.3": None}, {}, []),
        ),
        accept_current_surface=True,
    ).accept(record_path)

    second = FakeGradle(widget_graph())
    dep_read(
        tmp_path,
        Resolvers(
            gradle=second, artifacts=FakeArtifacts({"com.example:widget:1.2.3": None}, {}, [])
        ),
        record_path=record_path,
    )
    assert [a.coordinate for a in second.locked.artifacts] == ["com.example:widget:1.2.3"]
    assert second.locked.artifacts[0].checksum == "sha256:aaa"


def test_an_artifacts_own_manifest_is_reported_and_a_required_feature_overridden(tmp_path):
    manifest = ArtifactManifest(
        permissions=("com.google.android.gms.permission.AD_ID",),
        features=(ManifestFeature("android.hardware.camera", required=True),),
        components=(ManifestComponent("activity", "com.example.Ad", exported=True),),
        proguard_rules=True,
    )
    resolvers = Resolvers(
        gradle=FakeGradle(widget_graph()),
        artifacts=FakeArtifacts({"com.example:widget:1.2.3": manifest}, {}, []),
    )
    integration = dep_read(tmp_path, resolvers, accept_current_surface=True)
    codes = [d.rule.code for d in integration.diagnostics]
    assert "artifact-permission" in codes
    assert "artifact-feature-overridden" in codes
    assert "artifact-exported-component" in codes
    assert "artifact-proguard-rules" in codes
    entries = integration.record.distributions[0].entries
    assert any("resolved artifact manifest" in e for e in entries)


def test_a_resolved_swift_graph_with_a_branch_dependency_is_rejected(tmp_path):
    body = """
contract = "1"
[[ios.contributes.swift_packages]]
name = "Shim"
url = "https://example.com/shim"
requirement = { exact = "1.2.3" }
products = ["Shim"]
"""
    graph = SwiftGraph(
        (
            ResolvedSwiftPackage("Shim", "https://example.com/shim", "version", "1.2.3", "abc123"),
            ResolvedSwiftPackage(
                "Hidden", "https://example.com/hidden", "branch", None, "def456", ("pkg-swift",)
            ),
        )
    )
    integration = read(
        platform=Platform.IOS,
        closure=Closure.direct("pkg-swift"),
        application=Application(),
        profile=PROFILE,
        resolvers=Resolvers(swift=FakeSwift(graph)),
        sources=[build(tmp_path, body, name="pkg-swift", module="pkg_swift._native")],
    )
    assert "swift-graph-unpinnable" in {d.rule.code for d in integration.diagnostics}


def test_the_swift_record_keeps_the_revision_not_only_the_version(tmp_path):
    body = """
contract = "1"
[[ios.contributes.swift_packages]]
name = "Shim"
url = "https://example.com/shim"
requirement = { exact = "1.2.3" }
products = ["Shim"]
"""
    graph = SwiftGraph(
        (ResolvedSwiftPackage("Shim", "https://example.com/shim", "version", "1.2.3", "abc123"),)
    )
    integration = read(
        platform=Platform.IOS,
        closure=Closure.direct("pkg-swift"),
        application=Application(),
        profile=PROFILE,
        resolvers=Resolvers(swift=FakeSwift(graph)),
        sources=[build(tmp_path, body, name="pkg-swift", module="pkg_swift._native")],
        accept_current_surface=True,
    )
    assert integration.record.distributions[0].swift == {"Shim": "1.2.3 @ abc123"}


# --- §9 the record ----------------------------------------------------------


def test_the_first_build_is_not_an_exemption(tmp_path):
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pystripe"),
        application=answered(),
        profile=PROFILE,
        sources=[build(tmp_path)],
        record_path=tmp_path / "record.json",
    )
    absent = [d for d in integration.diagnostics if d.rule.code == "record-absent"]
    assert len(absent) == 1 and absent[0].blocking
    assert not (tmp_path / "record.json").exists()  # nothing written without acceptance


def test_an_accepted_record_makes_the_next_identical_build_quiet(tmp_path):
    record_path = tmp_path / "record.json"
    first = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pystripe"),
        application=answered(),
        profile=PROFILE,
        sources=[build(tmp_path)],
        record_path=record_path,
        accept_current_surface=True,
    )
    first.accept()
    second = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pystripe"),
        application=answered(),
        profile=PROFILE,
        sources=[build(tmp_path)],
        record_path=record_path,
    )
    assert second.ok and second.delta.empty


def test_a_new_permission_fails_the_build_attributed_to_its_distribution(tmp_path):
    record_path = tmp_path / "record.json"
    read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pystripe"),
        application=answered(),
        profile=PROFILE,
        sources=[build(tmp_path)],
        record_path=record_path,
        accept_current_surface=True,
    ).accept()

    grown = SIDE + """
[[android.contributes.permissions]]
name = "android.permission.ACCESS_FINE_LOCATION"
reason = "added in the version bump"
"""
    second = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pystripe"),
        application=answered(),
        profile=PROFILE,
        sources=[build(tmp_path, grown)],
        record_path=record_path,
    )
    drift = [d for d in second.diagnostics if d.rule.code == "record-drift"]
    assert len(drift) == 1 and drift[0].distributions == ("pystripe",)
    assert any("ACCESS_FINE_LOCATION" in line for line in drift[0].detail)


def test_a_changed_input_file_is_named_by_path(tmp_path):
    from native_integration import source_from_path

    root = tmp_path / "srcpkg" / "srcpkg" / "_native"
    (root / "java" / "org" / "example").mkdir(parents=True)
    (root / "native.toml").write_text(
        'contract = "1"\n[android.owns]\njava_namespaces = ["org.example"]\n'
        '[android.contributes.src]\njava = ["java"]\n',
        encoding="utf-8",
    )
    bridge = root / "java" / "org" / "example" / "Bridge.java"
    bridge.write_text("package org.example;\nclass Bridge {}\n", encoding="utf-8")
    source = source_from_path(root, distribution="srcpkg", version="1.0.0", module="srcpkg._native")

    record_path = tmp_path / "record.json"
    first = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("srcpkg"),
        application=Application(),
        sources=[source],
        record_path=record_path,
        accept_current_surface=True,
    )
    assert "java/org/example/Bridge.java" in first.record.distributions[0].inputs
    first.accept()

    bridge.write_text("package org.example;\nclass Bridge { int x; }\n", encoding="utf-8")
    second = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("srcpkg"),
        application=Application(),
        sources=[source],
        record_path=record_path,
    )
    assert second.delta.changed_inputs == (("srcpkg", "java/org/example/Bridge.java"),)
    drift = [d for d in second.diagnostics if d.rule.code == "record-drift"][0]
    assert any("Bridge.java changed" in line for line in drift.detail)


def test_the_report_says_how_a_distribution_entered_the_closure(tmp_path):
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.of({"pystripe": Origin(via=("some-ui-lib",))}),
        application=answered(),
        profile=PROFILE,
        sources=[build(tmp_path)],
        accept_current_surface=True,
    )
    assert "pystripe 1.0.0  (via some-ui-lib)" in integration.report()


def test_a_record_round_trips(tmp_path):
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pystripe"),
        application=answered(),
        profile=PROFILE,
        sources=[build(tmp_path)],
        accept_current_surface=True,
    )
    path = integration.accept(tmp_path / "record.json")
    assert IntegrationRecord.read(path) == integration.record


def test_payload_exclusions_cover_the_sidecar_and_module_stubs(tmp_path):
    body = """
contract = "1"
[[ios.contributes.swift_packages]]
name = "PyWebViews"
url = "https://example.com/wv"
requirement = { exact = "1.0.0" }
products = ["PyWebViews"]
[[ios.contributes.python_modules]]
name = "web_views"
swift_package = "PyWebViews"
"""
    graph = SwiftGraph(
        (ResolvedSwiftPackage("PyWebViews", "https://example.com/wv", "version", "1.0.0", "abc"),)
    )
    integration = read(
        platform=Platform.IOS,
        closure=Closure.direct("pywebviews"),
        application=Application(),
        profile=PROFILE,
        resolvers=Resolvers(swift=FakeSwift(graph)),
        sources=[build(tmp_path, body, name="pywebviews", module="pywebviews._native")],
        accept_current_surface=True,
    )
    exclusions = integration.payload_exclusions()
    assert "web_views.py" in exclusions and "web_views.pyi" in exclusions
    assert "pywebviews/_native/" in exclusions


# --- regressions ------------------------------------------------------------


def test_one_sidecar_may_not_register_a_module_name_twice(tmp_path):
    """The same ambiguity as the cross-distribution case, by a shorter path."""
    body = """
contract = "1"
[[ios.contributes.swift_packages]]
name = "A"
url = "https://example.com/a"
requirement = { exact = "1.0.0" }
products = ["A"]
[[ios.contributes.swift_packages]]
name = "B"
url = "https://example.com/b"
requirement = { exact = "1.0.0" }
products = ["B"]
[[ios.contributes.python_modules]]
name = "web_views"
swift_package = "A"
[[ios.contributes.python_modules]]
name = "web_views"
swift_package = "B"
"""
    integration = read(
        platform=Platform.IOS,
        closure=Closure.direct("pkg-two"),
        application=Application(),
        profile=PROFILE,
        resolvers=Resolvers(swift=FakeSwift(SwiftGraph())),
        sources=[build(tmp_path, body, name="pkg-two", module="pkg_two._native")],
    )
    duplicates = [d for d in integration.diagnostics if d.rule.code == "python-module-duplicate"]
    assert len(duplicates) == 1 and duplicates[0].blocking


def test_an_unsupplied_value_is_absent_rather_than_a_placeholder(tmp_path):
    """A caller that stages before checking must not get `${id}` in a manifest."""
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pystripe"),
        application=Application(android_sdk={"min_sdk": 24, "compile_sdk": 35}),
        profile=PROFILE,
        sources=[build(tmp_path)],
    )
    link = integration.effective.contributions[0].components[0].view_links[0]
    assert link.scheme is None
    assert link.unresolved == ("stripe_return_scheme",)
    assert not link.complete
    assert "unsupplied" in link.render()


def test_a_malformed_record_names_the_file_rather_than_raising_a_traceback(tmp_path):
    from native_integration import MalformedRecord

    truncated = tmp_path / "truncated.json"
    truncated.write_text('{"distributions": [{"name":', encoding="utf-8")
    with pytest.raises(MalformedRecord, match="is not valid JSON"):
        IntegrationRecord.read(truncated)

    wrong_shape = tmp_path / "wrong.json"
    wrong_shape.write_text('{"distributions": "not-a-list"}', encoding="utf-8")
    with pytest.raises(MalformedRecord, match="not a list of objects"):
        IntegrationRecord.read(wrong_shape)

    # An absent record is still None: "no record yet" is a different situation
    # from "a record I could not read", and only the first bootstraps.
    assert IntegrationRecord.read(tmp_path / "absent.json") is None


def test_an_unreadable_record_does_not_silently_re_bootstrap(tmp_path):
    from native_integration import MalformedRecord

    record_path = tmp_path / "record.json"
    record_path.write_text("}{ not json", encoding="utf-8")
    with pytest.raises(MalformedRecord):
        read(
            platform=Platform.ANDROID,
            closure=Closure.direct("pystripe"),
            application=answered(),
            profile=PROFILE,
            sources=[build(tmp_path)],
            record_path=record_path,
        )


SWIFT_SIDE = """
contract = "1"
[[ios.contributes.swift_packages]]
name = "Shim"
url = "https://example.com/shim"
requirement = { exact = "1.2.3" }
products = ["Shim"]
"""


def swift_read(tmp_path, targets, *, record_path=None, **kwargs):
    from native_integration.testing import stub_resolvers

    return read(
        platform=Platform.IOS,
        closure=Closure.direct("pkg-bin"),
        application=Application(),
        profile=PROFILE,
        resolvers=stub_resolvers(binary_targets={"Shim": targets}),
        sources=[build(tmp_path, SWIFT_SIDE, name="pkg-bin", module="pkg_bin._native")],
        record_path=record_path,
        **kwargs,
    )


def test_a_binary_targets_checksum_is_recorded_and_verified(tmp_path):
    """§7.4 — a package's revision pins its source, not bytes fetched from a URL."""
    from native_integration import BinaryTarget

    record_path = tmp_path / "record.json"
    first = swift_read(
        tmp_path,
        [BinaryTarget("ShimBinary", checksum="sha256:aaa", url="https://example.com/x.zip")],
        record_path=record_path,
        accept_current_surface=True,
    )
    assert first.record.distributions[0].swift_binaries == {"Shim/ShimBinary": "sha256:aaa"}
    first.accept()

    moved = swift_read(
        tmp_path,
        [BinaryTarget("ShimBinary", checksum="sha256:bbb", url="https://example.com/x.zip")],
        record_path=record_path,
    )
    mismatch = [
        d for d in moved.diagnostics if d.rule.code == "swift-binary-checksum-mismatch"
    ]
    assert len(mismatch) == 1 and mismatch[0].distributions == ("pkg-bin",)


def test_a_remote_binary_target_without_a_checksum_warns(tmp_path):
    from native_integration import BinaryTarget

    integration = swift_read(
        tmp_path,
        [BinaryTarget("ShimBinary", url="https://example.com/x.zip")],
        accept_current_surface=True,
    )
    warned = [d for d in integration.diagnostics if d.rule.code == "swift-binary-unchecksummed"]
    assert len(warned) == 1 and not warned[0].blocking


def test_a_local_binary_target_is_pinned_by_the_packages_revision(tmp_path):
    """No url means the bytes came with the checkout the revision already pins."""
    from native_integration import BinaryTarget

    integration = swift_read(
        tmp_path, [BinaryTarget("Vendored")], accept_current_surface=True
    )
    assert integration.ok, integration.diagnostics.render()


def test_accept_refuses_to_record_a_surface_that_cannot_be_built(tmp_path):
    """A record says the application accepted a surface *and could build it*."""
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pystripe"),
        application=Application(android_sdk={"min_sdk": 1, "compile_sdk": 1}),
        profile=PROFILE,
        sources=[build(tmp_path)],
        accept_current_surface=True,
    )
    codes = {d.rule.code for d in integration.gate_only}
    assert {"floor-unmet", "application-value-unsupplied", "component-export-unapproved"} <= codes

    with pytest.raises(IntegrationError):
        integration.accept(tmp_path / "record.json")
    assert not (tmp_path / "record.json").exists()


def test_accept_proceeds_when_only_the_record_gate_is_blocking(tmp_path):
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pystripe"),
        application=answered(),
        profile=PROFILE,
        sources=[build(tmp_path)],
        record_path=tmp_path / "record.json",
    )
    assert [d.rule.code for d in integration.errors] == ["record-absent"]
    assert integration.gate_only == ()
    assert integration.accept().exists()


def test_closure_from_installed_reports_what_it_could_not_find():
    closure = Closure.from_installed(["definitely-not-installed-xyz"])
    assert closure.missing == ("definitely-not-installed-xyz",)


# --- Batch 1: §6.7 attributes, §6.3 placeholders, §6.2's boolean floor ------


SCAN_STRICT = """
contract = "1"
platforms = ["android"]
[[android.contributes.permissions]]
name = "android.permission.BLUETOOTH_SCAN"
reason = "Beacon discovery, never for location"
never_for_location = true
max_sdk_version = 33
"""

SCAN_LOOSE = """
contract = "1"
platforms = ["android"]
[[android.contributes.permissions]]
name = "android.permission.BLUETOOTH_SCAN"
reason = "Scanning, and it does infer position"
"""


def test_one_permission_two_producers_takes_the_widest_need(tmp_path):
    """§6.7 — a permission is one fact about the built application.

    The strict declaration cannot narrow what the loose one needs: if any
    producer might derive location from a scan, the application cannot assert
    that none will, and a ceiling one producer does not want disappears.
    """
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("py-strict", "py-loose"),
        application=Application(android_sdk={"min_sdk": 24, "compile_sdk": 35}),
        profile=PROFILE,
        sources=[
            build(tmp_path, SCAN_STRICT, name="py-strict", module="py_strict._native"),
            build(tmp_path, SCAN_LOOSE, name="py-loose", module="py_loose._native"),
        ],
        accept_current_surface=True,
    )
    (permission,) = integration.effective.permissions()
    assert permission.name == "android.permission.BLUETOOTH_SCAN"
    assert permission.never_for_location is False
    assert permission.max_sdk_version is None
    assert integration.effective.permission_provenance(permission.name) == (
        "py-loose",
        "py-strict",
    )


def test_an_attribute_survives_when_nothing_contradicts_it(tmp_path):
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("py-strict"),
        application=Application(android_sdk={"min_sdk": 24, "compile_sdk": 35}),
        profile=PROFILE,
        sources=[build(tmp_path, SCAN_STRICT, name="py-strict", module="py_strict._native")],
        accept_current_surface=True,
    )
    (permission,) = integration.effective.permissions()
    assert permission.never_for_location and permission.max_sdk_version == 33


DESUGARING = """
contract = "1"
platforms = ["android"]
[android.requires]
core_library_desugaring = true
"""


def test_the_desugaring_floor_blocks_until_the_application_enables_it(tmp_path):
    """§6.2 — the consumer never enables it on the producer's behalf."""
    source = build(tmp_path, DESUGARING, name="py-media", module="py_media._native")
    unset = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("py-media"),
        application=Application(android_sdk={"min_sdk": 24, "compile_sdk": 35}),
        profile=PROFILE,
        sources=[source],
    )
    assert "floor-unmet" in [d.rule.code for d in unset.diagnostics]

    enabled = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("py-media"),
        application=Application(
            android_sdk={"min_sdk": 24, "compile_sdk": 35}, core_library_desugaring=True
        ),
        profile=PROFILE,
        sources=[source],
        accept_current_surface=True,
    )
    assert "floor-unmet" not in [d.rule.code for d in enabled.diagnostics]


PLACEHOLDER = """
contract = "1"
platforms = ["android"]
[[android.requires.application_values]]
id = "auth0_domain"
reason = "Your Auth0 tenant domain"
manifest_placeholder = "auth0Domain"
"""


def test_a_placeholder_is_delivered_and_recorded(tmp_path):
    """§6.3 — the value reaches a declared dependency's own manifest."""
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("py-auth0"),
        application=Application(
            android_sdk={"min_sdk": 24, "compile_sdk": 35},
            answers=MappingAnswers(
                application_values={"py-auth0": {"auth0_domain": "example.eu.auth0.com"}}
            ),
        ),
        profile=PROFILE,
        sources=[build(tmp_path, PLACEHOLDER, name="py-auth0", module="py_auth0._native")],
        accept_current_surface=True,
    )
    (contribution,) = integration.effective.contributions
    (placeholder,) = contribution.placeholders
    assert (placeholder.key, placeholder.value) == ("auth0Domain", "example.eu.auth0.com")
    record = integration.record
    assert any(
        "placeholder auth0Domain = example.eu.auth0.com" in line
        for distribution in record.distributions
        for line in distribution.entries
    )


ADS_A = """
contract = "1"
platforms = ["ios"]
[ios.contributes.info_plist]
skadnetwork_identifiers = ["su67r6k2v3.skadnetwork", "shared00id.skadnetwork"]
"""

ADS_B = """
contract = "1"
platforms = ["ios"]
[ios.contributes.info_plist]
skadnetwork_identifiers = ["shared00id.skadnetwork", "4fzdc2evr5.skadnetwork"]
"""


def test_skadnetwork_identifiers_merge_like_append(tmp_path):
    """§7.6 — application first, then distributions in name order, de-duplicated.

    Two mediation wrappers sharing a network is the ordinary case, not the
    exception: the shared identifier appears once, and the dictionary shape is
    the consumer's to render.
    """
    integration = read(
        platform=Platform.IOS,
        closure=Closure.direct("py-ads-a", "py-ads-b"),
        application=Application(
            deployment_target="15.0",
            skadnetwork_identifiers=("app00000id.skadnetwork",),
        ),
        profile=PROFILE,
        sources=[
            build(tmp_path, ADS_A, name="py-ads-a", module="py_ads_a._native"),
            build(tmp_path, ADS_B, name="py-ads-b", module="py_ads_b._native"),
        ],
        accept_current_surface=True,
    )
    items = integration.effective.skadnetwork_items(
        Application(
            deployment_target="15.0",
            skadnetwork_identifiers=("app00000id.skadnetwork",),
        )
    )
    assert [entry["SKAdNetworkIdentifier"] for entry in items] == [
        "app00000id.skadnetwork",
        "su67r6k2v3.skadnetwork",
        "shared00id.skadnetwork",
        "4fzdc2evr5.skadnetwork",
    ]


META = """
contract = "1"
platforms = ["ios"]
[[ios.requires.application_values]]
id = "facebook_app_id"
reason = "Your Meta app ID, from the App Dashboard"
info_plist_key = "FacebookAppID"
"""


def test_an_unsupplied_ios_application_value_blocks(tmp_path):
    """§7.3 — before this table the requirement could not even be stated."""
    integration = read(
        platform=Platform.IOS,
        closure=Closure.direct("py-meta"),
        application=Application(deployment_target="15.0"),
        profile=PROFILE,
        sources=[build(tmp_path, META, name="py-meta", module="py_meta._native")],
    )
    assert "prerequisite-unsatisfied" in [d.rule.code for d in integration.diagnostics]


def test_a_supplied_ios_application_value_reaches_the_plist(tmp_path):
    integration = read(
        platform=Platform.IOS,
        closure=Closure.direct("py-meta"),
        application=Application(
            deployment_target="15.0",
            answers=MappingAnswers(
                application_values={"py-meta": {"facebook_app_id": "1234567890"}}
            ),
        ),
        profile=PROFILE,
        sources=[build(tmp_path, META, name="py-meta", module="py_meta._native")],
        accept_current_surface=True,
    )
    assert [d.rule.code for d in integration.diagnostics] == []
    plist = integration.effective.info_plist(Application(deployment_target="15.0"))
    assert plist["FacebookAppID"] == "1234567890"


def test_the_application_keeps_its_own_plist_key_and_the_override_is_reported(tmp_path):
    """§7.3 — the same rule §6.3 states for a manifest key."""
    integration = read(
        platform=Platform.IOS,
        closure=Closure.direct("py-meta"),
        application=Application(
            deployment_target="15.0",
            info_plist_values={"FacebookAppID": "9999999999"},
            answers=MappingAnswers(
                application_values={"py-meta": {"facebook_app_id": "1234567890"}}
            ),
        ),
        profile=PROFILE,
        sources=[build(tmp_path, META, name="py-meta", module="py_meta._native")],
        accept_current_surface=True,
    )
    codes = [d.rule.code for d in integration.diagnostics]
    assert codes == ["meta-data-application-override"]
    (contribution,) = integration.effective.contributions
    (delivery,) = contribution.plist_deliveries
    assert delivery.value == "9999999999" and delivery.overridden_by_application


AUTOPILOT = """
contract = "1"
platforms = ["android"]
[android.owns]
java_namespaces = ["org.pyairship"]
[[android.contributes.meta_data]]
key = "com.urbanairship.autopilot"
value = "org.pyairship.PyAirshipAutopilot"
reason = "Loads Airship before any component receives an intent"
"""

FIXED_AND_SUPPLIED = """
contract = "1"
platforms = ["android"]
[[android.requires.application_values]]
id = "airship_key"
reason = "Your Airship app key"
manifest_meta_data = "com.urbanairship.autopilot"
"""


def test_a_fixed_meta_data_entry_reaches_the_manifest(tmp_path):
    """§6.10 — the declarative initialization path §11 said it was waiting for."""
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("py-airship"),
        application=Application(android_sdk={"min_sdk": 24, "compile_sdk": 35}),
        profile=PROFILE,
        sources=[build(tmp_path, AUTOPILOT, name="py-airship", module="py_airship._native")],
        accept_current_surface=True,
    )
    assert [d.rule.code for d in integration.diagnostics] == []
    (contribution,) = integration.effective.contributions
    (entry,) = contribution.meta_data
    assert entry.key == "com.urbanairship.autopilot"
    assert entry.value == "org.pyairship.PyAirshipAutopilot"


def test_a_fixed_entry_and_a_delivered_one_share_a_key_space(tmp_path):
    """§6.10 — set here and delivered there are the same manifest entry.

    Two distributions putting different values under one key fail, whichever
    half of §6.3 each of them used. Before this table the collision could not
    arise, because a producer had no way to set a key it knew the value of.
    """
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("py-airship", "py-other"),
        application=Application(
            android_sdk={"min_sdk": 24, "compile_sdk": 35},
            answers=MappingAnswers(application_values={"py-other": {"airship_key": "zzz"}}),
        ),
        profile=PROFILE,
        sources=[
            build(tmp_path, AUTOPILOT, name="py-airship", module="py_airship._native"),
            build(tmp_path, FIXED_AND_SUPPLIED, name="py-other", module="py_other._native"),
        ],
    )
    conflict = [d for d in integration.diagnostics if d.rule.code == "meta-data-conflict"]
    assert conflict, [d.rule.code for d in integration.diagnostics]
    assert set(conflict[0].distributions) == {"py-airship", "py-other"}


def test_the_application_keeps_its_own_meta_data_key(tmp_path):
    """§6.10's veto: setting the key is how an application refuses."""
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("py-airship"),
        application=Application(
            android_sdk={"min_sdk": 24, "compile_sdk": 35},
            manifest_meta_data={"com.urbanairship.autopilot": "com.example.MyAutopilot"},
        ),
        profile=PROFILE,
        sources=[build(tmp_path, AUTOPILOT, name="py-airship", module="py_airship._native")],
        accept_current_surface=True,
    )
    assert [d.rule.code for d in integration.diagnostics] == ["meta-data-application-override"]
    (contribution,) = integration.effective.contributions
    (entry,) = contribution.meta_data
    assert entry.value == "com.example.MyAutopilot" and entry.overridden_by_application


FAMILY = """
contract = "1"
platforms = ["android"]
[[android.requires.application_files]]
name = "airshipconfig.properties"
reason = "App key and secret from the Airship dashboard"

[[android.requires.resources]]
type = "drawable"
name = "ic_stat_notify"
reason = "The status bar icon"

[[android.requires.application_classes]]
id = "wechat_entry"
package_suffix = "wxapi"
name = "WXEntryActivity"
reason = "WeChat resolves this class by name under your own application ID"
"""


def test_the_android_family_blocks_until_the_application_answers(tmp_path):
    """§6.11 — three prerequisites, three unmet, each naming its distribution."""
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("py-family"),
        application=Application(android_sdk={"min_sdk": 24, "compile_sdk": 35}),
        profile=PROFILE,
        sources=[build(tmp_path, FAMILY, name="py-family", module="py_family._native")],
    )
    unsatisfied = [
        d for d in integration.diagnostics if d.rule.code == "prerequisite-unsatisfied"
    ]
    assert len(unsatisfied) == 3
    assert all(d.distributions == ("py-family",) for d in unsatisfied)


def test_the_android_family_is_satisfied_the_way_each_table_says(tmp_path):
    """A file wired in, a resource declared, and a class acknowledged.

    The class is acknowledgement rather than presence because the behaviour a
    vendor fixes -- what it extends, what it forwards -- is uninspectable, which
    is §2.4's rule and §7.3's judgment for url_schemes.
    """
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("py-family"),
        application=Application(
            android_sdk={"min_sdk": 24, "compile_sdk": 35},
            answers=MappingAnswers(
                android_assets=["airshipconfig.properties"],
                resources=[("drawable", "ic_stat_notify")],
                acknowledged_ids={"py-family": ["wechat_entry"]},
            ),
        ),
        profile=PROFILE,
        sources=[build(tmp_path, FAMILY, name="py-family", module="py_family._native")],
        accept_current_surface=True,
    )
    assert [d.rule.code for d in integration.diagnostics] == []
    assert len(integration.effective.prerequisites()) == 3


VISIBILITY = """
contract = "1"
platforms = ["android"]
[[android.contributes.queries]]
package = "com.google.android.apps.healthdata"
reason = "Health Connect availability check"

[[android.requires.app_links]]
id = "branch_deep_links"
reason = "Register your Branch link domain and host assetlinks.json on it"
"""


def test_queries_are_recorded_and_app_links_block_until_acknowledged(tmp_path):
    """§6.12 discloses; §6.11's app_links is acknowledgement, so it blocks first."""
    unanswered = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("py-branch"),
        application=Application(android_sdk={"min_sdk": 24, "compile_sdk": 35}),
        profile=PROFILE,
        sources=[build(tmp_path, VISIBILITY, name="py-branch", module="py_branch._native")],
    )
    assert "prerequisite-unsatisfied" in [d.rule.code for d in unanswered.diagnostics]

    acknowledged = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("py-branch"),
        application=Application(
            android_sdk={"min_sdk": 24, "compile_sdk": 35},
            answers=MappingAnswers(acknowledged_ids={"py-branch": ["branch_deep_links"]}),
        ),
        profile=PROFILE,
        sources=[build(tmp_path, VISIBILITY, name="py-branch", module="py_branch._native")],
        accept_current_surface=True,
    )
    assert [d.rule.code for d in acknowledged.diagnostics] == []
    (contribution,) = acknowledged.effective.contributions
    assert contribution.queries == (
        ("com.google.android.apps.healthdata", "Health Connect availability check"),
    )
    assert any(
        "queries com.google.android.apps.healthdata" in line
        for distribution in acknowledged.record.distributions
        for line in distribution.entries
    )


RTC = """
contract = "1"
platforms = ["android"]
[[android.contributes.gradle_dependencies]]
coordinate = "io.agora.rtc:full-sdk:4.5.0"
"""

VISION = """
contract = "1"
platforms = ["android"]
[[android.contributes.gradle_dependencies]]
coordinate = "org.tensorflow:tensorflow-lite:2.16.1"
"""


def _composed(tmp_path, *, answers=None):
    from native_integration.testing import stub_resolvers

    return dict(
        platform=Platform.ANDROID,
        closure=Closure.direct("py-rtc", "py-vision"),
        application=Application(
            android_sdk={"min_sdk": 24, "compile_sdk": 35},
            answers=answers or MappingAnswers(),
        ),
        sources=[
            build(tmp_path, RTC, name="py-rtc", module="py_rtc._native"),
            build(tmp_path, VISION, name="py-vision", module="py_vision._native"),
        ],
        resolvers=stub_resolvers(
            files={
                "io.agora.rtc:full-sdk:4.5.0": [
                    "lib/arm64-v8a/libc++_shared.so",
                    "META-INF/LICENSE",
                ],
                "org.tensorflow:tensorflow-lite:2.16.1": [
                    "lib/arm64-v8a/libc++_shared.so",
                    "META-INF/LICENSE",
                ],
            }
        ),
    )


def test_a_colliding_native_library_fails_and_names_both_distributions(tmp_path):
    """§9.1 — two C++ runtimes is a coin toss between two ABIs, not a default."""
    integration = read(profile=PROFILE, **_composed(tmp_path))
    collisions = [d for d in integration.diagnostics if d.rule.code == "packaging-collision"]
    assert len(collisions) == 1
    assert set(collisions[0].distributions) == {"py-rtc", "py-vision"}
    assert "libc++_shared.so" in collisions[0].message
    # The mapping back to distributions is what a Gradle duplicate-path error
    # cannot supply, so it must be in the message.
    assert "py-rtc" in collisions[0].message and "py-vision" in collisions[0].message


def test_packaging_metadata_is_resolved_without_asking(tmp_path):
    """A licence text is identical in effect whichever copy wins."""
    integration = read(profile=PROFILE, **_composed(tmp_path))
    resolved = [
        d for d in integration.diagnostics if d.rule.code == "packaging-collision-resolved"
    ]
    assert [d.message for d in resolved if "META-INF/LICENSE" in d.message]
    assert not [d for d in resolved if "libc++_shared" in d.message]


def test_the_application_may_choose_which_artifact_supplies_the_library(tmp_path):
    """Only the application knows whether the two SDKs tolerate one runtime."""
    integration = read(
        profile=PROFILE,
        accept_current_surface=True,
        **_composed(
            tmp_path,
            answers=MappingAnswers(
                packaging_choices={
                    "lib/arm64-v8a/libc++_shared.so": "io.agora.rtc:full-sdk:4.5.0"
                }
            ),
        ),
    )
    assert [d.rule.code for d in integration.diagnostics if d.rule.code == "packaging-collision"] == []
    chosen = [
        d
        for d in integration.diagnostics
        if d.rule.code == "packaging-collision-resolved" and "libc++_shared" in d.message
    ]
    assert chosen and "the application chose io.agora.rtc:full-sdk:4.5.0" in chosen[0].message


ADAPTER_A = """
contract = "1"
platforms = ["ios"]
[ios.contributes]
objc_categories = true
"""

ADAPTER_B = """
contract = "1"
platforms = ["ios"]
[ios.contributes]
objc_categories = true
"""

PLAIN_IOS = """
contract = "1"
platforms = ["ios"]
[ios.requires]
deployment_target = "15.0"
"""


def test_objc_categories_unions_and_names_who_asked(tmp_path):
    """§7.8 — one asking is enough, and §9 names them because it changes the link."""
    integration = read(
        platform=Platform.IOS,
        closure=Closure.direct("py-ads-a", "py-ads-b", "py-quiet"),
        application=Application(deployment_target="15.0"),
        profile=PROFILE,
        sources=[
            build(tmp_path, ADAPTER_A, name="py-ads-a", module="py_ads_a._native"),
            build(tmp_path, ADAPTER_B, name="py-ads-b", module="py_ads_b._native"),
            build(tmp_path, PLAIN_IOS, name="py-quiet", module="py_quiet._native"),
        ],
        accept_current_surface=True,
    )
    assert integration.effective.objc_categories() == ("py-ads-a", "py-ads-b")
    assert any(
        "objc-categories loaded at link time" in line
        for distribution in integration.record.distributions
        for line in distribution.entries
    )


def test_nothing_asks_and_the_link_is_untouched(tmp_path):
    integration = read(
        platform=Platform.IOS,
        closure=Closure.direct("py-quiet"),
        application=Application(deployment_target="15.0"),
        profile=PROFILE,
        sources=[build(tmp_path, PLAIN_IOS, name="py-quiet", module="py_quiet._native")],
        accept_current_surface=True,
    )
    assert integration.effective.objc_categories() == ()


SHIM_A = """
contract = "1"
platforms = ["ios"]
[ios.contributes.src]
swift = ["swift"]

[[ios.contributes.accessed_api_types]]
type = "NSPrivacyAccessedAPICategoryUserDefaults"
reasons = ["CA92.1"]
reason = "Caches the last selected region"
"""

SHIM_B = """
contract = "1"
platforms = ["ios"]
[ios.contributes.src]
swift = ["swift"]

[[ios.contributes.accessed_api_types]]
type = "NSPrivacyAccessedAPICategoryUserDefaults"
reasons = ["1C8F.1"]
reason = "Reads a value the host application wrote"

[[ios.contributes.accessed_api_types]]
type = "NSPrivacyAccessedAPICategoryFileTimestamp"
reasons = ["C617.1"]
"""


def test_two_shims_touching_one_api_category_both_tell_the_truth(tmp_path):
    """§7.5 — reasons for one type union; the application's entries come first."""
    integration = read(
        platform=Platform.IOS,
        closure=Closure.direct("py-shim-a", "py-shim-b"),
        application=Application(
            deployment_target="15.0",
            accessed_api_types=(("NSPrivacyAccessedAPICategoryDiskSpace", ("E174.1",)),),
        ),
        profile=PROFILE,
        sources=[
            build(tmp_path, SHIM_A, name="py-shim-a", module="py_shim_a._native",
                  files={"swift/A.swift": "// a"}),
            build(tmp_path, SHIM_B, name="py-shim-b", module="py_shim_b._native",
                  files={"swift/B.swift": "// b"}),
        ],
        accept_current_surface=True,
    )
    merged = dict(
        integration.effective.accessed_api_types(
            Application(
                deployment_target="15.0",
                accessed_api_types=(
                    ("NSPrivacyAccessedAPICategoryDiskSpace", ("E174.1",)),
                ),
            )
        )
    )
    assert merged["NSPrivacyAccessedAPICategoryUserDefaults"] == ("CA92.1", "1C8F.1")
    assert merged["NSPrivacyAccessedAPICategoryFileTimestamp"] == ("C617.1",)
    assert merged["NSPrivacyAccessedAPICategoryDiskSpace"] == ("E174.1",)
    assert any(
        "privacy-api NSPrivacyAccessedAPICategoryUserDefaults" in line
        for distribution in integration.record.distributions
        for line in distribution.entries
    )


# --- requirement coverage ---------------------------------------------------


def test_every_requirement_is_discharged_somewhere():
    """Every §8 requirement is discharged, structural, or named as beyond a reader.

    The count comes from first-attempt.md rather than a literal, because a hardcoded
    bound does not fail when the specification grows — it quietly covers less,
    which is how requirements 27 to 29 went unchecked.
    """
    import re
    from pathlib import Path as _Path

    spec = (_Path(__file__).resolve().parent.parent / "development" / "first-attempt.md").read_text(encoding="utf-8")
    block = spec.split("A conforming consumer **MUST**:")[1].split(
        "A conforming consumer **SHOULD**:"
    )[0]
    numbers = sorted(int(n) for n in re.findall(r"^(\d+)\.\s", block, re.M))
    assert numbers, "no §8 requirements found — the parse, not the library, is broken"
    assert numbers == list(range(1, len(numbers) + 1)), "§8 is not numbered 1..N"

    missing = [
        n
        for n in numbers
        if not rules_for_requirement(n)
        and n not in STRUCTURAL
        and n not in BEYOND_THE_READER
    ]
    assert missing == []


def test_nothing_claims_to_be_beyond_the_reader_and_is_not():
    """A requirement listed as out of reach must genuinely have no rule.

    Without this, BEYOND_THE_READER becomes a place to put a requirement that
    was merely inconvenient to implement.
    """
    overlap = [n for n in BEYOND_THE_READER if rules_for_requirement(n) or n in STRUCTURAL]
    assert overlap == []


def test_every_advisory_obligation_is_accounted_for():
    """§8's SHOULD list, by identifier. 'Not implemented' is a value, not a gap."""
    import re
    from pathlib import Path as _Path

    from native_integration.rules import ADVISORY

    spec = (_Path(__file__).resolve().parent.parent / "development" / "first-attempt.md").read_text(encoding="utf-8")
    block = spec.split("A conforming consumer **SHOULD**")[1].split("\n## ")[0]
    declared = set(re.findall(r"^- \*\*(S\d+)\.\*\*", block, re.M))
    assert declared, "no identified SHOULD items found in §8"
    assert declared == set(ADVISORY)


def test_the_severity_model_is_the_specifications_not_the_readers():
    """§8 names three outcomes; Severity has exactly three members."""
    from native_integration import Severity

    assert {s.name for s in Severity} == {"ERROR", "WARNING", "NOTE"}


def test_no_rule_is_declared_and_never_emitted():
    """A registry entry nothing raises is a rule the reader claims and does not enforce."""
    import re
    from pathlib import Path as _Path

    source = _Path(__file__).resolve().parent.parent / "src" / "native_integration"
    constants = re.findall(
        r"^([A-Z_]+) = _rule\(", (source / "rules.py").read_text(encoding="utf-8"), re.M
    )
    bodies = {f.read_text(encoding="utf-8") for f in source.glob("*.py") if f.name != "rules.py"}
    unused = [c for c in constants if not any(re.search(rf"rules\.{c}\b", b) for b in bodies)]
    assert unused == []


def test_the_requirements_table_is_current():
    """docs/REQUIREMENTS.md is generated; a stale one is worse than none."""
    import subprocess
    import sys as _sys
    from pathlib import Path as _Path

    root = _Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [_sys.executable, "tools/requirements_table.py", "--check"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_component_attributed_to_a_dependency_that_lacks_it_warns(tmp_path):
    body = """
contract = "1"
[[android.contributes.gradle_dependencies]]
coordinate = "com.example:widget:1.2.3"
[[android.contributes.components]]
kind = "receiver"
name = "com.example.Missing"
from_dependency = "com.example:widget"
"""
    resolvers = Resolvers(
        gradle=FakeGradle(widget_graph()),
        artifacts=FakeArtifacts(
            manifests={"com.example:widget:1.2.3": None},
            classes={"com.example:widget:1.2.3": ["com.example.Present"]},
            classpath=["com.example.Present"],
        ),
    )
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pkg-dep"),
        application=Application(),
        profile=PROFILE,
        resolvers=resolvers,
        sources=[build(tmp_path, body, name="pkg-dep", module="pkg_dep._native")],
        accept_current_surface=True,
    )
    warned = [d for d in integration.diagnostics if d.rule.code == "component-class-absent"]
    assert len(warned) == 1 and not warned[0].blocking
