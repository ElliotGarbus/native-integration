"""What an action's diagnostic has to carry (§5.3, §5.6, requirements 11 and 21).

The corpus asserts diagnostic *ids* and the distributions they name, because §8
fixes neither a consumer's wording nor its format. Requirement 11 is about the
content of the report rather than its identity, so it is checked here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from native_integration import Closure, Origin, read, source_from_path

ACTION = """contract = "1"

[[ios.requires.application_action]]
id = "app_group_entitlement"
summary = "Enable App Groups and add the shared identifier"
reason = "The container is shared through the entitlement."
instructions = "Open Signing & Capabilities and add the App Groups capability."
acceptance = [
  "The application target's entitlement lists the identifier",
  "Every extension target lists the same identifier",
]
"""


@pytest.fixture
def report(tmp_path: Path):
    def build(sidecar: str = ACTION) -> tuple[str, tuple[str, ...]]:
        root = tmp_path / "pyx" / "_native"
        root.mkdir(parents=True)
        (root / "native.toml").write_text(sidecar, encoding="utf-8")
        integration = read(
            [source_from_path(root, distribution="pyx", version="1.0.0", module="pyx._native")],
            platform="ios",
            closure=Closure.of({"pyx": Origin(direct=True)}),
        )
        found = next(f for f in integration.findings if f.obligation == "ni.req.14")
        return found.render(), found.detail
    return build


def test_the_producers_reason_is_reported(report):
    _, detail = report()
    assert "The container is shared through the entitlement." in detail


def test_the_summary_is_reported(report):
    """Requirement 11 names it first: an action's `summary` is what the author
    is being asked to do, and a finding without it says only that something is
    missing."""
    _, detail = report()
    assert any("Enable App Groups and add the shared identifier" in line for line in detail)


def test_the_instructions_are_reported(report):
    _, detail = report()
    assert any("Signing & Capabilities" in line for line in detail)


def test_each_acceptance_criterion_is_reported_separately(report):
    """§5.6: "Each item in `acceptance` is checked independently", so folding
    them into one line would undo what the producer was asked to split."""
    _, detail = report()
    items = [line for line in detail if line.startswith("  - ")]
    assert len(items) == 2


def test_every_line_of_supplied_prose_names_the_distribution(report):
    """§5.6: a consumer "**MUST** attribute this text to the declaring
    distribution wherever it renders it ... as content that distribution
    supplied", and **MUST NOT** present it as its own guidance. An agent acting
    on a scaffolded action has this text and nothing else, and the difference
    between a task from its principal and a request from a dependency is
    whether the attribution survived."""
    _, detail = report()
    supplied = [
        line for line in detail
        if "Enable App Groups" in line or "Signing & Capabilities" in line
        or line.startswith("pyx's acceptance")
    ]
    assert supplied, "no prose was rendered at all"
    assert all(line.startswith("pyx") for line in supplied)


def test_the_optional_fields_are_optional(report):
    """`instructions` and `acceptance` are optional, and a sidecar declaring
    neither still reports the summary rather than nothing."""
    rendered, detail = report(
        """contract = "1"

[[ios.requires.application_action]]
id = "bare"
summary = "Do the thing"
reason = "Because"
"""
    )
    assert any("Do the thing" in line for line in detail)
    assert not any(line.startswith("  - ") for line in detail)
