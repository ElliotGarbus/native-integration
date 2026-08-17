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
    assert len(EXAMPLES) == 10


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
    spec = (ROOT / "SPEC.md").read_text(encoding="utf-8")
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
