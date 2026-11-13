"""§8.5's obligations: reported, never blocking.

An advisory is a **SHOULD** rather than a **MUST**, and §8.5 says why the
distinction is worth keeping: each of these makes a real failure legible, and
none of them can be required of a consumer whose build system cannot reach the
information. So a consumer implements the ones it can and says which — claiming
an advisory it does not offer is how a conformance claim overstates itself.

These are the ones a reader can offer. They are all derivable from the sidecars
and the application's answers, which is the whole of what this library sees.
The rest of §8.5 needs a linked binary (S10, S15), a merged manifest (S11), a
resolved `.aar`'s contents (S6, S12) or SwiftPM's own conflict reporting (S14),
and this reader vouches for none of them.

:func:`claimed` is the list, and it names S1 as well, which `structure.py`
reports while walking the registry. The list is what a consumer declares; the
module that holds each branch is an implementation detail of this one.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from .application import Application
from .findings import Findings
from .integration import Resolved

#: §6.6: the one foreground-service type the platform exempts from a permission.
EXEMPT_SERVICE_TYPES = frozenset({"shortService"})


def report(
    resolved: Sequence[Resolved],
    *,
    application: Application,
    findings: Findings,
    platform: str,
) -> None:
    if platform != "android":
        return
    _namespaces(resolved, findings)
    _permission_reasons(resolved, findings)
    _suppressions(resolved, application, findings)
    _repositories(resolved, findings)
    _foreground_services(resolved, findings)


def _namespaces(resolved: Sequence[Resolved], findings: Findings) -> None:
    """S5: a single-label owned namespace.

    `mypkg` is a claim on every class anyone puts directly under `mypkg`, which
    is not what the producer meant and is not theirs to hold.
    """
    for entry in resolved:
        for namespace in entry.owns:
            if "." in namespace:
                continue
            findings.advisory(
                "S5",
                entry.sidecar.distribution,
                message=f"`{namespace}` is a single-label namespace",
                where="android.owns.java_namespaces",
                detail=["a reverse-domain claim is the one nobody else will make"],
            )


def _permission_reasons(resolved: Sequence[Resolved], findings: Findings) -> None:
    """S7: a permission's `reason`, carried into the record and reported.

    The record already carries it. This is the other half — an application
    author reviewing what a transitive dependency asked for wants the producer's
    own sentence, not a permission name they must go and look up.
    """
    for entry in resolved:
        for permission in entry.sidecar.entries("contributes", "permissions"):
            name, reason = permission.get("name"), permission.get("reason")
            if not isinstance(name, str) or not isinstance(reason, str):
                continue
            findings.advisory(
                "S7",
                entry.sidecar.distribution,
                message=f"{name}: {reason}",
                where="android.contributes.permissions",
            )


def _suppressions(
    resolved: Sequence[Resolved], application: Application, findings: Findings
) -> None:
    """S8: an active suppression, visible in standing diagnostics.

    A suppression is a decision that keeps applying, and one made a year ago
    against a dependency that has since changed what it needs is exactly the
    thing nobody re-reads. Reporting it every build is what keeps it a decision.
    """
    withdrawn: dict[str, list[str]] = {}
    for entry in resolved:
        for permission in entry.sidecar.entries("contributes", "permissions"):
            name = permission.get("name")
            if isinstance(name, str) and application.suppression(name) is not None:
                withdrawn.setdefault(name, []).append(entry.sidecar.distribution)

    for name, distributions in sorted(withdrawn.items()):
        findings.advisory(
            "S8",
            *distributions,
            message=f"{name} is suppressed, and was asked for",
            where="android.contributes.permissions",
            detail=["the suppression applies to every contributor of the name"],
        )


def _repositories(resolved: Sequence[Resolved], findings: Findings) -> None:
    """S9: contributed repositories, surfaced every build.

    §6.4 calls a repository the most powerful thing a sidecar can contribute.
    One added through a transitive dependency is one nobody chose, and the
    standing report is where an application sees it is there at all.
    """
    for entry in resolved:
        for repository in entry.sidecar.entries("contributes", "gradle_repositories"):
            url = repository.get("url")
            if not isinstance(url, str):
                continue
            findings.advisory(
                "S9",
                entry.sidecar.distribution,
                message=f"{url} is a contributed Maven repository",
                where="android.contributes.gradle_repositories",
                detail=_scoped(repository) + _because(repository),
            )


def _scoped(repository) -> list[str]:
    bounds = [
        f"{label}: {', '.join(str(v) for v in values)}"
        for label, values in (
            ("groups", repository.get("groups") or ()),
            ("modules", repository.get("modules") or ()),
        )
        if values
    ]
    return bounds or ["unscoped"]


def _because(repository) -> list[str]:
    reason = repository.get("reason")
    return [str(reason)] if isinstance(reason, str) else []


def _foreground_services(resolved: Sequence[Resolved], findings: Findings) -> None:
    """S13: a foreground-service type with no permission to run it.

    Android requires a `FOREGROUND_SERVICE_*` permission matching the type, and
    the failure without one is a `SecurityException` at the moment the service
    starts — on a user's device, in the feature the service exists for.
    `shortService` is the exception the platform itself makes.
    """
    for entry in resolved:
        held = {
            permission.get("name")
            for permission in entry.sidecar.entries("contributes", "permissions")
        }
        if any(
            isinstance(name, str) and name.startswith("android.permission.FOREGROUND_SERVICE")
            for name in held
        ):
            continue
        for component in entry.sidecar.entries("contributes", "components"):
            kinds = _service_types(component.get("foreground_service_type"))
            wanting = [kind for kind in kinds if kind not in EXEMPT_SERVICE_TYPES]
            if not wanting:
                continue
            findings.advisory(
                "S13",
                entry.sidecar.distribution,
                message=(
                    f"`{component.get('name')}` runs as {', '.join(wanting)} and the "
                    "sidecar contributes no FOREGROUND_SERVICE_* permission"
                ),
                where="android.contributes.components",
                detail=[
                    "without one the service raises a SecurityException the moment "
                    "it starts, on a device, in the feature it exists for"
                ],
            )


def _service_types(declared: object) -> tuple[str, ...]:
    if isinstance(declared, str):
        return (declared,)
    if isinstance(declared, (list, tuple)):
        return tuple(kind for kind in declared if isinstance(kind, str))
    return ()


def claimed() -> Mapping[str, str]:
    """The advisory codes this reader offers, and the module reporting each.

    Declared rather than derived, because §8.5 is a **SHOULD** and what a
    consumer offers is a claim it makes, not a fact about its call graph. What
    is derived is the other direction: `tests/test_requirements.py` holds every
    code here to one the registry defines.

    S1 is `structure.py`'s and belongs on this list even though it is reported
    from the other side of the library: §4.4 makes an unrecognized top-level
    *table* a warning rather than a refusal — a future platform and a typo are
    indistinguishable from inside version 1 — and a consumer that reports it is
    offering the advisory whichever module holds the branch.
    """
    return {
        "S1": "structure",
        "S5": "advisories",
        "S7": "advisories",
        "S8": "advisories",
        "S9": "advisories",
        "S13": "advisories",
    }
