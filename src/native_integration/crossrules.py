"""Rules that are not properties of any single sidecar.

Ownership is only meaningful across distributions: a namespace claim is
exclusive, a component class can be registered once, a Python module name can
be registered once, and two repositories may not contest the same coordinates.
Each of these fails **naming both** distributions, and none of them may be
resolved by file or copy order.
"""

from __future__ import annotations

from typing import Sequence

from . import naming, rules
from .diagnostics import DiagnosticBag
from .discovery import normalize_name
from .model import Sidecar


def check(sidecars: Sequence[Sidecar], *, bag: DiagnosticBag) -> None:
    ordered = sorted(sidecars, key=lambda s: normalize_name(s.distribution))
    _namespaces(ordered, bag)
    _components(ordered, bag)
    _repositories(ordered, bag)
    _python_modules(ordered, bag)
    _plist_values(ordered, bag)


def _namespaces(sidecars: Sequence[Sidecar], bag: DiagnosticBag) -> None:
    """§6.1 rule 5 — two distributions claiming overlapping namespaces fail, naming both."""
    claims: list[tuple[str, str]] = [
        (sidecar.distribution, namespace)
        for sidecar in sidecars
        if sidecar.android
        for namespace in sidecar.android.java_namespaces
    ]
    for index, (first_dist, first) in enumerate(claims):
        for second_dist, second in claims[index + 1 :]:
            if first_dist == second_dist:
                continue
            if naming.overlaps(first, second):
                bag.add(
                    rules.NAMESPACE_OVERLAP,
                    f"`{first}` ({first_dist}) and `{second}` ({second_dist}) overlap; a "
                    "Java namespace is an exclusive claim and the conflict must not be "
                    "resolved by file or copy order",
                    first_dist,
                    second_dist,
                )


def _components(sidecars: Sequence[Sidecar], bag: DiagnosticBag) -> None:
    """§6.8 — two distributions registering the same component class fail, naming both."""
    owners: dict[str, str] = {}
    for sidecar in sidecars:
        if not sidecar.android:
            continue
        for component in sidecar.android.components:
            previous = owners.get(component.name)
            if previous is not None and previous != sidecar.distribution:
                bag.add(
                    rules.COMPONENT_DUPLICATE,
                    f"both register the manifest component `{component.name}`",
                    previous,
                    sidecar.distribution,
                )
            else:
                owners[component.name] = sidecar.distribution


def _repositories(sidecars: Sequence[Sidecar], bag: DiagnosticBag) -> None:
    """§6.6 — overlapping scopes at different URLs are rejected.

    Gradle searches repositories in declaration order and takes a module's
    artifacts from the first repository that has its metadata, so an overlap
    makes the source of an artifact depend on declaration order rather than on
    anything either sidecar said. The same URL declared twice is not a conflict.
    """
    declared: list[tuple[str, str, frozenset[str]]] = [
        (sidecar.distribution, repository.url, frozenset(repository.scope))
        for sidecar in sidecars
        if sidecar.android
        for repository in sidecar.android.gradle_repositories
    ]
    for index, (first_dist, first_url, first_scope) in enumerate(declared):
        for second_dist, second_url, second_scope in declared[index + 1 :]:
            if first_url == second_url:
                continue
            contested = sorted(first_scope & second_scope)
            if not contested:
                continue
            bag.add(
                rules.REPOSITORY_SCOPE_OVERLAP,
                ", ".join(contested) + " may resolve from two repositories",
                first_dist,
                second_dist,
                detail=(f"{first_dist}  →  {first_url}", f"{second_dist}  →  {second_url}"),
            )


def _python_modules(sidecars: Sequence[Sidecar], bag: DiagnosticBag) -> None:
    """§7.7 — two distributions registering the same module name fail, naming both."""
    owners: dict[str, str] = {}
    for sidecar in sidecars:
        if not sidecar.ios:
            continue
        for module in sidecar.ios.python_modules:
            previous = owners.get(module.name)
            if previous is not None and previous != sidecar.distribution:
                bag.add(
                    rules.PYTHON_MODULE_DUPLICATE,
                    f"both register the Python module `{module.name}`",
                    previous,
                    sidecar.distribution,
                )
            else:
                owners[module.name] = sidecar.distribution


def _plist_values(sidecars: Sequence[Sidecar], bag: DiagnosticBag) -> None:
    """§7.6 — two distributions setting one scalar key to different values fail.

    A key an `application_values` entry delivers to (§7.3) is consumer-managed,
    so a *contribution* of the same key collides with it here rather than
    silently losing to whichever ran last. The delivered value itself is not
    known until the application answers, so the collision is on the key.
    """
    delivered: dict[str, str] = {}
    for sidecar in sidecars:
        if not sidecar.ios:
            continue
        for prerequisite in sidecar.ios.prerequisites:
            if prerequisite.info_plist_key:
                delivered.setdefault(prerequisite.info_plist_key, sidecar.distribution)

    setters: dict[str, tuple[str, object]] = {}
    for sidecar in sidecars:
        if not sidecar.ios:
            continue
        for key in sidecar.ios.info_plist_values:
            owner = delivered.get(key)
            if owner is not None:
                bag.add(
                    rules.PLIST_VALUE_CONFLICT,
                    f"contributes Info.plist `{key}`, which an application value "
                    "already delivers to; one key has one source",
                    owner,
                    sidecar.distribution,
                )
        for key, value in sidecar.ios.info_plist_values.items():
            previous = setters.get(key)
            if previous is None:
                setters[key] = (sidecar.distribution, value)
            elif previous[1] != value:
                bag.add(
                    rules.PLIST_VALUE_CONFLICT,
                    f"set Info.plist `{key}` to different values "
                    f"({previous[1]!r} and {value!r})",
                    previous[0],
                    sidecar.distribution,
                )
