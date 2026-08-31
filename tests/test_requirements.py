"""Every obligation is accounted for, and the accounting is not prose.

`docs/REQUIREMENTS.md` claims that each of §8's obligations is a code path in
this library or a named reason why it is not. A claim like that decays the
moment it is maintained by hand, so the table is generated and these tests hold
the generator to the two things that make it worth reading: nothing is missing,
and nothing is excused that is actually implemented.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

from native_integration import registry  # noqa: E402


def _tool():
    spec = importlib.util.spec_from_file_location(
        "requirements_table", ROOT / "tools" / "requirements_table.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tool():
    return _tool()


@pytest.fixture(scope="module")
def contract():
    return registry.load()


def numbers(contract) -> set[int]:
    return {
        int(identifier.rsplit(".", 1)[-1])
        for identifier in contract.diagnostics
        if identifier.startswith("ni.req.")
    }


def test_every_obligation_is_discharged_or_named(tool, contract):
    """The one that matters. An obligation in neither column is a gap, and a gap
    a conformance claim would paper over."""
    accounted = (
        set(tool.discharged())
        | tool.structural_image()
        | set(tool.STRUCTURAL)
        | set(tool.IN_WHAT_IT_PRODUCES)
        | set(tool.BEYOND_THE_READER)
    )
    assert numbers(contract) - accounted == set()


def test_every_note_is_about_an_obligation_that_exists(tool, contract):
    """A note against a number §8.4 does not define explains nothing, and would
    quietly stop being read the moment the numbering moved."""
    defined = numbers(contract)
    assert set(tool.BEYOND_THE_READER) <= defined
    assert set(tool.STRUCTURAL) <= defined
    assert set(tool.IN_WHAT_IT_PRODUCES) <= defined
    assert set(tool.SPLIT) <= defined


def test_a_declared_obligation_is_not_also_a_check(tool):
    """The claims are different, and claiming both without saying why is how a
    row overstates itself. `structural` says there is no call site at which the
    obligation can be forgotten, which a module reporting it contradicts — the
    check is the call site. `in what it produces` says nothing refuses over it.

    A requirement with clauses of both kinds is legitimate and has to be in
    `SPLIT`, naming which clause is which."""
    reported = set(tool.discharged()) | tool.structural_image()
    declared = set(tool.STRUCTURAL) | set(tool.IN_WHAT_IT_PRODUCES)
    assert declared & reported <= set(tool.SPLIT)


def test_nothing_is_split_that_is_not_claimed_twice(tool):
    """The exemption is not a place to park a number. A row that stopped being
    claimed twice should lose its entry rather than keep an excuse for an
    overlap that no longer exists."""
    reported = set(tool.discharged()) | tool.structural_image()
    declared = set(tool.STRUCTURAL) | set(tool.IN_WHAT_IT_PRODUCES)
    assert set(tool.SPLIT) <= declared & reported


def test_the_table_on_disk_is_current(tool):
    """CI runs `--check`; this makes the same failure a named test locally."""
    assert tool.OUTPUT.read_text(encoding="utf-8") == tool.build()


def test_the_advisories_offered_are_ones_the_registry_defines(tool, contract):
    """A consumer claiming an advisory nobody defined is claiming nothing."""
    defined = {
        identifier.rsplit(".", 1)[-1]
        for identifier in contract.diagnostics
        if identifier.startswith("ni.adv.")
    }
    assert set(tool.advisories_offered()) <= defined
