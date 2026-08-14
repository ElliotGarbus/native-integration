"""Stub ports, for tests and for a consumer that is not finished yet.

**These do not resolve anything.** They echo the declarations back as if the
resolver had returned exactly what was asked for: no transitives, no real
checksums, no archive contents. That makes them useful for exercising the rest
of the pipeline and useless as a substitute for the real thing — which is the
intent, since :mod:`native_integration.ports` exists to stop an unimplemented
obligation from passing quietly.

A consumer must not ship these.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from .ports import (
    ArtifactManifest,
    DependencyRequest,
    GradleGraph,
    ResolvedArtifact,
    ResolvedSwiftPackage,
    Resolvers,
    SwiftGraph,
    SwiftPackageRequest,
)


def _fake_checksum(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EchoGradleResolver:
    """Returns one artifact per declared dependency, at the requested version."""

    #: Override the version a module resolves to, to exercise §6.5's
    #: requested-versus-resolved reporting.
    versions: Mapping[str, str] = field(default_factory=dict)

    def resolve(
        self,
        requests: Sequence[DependencyRequest],
        repositories: Sequence[object],
        locked: GradleGraph | None = None,
    ) -> GradleGraph:
        artifacts: dict[str, ResolvedArtifact] = {}
        for request in requests:
            module = request.dependency.module
            version = self.versions.get(
                str(module), request.dependency.exact_version or request.dependency.at_least or "0"
            )
            key = f"{module}:{version}"
            previous = artifacts.get(key)
            declared_by = tuple(
                sorted({*(previous.declared_by if previous else ()), request.distribution})
            )
            artifacts[key] = ResolvedArtifact(
                module=module,
                version=version,
                checksum=_fake_checksum(key),
                declared_by=declared_by,
            )
        return GradleGraph(tuple(artifacts.values()))


@dataclass(frozen=True)
class EchoSwiftResolver:
    """Returns one resolved package per declared package, with a stub revision."""

    def resolve(
        self, requests: Sequence[SwiftPackageRequest], locked: SwiftGraph | None = None
    ) -> SwiftGraph:
        packages: dict[str, ResolvedSwiftPackage] = {}
        for request in requests:
            package = request.package
            kind = "version" if package.requirement_kind in ("exact", "from") else package.requirement_kind
            packages[package.name] = ResolvedSwiftPackage(
                name=package.name,
                url=package.url,
                kind=kind,
                version=package.requirement_value if kind == "version" else None,
                revision=_fake_checksum(package.url + package.requirement_value)[7:15],
                declared_by=(request.distribution,),
            )
        return SwiftGraph(tuple(packages.values()))


@dataclass(frozen=True)
class EmptyArtifactInspector:
    """Reports no manifests and no classes — every artifact looks inert."""

    manifests: Mapping[str, ArtifactManifest] = field(default_factory=dict)
    classes: Mapping[str, Sequence[str]] = field(default_factory=dict)

    def manifest_of(self, artifact: ResolvedArtifact) -> ArtifactManifest | None:
        return self.manifests.get(artifact.coordinate)

    def classes_of(self, artifact: ResolvedArtifact) -> Sequence[str]:
        return self.classes.get(artifact.coordinate, ())

    def classpath_classes(self) -> Sequence[str]:
        return tuple(c for classes in self.classes.values() for c in classes)


def stub_resolvers(**kwargs: object) -> Resolvers:
    """Every port, stubbed. Tests only."""
    return Resolvers(
        gradle=EchoGradleResolver(kwargs.get("versions", {})),  # type: ignore[arg-type]
        swift=EchoSwiftResolver(),
        artifacts=EmptyArtifactInspector(
            kwargs.get("manifests", {}),  # type: ignore[arg-type]
            kwargs.get("classes", {}),  # type: ignore[arg-type]
        ),
    )
