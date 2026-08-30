"""Reading a sidecar: the file, the gate, and the platform key.

§4.3's gate is the one place order is itself normative — "**MUST NOT** parse
such a sidecar partially" — so most of what is checked here is what the reader
declines to do.
"""

from __future__ import annotations

import pytest

from native_integration import document, registry
from native_integration.contract import ContractVersion
from native_integration.discovery import source_from_path
from native_integration.findings import Findings


@pytest.fixture
def sidecar(tmp_path):
    def factory(text: str, *, distribution: str = "pyexample", files=None):
        root = tmp_path / distribution / "_native"
        root.mkdir(parents=True, exist_ok=True)
        (root / "native.toml").write_text(text, encoding="utf-8")
        for relative, body in (files or {}).items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
        return source_from_path(root, distribution=distribution, version="1.0.0")

    return factory


def read(source, *, platform="android", origin="", implemented=None):
    log = Findings(registry.load())
    kwargs = {} if implemented is None else {"implemented": implemented}
    parsed = document.read(
        source, platform=platform, findings=log, origin=origin, **kwargs
    )
    return parsed, log


def ids(log) -> set[str]:
    return {entry["id"] for entry in log.as_diagnostics()}


# -- the file --------------------------------------------------------------


def test_a_well_formed_sidecar_is_read(sidecar):
    parsed, log = read(
        sidecar(
            """
            contract = "1"
            platforms = ["android"]
            [android.requires]
            min_sdk = 26
            """
        )
    )
    assert parsed is not None
    assert not list(log)
    assert parsed.contract == ContractVersion(1, 0)
    assert parsed.section("requires")["min_sdk"] == 26


def test_a_sidecar_that_is_not_toml_is_reported_not_raised(sidecar):
    parsed, log = read(sidecar('contract = "1"\n[android\n'))
    assert parsed is None
    assert ids(log) == {"ni.req.4"}


def test_a_missing_sidecar_is_reported(sidecar, tmp_path):
    source = source_from_path(tmp_path / "absent", distribution="pygone")
    parsed, log = read(source)
    assert parsed is None
    assert ids(log) == {"ni.req.4"}


# -- §4.3, the gate --------------------------------------------------------


def test_a_missing_contract_stops_the_read(sidecar):
    parsed, log = read(sidecar("[android.requires]\nmin_sdk = 26\n"))
    assert parsed is None
    assert ids(log) == {"ni.decl.contract.missing", "ni.req.7"}


@pytest.mark.parametrize("value", ['"1.0.0"', '"01"', '"1."', '" 1"', '"v1"'])
def test_the_contract_grammar_is_exact(sidecar, value):
    """§4.3 names these four outright: not lenient spellings of `"1"`."""
    parsed, log = read(sidecar(f"contract = {value}\n"))
    assert parsed is None
    assert ids(log) == {"ni.decl.contract.pattern", "ni.req.7"}


def test_a_contract_that_is_not_a_string_stops_the_read(sidecar):
    parsed, log = read(sidecar("contract = 1\n"))
    assert parsed is None
    assert ids(log) == {"ni.decl.contract.type", "ni.req.7"}


@pytest.mark.parametrize("declared", ["2", "2.1", "0"])
def test_another_major_is_refused(sidecar, declared):
    parsed, log = read(sidecar(f'contract = "{declared}"\n'))
    assert parsed is None
    assert ids(log) == {"ni.req.7"}


def test_a_greater_minor_is_refused(sidecar):
    parsed, log = read(sidecar('contract = "1.1"\n'))
    assert parsed is None
    assert ids(log) == {"ni.req.7"}


def test_a_lesser_minor_is_read(sidecar):
    parsed, log = read(
        sidecar('contract = "1"\n'), implemented=ContractVersion(1, 4)
    )
    assert parsed is not None
    assert not list(log)


def test_a_refused_sidecar_is_not_validated_further(sidecar):
    """"It **MUST NOT** parse such a sidecar partially" — so the unknown key and
    the unsupported platform below it are never reported, and never acted on."""
    parsed, log = read(
        sidecar(
            """
            contract = "2"
            nonsense = 1
            [android.contributes.permissions]
            """
        )
    )
    assert parsed is None
    assert ids(log) == {"ni.req.7"}


def test_a_capability_newer_than_the_declared_contract_is_refused(sidecar):
    """§4.3's under-declaration rule, which no v1 declaration can trigger: every
    `since` is 1.0. Driven from the registry so that issuing 1.1 is a registry
    edit, which is what the field is for."""
    parsed, log = read(
        sidecar('contract = "1"\nplatforms = ["android"]\n'),
        implemented=ContractVersion(1, 9),
    )
    assert parsed is not None
    assert not list(log)


# -- §4.5, the platform key ------------------------------------------------


def test_building_for_a_platform_the_key_omits_fails(sidecar):
    parsed, log = read(
        sidecar('contract = "1"\nplatforms = ["ios"]\n'),
        platform="android",
        origin="via pywrapper",
    )
    assert ids(log) == {"ni.req.9"}
    assert parsed is not None  # the sidecar is readable; the build is not viable
    reported = next(f for f in log if f.obligation == "ni.req.9")
    assert "via pywrapper" in " ".join(reported.detail)


def test_no_platforms_key_makes_no_claim(sidecar):
    _, log = read(sidecar('contract = "1"\n'), platform="ios")
    assert not list(log)


def test_a_platform_table_the_key_omits_is_a_contradiction(sidecar):
    """§4.5, and reported for the table this build is not for as much as for the
    one it is."""
    _, log = read(
        sidecar(
            """
            contract = "1"
            platforms = ["android"]
            [ios.contributes]
            objc_categories = true
            """
        ),
        platform="android",
    )
    assert ids(log) == {
        "ni.constraint.ios.platform-table-requires-listing.platforms",
        "ni.req.9",
    }


# -- §4.1, through resources.py --------------------------------------------


def test_a_declared_path_may_not_escape_the_sidecar_directory(sidecar):
    source = sidecar('contract = "1"\n')
    with pytest.raises(Exception) as raised:
        source.resolve("../elsewhere.java")
    assert "escapes" in str(raised.value)


def test_the_sidecar_directory_is_excluded_from_the_payload(sidecar):
    source = sidecar('contract = "1"\n')
    assert source.payload_exclusions() == ("pyexample/_native/",)
