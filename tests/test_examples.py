"""The repository's own sidecars, read by the library that implements the spec.

``tools/check_spec.py`` checks the *documents* for mechanical drift. This
checks the same files against the reader, which is a different question: a rule
the specification states and the library enforces is only worth something if the
worked examples survive it.

Resource verification is off because these are illustrative sidecars — they
declare ``java = ["java"]`` without shipping the tree a real wheel would.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from native_integration import (
    Application,
    Closure,
    ConsumerProfile,
    MappingAnswers,
    Platform,
    check_sidecar,
    read,
    source_from_path,
)
from native_integration.testing import stub_resolvers

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = sorted(
    [*ROOT.glob("examples/**/native.toml"), *ROOT.glob("development/examples/**/native.toml")]
)
REVIEW = ConsumerProfile(verify_resources=False)


def platforms_of(path: Path) -> list[Platform]:
    declared = tomllib.loads(path.read_text(encoding="utf-8")).get("platforms")
    if declared is None:
        return list(Platform)
    return [Platform(p) for p in declared]


def test_the_example_set_is_not_empty():
    assert len(EXAMPLES) == 18


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: str(p.relative_to(ROOT)))
def test_every_worked_example_is_valid(path):
    source = source_from_path(path.parent, distribution=path.parent.name, version="0")
    for platform in platforms_of(path):
        sidecar, bag = check_sidecar(source, platform=platform, profile=REVIEW)
        assert sidecar is not None, bag.render()
        assert bag.ok, f"{path.relative_to(ROOT)} [{platform}]\n{bag.render()}"


def test_the_pystripe_pair_reads_end_to_end():
    """examples/pystripe/ carries both halves; the library should join them.

    The application's spelling is illustrative — §2.2 defines the capability and
    not the syntax — so this adapts that file into an AnswerSource, which is
    exactly what a real consumer does with its own configuration format.
    """
    pair = ROOT / "examples" / "pystripe"
    app = tomllib.loads((pair / "app-pyproject.toml").read_text(encoding="utf-8"))
    tool = app["tool"]["examplebuild"]
    per_package = tool["native"]["pystripe"]

    answers = MappingAnswers(
        application_values={"pystripe": per_package["android"]["application_values"]},
        allow_exported={"pystripe": per_package["android"]["allow_exported"]},
        acknowledged_ids={"pystripe": per_package["ios"]["acknowledged"]},
    )
    application = Application(
        android_sdk=tool["android"],
        deployment_target="16.0",
        answers=answers,
    )
    source = source_from_path(pair, distribution="pystripe", version="1.0.0")

    android = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pystripe"),
        application=application,
        profile=REVIEW,
        resolvers=stub_resolvers(),
        sources=[source],
        accept_current_surface=True,
    )
    assert android.ok, android.diagnostics.render()
    link = android.effective.exported_components()[0].view_links[0]
    assert link.scheme == "trailmap-pay"  # substituted from the application's answer

    ios = read(
        platform=Platform.IOS,
        closure=Closure.direct("pystripe"),
        application=application,
        profile=REVIEW,
        resolvers=stub_resolvers(),
        sources=[source],
        accept_current_surface=True,
    )
    assert ios.ok, ios.diagnostics.render()
    assert not ios.effective.unresolved_conditionals()


def test_the_pystripe_pair_blocks_when_the_application_answers_nothing():
    """The same sidecar, with the application half removed."""
    pair = ROOT / "examples" / "pystripe"
    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pystripe"),
        application=Application(android_sdk={"min_sdk": 24, "compile_sdk": 35}),
        profile=REVIEW,
        resolvers=stub_resolvers(),
        sources=[source_from_path(pair, distribution="pystripe", version="1.0.0")],
    )
    codes = {d.rule.code for d in integration.diagnostics}
    assert {"application-value-unsupplied", "component-export-unapproved"} <= codes


def test_the_specs_own_complete_example_is_valid(tmp_path):
    """§5.1 shows a whole sidecar. The reader is what proves it is a real one."""
    spec = (ROOT / "development" / "first-attempt.md").read_text(encoding="utf-8")
    block = next(
        b for b in spec.split("```toml")[1:] if "examplytics" in b
    ).split("```")[0]
    root = tmp_path / "examplytics" / "_native"
    root.mkdir(parents=True)
    (root / "native.toml").write_text(block, encoding="utf-8")
    source = source_from_path(root, distribution="examplytics", version="1.0.0")

    for platform in Platform:
        sidecar, bag = check_sidecar(source, platform=platform, profile=REVIEW)
        assert sidecar is not None and bag.ok, f"[{platform}]\n{bag.render()}"

    android, _ = check_sidecar(source, platform=Platform.ANDROID, profile=REVIEW)
    ios, _ = check_sidecar(source, platform=Platform.IOS, profile=REVIEW)
    # It is meant to show all three categories of §2.1 at once.
    assert android.android.java_namespaces          # owns
    assert android.android.application_values       # requires
    assert android.android.permissions              # contributes
    assert ios.ios.prerequisites and ios.ios.swift_packages


@pytest.mark.skip(
    reason="README.md documents SPEC.md, and this reader implements "
    "development/first-attempt.md. Restore when the reader is rewritten; "
    "tools/check_spec.py validates the block against SPEC.md meanwhile."
)
def test_the_readme_kivmob_sidecar_is_valid(tmp_path):
    """The README's headline example, read as a sidecar rather than as prose."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    block = next(
        b
        for b in readme.split("```toml")[1:]
        if b.split("```")[0].strip().startswith("contract")
    ).split("```")[0]
    root = tmp_path / "kivmob" / "_native"
    root.mkdir(parents=True)
    (root / "native.toml").write_text(block, encoding="utf-8")

    source = source_from_path(root, distribution="kivmob", version="1.0.0")
    sidecar, bag = check_sidecar(source, platform=Platform.ANDROID, profile=REVIEW)
    assert sidecar is not None and bag.ok, bag.render()
    assert sidecar.android.application_values[0].id == "admob_app_id"


# --- the mediated-ads composition -------------------------------------------
#
# Every other example is one producer as a direct dependency. This set is three
# at once, which is the only way to exercise the rules whose whole justification
# is cross-distribution — and those are the rules with the least evidence behind
# them.

MEDIATED = ROOT / "development" / "examples" / "mediated-ads"
MEDIATED_NAMES = ("pyadmob", "pyadmob-applovin", "pyadmob-mintegral")


APP_CONFIG = MEDIATED / "app-pyproject.toml"


def _answers_from_the_application(platform: Platform) -> MappingAnswers:
    """Read the application's own file, the way a consumer would read its config.

    The nesting is `examplebuild`'s and illustrative; what is not illustrative
    is that every answer is filed under (platform, distribution, key). §2.2's
    join, read back out.
    """
    config = tomllib.loads(APP_CONFIG.read_text(encoding="utf-8"))
    native = config["tool"]["examplebuild"]["native"]
    values = {
        distribution: per_platform[platform.value]["application_values"]
        for distribution, per_platform in native.items()
        if platform.value in per_platform
        and "application_values" in per_platform[platform.value]
    }
    descriptions = (
        config["tool"]["examplebuild"].get(platform.value, {}).get("usage_descriptions", {})
    )
    return MappingAnswers(application_values=values, usage_descriptions=descriptions)


def _mediated(platform: Platform):
    sources = [
        source_from_path(
            MEDIATED / name,
            distribution=name,
            version="1.0.0",
            module=f"{name.replace('-', '_')}._native",
        )
        for name in MEDIATED_NAMES
    ]
    answers = _answers_from_the_application(platform)
    application = Application(
        android_sdk={"min_sdk": 24, "compile_sdk": 35},
        deployment_target="15.0",
        answers=answers,
    )
    return read(
        platform=platform,
        closure=Closure.direct(*MEDIATED_NAMES),
        application=application,
        profile=REVIEW,
        sources=sources,
        resolvers=stub_resolvers(),
        accept_current_surface=True,
    )


def test_three_ad_packages_compose_with_nothing_but_disclosure():
    """The baseline: nothing conflicts, and every diagnostic is a note.

    Not silence — §8's third outcome. Composing three ad packages produces a
    contributed repository reported with the prominence §6.6 demands, and a
    requested-versus-resolved line per dependency. Both are things a reviewer
    should see and neither is a problem, which is exactly what NOTE is for.
    """
    from native_integration import Severity

    for platform in (Platform.ANDROID, Platform.IOS):
        integration = _mediated(platform)
        louder = [d.rule.code for d in integration.diagnostics if d.rule.severity > Severity.NOTE]
        assert louder == [], platform

    android = _mediated(Platform.ANDROID)
    codes = sorted({d.rule.code for d in android.diagnostics})
    assert codes == ["dependency-version-substituted", "repository-contributed"]


def test_overlapping_skadnetwork_lists_de_duplicate():
    """§7.6 — three adapters, ~two overlaps, one entry each in the merged plist."""
    integration = _mediated(Platform.IOS)
    identifiers = [
        entry["SKAdNetworkIdentifier"]
        for entry in integration.effective.skadnetwork_items(Application())
    ]
    assert len(identifiers) == len(set(identifiers))
    # cstr6suwn9 is declared by pyadmob and pyadmob-mintegral; ludvb6z3bs by
    # pyadmob and pyadmob-applovin. Both appear once.
    assert identifiers.count("cstr6suwn9.skadnetwork") == 1
    assert identifiers.count("ludvb6z3bs.skadnetwork") == 1
    assert set(identifiers) == {
        "cstr6suwn9.skadnetwork",
        "ludvb6z3bs.skadnetwork",
        "4dzt52r2t5.skadnetwork",
        "5lm9lj6jb7.skadnetwork",
        "kbd757ywx3.skadnetwork",
    }


def test_objc_categories_unions_across_all_three():
    """§7.8 — one asking is enough, and §9 names every distribution that did."""
    integration = _mediated(Platform.IOS)
    assert integration.effective.objc_categories() == MEDIATED_NAMES


def test_one_meta_data_key_set_twice_to_one_value_coalesces():
    """§6.10 — equal values coalesce; only a disagreement fails."""
    integration = _mediated(Platform.ANDROID)
    entries = [
        entry
        for contribution in integration.effective.contributions
        for entry in contribution.meta_data
        if entry.key == "com.google.android.gms.ads.flag.OPTIMIZE_INITIALIZATION"
    ]
    assert len(entries) == 2  # declared twice, agreeing
    assert {e.value for e in entries} == {"true"}


def test_one_permission_declared_by_three_reaches_the_manifest_once():
    """§6.7 — the merged manifest carries one entry, however many asked."""
    integration = _mediated(Platform.ANDROID)
    names = [p.name for p in integration.effective.permissions()]
    assert names.count("android.permission.INTERNET") == 1
    assert integration.effective.permission_provenance("android.permission.INTERNET") == (
        "pyadmob",
        "pyadmob-applovin",
        "pyadmob-mintegral",
    )


def test_each_package_answers_its_own_vendor_key():
    """§6.3's per-distribution scoping, with three vendors in one application."""
    integration = _mediated(Platform.ANDROID)
    delivered = {
        entry.key: entry.value
        for contribution in integration.effective.contributions
        for entry in contribution.meta_data
    }
    assert delivered["com.google.android.gms.ads.APPLICATION_ID"].startswith("ca-app-pub-")
    # Whatever the application wrote, verbatim — the consumer never originates it.
    supplied = _answers_from_the_application(Platform.ANDROID)
    assert delivered["applovin.sdk.key"] == supplied.application_value(
        "pyadmob-applovin", "applovin_sdk_key"
    )


# --- the native-runtime collision -------------------------------------------
#
# The mediated-ads set ends by recording what it could not reach, and §9.1's
# packaging collisions was first on that list: ad adapters ship no native code
# that collides. This pair does. The file listings are stubbed because the
# reader resolves nothing from the network — what is under test is the rule and
# its diagnostic, not that these two releases collide today.

AGORA_COORDINATE = "io.agora.rtc:full-sdk:4.5.0"
TFLITE_COORDINATE = "org.tensorflow:tensorflow-lite:2.16.1"
SHARED_RUNTIME = "lib/arm64-v8a/libc++_shared.so"


def _rtc_and_vision(*, choices=None):
    from native_integration.answers import MappingAnswers as Answers

    sources = [
        source_from_path(
            ROOT / "development" / "examples" / name,
            distribution=name,
            version="1.0.0",
            module=f"{name}._native",
        )
        for name in ("pyagora", "pytflite")
    ]
    application = Application(
        android_sdk={"min_sdk": 24, "compile_sdk": 35},
        answers=Answers(
            android_assets=["detector.tflite"],
            packaging_choices=choices or {},
        ),
    )
    return read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pyagora", "pytflite"),
        application=application,
        profile=REVIEW,
        sources=sources,
        resolvers=stub_resolvers(
            files={
                AGORA_COORDINATE: [SHARED_RUNTIME, "META-INF/LICENSE"],
                TFLITE_COORDINATE: [SHARED_RUNTIME, "META-INF/LICENSE"],
            }
        ),
        accept_current_surface=True,
    )


def test_two_sdks_bundling_one_cpp_runtime_block_the_build():
    """§9.1 — and the diagnostic names the distributions, which Gradle cannot."""
    integration = _rtc_and_vision()
    collisions = [d for d in integration.diagnostics if d.rule.code == "packaging-collision"]
    assert len(collisions) == 1
    (collision,) = collisions
    assert set(collision.distributions) == {"pyagora", "pytflite"}
    assert SHARED_RUNTIME in collision.message
    assert "pyagora" in collision.message and "pytflite" in collision.message


def test_the_licence_file_collides_too_and_is_resolved_silently():
    """Treating both alike would fail every realistic build, or pick a runtime at random."""
    integration = _rtc_and_vision()
    resolved = [
        d for d in integration.diagnostics if d.rule.code == "packaging-collision-resolved"
    ]
    assert [d for d in resolved if "META-INF/LICENSE" in d.message]
    assert not [d for d in resolved if "libc++" in d.message]


def test_the_application_chooses_and_the_choice_is_recorded():
    """Only the application can know whether the two SDKs tolerate one runtime."""
    integration = _rtc_and_vision(choices={SHARED_RUNTIME: AGORA_COORDINATE})
    assert not [d for d in integration.diagnostics if d.rule.code == "packaging-collision"]
    chosen = [
        d
        for d in integration.diagnostics
        if d.rule.code == "packaging-collision-resolved" and "libc++" in d.message
    ]
    assert chosen and AGORA_COORDINATE in chosen[0].message


def test_the_application_file_answers_all_three_packages():
    """The other half of §2.2, at N > 1.

    `examples/pystripe/` answers one package; this answers three, on both
    platforms, from the file an application would actually write. Nothing in
    the set is left unsatisfied, which is the claim the file makes.
    """
    for platform in (Platform.ANDROID, Platform.IOS):
        integration = _mediated(platform)
        unmet = [
            d.rule.code
            for d in integration.diagnostics
            if d.rule.code in ("prerequisite-unsatisfied", "application-value-unsupplied")
        ]
        assert unmet == [], platform


def test_one_id_two_platforms_two_values():
    """§2.2 — the join is scoped by platform, which two `application_values` make load-bearing.

    pyadmob declares `admob_app_id` on both platforms and the AdMob console
    issues a different ID for each. An application answering once would satisfy
    the requirement and ship the wrong identifier on one build.
    """
    android = _answers_from_the_application(Platform.ANDROID)
    ios = _answers_from_the_application(Platform.IOS)
    on_android = android.application_value("pyadmob", "admob_app_id")
    on_ios = ios.application_value("pyadmob", "admob_app_id")
    assert on_android and on_ios and on_android != on_ios

    # And the value each build embeds is the one for that build.
    delivered = {
        entry.key: entry.value
        for contribution in _mediated(Platform.ANDROID).effective.contributions
        for entry in contribution.meta_data
    }
    assert delivered["com.google.android.gms.ads.APPLICATION_ID"] == on_android


def test_the_worked_records_are_current():
    """§9's record is a function of the sidecars and the application's answers.

    That is the property that makes it reviewable — a `git diff` of the record
    is the delta a reviewer reads — so the committed artifact has to be
    regenerated when either side changes. `python3 tools/record_example.py`.
    """
    import sys

    sys.path.insert(0, str(ROOT / "tools"))
    import record_example

    for platform in (Platform.ANDROID, Platform.IOS):
        path = MEDIATED / f"record-{platform.value}.json"
        assert path.read_text(encoding="utf-8") == record_example.record_for(platform), (
            f"{path.name} has drifted; run python3 tools/record_example.py"
        )
