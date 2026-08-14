"""Diagnostics, and the one property every diagnostic must have.

Requirement 8.15 — *name the contributing distribution in every diagnostic* —
is the reason this module exists as a type rather than as a logging call. A
:class:`Diagnostic` cannot be constructed without at least one distribution
name, so the requirement is discharged by the constructor rather than by the
author of each message remembering it.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Iterable, Iterator, Sequence


class Severity(enum.IntEnum):
    """How a diagnostic bears on the build.

    ``NOTE`` is not a lesser warning: §7.3 rule 5 and §9 both require material
    to be *recorded without failing the build*, and that is what a note is.
    """

    NOTE = 10
    WARNING = 20
    ERROR = 30

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name.lower()


@dataclass(frozen=True)
class Rule:
    """One enforceable obligation, declared once in :mod:`native_integration.rules`.

    ``requirements`` names the §8 requirement numbers the rule discharges, which
    is what makes the mapping in ``docs/REQUIREMENTS.md`` checkable rather than
    aspirational.
    """

    code: str
    section: str
    severity: Severity
    requirements: tuple[int, ...] = ()

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.code


class SpecViolation(Exception):
    """Raised when a caller asks for a result the specification forbids."""


class UnimplementedObligation(SpecViolation):
    """A consumer obligation this library cannot discharge alone, left unimplemented.

    Raised — never merely warned about — when a sidecar declares material whose
    validation needs something only the consuming build tool can supply (a
    resolved Gradle graph, an archive listing, a resolved ``.aar``'s manifest).
    Failing here is the point: a consumer that omits a port must not receive a
    clean result that looks like the rule was checked.
    """

    def __init__(self, message: str, *, requirements: Sequence[int] = (), section: str = "") -> None:
        self.requirements = tuple(requirements)
        self.section = section
        detail = ""
        if requirements:
            detail = f" (requirement{'s' if len(self.requirements) > 1 else ''} " + ", ".join(
                f"8.{n}" for n in self.requirements
            ) + ")"
        super().__init__(f"{message}{detail}")


class IntegrationError(SpecViolation):
    """Raised by ``raise_for_errors()`` when blocking diagnostics are present."""

    def __init__(self, diagnostics: Sequence["Diagnostic"]) -> None:
        self.diagnostics = tuple(diagnostics)
        body = "\n".join(f"  {d.render()}" for d in self.diagnostics)
        super().__init__(f"native integration failed:\n{body}")


@dataclass(frozen=True)
class Diagnostic:
    """A single finding, always attributed to the distribution(s) it concerns."""

    rule: Rule
    message: str
    distributions: tuple[str, ...]
    detail: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.distributions:
            raise ValueError(
                f"{self.rule.code}: a diagnostic must name the distribution it concerns "
                "(requirement 8.15)"
            )
        if any(not d for d in self.distributions):
            raise ValueError(f"{self.rule.code}: distribution names must be non-empty")

    @property
    def severity(self) -> Severity:
        return self.rule.severity

    @property
    def section(self) -> str:
        return self.rule.section

    @property
    def blocking(self) -> bool:
        return self.rule.severity is Severity.ERROR

    def render(self) -> str:
        who = ", ".join(self.distributions)
        head = f"[{self.severity}] {who}: {self.message}  ({self.section}, {self.rule.code})"
        return "\n".join([head, *(f"    {line}" for line in self.detail)])

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.render()


@dataclass
class DiagnosticBag:
    """Diagnostics collected in the order they were found.

    Validation collects rather than raising on the first problem: a build tool
    that reports one broken sidecar per run makes the application author fix
    them one at a time. ``raise_for_errors()`` is the fail-closed exit.
    """

    items: list[Diagnostic] = field(default_factory=list)

    def add(
        self,
        rule: Rule,
        message: str,
        *distributions: str,
        detail: Iterable[str] = (),
    ) -> Diagnostic:
        diagnostic = Diagnostic(rule, message, tuple(distributions), tuple(detail))
        self.items.append(diagnostic)
        return diagnostic

    def extend(self, other: Iterable[Diagnostic]) -> None:
        self.items.extend(other)

    @property
    def errors(self) -> tuple[Diagnostic, ...]:
        return tuple(d for d in self.items if d.severity is Severity.ERROR)

    @property
    def warnings(self) -> tuple[Diagnostic, ...]:
        return tuple(d for d in self.items if d.severity is Severity.WARNING)

    @property
    def notes(self) -> tuple[Diagnostic, ...]:
        return tuple(d for d in self.items if d.severity is Severity.NOTE)

    @property
    def ok(self) -> bool:
        return not self.errors

    def raise_for_errors(self) -> None:
        if self.errors:
            raise IntegrationError(self.errors)

    def for_distribution(self, name: str) -> tuple[Diagnostic, ...]:
        return tuple(d for d in self.items if name in d.distributions)

    def __iter__(self) -> Iterator[Diagnostic]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def render(self) -> str:
        return "\n".join(d.render() for d in self.items)
