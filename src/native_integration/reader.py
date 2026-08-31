"""The whole read, in the order the specification puts it.

Each stage below is a section of the document rather than a stage of a
pipeline someone designed, and the order is the one §4.3 fixes: nothing is
interpreted before the contract is checked, nothing closure-wide is decided
before every sidecar has been read, and nothing is compared against the last
accepted record until there is a resolution to compare.

What this does **not** do is generate anything. A consumer is a build tool and
this is not one: it reads, validates, resolves and records, and hands the
result to whatever writes the Gradle files or the Xcode project.

That boundary is why the conformance corpus reports six of its case runs as
*unverified* against this reader rather than passed. Every one is an assertion
about generated output — that the sidecar stayed out of the payload, that a
view-link's attributes were written through to the manifest, that a feature
decision reached it, that the Python module stubs were excluded, that the
categories were linked. The harness asks for a manifest or a payload to
inspect, there is none, and *unverified* is the honest answer to a question
about output nobody here produces. Passing them would take a build tool, not a
better reader.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

from . import acceptance, advisories, document, graph as graphs, integration, semantics
from .application import Application
from .discovery import Closure
from .findings import Finding, Findings
from .graph import Graph
from .integration import Resolved
from .recording import Record
from .registry import PLATFORMS, load as load_registry
from .resources import SidecarSource


class UnimplementedProfile(ValueError):
    """Asked to build for a platform this consumer's profile set omits (§8.1).

    Requirement 9's second sentence: a consumer **MUST** fail "rather than
    building partially" when the platform is one whose conformance profile it
    does not implement. §8.1 makes conformance per-platform on purpose, so an
    Android-only tool is a conforming consumer — and the way it stays one is by
    refusing iOS outright rather than reading iOS sidecars with half the rules.

    Raised rather than reported. Every other failure in this library is a
    finding, because every other failure is something a sidecar or an
    application did and the report is how a person learns of it. This one is
    the consumer's own configuration, known before a single sidecar is read,
    and there is no distribution to attribute it to. A caller that ignores
    `Integration.ok` would build partially anyway; a caller that never gets an
    `Integration` cannot.
    """


class IntegrationError(Exception):
    """Raised by :meth:`Integration.raise_for_errors`."""

    def __init__(self, findings: Sequence[Finding]) -> None:
        self.findings = tuple(findings)
        super().__init__(
            f"{len(self.findings)} blocking finding"
            f"{'' if len(self.findings) == 1 else 's'}:\n"
            + "\n".join(found.render() for found in self.findings)
        )


@dataclass(frozen=True)
class Integration:
    """One resolved integration: what it found, and what it concluded."""

    platform: str
    record: Record
    findings: Findings
    resolved: tuple[Resolved, ...] = ()
    delta: acceptance.Delta = field(default_factory=acceptance.Delta)

    @property
    def ok(self) -> bool:
        """Whether the build may proceed."""
        return self.findings.ok

    def report(self) -> str:
        return self.findings.render()

    def raise_for_errors(self) -> None:
        if not self.ok:
            raise IntegrationError(self.findings.blocking)


def read(
    sources: Iterable[SidecarSource],
    *,
    platform: str,
    application: Application | None = None,
    closure: Closure | None = None,
    graph: Graph | None = None,
    accepted: str | None = None,
    contract: str = "1.0",
    profiles: Sequence[str] = PLATFORMS,
) -> Integration:
    """Read every sidecar and resolve them into one integration.

    `sources` is what discovery found. `closure` says how each distribution
    entered, which the record carries and requirement 1 turns on. `graph` is a
    resolution the consumer already performed — §9.4's obligations are about
    what a resolved artifact declares, so without one those go unchecked rather
    than guessed at. `accepted` is the last accepted record; absent one this is
    a first build, which §9.1 gates exactly as it gates a change, and which
    `application.initial_acceptance` is how an application passes.

    `profiles` names the §8.1 conformance profiles the calling consumer
    implements. It defaults to both because this reader implements both; a tool
    that generates only Gradle passes `("android",)` and gets
    :class:`UnimplementedProfile` for anything else, which is requirement 9's
    "fail, rather than building partially".
    """
    if platform not in profiles:
        raise UnimplementedProfile(
            f"this consumer does not implement the {platform!r} conformance "
            f"profile (it implements {', '.join(sorted(profiles)) or 'none'}); "
            "§8.1 makes conformance per-platform, and requirement 9 requires "
            "failing here rather than building part of it"
        )

    application = application or Application()
    closure = closure or Closure.isolated_environment()
    graph = graph or Graph()

    findings = Findings(load_registry())
    record = Record()
    integration.build_facts(record, contract=contract, platform=platform)

    resolved: list[Resolved] = []
    for source in sources:
        # §3.2 again, in case a caller assembled `sources` by hand: a
        # distribution outside the closure is skipped in silence.
        if not closure.contains(source.distribution):
            continue
        origin = closure.origin(source.distribution)
        parsed = document.read(
            source, platform=platform, findings=findings, origin=origin.render()
        )
        if parsed is None:
            continue
        resolved.append(
            integration.resolve(
                parsed,
                application=application,
                findings=findings,
                record=record,
                origin="direct" if origin.direct else "transitive",
                via=origin.via,
                resolved_versions=graphs.resolved_versions(graph),
            )
        )

    semantics.check(
        resolved,
        application=application,
        findings=findings,
        record=record,
        platform=platform,
    )
    advisories.report(
        resolved, application=application, findings=findings, platform=platform
    )
    integration.decisions(
        resolved, application=application, findings=findings, record=record
    )
    graphs.check(
        graph,
        resolved,
        application=application,
        findings=findings,
        record=record,
        platform=platform,
        date=application.date,
    )
    delta = acceptance.check(
        record,
        accepted,
        findings=findings,
        application=application,
        distributions=[source.distribution for source in sources],
    )

    return Integration(
        platform=platform,
        record=record,
        findings=findings,
        resolved=tuple(resolved),
        delta=delta,
    )
