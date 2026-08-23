"""Native dependency resolution, and the rules that only a resolved graph can settle.

Four obligations live here, all of them needing a port from
:mod:`native_integration.ports`:

* **the locked graph** (§6.5, §7.4) — every artifact and version including
  transitives, with a checksum per artifact, verified on subsequent builds;
* **resolution failure** (requirement 8.16) — when the resolver fails, report
  every declared coordinate, module and package *with the distribution that
  declared it*, which is the mapping the resolver does not have;
* **dependency keeps** (§6.9) — a pattern is checked against the effective
  compilation classpath, not merely against the artifact it names, because the
  generated rule reaches every matching class in the program;
* **what the artifacts themselves declare** (§9) — permissions, features and
  components from a resolved ``.aar``'s own manifest, attributed to the
  artifact rather than to the distribution that named the coordinate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from . import naming, rules
from .context import Application
from .diagnostics import DiagnosticBag
from .discovery import normalize_name
from .model import Platform, Sidecar
from .naming import Module
from .ports import (
    ArtifactManifest,
    DependencyRequest,
    GradleGraph,
    ResolutionFailure,
    ResolvedSwiftPackage,
    Resolvers,
    SwiftGraph,
    SwiftPackageRequest,
)


@dataclass(frozen=True)
class ArtifactFinding:
    """Something a resolved artifact's own manifest declares (§9)."""

    artifact: str
    kind: str  # permission | feature | component | proguard
    detail: str
    #: The distribution whose declaration pulled the artifact in, for attribution.
    distribution: str


@dataclass(frozen=True)
class NativeResolution:
    gradle: GradleGraph = field(default_factory=GradleGraph)
    swift: SwiftGraph = field(default_factory=SwiftGraph)
    artifact_findings: tuple[ArtifactFinding, ...] = ()
    resolved: bool = True


def resolve(
    sidecars: Sequence[Sidecar],
    *,
    platform: Platform,
    application: Application,
    resolvers: Resolvers,
    previous_checksums: Mapping[str, str] | None = None,
    locked_gradle: GradleGraph | None = None,
    locked_swift: SwiftGraph | None = None,
    bag: DiagnosticBag,
) -> NativeResolution:
    if platform is Platform.ANDROID:
        return _android(
            sidecars,
            application=application,
            resolvers=resolvers,
            previous_checksums=previous_checksums or {},
            locked=locked_gradle,
            bag=bag,
        )
    return _ios(
        sidecars,
        resolvers=resolvers,
        locked=locked_swift,
        previous_checksums=previous_checksums or {},
        bag=bag,
    )


# --- Android ----------------------------------------------------------------


def _android(
    sidecars: Sequence[Sidecar],
    *,
    application: Application,
    resolvers: Resolvers,
    previous_checksums: Mapping[str, str],
    locked: GradleGraph | None,
    bag: DiagnosticBag,
) -> NativeResolution:
    requests: list[DependencyRequest] = []
    repositories: list[object] = []
    for sidecar in sorted(sidecars, key=lambda s: normalize_name(s.distribution)):
        if sidecar.android is None:
            continue
        for dependency in sidecar.android.gradle_dependencies:
            requests.append(DependencyRequest(sidecar.distribution, dependency))
        repositories.extend(sidecar.android.gradle_repositories)

    if not requests:
        return NativeResolution()

    declarers = sorted({r.distribution for r in requests})
    resolver = resolvers.require_gradle(declarers)

    try:
        graph = resolver.resolve(requests, repositories, locked)
    except ResolutionFailure as exc:
        # Requirement 8.16: the resolver's own error names an artifact neither
        # application author has heard of. This is the line that connects it
        # back to the Python distributions that asked for it.
        bag.add(
            rules.RESOLUTION_FAILED,
            f"native dependency resolution failed: {exc}",
            *declarers,
            detail=tuple(
                f"{r.dependency.render()}  ← {r.distribution}"
                for r in sorted(requests, key=lambda r: r.dependency.render())
            ),
        )
        return NativeResolution(resolved=False)

    _requested_versus_resolved(requests, graph, bag)
    _verify_checksums(graph, requests, previous_checksums, bag)

    findings: list[ArtifactFinding] = []
    if graph.artifacts:
        findings.extend(_artifact_manifests(graph, requests, application, resolvers, bag))
    if graph.artifacts:
        findings.extend(_packaging_collisions(graph, requests, application, resolvers, bag))
    findings.extend(_dependency_keeps(sidecars, graph, resolvers, application, bag))
    _component_classes(sidecars, graph, resolvers, bag)
    return NativeResolution(gradle=graph, artifact_findings=tuple(findings))


def _declarers_of(requests: Sequence[DependencyRequest], module: Module) -> tuple[str, ...]:
    return tuple(sorted({r.distribution for r in requests if r.dependency.module == module}))


def _requested_versus_resolved(
    requests: Sequence[DependencyRequest], graph: GradleGraph, bag: DiagnosticBag
) -> None:
    """§6.5 — a declared version is a requirement, not a pin; show both when they differ."""
    for request in requests:
        artifact = graph.find(request.dependency.module)
        if artifact is None:
            continue
        if request.dependency.exact_version and artifact.version != request.dependency.exact_version:
            bag.add(
                rules.DEPENDENCY_VERSION_SUBSTITUTED,
                f"{request.dependency.module}  requested "
                f"{request.dependency.exact_version} → resolved {artifact.version}",
                request.distribution,
            )
        elif request.dependency.is_range:
            bag.add(
                rules.DEPENDENCY_VERSION_SUBSTITUTED,
                f"{request.dependency.module}  requested {request.dependency.requested} "
                f"→ resolved {artifact.version}",
                request.distribution,
            )


def _verify_checksums(
    graph: GradleGraph,
    requests: Sequence[DependencyRequest],
    previous: Mapping[str, str],
    bag: DiagnosticBag,
) -> None:
    """§6.5 — recording without verifying would leave the guarantee descriptive."""
    for artifact in graph.artifacts:
        recorded = previous.get(artifact.coordinate)
        if recorded is None or recorded == artifact.checksum:
            continue
        declarers = _declarers_of(requests, artifact.module) or artifact.declared_by or ("unknown",)
        bag.add(
            rules.DEPENDENCY_CHECKSUM_MISMATCH,
            f"{artifact.coordinate} does not match the recorded checksum "
            f"({recorded} → {artifact.checksum}); a repository can serve different bytes "
            "under one coordinate",
            *declarers,
        )


def _artifact_manifests(
    graph: GradleGraph,
    requests: Sequence[DependencyRequest],
    application: Application,
    resolvers: Resolvers,
    bag: DiagnosticBag,
) -> list[ArtifactFinding]:
    """§9 — what the resolved artifacts declare, attributed to the artifact."""
    declarers = sorted({r.distribution for r in requests})
    inspector = resolvers.require_artifacts(
        declarers, "reading the resolved artifacts' own manifests"
    )
    findings: list[ArtifactFinding] = []

    for artifact in sorted(graph.artifacts, key=lambda a: a.coordinate):
        manifest: ArtifactManifest | None = inspector.manifest_of(artifact)
        if manifest is None:
            continue
        blame = _declarers_of(requests, artifact.module) or artifact.declared_by or tuple(declarers)

        for permission in manifest.permissions:
            findings.append(
                ArtifactFinding(artifact.coordinate, "permission", permission, blame[0])
            )
            bag.add(
                rules.ARTIFACT_PERMISSION,
                f"from {artifact.coordinate} (resolved artifact manifest): "
                f"+ permission {permission}",
                *blame,
            )

        for feature in manifest.features:
            detail = f"{feature.name} (required={str(feature.required).lower()})"
            findings.append(ArtifactFinding(artifact.coordinate, "feature", detail, blame[0]))
            if feature.required and feature.name not in application.required_features:
                # Silently shrinking an application's device reach is the same
                # harm whoever authors it. Report, and override to false.
                bag.add(
                    rules.ARTIFACT_FEATURE_OVERRIDDEN,
                    f"{artifact.coordinate} declares <uses-feature {feature.name} "
                    'required="true">; overridden to required="false" because the '
                    "application does not declare it required",
                    *blame,
                )

        for component in manifest.components:
            detail = f"{component.kind} {component.name}" + (" exported" if component.exported else "")
            findings.append(ArtifactFinding(artifact.coordinate, "component", detail, blame[0]))
            if component.exported:
                bag.add(
                    rules.ARTIFACT_EXPORTED_COMPONENT,
                    f"{artifact.coordinate} declares an exported {component.kind} "
                    f"{component.name}; reported with the same prominence as a contributed "
                    "one, so every externally reachable surface is visible",
                    *blame,
                )

        if manifest.proguard_rules:
            findings.append(
                ArtifactFinding(artifact.coordinate, "proguard", "consumer rules", blame[0])
            )
            bag.add(
                rules.ARTIFACT_PROGUARD_RULES,
                f"{artifact.coordinate} carries consumer ProGuard rules, appended to the "
                "application's shrinker configuration without passing through §6.9's scoping",
                *blame,
            )

    return findings


#: §9.1 — packaging metadata a consumer may resolve on its own authority. Not
#: code, not loaded at runtime, and identical in effect whichever copy wins.
_METADATA_PREFIXES = ("META-INF/",)
#: …with the exception of what *is* code or behaviour under that prefix.
_METADATA_EXCEPTIONS = ("META-INF/services/", "META-INF/native/")


def _is_metadata(path: str) -> bool:
    if any(path.startswith(prefix) for prefix in _METADATA_EXCEPTIONS):
        return False
    return any(path.startswith(prefix) for prefix in _METADATA_PREFIXES)


def _packaging_collisions(
    graph: GradleGraph,
    requests: Sequence[DependencyRequest],
    application: Application,
    resolvers: Resolvers,
    bag: DiagnosticBag,
) -> list[ArtifactFinding]:
    """§9.1 — one packaged path claimed by two distributions' artifacts.

    The producers cannot see this: a collision exists only in a combination,
    and neither of them knows what it will be composed with. What the consumer
    adds over the build system's own duplicate-path error is the mapping back
    to the *distributions* that asked for the artifacts.
    """
    declarers = sorted({r.distribution for r in requests})
    inspector = resolvers.require_artifacts(
        declarers, "listing the resolved artifacts' packaged files (§9.1)"
    )

    claims: dict[str, dict[str, str]] = {}
    for artifact in sorted(graph.artifacts, key=lambda a: a.coordinate):
        blame = _declarers_of(requests, artifact.module) or artifact.declared_by or tuple(declarers)
        for path in inspector.files_of(artifact):
            for distribution in blame:
                claims.setdefault(path, {})[distribution] = artifact.coordinate

    findings: list[ArtifactFinding] = []
    for path in sorted(claims):
        by_distribution = claims[path]
        if len(by_distribution) < 2:
            continue
        blame = tuple(sorted(by_distribution))
        sources = ", ".join(f"{d} → {by_distribution[d]}" for d in blame)

        if _is_metadata(path):
            # Deterministic, and not by resolution order: the first artifact in
            # normalized distribution order supplies it.
            winner = by_distribution[blame[0]]
            findings.append(
                ArtifactFinding(winner, "packaging", f"{path} (metadata, kept {winner})", blame[0])
            )
            bag.add(
                rules.PACKAGING_COLLISION_RESOLVED,
                f"`{path}` is carried by more than one artifact ({sources}); kept "
                f"{winner} as packaging metadata",
                *blame,
            )
            continue

        chosen = application.answers.packaging_choice(path)
        if chosen is None:
            bag.add(
                rules.PACKAGING_COLLISION,
                f"`{path}` is carried by more than one artifact ({sources}); choosing "
                "one silently would decide at random which native code the "
                "application runs, so the application must choose",
                *blame,
            )
            continue

        findings.append(ArtifactFinding(chosen, "packaging", f"{path} (chosen {chosen})", blame[0]))
        bag.add(
            rules.PACKAGING_COLLISION_RESOLVED,
            f"`{path}` is carried by more than one artifact ({sources}); the "
            f"application chose {chosen}",
            *blame,
        )

    return findings


def _component_classes(
    sidecars: Sequence[Sidecar], graph: GradleGraph, resolvers: Resolvers, bag: DiagnosticBag
) -> None:
    """§8's SHOULD — verify a ``from_dependency`` component's class exists.

    A warning, not an error: the specification makes this a SHOULD, and an
    inspector that reports no classes for an artifact it cannot open would
    otherwise turn every such component into a build failure.
    """
    if resolvers.artifacts is None:
        return
    for sidecar in sidecars:
        if sidecar.android is None:
            continue
        for component in sidecar.android.components:
            if component.producer_sourced:
                continue
            try:
                module = Module.parse(component.from_dependency or "")
            except ValueError:
                continue
            classes: set[str] = set()
            for artifact in graph.of_dependency(module):
                classes.update(resolvers.artifacts.classes_of(artifact))
            if classes and component.name not in classes:
                bag.add(
                    rules.COMPONENT_CLASS_ABSENT,
                    f"component `{component.name}` is attributed to "
                    f"{component.from_dependency}, whose resolved artifacts do not contain "
                    "that class",
                    sidecar.distribution,
                )


def _dependency_keeps(
    sidecars: Sequence[Sidecar],
    graph: GradleGraph,
    resolvers: Resolvers,
    application: Application,
    bag: DiagnosticBag,
) -> list[ArtifactFinding]:
    """§6.9 — a keep pattern must reach nothing outside the dependency it names."""
    keeps = [
        (sidecar.distribution, keep)
        for sidecar in sidecars
        if sidecar.android
        for keep in sidecar.android.dependency_keeps
    ]
    if not keeps:
        return []
    if not application.shrinking_enabled:
        # §6.9 — keeps apply only when the application has enabled shrinking, so
        # there is nothing to validate against and nothing to generate.
        return []

    declarers = sorted({d for d, _ in keeps})
    inspector = resolvers.require_artifacts(declarers, "validating a dependency keep pattern")
    classpath = list(inspector.classpath_classes())

    for distribution, keep in keeps:
        try:
            module = Module.parse(keep.from_dependency)
        except ValueError:
            continue  # already reported during parse
        owned: set[str] = set()
        for artifact in graph.of_dependency(module):
            owned.update(inspector.classes_of(artifact))
        matcher = naming.compile_keep_pattern(keep.pattern)
        strays = sorted(c for c in classpath if matcher.match(c) and c not in owned)
        if strays:
            bag.add(
                rules.KEEP_MATCHES_FOREIGN_CLASS,
                f"keep pattern `{keep.pattern}` names {keep.from_dependency} but also "
                f"matches {strays[0]}, which that dependency's resolved artifacts do not "
                "contain",
                distribution,
                detail=tuple(strays[:10]),
            )
    return []


# --- iOS --------------------------------------------------------------------


def _ios(
    sidecars: Sequence[Sidecar],
    *,
    resolvers: Resolvers,
    locked: SwiftGraph | None,
    previous_checksums: Mapping[str, str],
    bag: DiagnosticBag,
) -> NativeResolution:
    requests: list[SwiftPackageRequest] = []
    for sidecar in sorted(sidecars, key=lambda s: normalize_name(s.distribution)):
        if sidecar.ios is None:
            continue
        for package in sidecar.ios.swift_packages:
            requests.append(SwiftPackageRequest(sidecar.distribution, package))

    if not requests:
        return NativeResolution()

    declarers = sorted({r.distribution for r in requests})
    resolver = resolvers.require_swift(declarers)

    try:
        graph = resolver.resolve(requests, locked)
    except ResolutionFailure as exc:
        bag.add(
            rules.RESOLUTION_FAILED,
            f"Swift package resolution failed: {exc}",
            *declarers,
            detail=tuple(
                f"{r.package.render()}  ← {r.distribution}"
                for r in sorted(requests, key=lambda r: r.package.name)
            ),
        )
        return NativeResolution(resolved=False)

    # The declaration rules bind the sidecar; the resolved graph is where they
    # are enforced. A declared package's own Package.swift may name anything.
    for package in graph.packages:
        if package.kind in ("branch", "path"):
            blame = package.declared_by or tuple(declarers)
            bag.add(
                rules.SWIFT_GRAPH_UNPINNABLE,
                f"the resolved Swift graph contains `{package.name}` as a {package.kind} "
                "dependency; a branch revision has no stable meaning and a path dependency "
                "does not resolve on another machine",
                *blame,
            )
        _binary_targets(package, declarers, previous_checksums, bag)
    return NativeResolution(swift=graph)


def _binary_targets(
    package: ResolvedSwiftPackage,
    declarers: Sequence[str],
    previous: Mapping[str, str],
    bag: DiagnosticBag,
) -> None:
    """§7.4 — a package's revision pins its source, not the bytes it fetches."""
    blame = package.declared_by or tuple(declarers)
    for target in package.binary_targets:
        key = f"{package.name}/{target.name}"
        if target.checksum is None:
            if target.remote:
                bag.add(
                    rules.SWIFT_BINARY_UNCHECKSUMMED,
                    f"binary target {key} is fetched from {target.url} and declares no "
                    "checksum; the record pins nothing for it",
                    *blame,
                )
            continue
        recorded = previous.get(key)
        if recorded is not None and recorded != target.checksum:
            bag.add(
                rules.SWIFT_BINARY_CHECKSUM_MISMATCH,
                f"binary target {key} does not match the recorded checksum "
                f"({recorded} → {target.checksum}); the package's revision does not pin "
                "bytes fetched from a URL",
                *blame,
            )
