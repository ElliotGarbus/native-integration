"""§5.2's `inline` kind, and what counts as referencing one (requirement 13).

`R13_inline_value_unreferenced` carries the case that matters — a value nothing
names, answered by the application and discarded. What is here is the other
side: the reference forms that make a value reachable. §5.3's `uses` has a
fixture; §6.6's `{ application_value = ... }` does not, because it is Android's
alone and the rule it exercises is core's.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from native_integration import Closure, Origin, integration, read, source_from_path

VALUES = """
[[android.requires.application_value]]
id = "deep_link_host"
kind = "inline"
reason = "The host your links use"
placeholder = "<TODO: links.example.com>"
"""

COMPONENT = """
[android.owns]
java_namespaces = ["org.example.mypkg"]

[[android.contributes.components]]
kind = "activity"
name = "org.example.mypkg.LinkActivity"
exported_required = true
reason = "Receives the deep link"

[[android.contributes.components.view_links]]
scheme = "https"
host = { application_value = "deep_link_host" }
"""


@pytest.fixture
def complaints(tmp_path: Path):
    def build(body: str) -> list[str]:
        root = tmp_path / "pyx" / "_native"
        root.mkdir(parents=True)
        (root / "native.toml").write_text(f'contract = "1"\n{body}', encoding="utf-8")
        integration = read(
            [source_from_path(root, distribution="pyx", version="1.0.0", module="pyx._native")],
            platform="android",
            closure=Closure.of({"pyx": Origin(direct=True)}),
        )
        return [
            finding.message
            for finding in integration.findings
            if "referenced by nothing" in finding.message
        ]
    return build


def test_a_value_no_declaration_names_is_rejected(complaints):
    assert any("deep_link_host" in message for message in complaints(VALUES))


def test_a_value_a_contribution_references_is_not(complaints):
    """§6.6's inline reference is nested two tables deep inside an attribute
    that the registry leaves open, so a check looking only at the fields it
    knows would find nothing and reject a value that is used."""
    assert complaints(VALUES + COMPONENT) == []


def test_the_reference_must_be_the_whole_attribute():
    """`{ application_value = "..." }` is a reference; a table carrying that key
    among others is not one, and counting it would let an unrelated table
    silence the rule. The registry's `string_or_inline_reference` refuses the
    second shape before resolution reaches it, so this is checked directly:
    the guard exists to keep the walk honest if a later contract admits a form
    that structure alone cannot distinguish."""
    assert list(integration._referenced({"host": {"application_value": "x"}})) == ["x"]
    assert list(integration._referenced({"host": {"application_value": "x", "port": 1}})) == []


def test_only_inline_values_need_a_referrer(complaints):
    """Every other kind names a `key`, which is where the answer goes, so
    nothing has to point at it."""
    keyed = """
[[android.requires.application_value]]
id = "analytics_key"
kind = "meta_data"
key = "com.example.API_KEY"
reason = "Your project key"
placeholder = "<TODO: your key>"
"""
    assert complaints(keyed) == []
