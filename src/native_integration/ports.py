"""Obligations this library cannot discharge alone — and will not let a consumer skip.

Requirements 8.11, 8.12, 8.16 and 8.19 all need something only the consuming
build tool has: a resolved Gradle graph with per-artifact checksums, a resolved
Swift package graph with revisions, the class listing of an archive, the
``AndroidManifest.xml`` inside a resolved ``.aar``. This module defines those as
ports.

The important part is the failure mode. When a sidecar declares material whose
rules need a port and the consumer supplied none, the library raises
:class:`~native_integration.diagnostics.UnimplementedObligation` rather than
returning a clean result. A tool must not be able to pass validation by leaving
a check unimplemented — that is exactly the "silently ignored" failure §4.4
exists to prevent, one level up.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence, runtime_checkable

from .diagnostics import UnimplementedObligation
from .model import GradleDependency, SwiftPackage
from .naming import Module


class ResolutionFailure(Exception):
    """Native dependency resolution failed.

    Raised by a resolver port; the library converts it into a diagnostic that
    reports **every** declared coordinate, module and Swift package with the
    distribution that declared it (requirement 8.16) — the mapping the
    underlying resolver does not have.
    """


@dataclass(frozen=True)
class DependencyRequest:
    """One declared dependency, with the distribution that declared it."""

    distribution: str
    dependency: GradleDependency


@dataclass(frozen=True)
class SwiftPackageRequest:
    distribution: str
    package: SwiftPackage


@dataclass(frozen=True)
class ResolvedArtifact:
    """One artifact in the resolved Gradle graph, transitives included."""

    module: Module
    version: str
    #: A content hash of the artifact as fetched. §6.5 requires recording one
    #: per resolved artifact and verifying it on every subsequent build:
    #: a repository can serve different bytes under one coordinate, which is
    #: the case the checksum exists to catch.
    checksum: str
    #: The distributions whose declarations pulled this artifact in, where the
    #: resolver can say. Empty for a transitive nobody declared directly.
    declared_by: tuple[str, ...] = ()
    #: Local path to the fetched artifact, when there is one.
    path: str | None = None

    @property
    def coordinate(self) -> str:
        return f"{self.module}:{self.version}"


@dataclass(frozen=True)
class GradleGraph:
    artifacts: tuple[ResolvedArtifact, ...] = ()

    def find(self, module: Module) -> ResolvedArtifact | None:
        for artifact in self.artifacts:
            if artifact.module == module:
                return artifact
        return None

    def of_dependency(self, module: Module) -> tuple[ResolvedArtifact, ...]:
        """The artifacts belonging to one declared dependency.

        §6.9 checks a keep pattern against what a dependency's **resolved
        artifacts** contain, which is this — not everything on the classpath.
        """
        found = self.find(module)
        return (found,) if found else ()


@dataclass(frozen=True)
class BinaryTarget:
    """A prebuilt artifact a Swift package vends (§7.4, §11).

    The package's revision pins its *source*; it does not pin bytes fetched
    from ``url``. SwiftPM already requires a ``checksum`` for a remote binary
    target, and that is what the record keeps.
    """

    name: str
    checksum: str | None = None
    url: str | None = None

    @property
    def remote(self) -> bool:
        return self.url is not None


@dataclass(frozen=True)
class ResolvedSwiftPackage:
    """One package in the resolved Swift graph, transitives included."""

    name: str
    url: str
    #: ``version`` | ``branch`` | ``revision`` | ``path`` — §7.4 rejects a
    #: resolved graph containing a branch or a path dependency, whatever the
    #: declaration said, because a declared package's own ``Package.swift`` may
    #: name anything.
    kind: str
    version: str | None = None
    #: The commit. §7.4: a version is a tag and a tag can be moved, so the
    #: record must preserve both.
    revision: str | None = None
    declared_by: tuple[str, ...] = ()
    #: Prebuilt targets this package vends. Empty for a source-only package,
    #: which is the common case.
    binary_targets: tuple[BinaryTarget, ...] = ()


@dataclass(frozen=True)
class SwiftGraph:
    packages: tuple[ResolvedSwiftPackage, ...] = ()


@dataclass(frozen=True)
class ManifestComponent:
    kind: str
    name: str
    exported: bool = False


@dataclass(frozen=True)
class ManifestFeature:
    name: str
    required: bool = False


@dataclass(frozen=True)
class ArtifactManifest:
    """What a resolved Android artifact's own ``AndroidManifest.xml`` declares (§9)."""

    permissions: tuple[str, ...] = ()
    features: tuple[ManifestFeature, ...] = ()
    components: tuple[ManifestComponent, ...] = ()
    #: Whether the ``.aar`` carries consumer ProGuard rules, which AGP appends
    #: to the application's shrinker configuration without passing through
    #: §6.9's scoping. Reporting them is a SHOULD.
    proguard_rules: bool = False


@runtime_checkable
class GradleResolver(Protocol):
    """Resolves declared Gradle dependencies to a locked graph (§6.5).

    ``locked`` is the graph from the last accepted integration record, or None
    on a first resolution. §6.5 requires a consumer to **resolve from that
    record on subsequent builds until a new resolution is accepted**, so it is
    an argument rather than something the resolver is left to find.
    """

    def resolve(
        self,
        requests: Sequence[DependencyRequest],
        repositories: Sequence[object],
        locked: "GradleGraph | None" = None,
    ) -> GradleGraph: ...


@runtime_checkable
class SwiftResolver(Protocol):
    """Resolves declared Swift packages to a locked graph (§7.4).

    ``locked`` carries the previously recorded resolution, versions **and
    revisions**, for the same reason as :class:`GradleResolver`.
    """

    def resolve(
        self, requests: Sequence[SwiftPackageRequest], locked: "SwiftGraph | None" = None
    ) -> SwiftGraph: ...


@runtime_checkable
class ArtifactInspector(Protocol):
    """Reads inside resolved artifacts — an unzip-and-list, not a parser."""

    def manifest_of(self, artifact: ResolvedArtifact) -> ArtifactManifest | None:
        """The artifact's own manifest, or None when it carries none (a ``.jar``)."""
        ...

    def classes_of(self, artifact: ResolvedArtifact) -> Sequence[str]:
        """Fully qualified class names inside the artifact (§6.9)."""
        ...

    def files_of(self, artifact: ResolvedArtifact) -> Sequence[str]:
        """Packaged file paths inside the artifact (§9.1).

        The paths as they would land in the application — ``META-INF/LICENSE``,
        ``lib/arm64-v8a/libc++_shared.so`` — because a collision is a collision
        of destinations, not of archive members.
        """
        ...

    def classpath_classes(self) -> Sequence[str]:
        """Every class on the effective compilation classpath (§6.9).

        The keep rule this library generates is ``-keep class <pattern> { *; }``
        and R8 applies it to the whole program, so confirming the named
        dependency *contains* matching classes would not establish that the
        rule reaches nothing else.
        """
        ...


@dataclass(frozen=True)
class Resolvers:
    """The ports a consumer supplies. Absent ones fail closed when needed."""

    gradle: GradleResolver | None = None
    swift: SwiftResolver | None = None
    artifacts: ArtifactInspector | None = None

    def require_gradle(self, distributions: Sequence[str]) -> GradleResolver:
        if self.gradle is None:
            raise UnimplementedObligation(
                "a Gradle dependency was declared by "
                + ", ".join(sorted(distributions))
                + ", but no GradleResolver was supplied: the resolved graph must be "
                "locked and checksummed, and this library cannot do it for you",
                requirements=(12, 16),
                section="§6.5",
            )
        return self.gradle

    def require_swift(self, distributions: Sequence[str]) -> SwiftResolver:
        if self.swift is None:
            raise UnimplementedObligation(
                "a Swift package was declared by "
                + ", ".join(sorted(distributions))
                + ", but no SwiftResolver was supplied: the resolved graph must be "
                "locked with its revisions, and this library cannot do it for you",
                requirements=(12, 16),
                section="§7.4",
            )
        return self.swift

    def require_artifacts(self, distributions: Sequence[str], why: str) -> ArtifactInspector:
        if self.artifacts is None:
            raise UnimplementedObligation(
                f"{why} (declared by {', '.join(sorted(distributions))}) needs an "
                "ArtifactInspector, and none was supplied",
                requirements=(11, 19),
                section="§6.9/§9",
            )
        return self.artifacts


#: A consumer that has implemented nothing yet. Every port is absent, so any
#: sidecar that needs one fails loudly rather than quietly.
NO_RESOLVERS = Resolvers()
