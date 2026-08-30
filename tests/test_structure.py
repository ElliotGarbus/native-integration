"""Structural validation against the registry.

Two kinds of test. The corpus and the worked examples establish that the
validator agrees with material the repository already holds correct — no false
positives on a valid sidecar, and exactly the expected ids on an invalid one.
The unit tests below them cover the shapes no fixture happens to exercise,
including the one thing a JSON Schema cannot see.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from native_integration import registry, structure
from native_integration.findings import Findings

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "development" / "redesign" / "examples"
CONFORMANCE = ROOT / "conformance"


@pytest.fixture(scope="module")
def contract() -> registry.Registry:
    return registry.load()


def report(document, *, platform="android", distribution="pyexample") -> Findings:
    log = Findings(registry.load())
    structure.validate(
        document, platform=platform, distribution=distribution, findings=log
    )
    return log


def ids(document, **kwargs) -> set[str]:
    return {entry["id"] for entry in report(document, **kwargs).as_diagnostics()}


# -- against material the repository already holds correct -----------------


def _examples() -> list[tuple[Path, str]]:
    found = []
    for path in sorted(EXAMPLES.glob("*/native.toml")):
        document = tomllib.loads(path.read_text(encoding="utf-8"))
        found.extend((path, p) for p in ("android", "ios") if p in document)
    return found


@pytest.mark.parametrize(
    "path, platform", _examples(), ids=lambda v: v if isinstance(v, str) else v.parent.name
)
def test_a_current_model_example_validates_clean(path, platform):
    document = tomllib.loads(path.read_text(encoding="utf-8"))
    log = report(document, platform=platform, distribution=path.parent.name)
    assert not list(log), log.render()


def _corpus_sidecars() -> list[tuple[Path, Path, str]]:
    found = []
    for case in sorted(CONFORMANCE.glob("*/*/case.toml")):
        for sidecar in sorted(case.parent.glob("input/**/_native/native.toml")):
            head = sidecar.relative_to(case.parent / "input").parts[0]
            if head in ("android", "ios"):
                platform = head
            else:
                closure = tomllib.loads(
                    (case.parent / "input" / "closure.toml").read_text(encoding="utf-8")
                )
                platform = closure["platform"]
            found.append((case, sidecar, platform))
    return found


def test_the_corpus_ships_sidecars_to_check():
    assert len(_corpus_sidecars()) > 50


@pytest.mark.parametrize(
    "case, sidecar, platform",
    _corpus_sidecars(),
    ids=lambda v: v if isinstance(v, str) else v.parent.name,
)
def test_no_corpus_sidecar_draws_an_unexpected_structural_finding(case, sidecar, platform):
    """`run.py` fails a consumer on any diagnostic the case does not list, so a
    structural check that fires where the case expects a semantic one is a
    failure even though the build outcome would be the same."""
    expected = {
        finding["id"]
        for finding in tomllib.loads(case.read_text(encoding="utf-8")).get("diagnostics", [])
    }
    document = tomllib.loads(sidecar.read_text(encoding="utf-8"))
    reported = ids(
        document, platform=platform, distribution=sidecar.parents[2].name
    )
    assert not reported - expected


@pytest.mark.parametrize(
    "case, expected",
    [
        (
            "core/R08_misspelled_top_level_key",
            {"ni.req.8"},
        ),
        (
            "core/R22_requirement_id_collision",
            {
                "ni.decl.<platform>.requires.application_value.id.duplicate",
                "ni.req.22",
            },
        ),
        (
            "android/R28_feature_required_promotion",
            {"ni.decl.android.contributes.features.required.forbidden", "ni.req.28"},
        ),
        (
            "ios/R33_duplicate_package_name",
            {"ni.decl.ios.contributes.swift_packages.name.duplicate", "ni.req.33"},
        ),
        (
            "ios/R34_accessed_api_without_swift",
            {
                "ni.constraint.ios.contributes.accessed_api_types"
                ".requires-present.src.swift",
                "ni.req.34",
            },
        ),
        (
            "ios/R35_usage_description_contributed",
            {
                "ni.decl.ios.contributes.info_plist.values"
                ".refuses.usage-description-suffix",
                "ni.req.35",
            },
        ),
        (
            "ios/R35_capability_key_contributed",
            {
                "ni.decl.ios.contributes.info_plist.append.refuses.capability-keys",
                "ni.req.35",
            },
        ),
    ],
)
def test_a_structural_case_reports_exactly_what_it_expects(case, expected):
    directory = CONFORMANCE / case
    reported: set[str] = set()
    for sidecar, platform in [
        (s, p) for c, s, p in _corpus_sidecars() if c.parent == directory
    ]:
        document = tomllib.loads(sidecar.read_text(encoding="utf-8"))
        reported |= ids(document, platform=platform, distribution=sidecar.parents[2].name)
    assert reported == expected


# -- the shapes no fixture exercises ---------------------------------------


def test_a_toml_float_is_not_a_toml_integer():
    """§5.1: "a **TOML integer** — `"24"` and `24.0` are rejected". JSON has one
    number type, so this is the check the generated schema cannot make."""
    assert "ni.decl.android.requires.min_sdk.type" in ids(
        {"contract": "1", "android": {"requires": {"min_sdk": 24.0}}}
    )
    assert "ni.decl.android.requires.min_sdk.type" in ids(
        {"contract": "1", "android": {"requires": {"min_sdk": "24"}}}
    )
    assert not ids({"contract": "1", "android": {"requires": {"min_sdk": 24}}})


def test_a_boolean_is_not_an_integer():
    """`true` is an `int` in Python and is not one in TOML."""
    assert "ni.decl.android.requires.min_sdk.type" in ids(
        {"contract": "1", "android": {"requires": {"min_sdk": True}}}
    )


def test_only_true_rejects_false():
    assert "ni.decl.android.requires.core_library_desugaring.false" in ids(
        {"contract": "1", "android": {"requires": {"core_library_desugaring": False}}}
    )
    assert not ids(
        {"contract": "1", "android": {"requires": {"core_library_desugaring": True}}}
    )


def test_contract_is_required_and_bounded():
    assert "ni.decl.contract.missing" in ids({"platforms": ["android"]})
    assert "ni.decl.contract.pattern" in ids({"contract": "01"})
    assert "ni.decl.contract.type" in ids({"contract": 1})
    assert not ids({"contract": "1.1"})


def test_an_unknown_top_level_key_fails_closed_and_a_table_is_advised():
    """§4.4 separates the two: a future platform and a misspelling look alike."""
    assert "ni.req.8" in ids({"contract": "1", "androd": "yes"})
    log = report({"contract": "1", "windows": {"requires": {}}})
    assert not log.as_diagnostics()
    assert [entry["id"] for entry in log.as_advisories()] == ["ni.adv.S1"]


def test_an_unknown_key_inside_a_container_is_named_precisely():
    reported = ids(
        {
            "contract": "1",
            "android": {
                "contributes": {"permissions": [{"name": "android.permission.CAMERA",
                                                 "resaon": "typo"}]}
            },
        }
    )
    assert "ni.decl.android.contributes.permissions.unknown-key" in reported


def test_a_kind_belonging_to_the_other_platform_is_rejected_where_it_sits():
    """§5.5's Platform column is normative."""
    document = {
        "contract": "1",
        "android": {
            "requires": {
                "application_value": [
                    {"id": "k", "kind": "info_plist", "key": "NSCamera", "reason": "r"}
                ]
            }
        },
    }
    assert "ni.decl.<platform>.requires.application_value.kind.wrong-platform" in ids(
        document
    )


def test_an_https_url_is_required_and_user_info_is_a_credential():
    def repositories(url):
        return {
            "contract": "1",
            "android": {
                "contributes": {
                    "gradle_repositories": [{"url": url, "reason": "vendor sdk",
                                             "groups": ["com.vendor"]}]
                }
            },
        }

    identifier = "ni.decl.android.contributes.gradle_repositories.url.scheme"
    assert identifier in ids(repositories("http://repo.vendor.com/maven"))
    assert identifier in ids(repositories("https://user:pass@repo.vendor.com/maven"))
    assert not ids(repositories("HTTPS://repo.vendor.com/maven"))


def test_a_dependency_declares_exactly_one_of_its_two_shapes():
    def dependency(entry):
        return {
            "contract": "1",
            "android": {"contributes": {"gradle_dependencies": [entry]}},
        }

    identifier = "ni.decl.android.contributes.gradle_dependencies.exactly-one-of"
    assert identifier in ids(dependency({"configuration": "implementation"}))
    assert identifier in ids(
        dependency({"coordinate": "com.vendor:sdk:1.2.3", "module": "com.vendor:sdk"})
    )
    assert not ids(dependency({"coordinate": "com.vendor:sdk:1.2.3"}))


def test_a_version_range_is_an_inline_table_of_exactly_its_two_bounds():
    def versioned(version):
        return {
            "contract": "1",
            "android": {
                "contributes": {
                    "gradle_dependencies": [
                        {"module": "com.vendor:sdk", "version": version}
                    ]
                }
            },
        }

    identifier = "ni.decl.android.contributes.gradle_dependencies.version.type"
    assert identifier in ids(versioned({"at_least": "1.2.3"}))
    assert identifier in ids(versioned({"at_least": "1.2.3", "below": "2", "up_to": "3"}))
    assert identifier in ids(versioned("1.2.3"))
    assert not ids(versioned({"at_least": "1.2.3", "below": "2.0.0"}))


def test_a_swift_package_requirement_takes_exactly_one_form():
    def package(requirement):
        return {
            "contract": "1",
            "ios": {
                "contributes": {
                    "swift_packages": [
                        {
                            "name": "Vendor",
                            "url": "https://github.com/vendor/sdk",
                            "products": ["VendorKit"],
                            "requirement": requirement,
                        }
                    ]
                }
            },
        }

    identifier = "ni.decl.ios.contributes.swift_packages.requirement.type"
    assert identifier in ids(package({"from": "1.0.0", "exact": "1.0.0"}), platform="ios")
    assert identifier in ids(package({"branch": "main"}), platform="ios")
    assert not ids(package({"from": "1.0.0"}), platform="ios")


def test_a_view_link_attribute_is_open_but_its_spelling_is_not():
    """§6.6 writes an unrecognized attribute through; the one it rejects is a
    name the conversion to an `android:` attribute is not defined for."""

    def component(link):
        return {
            "contract": "1",
            "android": {
                "owns": {"java_namespaces": ["com.vendor.sdk"]},
                "contributes": {
                    "components": [
                        {
                            "kind": "activity",
                            "name": "com.vendor.sdk.ReturnActivity",
                            "exported_required": True,
                            "reason": "browser return",
                            "view_links": [link],
                        }
                    ]
                },
            },
        }

    identifier = "ni.decl.android.contributes.components.view_links.open-key-pattern"
    assert not ids(component({"scheme": "vendor", "host": "callback"}))
    assert identifier in ids(component({"scheme": "vendor", "Host": "callback"}))
    assert "ni.decl.android.contributes.components.view_links.scheme.missing" in ids(
        component({"host": "callback"})
    )


def test_a_reference_must_name_something_the_same_sidecar_declares():
    def modules(package):
        return {
            "contract": "1",
            "ios": {
                "contributes": {
                    "swift_packages": [
                        {
                            "name": "Vendor",
                            "url": "https://github.com/vendor/sdk",
                            "products": ["VendorKit"],
                            "requirement": {"from": "1.0.0"},
                        }
                    ],
                    "python_modules": [{"name": "vendor", "swift_package": package}],
                }
            },
        }

    identifier = "ni.decl.ios.contributes.python_modules.swift_package.unresolved"
    assert identifier in ids(modules("Absent"), platform="ios")
    assert not ids(modules("Vendor"), platform="ios")


def test_a_from_dependency_names_a_dependency_the_sidecar_declares():
    """§6.6: `group:artifact` of one it declares — `module` outright, or a
    `coordinate` with the version removed."""

    def keep(named):
        return {
            "contract": "1",
            "android": {
                "contributes": {
                    "gradle_dependencies": [{"coordinate": "com.vendor:sdk:1.2.3"}],
                    "r8": {"keep": [{"pattern": "com.vendor.**", "from_dependency": named}]},
                }
            },
        }

    identifier = "ni.decl.android.contributes.r8.keep.from_dependency.unresolved"
    assert identifier in ids(keep("com.other:sdk"))
    assert not ids(keep("com.vendor:sdk"))


def test_a_platform_table_contradicting_platforms_is_rejected():
    """§4.5, and for the table this build is not for as much as the one it is."""
    reported = ids(
        {
            "contract": "1",
            "platforms": ["android"],
            "ios": {"contributes": {"objc_categories": True}},
        }
    )
    assert "ni.constraint.ios.platform-table-requires-listing.platforms" in reported
    assert not ids({"contract": "1", "platforms": ["android", "ios"],
                    "ios": {"contributes": {"objc_categories": True}}})


def test_a_forbidden_key_is_named_by_its_own_rule():
    """§6.5: rejected "with a diagnostic naming this rule — not the generic
    unknown-key message"."""
    reported = ids(
        {
            "contract": "1",
            "android": {
                "contributes": {
                    "features": [{"name": "android.hardware.camera", "required": False}]
                }
            },
        }
    )
    assert "ni.decl.android.contributes.features.required.forbidden" in reported
    assert "ni.decl.android.contributes.features.unknown-key" not in reported


def test_every_finding_names_a_distribution():
    """Requirement 18, discharged by the constructor rather than remembered."""
    log = report({"contract": "1", "androd": "yes"}, distribution="pyexample")
    assert log.items
    for found in log:
        assert found.distributions == ("pyexample",)
