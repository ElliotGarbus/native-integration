"""Discovery, the application's answers, the ports, and the §9 record."""

from __future__ import annotations

from dataclasses import dataclass
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
from native_integration.rules import RULES, STRUCTURAL, rules_for_requirement

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
        accepted=True,
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


def build(tmp_path, body=SIDE, *, name="pystripe", module="pystripe._native"):
    from native_integration import source_from_path

    root = tmp_path / name / module.replace(".", "/")
    root.mkdir(parents=True, exist_ok=True)
    (root / "native.toml").write_text(body, encoding="utf-8")
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
        accepted=True,
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
        accepted=True,
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
        accepted=True,
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
    integration = ios_read(tmp_path, both, accepted=True)
    assert not any(d.rule.code == "prerequisite-unsatisfied" for d in integration.diagnostics)


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
        accepted=True,
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
        accepted=True,
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
    integration = dep_read(tmp_path, resolvers, accepted=True)
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
    integration = dep_read(tmp_path, resolvers, accepted=True)
    assert integration.ok, integration.diagnostics.render()


def test_a_checksum_mismatch_fails_the_next_build(tmp_path):
    resolvers = Resolvers(
        gradle=FakeGradle(widget_graph()),
        artifacts=FakeArtifacts({"com.example:widget:1.2.3": None}, {}, []),
    )
    first = dep_read(tmp_path, resolvers, accepted=True)
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
        accepted=True,
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
    integration = dep_read(tmp_path, resolvers, accepted=True)
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
        accepted=True,
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
        accepted=True,
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
        accepted=True,
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
        accepted=True,
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
        accepted=True,
    )
    assert "pystripe 1.0.0  (via some-ui-lib)" in integration.report()


def test_a_record_round_trips(tmp_path):
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pystripe"),
        application=answered(),
        profile=PROFILE,
        sources=[build(tmp_path)],
        accepted=True,
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
        accepted=True,
    )
    exclusions = integration.payload_exclusions()
    assert "web_views.py" in exclusions and "web_views.pyi" in exclusions
    assert "pywebviews/_native/" in exclusions


# --- requirement coverage ---------------------------------------------------


def test_every_requirement_is_discharged_somewhere():
    """§8 numbers 1..26. A requirement in neither table has fallen out of the library."""
    missing = [
        n for n in range(1, 27) if not rules_for_requirement(n) and n not in STRUCTURAL
    ]
    assert missing == []


def test_no_rule_is_declared_and_never_emitted():
    """A registry entry nothing raises is a rule the reader claims and does not enforce."""
    import re
    from pathlib import Path as _Path

    source = _Path(__file__).resolve().parent.parent / "src" / "native_integration"
    constants = re.findall(r"^([A-Z_]+) = _rule\(", (source / "rules.py").read_text(), re.M)
    bodies = {f.read_text() for f in source.glob("*.py") if f.name != "rules.py"}
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
        accepted=True,
    )
    warned = [d for d in integration.diagnostics if d.rule.code == "component-class-absent"]
    assert len(warned) == 1 and not warned[0].blocking
