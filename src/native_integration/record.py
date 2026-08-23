"""The integration record: review of the native surface, integrity of the inputs.

§9's lifecycle is five steps — compute, compare, report the delta, fail or
require explicit acceptance, update on acceptance — and the first build is step
4, not an exemption. That last point is the one an implementation is most
likely to get wrong, because writing a record and proceeding on the first run
feels like initialization; it is instead the moment an application acquires
*all* of its inherited native surface at once.

The record is JSON with sorted keys: durable, diffable, and normally committed.
It never contains a credential.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Iterable, Mapping

from .diagnostics import SpecViolation
from .discovery import normalize_name
from .effective import Contribution, EffectiveSet
from .native import NativeResolution
from .naming import Module
from .ports import GradleGraph, ResolvedArtifact, ResolvedSwiftPackage, SwiftGraph

RECORD_FORMAT = 1


class MalformedRecord(SpecViolation):
    """An integration record exists but cannot be read.

    An exception rather than a diagnostic, because a diagnostic must name the
    distribution it concerns and a broken lock file concerns none of them — it
    is a fault in the application's own repository. The message names the path
    and the reason, which is what the person editing it needs.
    """

    def __init__(self, source: str, reason: str) -> None:
        self.source = source
        self.reason = reason
        super().__init__(f"integration record {source} {reason}")


@dataclass(frozen=True)
class DistributionRecord:
    name: str
    version: str
    origin: str
    contract: str
    #: SHA-256 per integration input, keyed by normalized relative path.
    inputs: Mapping[str, str] = field(default_factory=dict)
    #: One canonical line per contributed thing. A set difference over these is
    #: the delta a reviewer reads.
    entries: tuple[str, ...] = ()
    #: coordinate → checksum, for the verification §6.5 requires next build.
    artifacts: Mapping[str, str] = field(default_factory=dict)
    #: Swift packages as ``name → "version @ revision"``. A version is a tag and
    #: a tag can be moved, so both are preserved.
    swift: Mapping[str, str] = field(default_factory=dict)
    #: ``package/target`` → checksum, for every binary target in the resolved
    #: Swift graph. The package's revision pins its source and not these (§7.4).
    swift_binaries: Mapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "origin": self.origin,
            "contract": self.contract,
            "inputs": dict(sorted(self.inputs.items())),
            "entries": list(self.entries),
            "artifacts": dict(sorted(self.artifacts.items())),
            "swift": dict(sorted(self.swift.items())),
            "swift_binaries": dict(sorted(self.swift_binaries.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "DistributionRecord":
        return cls(
            name=str(data.get("name", "")),
            version=str(data.get("version", "")),
            origin=str(data.get("origin", "")),
            contract=str(data.get("contract", "")),
            inputs=dict(data.get("inputs", {}) or {}),  # type: ignore[arg-type]
            entries=tuple(data.get("entries", []) or ()),  # type: ignore[arg-type]
            artifacts=dict(data.get("artifacts", {}) or {}),  # type: ignore[arg-type]
            swift=dict(data.get("swift", {}) or {}),  # type: ignore[arg-type]
            swift_binaries=dict(data.get("swift_binaries", {}) or {}),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class IntegrationRecord:
    platform: str
    contract: str
    distributions: tuple[DistributionRecord, ...] = ()

    def to_dict(self) -> dict:
        return {
            "record": RECORD_FORMAT,
            "platform": self.platform,
            "contract": self.contract,
            "distributions": [d.to_dict() for d in self.distributions],
        }

    def dumps(self) -> str:
        # ensure_ascii=False because the record is meant to be read in a diff,
        # and `—` in place of an em dash is noise a reviewer must decode.
        return json.dumps(self.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"

    @classmethod
    def loads(cls, text: str, *, source: str = "<string>") -> "IntegrationRecord":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise MalformedRecord(source, f"is not valid JSON ({exc})") from exc
        if not isinstance(data, dict):
            raise MalformedRecord(source, "is not a JSON object")
        entries = data.get("distributions", [])
        if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
            raise MalformedRecord(source, "`distributions` is not a list of objects")
        return cls(
            platform=str(data.get("platform", "")),
            contract=str(data.get("contract", "")),
            distributions=tuple(DistributionRecord.from_dict(d) for d in entries),
        )

    @classmethod
    def read(cls, path: Path | str) -> "IntegrationRecord | None":
        """The last accepted record, or None when there is none.

        A record that exists but cannot be read raises rather than returning
        None: "no record" and "a record I could not parse" lead to opposite
        actions, and treating the second as the first would silently re-bootstrap
        a lock the application had already accepted.
        """
        file = Path(path)
        if not file.exists():
            return None
        try:
            text = file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise MalformedRecord(str(file), f"could not be read ({exc})") from exc
        return cls.loads(text, source=str(file))

    def write(self, path: Path | str) -> Path:
        file = Path(path)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(self.dumps(), encoding="utf-8")
        return file

    def get(self, name: str) -> DistributionRecord | None:
        for distribution in self.distributions:
            if normalize_name(distribution.name) == normalize_name(name):
                return distribution
        return None

    def checksums(self) -> dict[str, str]:
        """Every recorded content hash, for verification on the next build.

        Maven artifacts (§6.5) and Swift binary targets (§7.4) share one map:
        their keys cannot collide — a coordinate is ``group:artifact:version``
        and a binary target is ``package/target`` — and both answer the same
        question, which is whether the bytes changed under a fixed name.
        """
        out: dict[str, str] = {}
        for distribution in self.distributions:
            out.update(distribution.artifacts)
            out.update(distribution.swift_binaries)
        return out

    def artifact_checksums(self) -> dict[str, str]:
        """Maven artifact checksums only, without the Swift binary targets."""
        out: dict[str, str] = {}
        for distribution in self.distributions:
            out.update(distribution.artifacts)
        return out

    def locked_gradle(self) -> GradleGraph:
        """The recorded Gradle graph, to resolve from on a subsequent build (§6.5)."""
        artifacts = []
        for coordinate, checksum in sorted(self.artifact_checksums().items()):
            try:
                module, version = coordinate.rsplit(":", 1)
                group, artifact = module.split(":")
            except ValueError:  # pragma: no cover - a hand-edited record
                continue
            artifacts.append(
                ResolvedArtifact(Module(group, artifact), version, checksum)
            )
        return GradleGraph(tuple(artifacts))

    def locked_swift(self) -> SwiftGraph:
        """The recorded Swift graph, versions **and** revisions (§7.4)."""
        packages = []
        for distribution in self.distributions:
            for name, recorded in sorted(distribution.swift.items()):
                version, _, revision = recorded.partition(" @ ")
                packages.append(
                    ResolvedSwiftPackage(
                        name=name,
                        url="",
                        kind="version",
                        version=version or None,
                        revision=revision or None,
                        declared_by=(distribution.name,),
                    )
                )
        return SwiftGraph(tuple(packages))


# --- building ---------------------------------------------------------------


def _attributes(permission) -> str:
    """§6.7's optional attributes, shown so a review sees what was narrowed."""
    parts = []
    if permission.max_sdk_version is not None:
        parts.append(f"maxSdk {permission.max_sdk_version}")
    if permission.never_for_location:
        parts.append("neverForLocation")
    return f" [{', '.join(parts)}]" if parts else ""


def _entries(contribution: Contribution, resolution: NativeResolution) -> tuple[str, ...]:
    out: list[str] = []

    for permission in contribution.permissions:
        reason = f'  ("{permission.reason}")' if permission.reason else ""
        if permission.suppressed:
            out.append(f"permission {permission.name} (suppressed by application)")
        else:
            out.append(f"permission {permission.name}{_attributes(permission)}{reason}")

    for feature in contribution.features:
        out.append(f"feature {feature.name} (required=false)")

    for entry in contribution.components:
        state = "exported" if entry.exported else "not exported"
        out.append(f"component {entry.kind} {entry.name} ({state})")
        for link in entry.view_links:
            out.append(f"  view_link {entry.name}: {link.render()}")
        for action in entry.actions:
            out.append(f"  intent_filter {entry.name}: {action}")

    for meta in contribution.meta_data:
        suffix = " (application override)" if meta.overridden_by_application else ""
        out.append(f"meta-data {meta.key} = {meta.value}{suffix}")

    for target, reason in contribution.queries:
        out.append(f"queries {target}  (\"{reason}\")")

    for delivery in contribution.plist_deliveries:
        suffix = " (application override)" if delivery.overridden_by_application else ""
        out.append(f"info-plist {delivery.key} = {delivery.value}{suffix}")

    for identifier in contribution.skadnetwork_identifiers:
        out.append(f"skadnetwork {identifier}")

    for placeholder in contribution.placeholders:
        suffix = " (application override)" if placeholder.overridden_by_application else ""
        out.append(f"placeholder {placeholder.key} = {placeholder.value}{suffix}")

    for dependency in contribution.dependencies:
        artifact = resolution.gradle.find(dependency.module)
        if artifact is None:
            out.append(f"dependency {dependency.render()}")
        elif dependency.exact_version == artifact.version:
            out.append(f"dependency {artifact.coordinate}")
        else:
            out.append(
                f"dependency {dependency.module}  requested {dependency.requested} "
                f"→ resolved {artifact.version}"
            )

    for entry in contribution.repositories:
        scope = ", ".join(entry.repository.scope)
        line = f"REPOSITORY {entry.repository.url} → {scope}"
        if entry.repository.credentials_required:
            line += (
                "  authenticated — "
                + ("credentials configured" if entry.credentials_configured else "no credentials")
            )
        out.append(line)

    for pattern in contribution.keep_patterns:
        out.append(f"keep {pattern}")

    for package in contribution.swift_packages:
        resolved = next(
            (p for p in resolution.swift.packages if p.name == package.name), None
        )
        if resolved is None:
            out.append(f"swift-package {package.render()}")
        else:
            out.append(
                f"swift-package {package.name} {package.url} "
                f"{resolved.version or resolved.kind} @ {resolved.revision or 'unrecorded'}"
            )

    for module in contribution.python_modules:
        out.append(
            f"python-module {module.name} ← {module.swift_package} ({module.init_symbol})"
        )

    for key in sorted(contribution.info_plist_values):
        out.append(f"plist {key} = {contribution.info_plist_values[key]!r}")
    for key in sorted(contribution.info_plist_append):
        values = list(contribution.info_plist_append[key])
        out.append(f"plist-append {key} += {values!r}")

    for path in contribution.source_files:
        out.append(f"source {path}")

    for status in contribution.prerequisites:
        if status.satisfied:
            continue
        # §7.3 rule 5: a conditional prerequisite that is unsatisfied is
        # recorded and does not fail the build. A log line scrolls past; the
        # whole value of a conditional prerequisite is that it survives to be
        # read later.
        state = "conditional, unresolved" if status.prerequisite.conditional else "NOT SATISFIED"
        out.append(
            f"requires {status.prerequisite.kind.value} {status.prerequisite.key} ({state})"
        )

    for finding in resolution.artifact_findings:
        if normalize_name(finding.distribution) != normalize_name(contribution.distribution):
            continue
        out.append(f"from {finding.artifact} (resolved artifact manifest): {finding.kind} {finding.detail}")

    return tuple(out)


def build(
    effective: EffectiveSet,
    resolution: NativeResolution,
    *,
    contract: str,
) -> IntegrationRecord:
    """Step 1 of §9's lifecycle, in serializable form."""
    distributions = []
    claimed: set[str] = set()
    ordered = sorted(effective.contributions, key=lambda c: normalize_name(c.distribution))
    for contribution in ordered:
        artifacts = _artifacts_for(contribution, resolution.gradle)
        claimed.update(artifacts)
        swift = _swift_for(contribution, resolution.swift)
        swift_binaries = _swift_binaries_for(contribution, resolution.swift)
        distributions.append(
            DistributionRecord(
                name=contribution.distribution,
                version=contribution.version,
                origin=contribution.origin.render(),
                contract=contribution.contract,
                inputs=dict(contribution.inputs),
                entries=_entries(contribution, resolution),
                artifacts=artifacts,
                swift=swift,
                swift_binaries=swift_binaries,
            )
        )

    # §6.5 and §7.4 lock the **fully resolved graph, transitives included**. A
    # transitive nobody declared directly belongs to no distribution's record on
    # the rule above, so it is filed against the first distribution that
    # declared any dependency — recorded exactly once, and stably, because the
    # order is normalized distribution name.
    orphans = {
        artifact.coordinate: artifact.checksum
        for artifact in resolution.gradle.artifacts
        if artifact.coordinate not in claimed
    }
    if orphans:
        for index, contribution in enumerate(ordered):
            if contribution.dependencies:
                merged = {**distributions[index].artifacts, **orphans}
                distributions[index] = replace(distributions[index], artifacts=merged)
                break

    orphan_packages = {
        package.name: f"{package.version or package.kind} @ {package.revision or 'unrecorded'}"
        for package in resolution.swift.packages
        if not any(package.name in d.swift for d in distributions)
    }
    if orphan_packages:
        for index, contribution in enumerate(ordered):
            if contribution.swift_packages:
                merged = {**distributions[index].swift, **orphan_packages}
                distributions[index] = replace(distributions[index], swift=merged)
                break

    return IntegrationRecord(
        platform=effective.platform.value, contract=contract, distributions=tuple(distributions)
    )


def _artifacts_for(contribution: Contribution, graph: GradleGraph) -> dict[str, str]:
    """The resolved graph, transitives included, recorded against its declarer.

    A transitive nobody declared directly is attributed to the first declaring
    distribution in normalized order, so it is recorded exactly once and the
    record stays stable across runs.
    """
    if not contribution.dependencies:
        return {}
    declared = {d.module for d in contribution.dependencies}
    out: dict[str, str] = {}
    for artifact in graph.artifacts:
        if artifact.module in declared or normalize_name(contribution.distribution) in {
            normalize_name(d) for d in artifact.declared_by
        }:
            out[artifact.coordinate] = artifact.checksum
    return out


def _swift_for(contribution: Contribution, graph: SwiftGraph) -> dict[str, str]:
    if not contribution.swift_packages:
        return {}
    names = {p.name for p in contribution.swift_packages}
    out: dict[str, str] = {}
    for package in graph.packages:
        if package.name in names or normalize_name(contribution.distribution) in {
            normalize_name(d) for d in package.declared_by
        }:
            out[package.name] = f"{package.version or package.kind} @ {package.revision or 'unrecorded'}"
    return out


def _swift_binaries_for(contribution: Contribution, graph: SwiftGraph) -> dict[str, str]:
    """§7.4 — record what a package's revision does not pin."""
    if not contribution.swift_packages:
        return {}
    names = {p.name for p in contribution.swift_packages}
    out: dict[str, str] = {}
    for package in graph.packages:
        owned = package.name in names or normalize_name(contribution.distribution) in {
            normalize_name(d) for d in package.declared_by
        }
        if not owned:
            continue
        for target in package.binary_targets:
            if target.checksum is not None:
                out[f"{package.name}/{target.name}"] = target.checksum
    return out


# --- comparison -------------------------------------------------------------


@dataclass(frozen=True)
class Delta:
    """What changed since the last accepted record."""

    new_distributions: tuple[str, ...] = ()
    gone_distributions: tuple[str, ...] = ()
    added: tuple[tuple[str, str], ...] = ()
    removed: tuple[tuple[str, str], ...] = ()
    changed_inputs: tuple[tuple[str, str], ...] = ()
    changed_artifacts: tuple[tuple[str, str], ...] = ()

    @property
    def empty(self) -> bool:
        return not (
            self.new_distributions
            or self.gone_distributions
            or self.added
            or self.removed
            or self.changed_inputs
            or self.changed_artifacts
        )

    def render(self) -> str:
        lines: list[str] = []
        by_distribution: dict[str, list[str]] = {}
        for distribution, entry in self.added:
            by_distribution.setdefault(distribution, []).append(f"  + {entry}")
        for distribution, entry in self.removed:
            by_distribution.setdefault(distribution, []).append(f"  − {entry}")
        for distribution, path in self.changed_inputs:
            by_distribution.setdefault(distribution, []).append(f"  ~ {path} changed")
        for distribution, coordinate in self.changed_artifacts:
            by_distribution.setdefault(distribution, []).append(f"  ! {coordinate} checksum changed")
        for distribution in sorted(by_distribution):
            marker = "  (new)" if distribution in self.new_distributions else ""
            lines.append(f"{distribution}{marker}")
            lines.extend(sorted(by_distribution[distribution]))
        for distribution in self.gone_distributions:
            lines.append(f"{distribution}  (no longer in the dependency closure)")
        return "\n".join(lines)


def compare(previous: IntegrationRecord | None, current: IntegrationRecord) -> Delta:
    """Step 2 of §9's lifecycle. ``previous`` of ``None`` makes everything new."""
    previous_names = {normalize_name(d.name) for d in (previous.distributions if previous else ())}
    current_names = {normalize_name(d.name) for d in current.distributions}

    added: list[tuple[str, str]] = []
    removed: list[tuple[str, str]] = []
    changed_inputs: list[tuple[str, str]] = []
    changed_artifacts: list[tuple[str, str]] = []

    for distribution in current.distributions:
        before = previous.get(distribution.name) if previous else None
        old_entries = set(before.entries) if before else set()
        new_entries = set(distribution.entries)
        added.extend((distribution.name, e) for e in sorted(new_entries - old_entries))
        removed.extend((distribution.name, e) for e in sorted(old_entries - new_entries))

        old_inputs = dict(before.inputs) if before else {}
        for path, digest in sorted(distribution.inputs.items()):
            if path in old_inputs and old_inputs[path] != digest:
                changed_inputs.append((distribution.name, path))

        old_artifacts = {**(dict(before.artifacts) if before else {}),
                         **(dict(before.swift_binaries) if before else {})}
        current_hashes = {**distribution.artifacts, **distribution.swift_binaries}
        for coordinate, checksum in sorted(current_hashes.items()):
            if coordinate in old_artifacts and old_artifacts[coordinate] != checksum:
                changed_artifacts.append((distribution.name, coordinate))

    gone = []
    for distribution in previous.distributions if previous else ():
        if normalize_name(distribution.name) not in current_names:
            gone.append(distribution.name)
            removed.extend((distribution.name, e) for e in sorted(set(distribution.entries)))

    new = [d.name for d in current.distributions if normalize_name(d.name) not in previous_names]

    return Delta(
        new_distributions=tuple(sorted(new)),
        gone_distributions=tuple(sorted(gone)),
        added=tuple(added),
        removed=tuple(removed),
        changed_inputs=tuple(changed_inputs),
        changed_artifacts=tuple(changed_artifacts),
    )


def report(record: IntegrationRecord, *, prerequisites: Iterable[str] = ()) -> str:
    """§9's report: the distribution, how it entered the closure, and the delta.

    The middle element matters most for the case that motivates the
    requirement — a transitive dependency the application author has never
    heard of.
    """
    lines: list[str] = []
    for distribution in record.distributions:
        lines.append(f"{distribution.name} {distribution.version}  ({distribution.origin})")
        for entry in distribution.entries:
            marker = "!" if entry.startswith(("REPOSITORY", "requires")) else "+"
            lines.append(f"  {marker} {entry}")
    lines.extend(prerequisites)
    return "\n".join(lines)
