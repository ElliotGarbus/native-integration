from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from native_integration import (  # noqa: E402
    Application,
    ConsumerProfile,
    MappingAnswers,
    Platform,
    SidecarSource,
    check_sidecar,
)


@pytest.fixture
def make_sidecar(tmp_path):
    """Write a native.toml (plus any extra files) and return a SidecarSource."""

    def factory(text: str, *, distribution: str = "example-pkg", files: dict[str, str] | None = None):
        root = tmp_path / distribution.replace("-", "_") / "_native"
        root.mkdir(parents=True, exist_ok=True)
        (root / "native.toml").write_text(text, encoding="utf-8")
        for relative, body in (files or {}).items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
        return SidecarSource(
            distribution=distribution,
            version="1.0.0",
            module=f"{distribution.replace('-', '_')}._native",
            root=root,
            package_relpath=f"{distribution.replace('-', '_')}/_native",
        )

    return factory


@pytest.fixture
def parse(make_sidecar):
    """Parse a sidecar and return (sidecar, codes, bag)."""

    def factory(
        text: str,
        *,
        platform: Platform = Platform.ANDROID,
        distribution: str = "example-pkg",
        files: dict[str, str] | None = None,
        profile: ConsumerProfile | None = None,
    ):
        source = make_sidecar(text, distribution=distribution, files=files)
        sidecar, bag = check_sidecar(source, platform=platform, profile=profile)
        return sidecar, [d.rule.code for d in bag], bag

    return factory


@pytest.fixture
def application():
    return Application(
        android_sdk={"min_sdk": 24, "compile_sdk": 35, "target_sdk": 34},
        deployment_target="16.0",
        answers=MappingAnswers(),
    )
