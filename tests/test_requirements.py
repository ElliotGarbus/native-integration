"""Every obligation is accounted for, and the accounting is not prose.

`docs/REQUIREMENTS.md` claims that each of §8's obligations is a code path in
this library or a named reason why it is not. A claim like that decays the
moment it is maintained by hand, so the table is generated and these tests hold
the generator to the two things that make it worth reading: nothing is missing,
and nothing is excused that is actually implemented.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

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
        | set(tool.BEYOND_THE_READER)
    )
    assert numbers(contract) - accounted == set()


def test_every_note_is_about_an_obligation_that_exists(tool, contract):
    """A note against a number §8.4 does not define explains nothing, and would
    quietly stop being read the moment the numbering moved."""
    defined = numbers(contract)
    assert set(tool.BEYOND_THE_READER) <= defined
    assert set(tool.STRUCTURAL) <= defined


def test_a_structural_obligation_is_not_also_a_check(tool):
    """The two are different claims. `structural` says there is no call site at
    which the obligation can be forgotten, which a module reporting it would
    contradict — the check is the call site."""
    reported = set(tool.discharged()) | tool.structural_image()
    assert set(tool.STRUCTURAL) & reported == set()


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
    assert tool.advisories_offered() <= defined
