"""Finding sidecars (§3), and the two ways to get that wrong.

Iteration, not lookup: every entry in the group is read and the entry-point
*name* is ignored, because a name-keyed lookup silently skips any distribution
that labelled it differently. And nothing is imported, ever — not even the
module the entry point names. The value is spelled as a module reference so the
metadata stays truthful to the entry-points specification; this reads the named
directory's *files*.

The candidate set is the application's resolved dependency closure. It is an
input here rather than something this library computes, because the closure is
resolved for the **target platform**, which the consuming build tool knows and
a desktop interpreter does not. Requirement 1 says so in terms — markers and
extras are evaluated "for the target platform and Python version, never for the
build host" — so there is deliberately no constructor here that walks what
happens to be installed. A prohibition is discharged by having no code that can
violate it, and a convenience that resolves against this interpreter is exactly
the code that can.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Iterable, Mapping

from .contract import ENTRY_POINT_GROUP
from .findings import Findings
from .resources import SIDECAR_NAME, SidecarSource

#: §8.4, by number. Everything discovery can fail on is one of two obligations:
#: a distribution declaring more than one entry (2), and a resource that cannot
#: be materialized or read (4).
ONE_ENTRY = 2
UNREADABLE = 4

_MODULE_REFERENCE = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*\Z")


def normalize_name(name: str) -> str:
    """PEP 503 normalization, so ``Py_Stripe`` and ``py-stripe`` are one name."""
    return re.sub(r"[-_.]+", "-", name).lower()


@dataclass(frozen=True)
class Origin:
    """How a distribution entered the dependency closure (§3.2, §9).

    ``via`` names the producer's immediate dependents — at least, per §3.2 —
    and is sorted, so any path reported is deterministic across runs.
    """

    direct: bool = False
    via: tuple[str, ...] = ()

    def render(self) -> str:
        if self.direct:
            return "direct dependency"
        if self.via:
            return "via " + ", ".join(self.via)
        return "in the dependency closure"


@dataclass(frozen=True)
class Closure:
    """The application's resolved dependency closure for the target platform."""

    members: Mapping[str, Origin] = field(default_factory=dict)
    #: §3.2's allowance: a consumer operating in an isolated environment
    #: containing exactly the closure may treat all installed distributions as
    #: candidates.
    isolated: bool = False

    @classmethod
    def direct(cls, *names: str) -> "Closure":
        return cls({normalize_name(n): Origin(direct=True) for n in names})

    @classmethod
    def of(cls, members: Mapping[str, Origin]) -> "Closure":
        return cls({normalize_name(k): v for k, v in members.items()})

    @classmethod
    def isolated_environment(cls) -> "Closure":
        return cls({}, isolated=True)

    def contains(self, name: str) -> bool:
        return self.isolated or normalize_name(name) in self.members

    def origin(self, name: str) -> Origin:
        return self.members.get(normalize_name(name), Origin())

    def __contains__(self, name: str) -> bool:  # pragma: no cover - convenience
        return self.contains(name)


def _entry_points(dist: metadata.Distribution) -> list[metadata.EntryPoint]:
    return [ep for ep in dist.entry_points if ep.group == ENTRY_POINT_GROUP]


def discover(
    *,
    closure: Closure,
    findings: Findings,
    distributions: Iterable[metadata.Distribution] | None = None,
) -> list[SidecarSource]:
    """Every sidecar in the closure, as readable sources.

    A distribution outside the closure is skipped in silence: a debugging tool
    that happens to be installed beside the application, and happens to ship a
    sidecar, must not configure it — and is not an error either.
    """
    found: list[SidecarSource] = []
    seen: set[str] = set()

    for dist in distributions if distributions is not None else metadata.distributions():
        name = dist.metadata["Name"]
        if not name:  # pragma: no cover - malformed installs exist
            continue
        key = normalize_name(name)
        if key in seen:
            continue
        entries = _entry_points(dist)
        if not entries:
            continue
        seen.add(key)

        if not closure.contains(name):
            continue

        if len(entries) > 1:
            findings.requirement(
                ONE_ENTRY,
                name,
                message=(
                    f"declares {len(entries)} entries in {ENTRY_POINT_GROUP} "
                    f"({', '.join(sorted(e.name for e in entries))}); a consumer must "
                    "not select one or merge them"
                ),
            )
            continue

        source = locate(dist, entries[0].value, findings=findings)
        if source is not None:
            found.append(source)

    return sorted(found, key=lambda s: normalize_name(s.distribution))


def locate(
    dist: metadata.Distribution, value: str, *, findings: Findings
) -> SidecarSource | None:
    """Turn an entry-point value into a readable sidecar directory.

    The dotted path is interpreted as a directory within the distribution —
    ``mypkg._native`` → ``mypkg/_native/`` — and reached through the
    distribution's metadata/file-resource interface, never by assuming a
    conventional ``site-packages`` layout.
    """
    name = dist.metadata["Name"]
    if ":" in value or not _MODULE_REFERENCE.match(value.strip()):
        findings.requirement(
            UNREADABLE,
            name,
            message=(
                f"entry-point value {value!r} is not an importable module reference — "
                "a dotted path of Python identifiers, with no `:attr` suffix"
            ),
        )
        return None

    module = value.strip()
    relative = module.replace(".", "/")
    try:
        located = dist.locate_file(relative)
    except Exception as exc:  # pragma: no cover - loader dependent
        findings.requirement(
            UNREADABLE,
            name,
            message=f"the resources of `{module}` could not be materialized: {exc}",
        )
        return None

    root = Path(str(located))
    if not root.is_dir():
        findings.requirement(
            UNREADABLE,
            name,
            message=f"entry point names `{module}`, but {root} is not a readable directory",
        )
        return None
    if not (root / SIDECAR_NAME).exists():
        findings.requirement(
            UNREADABLE,
            name,
            message=f"entry point names `{module}`, which contains no {SIDECAR_NAME}",
        )
        return None

    return SidecarSource(
        distribution=name,
        version=dist.version or "",
        module=module,
        root=root,
        package_relpath=relative,
    )


def source_from_path(
    root: Path | str, *, distribution: str, version: str = "", module: str = ""
) -> SidecarSource:
    """A sidecar source for a directory on disk.

    For tests, for a producer checking its own sidecar before publishing, and
    for the worked examples in this repository — none of which are installed
    distributions.
    """
    path = Path(root)
    return SidecarSource(
        distribution=distribution,
        version=version,
        module=module or f"{distribution.replace('-', '_')}._native",
        root=path,
        package_relpath=module.replace(".", "/") if module else "",
    )
