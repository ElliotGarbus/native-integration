"""What the reader reports, and the two ids each report carries.

A finding names the obligation it answers to — `ni.req.<n>`, or `ni.adv.<Sn>`
for §8.5 — and, where the registry defines one, the precise id of the rule that
failed. `conformance/README.md` states the pairing: the requirement id says
which obligation went unmet, the precise id says which rule, and an author
repairing a sidecar wants the second.

Requirement 18 — *name the contributing distribution in every diagnostic* — is
discharged by the constructor rather than by remembering it at each call site.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Mapping, Sequence

from . import obligations
from .registry import Registry

BLOCKING = "blocking"
ADVISORY = "advisory"


@dataclass(frozen=True)
class Finding:
    """One report, attributed to the distributions it concerns."""

    obligation: str
    distributions: tuple[str, ...]
    message: str
    section: str
    severity: str
    rule: str | None = None
    where: str = ""
    detail: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.distributions:
            raise ValueError(
                f"{self.obligation}: a finding must name the distribution it "
                "concerns (requirement 18)"
            )
        if any(not name for name in self.distributions):
            raise ValueError(f"{self.obligation}: distribution names must be non-empty")

    @property
    def identifiers(self) -> tuple[str, ...]:
        """Every id this finding is reported under, most specific first."""
        return ((self.rule,) if self.rule else ()) + (self.obligation,)

    @property
    def blocking(self) -> bool:
        return self.severity == BLOCKING

    def render(self) -> str:
        who = ", ".join(self.distributions)
        head = f"[{self.severity}] {who}: {self.message}"
        tail = f"  (§{self.section}, {', '.join(self.identifiers)})"
        lines = [head + tail]
        if self.where:
            lines.append(f"    at {self.where}")
        lines.extend(f"    {line}" for line in self.detail)
        return "\n".join(lines)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.render()


@dataclass
class Findings:
    """Findings in the order they were made, and the registry that names them.

    Every constructor resolves its id through the registry, so a finding cannot
    cite an id no generator emits.
    """

    registry: Registry
    items: list[Finding] = field(default_factory=list)

    def _add(
        self,
        *,
        obligation: str,
        distributions: Sequence[str],
        message: str,
        section: str,
        severity: str,
        rule: str | None,
        where: str,
        detail: Iterable[str],
    ) -> Finding:
        found = Finding(
            obligation=obligation,
            distributions=tuple(dict.fromkeys(distributions)),
            message=message,
            section=section,
            severity=severity,
            rule=rule,
            where=where,
            detail=tuple(detail),
        )
        self.items.append(found)
        return found

    def rule(
        self,
        identifier: str,
        *distributions: str,
        message: str = "",
        where: str = "",
        detail: Iterable[str] = (),
    ) -> Finding:
        """A finding for a check the registry names, with its requirement."""
        about = self.registry.about(identifier)
        number = obligations.for_identifier(identifier, self.registry)
        return self._add(
            obligation=self.registry.requirement_id(number),
            distributions=distributions,
            message=message or str(about["summary"]),
            section=str(about["section"]),
            severity=str(about["severity"]),
            rule=identifier,
            where=where,
            detail=detail,
        )

    def requirement(
        self,
        number: int,
        *distributions: str,
        message: str = "",
        where: str = "",
        detail: Iterable[str] = (),
    ) -> Finding:
        """A finding for a rule the registry defines no precise id for."""
        identifier = self.registry.requirement_id(number)
        about = self.registry.about(identifier)
        return self._add(
            obligation=identifier,
            distributions=distributions,
            message=message or str(about["summary"]),
            section=str(about["section"]),
            severity=str(about["severity"]),
            rule=None,
            where=where,
            detail=detail,
        )

    def advisory(
        self,
        code: str,
        *distributions: str,
        message: str = "",
        where: str = "",
        detail: Iterable[str] = (),
    ) -> Finding:
        """A §8.5 obligation. Reported, never blocking."""
        identifier = self.registry.advisory_id(code)
        about = self.registry.about(identifier)
        return self._add(
            obligation=identifier,
            distributions=distributions,
            message=message or str(about["summary"]),
            section=str(about["section"]),
            severity=ADVISORY,
            rule=None,
            where=where,
            detail=detail,
        )

    # -- views -------------------------------------------------------------

    @property
    def blocking(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.items if f.blocking)

    @property
    def advisories(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.items if not f.blocking)

    @property
    def ok(self) -> bool:
        return not self.blocking

    def for_distribution(self, name: str) -> tuple[Finding, ...]:
        return tuple(f for f in self.items if name in f.distributions)

    def _reported(self, source: Iterable[Finding]) -> list[dict[str, Any]]:
        """Findings as `{id, distributions}`, one entry per id.

        Two findings citing one id are one report naming both distributions:
        §6.1's collision is a single failure between two producers, and a
        consumer that reported it twice would still have to name both.
        """
        named: dict[str, list[str]] = {}
        for found in source:
            for identifier in found.identifiers:
                seen = named.setdefault(identifier, [])
                seen.extend(d for d in found.distributions if d not in seen)
        return [
            {"id": identifier, "distributions": sorted(named[identifier])}
            for identifier in sorted(named)
        ]

    def as_diagnostics(self) -> list[dict[str, Any]]:
        return self._reported(self.blocking)

    def as_advisories(self) -> list[dict[str, Any]]:
        return self._reported(self.advisories)

    def __iter__(self) -> Iterator[Finding]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def render(self) -> str:
        return "\n".join(found.render() for found in self.items)


def where(path: Sequence[Any]) -> str:
    """A document path as an author would point at it."""
    rendered = ""
    for step in path:
        if isinstance(step, int):
            rendered += f"[{step}]"
        else:
            rendered += f".{step}" if rendered else str(step)
    return rendered
