"""§8.1's per-platform conformance, and requirement 9's second sentence.

`R09_platform_not_supported` covers the first sentence — a sidecar whose
`platforms` key omits the platform being built. This is the other one: a
*consumer* asked for a profile it does not implement. The corpus cannot carry
it, because a case tests the consumer under test and this reader implements
both profiles; what is testable is that the refusal exists and that a caller
can declare a narrower profile set.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from native_integration import (
    Closure,
    Origin,
    UnimplementedProfile,
    read,
    source_from_path,
)

SIDECAR = """contract = "1"
platforms = ["android"]

[[android.contributes.gradle_dependencies]]
coordinate = "com.example:sdk:1.2.0"
configuration = "implementation"
"""


@pytest.fixture
def sources(tmp_path: Path):
    root = tmp_path / "pyx" / "_native"
    root.mkdir(parents=True)
    (root / "native.toml").write_text(SIDECAR, encoding="utf-8")
    return [source_from_path(root, distribution="pyx", version="1.0.0", module="pyx._native")]


def build(sources, platform: str, **kwargs):
    return read(
        sources,
        platform=platform,
        closure=Closure.of({"pyx": Origin(direct=True)}),
        **kwargs,
    )


def test_a_reader_implementing_both_profiles_builds_either(sources):
    assert build(sources, "android").platform == "android"
    assert build(sources, "ios").platform == "ios"


def test_a_narrower_consumer_refuses_the_profile_it_lacks(sources):
    """An Android-only build tool is a conforming consumer under §8.1. What it
    must not do is read an iOS sidecar with the Android profile's rules and
    call the result a build."""
    with pytest.raises(UnimplementedProfile):
        build(sources, "ios", profiles=("android",))


def test_the_refusal_precedes_any_reading(sources):
    """"Rather than building partially" is why this is checked before the first
    sidecar is opened: a partial resolution that a caller might use is the harm,
    so none is produced."""
    with pytest.raises(UnimplementedProfile) as raised:
        read([], platform="ios", closure=Closure.isolated_environment(), profiles=("android",))
    assert "ios" in str(raised.value)


def test_a_platform_the_specification_does_not_define_is_refused_too(sources):
    """§4.5's vocabulary is closed, so `macos` is not a profile anyone
    implements. Reaching structural validation with it would report an
    unrecognized top-level table, which describes the sidecar rather than the
    request."""
    with pytest.raises(UnimplementedProfile):
        build(sources, "macos")
