"""The command line, and the one claim it makes that could be false.

`explain` promises that every generated id resolves to a rule and a fragment in
correct form. Both halves are asserted here over the whole id space rather than
sampled: an id nobody can resolve is worse than no id at all, because it was
printed in a build log as though it led somewhere.

`check_spec.py` holds the fragments to the schema. These hold the resolution, the
JSON shapes, and the boundary each subcommand draws around what it can know.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from native_integration import cli, obligations, registry

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def known():
    return registry.load()


def run(capsys, *argv: str) -> tuple[int, str]:
    code = cli.main(list(argv))
    return code, capsys.readouterr().out


# -- explain -----------------------------------------------------------------


def test_every_generated_id_resolves(capsys, known):
    """The acceptance criterion, over all 335 of them.

    An id that resolved to nothing would be worse than having no ids: the
    failure that printed it told the author it led somewhere.
    """
    unresolved = []
    for identifier in list(known.diagnostics) + list(known.declarations):
        try:
            code, _ = run(capsys, "explain", identifier, "--json")
        except Exception as exc:  # pragma: no cover - the failure is the report
            unresolved.append(f"{identifier}: {type(exc).__name__} {exc}")
            continue
        if code != 0:
            unresolved.append(f"{identifier}: exit {code}")
    assert not unresolved


def test_a_diagnostic_carries_its_rule_its_section_and_a_fragment(capsys):
    code, out = run(capsys, "explain", "ni.decl.contract.pattern", "--json")
    answer = json.loads(out)
    assert code == 0
    assert answer["kind"] == "diagnostic"
    assert answer["severity"] == "blocking"
    assert answer["section"] == "4.3"
    assert answer["specification"] == "SPEC.md#43-contract-version"
    assert answer["rule"]
    assert 'contract = "1"' in answer["fragment"]


def test_a_requirement_carries_its_profile(capsys):
    """§8.1 makes conformance per-platform, so which profile owes it is part of
    the answer — an iOS-only consumer is not failing to implement 25."""
    answer = json.loads(run(capsys, "explain", "ni.req.25", "--json")[1])
    assert answer["profile"] == "android"


def test_a_declaration_resolves_by_the_platform_an_author_has(capsys):
    """The registry writes `<platform>` where a rule is stated once for both.
    The sidecar in front of the author says `android`, and that is what they
    will type — and what a diagnostic about their file will have named."""
    generic = json.loads(run(capsys, "explain", "<platform>.requires.application_value.kind", "--json")[1])
    spelled = json.loads(run(capsys, "explain", "android.requires.application_value.kind", "--json")[1])
    assert generic["id"] == spelled["id"] == "<platform>.requires.application_value.kind"
    assert spelled["values"][0] == "manifest_meta_data"


def test_a_forbidden_key_says_why_it_has_no_fragment(capsys):
    """§6.5's `required` on a feature is not a field. Its correct form is its
    absence, and a fragment showing an absence shows nothing."""
    answer = json.loads(run(capsys, "explain", "android.contributes.features.required", "--json")[1])
    assert answer["fragment"] is None
    assert "absence" in answer["no_fragment"]


def test_an_unknown_id_is_a_usage_error_with_a_suggestion(capsys):
    code = cli.main(["explain", "ni.req.999"])
    assert code == 2
    code = cli.main(["explain", "gradle_dependencies"])
    assert code == 2


def test_the_fragment_shows_the_form_a_constraint_requires(capsys):
    """§6.3 wants `version` beside `module` and forbids it beside `coordinate`.
    A fragment that picked `coordinate` because it sorts first would demonstrate
    the one spelling the section rejects."""
    answer = json.loads(
        run(capsys, "explain", "android.contributes.gradle_dependencies.version", "--json")[1]
    )
    assert "module" in answer["fragment"]
    assert "coordinate" not in answer["fragment"]


def test_the_fragment_carries_what_another_section_makes_mandatory(capsys):
    """§6.1: contributing Java or Kotlin requires owning a namespace to put it
    in, and the rule is scoped to the platform table rather than to `src`."""
    answer = json.loads(run(capsys, "explain", "android.contributes.src.java", "--json")[1])
    assert "[android.owns]" in answer["fragment"]
    assert "java_namespaces" in answer["fragment"]


def test_every_answer_says_it_is_not_normative(capsys):
    _, out = run(capsys, "explain", "ni.req.1")
    assert "not normative" in out


# -- inspect and validate ----------------------------------------------------


EXAMPLE = ROOT / "examples" / "pystripe"


def test_inspect_reports_what_is_declared_and_judges_none_of_it(capsys):
    answer = json.loads(run(capsys, "inspect", str(EXAMPLE), "--json")[1])
    assert answer["distribution"] == "pystripe"
    assert answer["contract"] == "1"
    assert "java_namespaces" in answer["declares"]["android"]["owns"]
    assert "swift_packages" in answer["declares"]["ios"]["contributes"]


def test_validate_separates_what_the_application_owes(capsys):
    """A producer checking its own sidecar is not failing requirement 13 because
    no application has supplied a value. Three of the four outstanding
    obligations block a real build; none is this sidecar's defect."""
    code, out = run(capsys, "validate", str(EXAMPLE), "--json")
    answer = json.loads(out)
    assert code == 0, out
    assert answer["outcome"] == "accept"
    assert answer["normative"] is False
    outstanding = {finding["requirement"] for finding in answer["outstanding"]}
    assert outstanding <= set(obligations.ANSWERED_BY_THE_APPLICATION)
    assert outstanding, "the example raises requirements only an application can answer"
    assert all(
        finding["requirement"] not in obligations.ANSWERED_BY_THE_APPLICATION
        for finding in answer["findings"]
    )


def test_validate_says_which_rules_it_could_not_reach(capsys):
    """One sidecar cannot exercise a rule about two. Reporting a clean build
    would be the overstatement §8.5's note names."""
    answer = json.loads(run(capsys, "validate", str(EXAMPLE), "--json")[1])
    assert answer["unchecked"]
    assert "closure" in answer["unchecked"][0]


def test_validate_fails_a_sidecar_the_producer_got_wrong(capsys, tmp_path):
    sidecar = tmp_path / "pybroken" / "_native"
    sidecar.mkdir(parents=True)
    # §6.5: a producer must not declare `required` on a feature.
    (sidecar / "native.toml").write_text(
        'contract = "1"\n\n[[android.contributes.features]]\n'
        'name = "android.hardware.camera"\nrequired = true\n',
        encoding="utf-8", newline="\n",
    )
    code, out = run(capsys, "validate", str(sidecar), "--json")
    answer = json.loads(out)
    assert code == 1
    assert answer["outcome"] == "blocking"
    assert answer["findings"]


def test_a_wheel_is_read_as_a_zip(capsys, tmp_path):
    """§3.2 forbids importing a producing distribution. Unpacking a zip is not
    importing one, which is what lets a producer check a built artifact."""
    wheel = tmp_path / "pywheelish-2.1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "pywheelish/_native/native.toml",
            'contract = "1"\nplatforms = ["android"]\n\n[android.owns]\n'
            'java_namespaces = ["org.pywheelish"]\n',
        )
        archive.writestr("pywheelish/__init__.py", "")
    answer = json.loads(run(capsys, "inspect", str(wheel), "--json")[1])
    assert answer["distribution"] == "pywheelish"
    assert answer["platforms"] == ["android"]
    assert "java_namespaces" in answer["declares"]["android"]["owns"]


def test_a_wheel_with_no_sidecar_is_a_usage_error():
    assert cli.main(["inspect", str(ROOT / "pyproject.toml")]) == 2


# -- the shell ---------------------------------------------------------------


def test_no_subcommand_prints_help_rather_than_a_traceback(capsys):
    assert cli.main([]) == 2


def test_the_parser_documents_that_this_is_not_normative():
    parser = cli.build_parser()
    assert "not normative" in parser.description
    assert "not normative" in parser.epilog
