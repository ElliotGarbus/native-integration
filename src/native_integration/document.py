"""Reading one sidecar: parse, gate, then validate (§4.1, §4.2, §4.3, §4.5).

The order matters and is the specification's. §4.3 requires a consumer to reject
a sidecar declaring a contract it does not implement and says it "**MUST NOT**
parse such a sidecar partially" — so the gate runs before structural validation,
and a sidecar that fails it yields nothing at all rather than a half-read
document whose keys mean whatever version 2 says they mean.

Reading files is `resources.py`'s, and §4.1's containment and symlink rules are
enforced there so that no caller can reach a declared path without them.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from typing import Any, Mapping

from . import structure
from .contract import IMPLEMENTED, ContractVersion
from .findings import Findings
from .registry import PLATFORMS
from .resources import ResourceError, SidecarSource

#: §4.3's gate, §4.5's platform key, and the fail-closed rule, by number.
GATE = 7
PLATFORM_SUPPORT = 9
UNREADABLE = 4


@dataclass(frozen=True)
class Sidecar:
    """One distribution's sidecar, parsed and gated, for one platform."""

    distribution: str
    version: str
    source: SidecarSource
    document: Mapping[str, Any]
    contract: ContractVersion
    platform: str

    @property
    def table(self) -> Mapping[str, Any]:
        """The platform table this build reads, which may be absent."""
        held = self.document.get(self.platform)
        return held if isinstance(held, dict) else {}

    def section(self, *path: str) -> Mapping[str, Any]:
        cursor: Any = self.table
        for step in path:
            if not isinstance(cursor, dict):
                return {}
            cursor = cursor.get(step, {})
        return cursor if isinstance(cursor, dict) else {}

    def entries(self, *path: str) -> tuple[Mapping[str, Any], ...]:
        cursor: Any = self.table
        for step in path[:-1]:
            if not isinstance(cursor, dict):
                return ()
            cursor = cursor.get(step, {})
        if not isinstance(cursor, dict):
            return ()
        held = cursor.get(path[-1], [])
        if not isinstance(held, list):
            return ()
        return tuple(entry for entry in held if isinstance(entry, dict))


def read(
    source: SidecarSource,
    *,
    platform: str,
    findings: Findings,
    origin: str = "",
    implemented: ContractVersion = IMPLEMENTED,
) -> Sidecar | None:
    """Parse and validate one sidecar, or report why it cannot be read.

    Returns `None` when nothing further may be trusted: the file could not be
    read, it is not TOML, its `contract` is malformed, or it names a contract
    this reader does not implement.
    """
    document = _parse(source, findings)
    if document is None:
        return None

    declared = _gate(document, source, findings, implemented)
    if declared is None:
        return None

    structure.validate(
        document,
        platform=platform,
        distribution=source.distribution,
        findings=findings,
    )
    _under_declaration(document, declared, source, findings)
    _platform_support(document, platform, source, findings, origin)

    return Sidecar(
        distribution=source.distribution,
        version=source.version,
        source=source,
        document=document,
        contract=declared,
        platform=platform,
    )


def _parse(source: SidecarSource, findings: Findings) -> Mapping[str, Any] | None:
    try:
        raw = source.sidecar_bytes()
    except ResourceError as exc:
        findings.requirement(
            UNREADABLE,
            source.distribution,
            message=f"the sidecar could not be read: {exc.reason}",
            where=exc.relpath,
        )
        return None
    try:
        return tomllib.loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        findings.requirement(
            UNREADABLE, source.distribution, message="the sidecar is not UTF-8"
        )
        return None
    except tomllib.TOMLDecodeError as exc:
        # §4.2 makes the sidecar a TOML file and states no rule for one that is
        # not; requirement 4 is the obligation it falls under, being a resource
        # the consumer cannot read as what it is.
        findings.requirement(
            UNREADABLE, source.distribution, message=f"the sidecar is not valid TOML: {exc}"
        )
        return None


def _gate(
    document: Mapping[str, Any],
    source: SidecarSource,
    findings: Findings,
    implemented: ContractVersion,
) -> ContractVersion | None:
    """§4.3, in the order the section states it.

    The `contract` key's own shape is a registry check and carries its precise
    id. What the registry cannot state is the comparison against the consumer's
    own version, which no schema knows.
    """
    if "contract" not in document:
        findings.rule("ni.decl.contract.missing", source.distribution, where="contract")
        return None

    declared = document["contract"]
    if not isinstance(declared, str):
        findings.rule("ni.decl.contract.type", source.distribution, where="contract")
        return None
    try:
        version = ContractVersion.parse(declared)
    except ValueError:
        findings.rule(
            "ni.decl.contract.pattern",
            source.distribution,
            where="contract",
            detail=[
                f"`{declared}` is not a major, optionally with a minor",
                'the grammar is exact: "1.0.0", "01", "1." and " 1" are invalid',
            ],
        )
        return None

    if version.major != implemented.major or version.minor > implemented.minor:
        findings.requirement(
            GATE,
            source.distribution,
            message=(
                f"the sidecar needs contract {version.canonical}, and this reader "
                f"implements {implemented.canonical}"
            ),
            where="contract",
            detail=["the sidecar is not read further; a partial read would build "
                    "from a document nobody wrote"],
        )
        return None
    return version


def _under_declaration(
    document: Mapping[str, Any],
    declared: ContractVersion,
    source: SidecarSource,
    findings: Findings,
) -> None:
    """§4.3's third rule: using a capability newer than the contract named.

    Every v1 declaration is `since = "1.0"`, so nothing here can fire yet. It is
    written from `since` rather than from a list so that issuing 1.1 is a
    registry edit, which is the whole reason the field exists.
    """
    registry = findings.registry
    for platform in PLATFORMS:
        for node in registry.tree(platform).walk():
            since = node.get("since")
            if not since or not _reaches(document, node.path):
                continue
            needed = ContractVersion.parse(str(since))
            if needed > declared:
                findings.requirement(
                    GATE,
                    source.distribution,
                    message=(
                        f"`{node.id}` was introduced in contract {needed.canonical}, "
                        f"and the sidecar declares {declared.canonical}"
                    ),
                    where=".".join(node.path),
                )


def _reaches(document: Mapping[str, Any], path: tuple[str, ...]) -> bool:
    """Whether a declaration's path is present, through arrays of tables."""
    cursors: list[Any] = [document]
    for step in path:
        following: list[Any] = []
        for cursor in cursors:
            if isinstance(cursor, list):
                following.extend(
                    entry[step] for entry in cursor if isinstance(entry, dict) and step in entry
                )
            elif isinstance(cursor, dict) and step in cursor:
                following.append(cursor[step])
        if not following:
            return False
        cursors = following
    return True


def _platform_support(
    document: Mapping[str, Any],
    platform: str,
    source: SidecarSource,
    findings: Findings,
    origin: str,
) -> None:
    """§4.5: building for a platform `platforms` omits.

    No `platforms` key makes no claim, so this bites only where the key is
    present. The provenance matters as much as the failure: a transitive
    distribution is one the application author has never heard of, and a
    diagnostic naming only the package sends them looking.
    """
    declared = document.get("platforms")
    if not isinstance(declared, list) or platform in declared:
        return
    findings.requirement(
        PLATFORM_SUPPORT,
        source.distribution,
        message=f"the distribution does not support {platform}",
        where="platforms",
        detail=[
            line
            for line in (
                f"`platforms` names {', '.join(f'`{p}`' for p in declared) or 'nothing'}",
                f"it entered the closure {origin}" if origin else "",
            )
            if line
        ],
    )
