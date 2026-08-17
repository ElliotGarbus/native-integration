"""The whole read, in the order §9 prescribes.

``read()`` is the entry point a consuming build tool calls. It discovers,
parses, validates, applies the application's answers, resolves native
dependencies through the consumer's ports, computes the integration record,
compares it against the last accepted one, and refuses to proceed through an
unaccepted change — including the first build.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from . import crossrules, effective as effective_module, native, record as record_module, rules, sidecar as sidecar_module
from .context import Application, ConsumerProfile
from .diagnostics import Diagnostic, DiagnosticBag, IntegrationError
from .discovery import Closure, discover
from .effective import EffectiveSet
from .model import Platform, Sidecar
from .native import NativeResolution
from .ports import NO_RESOLVERS, Resolvers
from .record import Delta, IntegrationRecord
from .resources import SidecarSource


@dataclass(frozen=True)
class Integration:
    """Everything one read produced."""

    platform: Platform
    sidecars: tuple[Sidecar, ...]
    effective: EffectiveSet
    resolution: NativeResolution
    record: IntegrationRecord
    delta: Delta
    previous: IntegrationRecord | None
    diagnostics: DiagnosticBag = field(default_factory=DiagnosticBag)
    record_path: Path | None = None

    @property
    def ok(self) -> bool:
        return self.diagnostics.ok

    @property
    def errors(self) -> tuple[Diagnostic, ...]:
        return self.diagnostics.errors

    def raise_for_errors(self) -> None:
        self.diagnostics.raise_for_errors()

    def report(self) -> str:
        """The §9 report: distribution, how it entered the closure, and the delta."""
        body = record_module.report(self.record)
        if not self.delta.empty:
            body += "\n\nchanges since the last accepted record:\n" + self.delta.render()
        notes = [d.render() for d in self.diagnostics if not d.blocking]
        if notes:
            body += "\n\n" + "\n".join(notes)
        return body

    @property
    def gate_only(self) -> tuple[Diagnostic, ...]:
        """Blocking diagnostics other than the record gate itself.

        The record gate is the one blocking diagnostic acceptance is *supposed*
        to answer. Anything else means the surface being accepted is not one
        this application can build.
        """
        return tuple(
            d for d in self.errors if d.rule not in (rules.RECORD_ABSENT, rules.RECORD_DRIFT)
        )

    def accept(self, path: Path | str | None = None) -> Path:
        """Step 5 — update the record, only on acceptance.

        Refuses when the integration has blocking diagnostics beyond the record
        gate. A record is the statement *this is the native surface the
        application accepted and could build*; writing one for a surface with an
        unsupplied application value or an unapproved export would certify
        something untrue, and would leave the next build comparing against a
        baseline that was never valid.
        """
        blocking = self.gate_only
        if blocking:
            raise IntegrationError(blocking)
        target = Path(path) if path is not None else self.record_path
        if target is None:
            raise ValueError("no record path: pass one to accept() or to read()")
        return self.record.write(target)

    def payload_exclusions(self) -> tuple[str, ...]:
        return self.effective.python_payload_exclusions()


def read(
    *,
    platform: Platform | str,
    closure: Closure,
    application: Application,
    profile: ConsumerProfile | None = None,
    resolvers: Resolvers = NO_RESOLVERS,
    sources: Sequence[SidecarSource] | None = None,
    distributions: Iterable[object] | None = None,
    record_path: Path | str | None = None,
    previous: IntegrationRecord | None = None,
    accept_current_surface: bool = False,
) -> Integration:
    """Discover, validate and stage-plan the application's native integration.

    ``accept_current_surface=True`` says the application has explicitly approved
    whatever this read computes — a re-lock, a flag, a committed record,
    whichever the consumer's workflow uses (§9 leaves the form to the consumer).
    Without it, a first build or a changed one produces a blocking diagnostic
    rather than a silent write.

    It is spelled as an instruction rather than as ``accepted=True`` because
    that is what it is: not "this was accepted at some point" but "accept what
    you are about to compute". A consumer wiring it to a global flag is turning
    the review gate of §9 off, and the name should make that visible at the call
    site.
    """
    platform = Platform(platform) if isinstance(platform, str) else platform
    profile = profile or ConsumerProfile()
    bag = DiagnosticBag()

    if sources is None:
        sources = discover(closure=closure, bag=bag, distributions=distributions)  # type: ignore[arg-type]

    sidecars: list[Sidecar] = []
    for source in sources:
        parsed = sidecar_module.parse(source, platform=platform, profile=profile, bag=bag)
        if parsed is not None:
            sidecars.append(parsed)

    crossrules.check(sidecars, bag=bag)

    effective = effective_module.compute(
        sidecars,
        platform=platform,
        closure=closure,
        application=application,
        bag=bag,
    )

    if previous is None and record_path is not None:
        previous = IntegrationRecord.read(record_path)

    resolution = native.resolve(
        sidecars,
        platform=platform,
        application=application,
        resolvers=resolvers,
        previous_checksums=previous.checksums() if previous else {},
        locked_gradle=previous.locked_gradle() if previous else None,
        locked_swift=previous.locked_swift() if previous else None,
        bag=bag,
    )

    current = record_module.build(effective, resolution, contract=profile.contract.canonical)
    delta = record_module.compare(previous, current)

    if current.distributions and not accept_current_surface:
        _gate_record(previous, delta, current, bag)

    return Integration(
        platform=platform,
        sidecars=tuple(sidecars),
        effective=effective,
        resolution=resolution,
        record=current,
        delta=delta,
        previous=previous,
        diagnostics=bag,
        record_path=Path(record_path) if record_path is not None else None,
    )


def _gate_record(
    previous: IntegrationRecord | None,
    delta: Delta,
    current: IntegrationRecord,
    bag: DiagnosticBag,
) -> None:
    names = [d.name for d in current.distributions]
    if previous is None:
        bag.add(
            rules.RECORD_ABSENT,
            "no accepted integration record exists; the whole effective set needs explicit "
            "acceptance before the build proceeds — the first build is where an application "
            "acquires all of its inherited native surface at once",
            *names,
            detail=tuple(delta.render().splitlines()),
        )
        return
    if not delta.empty:
        touched = sorted(
            {d for d, _ in (*delta.added, *delta.removed, *delta.changed_inputs, *delta.changed_artifacts)}
            | set(delta.new_distributions)
            | set(delta.gone_distributions)
        )
        bag.add(
            rules.RECORD_DRIFT,
            "the native surface has changed since the last accepted integration record",
            *(touched or names),
            detail=tuple(delta.render().splitlines()),
        )


def check_sidecar(
    source: SidecarSource,
    *,
    platform: Platform | str,
    profile: ConsumerProfile | None = None,
) -> tuple[Sidecar | None, DiagnosticBag]:
    """Validate one sidecar in isolation.

    For a package author checking their own ``native.toml`` before publishing,
    and for tests. Cross-distribution rules cannot be checked from one sidecar
    and are not attempted here.
    """
    platform = Platform(platform) if isinstance(platform, str) else platform
    bag = DiagnosticBag()
    parsed = sidecar_module.parse(
        source, platform=platform, profile=profile or ConsumerProfile(), bag=bag
    )
    return parsed, bag


__all__ = ["Integration", "read", "check_sidecar", "IntegrationError"]
