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
a desktop interpreter does not.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from . import rules
from .contract import ENTRY_POINT_GROUP
from .diagnostics import DiagnosticBag
from .resources import SIDECAR_NAME, SidecarSource

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
    #: Names :meth:`from_installed` walked to and could not find. A closure with
    #: anything here is incomplete, and a distribution that would have declared a
    #: sidecar may be missing from it — so it is reported rather than swallowed.
    missing: tuple[str, ...] = ()

    @classmethod
    def direct(cls, *names: str) -> "Closure":
        return cls({normalize_name(n): Origin(direct=True) for n in names})

    @classmethod
    def of(cls, members: Mapping[str, Origin]) -> "Closure":
        return cls({normalize_name(k): v for k, v in members.items()})

    @classmethod
    def isolated_environment(cls) -> "Closure":
        return cls({}, isolated=True)

    @classmethod
    def from_installed(
        cls, roots: Sequence[str], *, extras: Mapping[str, Sequence[str]] | None = None
    ) -> "Closure":
        """Walk ``Requires-Dist`` from ``roots`` over the *installed* distributions.

        A convenience for tools that build for the host, and a starting point
        for others. It needs ``packaging`` (``pip install native-integration[closure]``)
        to parse requirements and evaluate environment markers, and it resolves
        against this interpreter — which is not the target platform, so a real
        consumer should supply its own closure instead.
        """
        try:
            from packaging.requirements import Requirement  # noqa: PLC0415
        except ModuleNotFoundError as exc:  # pragma: no cover - depends on install
            raise RuntimeError(
                "Closure.from_installed() needs `packaging`; install "
                "native-integration[closure], or construct a Closure directly"
            ) from exc

        extras = {normalize_name(k): tuple(v) for k, v in (extras or {}).items()}
        origins: dict[str, Origin] = {}
        for root in roots:
            origins[normalize_name(root)] = Origin(direct=True)

        frontier = list(origins)
        dependents: dict[str, set[str]] = {}
        missing: list[str] = []
        while frontier:
            current = frontier.pop(0)
            try:
                dist = metadata.distribution(current)
            except metadata.PackageNotFoundError:
                # Not installed here, so its own requirements cannot be walked
                # and any sidecar it ships is invisible. Recorded rather than
                # swallowed: the caller is entitled to know the closure is
                # partial before it decides what may configure the build.
                missing.append(current)
                continue
            wanted = set(extras.get(current, ()))
            for raw in dist.metadata.get_all("Requires-Dist") or []:
                requirement = Requirement(raw)
                environment = {"extra": ""}
                if requirement.marker is not None:
                    if not any(
                        requirement.marker.evaluate({**environment, "extra": e})
                        for e in ("", *wanted)
                    ):
                        continue
                name = normalize_name(requirement.name)
                dependents.setdefault(name, set()).add(normalize_name(current))
                if name not in origins:
                    origins[name] = Origin()
                    frontier.append(name)

        return cls(
            {
                name: origin
                if origin.direct
                else Origin(via=tuple(sorted(dependents.get(name, ()))))
                for name, origin in origins.items()
            },
            missing=tuple(sorted(missing)),
        )

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
    bag: DiagnosticBag,
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
            bag.add(
                rules.MULTIPLE_ENTRY_POINTS,
                f"declares {len(entries)} entries in {ENTRY_POINT_GROUP} "
                f"({', '.join(sorted(e.name for e in entries))}); a consumer must not "
                "select one or merge them",
                name,
            )
            continue

        source = locate(dist, entries[0].value, bag=bag)
        if source is not None:
            found.append(source)

    return sorted(found, key=lambda s: normalize_name(s.distribution))


def locate(
    dist: metadata.Distribution, value: str, *, bag: DiagnosticBag
) -> SidecarSource | None:
    """Turn an entry-point value into a readable sidecar directory.

    The dotted path is interpreted as a directory within the distribution —
    ``mypkg._native`` → ``mypkg/_native/`` — and reached through the
    distribution's metadata/file-resource interface, never by assuming a
    conventional ``site-packages`` layout.
    """
    name = dist.metadata["Name"]
    if ":" in value or not _MODULE_REFERENCE.match(value.strip()):
        bag.add(
            rules.ENTRY_POINT_VALUE_INVALID,
            f"entry-point value {value!r} is not an importable module reference — a dotted "
            "path of Python identifiers, with no `:attr` suffix",
            name,
        )
        return None

    module = value.strip()
    relative = module.replace(".", "/")
    try:
        located = dist.locate_file(relative)
    except Exception as exc:  # pragma: no cover - loader dependent
        bag.add(
            rules.RESOURCE_UNREADABLE,
            f"the resources of `{module}` could not be materialized: {exc}",
            name,
        )
        return None

    root = Path(str(located))
    if not root.is_dir():
        bag.add(
            rules.RESOURCE_UNREADABLE,
            f"entry point names `{module}`, but {root} is not a readable directory",
            name,
        )
        return None
    if not (root / SIDECAR_NAME).exists():
        bag.add(
            rules.SIDECAR_MISSING,
            f"entry point names `{module}`, which contains no {SIDECAR_NAME}",
            name,
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
