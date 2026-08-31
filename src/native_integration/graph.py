"""The resolved native graph, and what it brings with it (§6.3, §6.7, §7.2, §9.4, §9.7).

None of this is expressible by shipping sidecars. §9.4 binds a consumer to what
a resolved artifact *declares* — permissions, features and components in an
`.aar`'s own manifest — and §7.2 puts its strongest check on the resolved graph
rather than on the declaration, because the offending package is one a producer
never named. So the graph is an input here, stated by whoever resolved it.

**What §9.4 offers is attribution and review, not restriction.** The gates in
§§5–7 bind only what a sidecar declares, and a producer that puts the same
material in a Maven artifact bypasses all of them. Policing arbitrary library
code is not attempted and would not succeed; making it visible is.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .application import Application
from .findings import Findings
from .integration import Resolved
from .recording import Record, digest, normalize_name

#: §8.4, by number.
KEEP = 31
UNPINNABLE = 33
FEATURE = 41
COLLISION = 44

#: §9.7's closed list: a file **directly** under `META-INF/`, never one in a
#: subdirectory of it, whose name is one of these. Everything else there — a
#: `META-INF/services/…` registration above all — is code by any useful
#: definition, and dropping one copy silently removes an implementation the
#: losing library registered.
METADATA_NAMES = frozenset(
    {"MANIFEST.MF", "INDEX.LIST", "DEPENDENCIES",
     "LICENSE", "LICENSE.txt", "LICENSE.md",
     "NOTICE", "NOTICE.txt", "NOTICE.md"}
)
METADATA_SUFFIXES = (".SF", ".DSA", ".RSA", ".EC")


def is_packaging_metadata(path: str) -> bool:
    """§9.7's closed list, and not the `META-INF/` prefix."""
    head, separator, name = path.partition("/")
    if head != "META-INF" or not separator or "/" in name:
        return False
    if name.endswith(METADATA_SUFFIXES):
        return True
    stem = name.split("-", 1)[0] if "-" in name else name
    return name in METADATA_NAMES or (
        stem in METADATA_NAMES and f"{stem}-" in name
    )


@dataclass(frozen=True)
class Artifact:
    """One resolved Maven artifact, as the resolver reported it."""

    coordinate: str
    sha256: str
    declared_by: str
    transitive: bool = False
    files: tuple[str, ...] = ()
    classes: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    features: tuple[tuple[str, bool], ...] = ()
    components: tuple[tuple[str, bool], ...] = ()

    @property
    def module(self) -> str:
        return self.coordinate.rsplit(":", 1)[0]

    @property
    def version(self) -> str:
        return self.coordinate.rsplit(":", 1)[-1]


@dataclass(frozen=True)
class Package:
    """One resolved Swift package. `path` and `branch` are what §7.2 rejects."""

    url: str
    declared_by: str
    version: str = ""
    revision: str = ""
    transitive: bool = False
    path: str = ""
    branch: str = ""
    binary_targets: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Graph:
    """A stated resolution. Empty means the consumer was told nothing."""

    artifacts: tuple[Artifact, ...] = ()
    packages: tuple[Package, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.artifacts or self.packages)


def graph_of(raw: Mapping[str, Any]) -> Graph:
    """A `resolved.toml`, as the corpus and a build tool's own resolver spell it."""
    return Graph(
        artifacts=tuple(
            Artifact(
                coordinate=str(entry["coordinate"]),
                sha256=str(entry.get("sha256", "")),
                declared_by=str(entry.get("declared_by", "")),
                transitive=bool(entry.get("transitive", False)),
                files=tuple(entry.get("files", ())),
                classes=tuple(entry.get("classes", ())),
                permissions=tuple(p["name"] for p in entry.get("permission", ())),
                features=tuple(
                    (f["name"], bool(f.get("required", False)))
                    for f in entry.get("feature", ())
                ),
                components=tuple(
                    (c["name"], bool(c.get("exported", False)))
                    for c in entry.get("component", ())
                ),
            )
            for entry in raw.get("artifact", ())
        ),
        packages=tuple(
            Package(
                url=str(entry["url"]),
                declared_by=str(entry.get("declared_by", "")),
                version=str(entry.get("version", "")),
                revision=str(entry.get("revision", "")),
                transitive=bool(entry.get("transitive", False)),
                path=str(entry.get("path", "")),
                branch=str(entry.get("branch", "")),
                binary_targets=tuple(
                    (b["name"], b["checksum"]) for b in entry.get("binary_target", ())
                ),
            )
            for entry in raw.get("package", ())
        ),
    )


def check(
    graph: Graph,
    resolved: Sequence[Resolved],
    *,
    application: Application,
    findings: Findings,
    record: Record,
    platform: str,
    date: str = "",
) -> None:
    """Every obligation the graph carries, and the facts it adds to the record."""
    if platform == "android":
        _artifacts(graph, record)
        _declared(graph, application, findings, record, date)
        _keeps(graph, resolved, findings)
        _collisions(graph, application, findings, record, date)
    else:
        _packages(graph, resolved, findings, record)


# -- §6.3: the locked graph --------------------------------------------------


def _artifacts(graph: Graph, record: Record) -> None:
    for artifact in graph.artifacts:
        record.add(
            "dist", normalize_name(artifact.declared_by), "artifact", artifact.coordinate,
            sha256=digest(artifact.sha256),
            transitive=True if artifact.transitive else None,
        )


def resolved_versions(graph: Graph) -> Mapping[str, str]:
    """What each declared module actually became, for `resolved=` on its fact.

    Only the artifacts a sidecar named: a transitive one is in the graph under
    its own coordinate and answers to no declaration.
    """
    return {
        artifact.module: artifact.version
        for artifact in graph.artifacts
        if not artifact.transitive
    }


# -- §9.4: what a resolved artifact declares ---------------------------------


def _declared(
    graph: Graph,
    application: Application,
    findings: Findings,
    record: Record,
    date: str,
) -> None:
    """Attribution to the *artifact*, which is the whole point of §9.4.

    The `dist` subject says which distribution pulled it in. A `required="true"`
    feature is the category-1 half: an artifact must not silently make hardware
    mandatory, because a device without it stops being able to install the
    application at all.
    """
    for artifact in graph.artifacts:
        subject = normalize_name(artifact.declared_by)
        for permission in artifact.permissions:
            record.add(
                "dist", subject, "artifact-declares", artifact.coordinate,
                "permission", permission,
            )
        for component, exported in artifact.components:
            record.add(
                "dist", subject, "artifact-declares", artifact.coordinate,
                "component", component, exported=exported,
            )
        for feature, required in artifact.features:
            record.add(
                "dist", subject, "artifact-declares", artifact.coordinate,
                "feature", feature, required=required,
            )
            if not required:
                continue
            decision = application.artifact_feature(feature)
            if decision is None or not decision.keep:
                findings.requirement(
                    FEATURE,
                    artifact.declared_by,
                    message=(
                        f"`{artifact.coordinate}` declares `{feature}` as required, "
                        "and the application has not decided"
                    ),
                    where=artifact.coordinate,
                    detail=[
                        "a required feature removes the application from Play for "
                        "every device without the hardware",
                        "the application decides whether to keep it required or "
                        "relax it to optional",
                    ],
                )
                continue
            record.add(
                "decision", "artifact-feature", feature,
                artifact=artifact.coordinate,
                date=decision.date or date or None,
                distribution=subject,
                keep=decision.keep,
            )


# -- §6.7: a keep pattern against what the dependency actually contains ------


def _glob(pattern: str) -> re.Pattern[str]:
    """§6.7's patterns are R8's: `**` crosses package separators, `*` does not."""
    out = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**", index):
            out.append(".*")
            index += 2
        elif pattern[index] == "*":
            out.append("[^.]*")
            index += 1
        else:
            out.append(re.escape(pattern[index]))
            index += 1
    return re.compile(r"\A" + "".join(out) + r"\Z")


def _keeps(graph: Graph, resolved: Sequence[Resolved], findings: Findings) -> None:
    """"A listing of archive contents, not a parser" — §6.7 says so in as many words.

    A dependency keep names the artifact whose classes it may hold, and the
    pattern is rejected where it matches a class from outside it. The stray
    class is the point: a keep wider than its dependency defeats shrinking for
    whoever else happens to sit under the same package name.
    """
    by_module: dict[str, Artifact] = {a.module: a for a in graph.artifacts}
    for entry in resolved:
        keeps = entry.sidecar.section("contributes", "r8").get("keep", [])
        if not isinstance(keeps, list):
            continue
        for keep in keeps:
            if not isinstance(keep, dict):
                continue
            pattern, named = keep.get("pattern"), keep.get("from_dependency")
            if not isinstance(pattern, str) or not isinstance(named, str):
                continue
            matcher = _glob(pattern)
            stray = sorted(
                {
                    class_name
                    for module, artifact in by_module.items()
                    if module != named
                    for class_name in artifact.classes
                    if matcher.match(class_name)
                }
            )
            if not stray:
                continue
            findings.requirement(
                KEEP,
                entry.sidecar.distribution,
                message=(
                    f"the keep pattern `{pattern}` matches a class "
                    f"`{named}` does not ship"
                ),
                where="android.contributes.r8.keep",
                detail=[f"`{name}`" for name in stray],
            )


# -- §9.7: two artifacts, one packaged path ----------------------------------


def _collisions(
    graph: Graph,
    application: Application,
    findings: Findings,
    record: Record,
    date: str,
) -> None:
    """The producers cannot see the collision; the consumer is the only party that can.

    Packaging metadata a consumer may settle itself, by a rule that does not
    depend on resolution order, and must record that it did. Anything else — a
    service-loader registration, a native library — it must not choose silently.
    """
    where: dict[str, list[Artifact]] = {}
    for artifact in graph.artifacts:
        for path in artifact.files:
            where.setdefault(path, []).append(artifact)

    for path, carrying in sorted(where.items()):
        distributions = {normalize_name(a.declared_by) for a in carrying}
        # §9.7 collides artifacts "from **different distributions**": one
        # distribution's own two artifacts are its business.
        if len(carrying) < 2 or len(distributions) < 2:
            continue
        artifacts = sorted(a.coordinate for a in carrying)
        chosen = application.packaging_choice(path)

        if chosen is not None:
            decided, winner, when = "application", chosen.artifact, chosen.date
        elif is_packaging_metadata(path):
            # §9.7 fixes no rule, so two conforming consumers may keep different
            # copies. The corpus elides `chosen` on a consumer-decided line for
            # exactly that reason; this one keeps the first coordinate in sorted
            # order, which does not depend on resolution order.
            decided, winner, when = "consumer", artifacts[0], date
        else:
            findings.requirement(
                COLLISION,
                *sorted(a.declared_by for a in carrying),
                message=f"two artifacts carry `{path}`, and the application has not chosen",
                where=path,
                detail=[
                    "carried by " + ", ".join(f"`{c}`" for c in artifacts),
                    "not packaging metadata, so a consumer may not settle it itself",
                ],
            )
            continue

        record.add(
            "decision", "collision", path,
            artifacts=artifacts,
            chosen=winner,
            date=when or None,
            decided=decided,
            distributions=sorted(distributions),
        )


# -- §7.2: the resolved Swift graph ------------------------------------------


def _packages(
    graph: Graph, resolved: Sequence[Resolved], findings: Findings, record: Record
) -> None:
    """§7.2's strongest check is here rather than on the declaration.

    A path or branch dependency anywhere in the graph is rejected, however
    cleanly the sidecar that pulled it in is written — the offending package is
    one the producer never named, and only the resolved graph reveals it.
    """
    from .integration import _requirement_of

    # A resolved package carries what was asked for beside what arrived, which
    # is the pair a reviewer compares. The join is the `url`, as it is in §7.2.
    requested = {
        str(declaration.get("url")): _requirement_of(declaration)
        for entry in resolved
        for declaration in entry.sidecar.entries("contributes", "swift_packages")
    }

    for package in graph.packages:
        unpinnable = [
            f"{label} `{value}`"
            for label, value in (("path", package.path), ("branch", package.branch))
            if value
        ]
        if unpinnable:
            findings.requirement(
                UNPINNABLE,
                package.declared_by,
                message=f"`{package.url}` resolves through an unpinnable dependency",
                where=package.url,
                detail=[
                    *unpinnable,
                    "a build resolving through it is not reproducible, and the "
                    "sidecar that pulled it in never named it",
                ],
            )
            continue
        record.add(
            "dist", normalize_name(package.declared_by), "package", package.url,
            requested=requested.get(package.url),
            revision=package.revision,
            version=package.version,
            transitive=True if package.transitive else None,
        )
        for name, checksum in package.binary_targets:
            record.add(
                "dist", normalize_name(package.declared_by), "binary-target", name,
                checksum=digest(checksum),
            )


