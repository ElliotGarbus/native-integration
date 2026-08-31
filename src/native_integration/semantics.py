"""The rules no single sidecar can break (§5.2, §6.1, §6.3, §6.4, §6.7, §6.8, §7.5).

Each sidecar here is valid on its own. Only a consumer holding the whole closure
sees the conflict, and only it knows which Python distributions to name — Gradle
sees one module, the manifest shows one entry, and the application author sees a
build that works until the day the order changes.

That is why every rule below names *both* distributions. A diagnostic that named
the merged result would describe a symptom the author cannot act on: they do not
choose the manifest, they choose the dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .application import Application
from .findings import Findings
from .integration import Resolved

#: §8.4, by number.
OWNERSHIP = 23
CONFIGURATION = 25
REPOSITORY = 27
KEEP = 31
META_DATA = 32
VALUE_CONFLICT = 17
PYTHON_MODULE = 36

#: §6.1: the bootstrap namespaces of the known Python-mobile toolchains. The
#: list is consumer-independent so that one toolchain's runtime cannot be
#: clobbered because a different toolchain built the application — a consumer
#: defending only its own bootstrap is non-conforming even though its own builds
#: look fine.
RESERVED: tuple[str, ...] = (
    "org.kivy.android",
    "org.libsdl.app",
    "org.jnius",
    "org.renpy.android",
    "com.chaquo.python",
    "org.beeware.android",
)

#: §5.2's kinds that share a key space with a §6 or §7 contribution.
SHARED_KEY_SPACE: Mapping[str, str] = {
    "manifest_meta_data": "android",
    "info_plist": "ios",
}


def contains(outer: str, inner: str) -> bool:
    """§6.1's containment, on dot-separated segments and never on raw strings.

    So `org.kivy.android` contains `org.kivy.android.helpers` and does not
    contain `org.kivy.androidx`, and `PyGMA` does not contain `PyGMAKit`.
    """
    return inner == outer or inner.startswith(outer + ".")


def literal_prefix(pattern: str) -> str:
    """§6.7: the longest run of leading dot-separated segments with no wildcard.

    The truncation is deliberate. Stopping at the first wildcard segment rather
    than reasoning about what `org.example.my*` can match is what keeps this
    identical between two consumers.
    """
    kept: list[str] = []
    for segment in pattern.split("."):
        if "*" in segment or "?" in segment:
            break
        kept.append(segment)
    return ".".join(kept)


@dataclass(frozen=True)
class _Claim:
    """One thing a distribution declared, kept beside who declared it."""

    distribution: str
    value: Any
    where: str = ""


def check(
    resolved: Sequence[Resolved],
    *,
    application: Application,
    findings: Findings,
    platform: str,
    reserved: Iterable[str] = RESERVED,
) -> None:
    """Every closure-wide rule, over the sidecars that survived validation."""
    if platform == "android":
        _ownership(resolved, findings, tuple(reserved))
        _keep_patterns(resolved, findings)
        _configurations(resolved, findings)
        _repositories(resolved, findings)
        _meta_data(resolved, application, findings)
    else:
        _python_modules(resolved, findings)
    _values(resolved, application, findings, platform)


# -- §6.1: ownership ---------------------------------------------------------


def _ownership(
    resolved: Sequence[Resolved], findings: Findings, reserved: tuple[str, ...]
) -> None:
    """Rules 4 and 5, and the substitution they exist to close.

    A distribution shipping `org/kivy/android/PythonActivity.java` silently
    replaces the application's entry point; two distributions claiming one
    namespace let a consumer that resolves by order replace one producer's class
    with another's.
    """
    for entry in resolved:
        for namespace in entry.owns:
            occupied = [p for p in reserved if contains(p, namespace) or contains(namespace, p)]
            if occupied:
                findings.requirement(
                    OWNERSHIP,
                    entry.sidecar.distribution,
                    message=f"`{namespace}` is under a reserved prefix",
                    where="android.owns.java_namespaces",
                    detail=[
                        f"reserved: {', '.join(f'`{p}`' for p in occupied)}",
                        "a toolchain's bootstrap namespace is not claimable, whichever "
                        "toolchain built the application",
                    ],
                )

    for first, second in _pairs(resolved):
        overlapping = sorted(
            {
                (one, other)
                for one in first.owns
                for other in second.owns
                if contains(one, other) or contains(other, one)
            }
        )
        if not overlapping:
            continue
        findings.requirement(
            OWNERSHIP,
            first.sidecar.distribution,
            second.sidecar.distribution,
            message="two distributions claim overlapping Java namespaces",
            where="android.owns.java_namespaces",
            detail=[
                f"`{one}` and `{other}`" if one != other else f"both claim `{one}`"
                for one, other in overlapping
            ],
        )


def _keep_patterns(resolved: Sequence[Resolved], findings: Findings) -> None:
    """§6.1 rule 3, through §6.7's literal prefix.

    A keep rule applies to the whole program, so a pattern wider than the claim
    keeps classes the distribution never owned — another producer's, or the
    application's — and silently defeats shrinking for them.
    """
    for entry in resolved:
        patterns = entry.sidecar.section("contributes", "r8").get("keep_classes", [])
        if not isinstance(patterns, list):
            continue
        for pattern in patterns:
            if not isinstance(pattern, str):
                continue
            prefix = literal_prefix(pattern)
            if any(contains(namespace, prefix) for namespace in entry.owns):
                continue
            findings.requirement(
                KEEP,
                entry.sidecar.distribution,
                message=f"the keep pattern `{pattern}` is wider than any owned namespace",
                where="android.contributes.r8.keep_classes",
                detail=[
                    f"its literal prefix is `{prefix}`",
                    "owned: " + (", ".join(f"`{n}`" for n in entry.owns) or "nothing"),
                ],
            )


# -- §6.3: one module, two configurations ------------------------------------


def _configurations(resolved: Sequence[Resolved], findings: Findings) -> None:
    """§6.3's conservative rule, and why the obvious merge is wrong.

    `api` and `implementation` differ only in what they expose downstream, so a
    widest-wins merge would be defensible — and would put a dependency on the
    *application's* compile classpath because some transitive producer asked for
    `api`. The application then compiles against a library nobody chose to
    expose to it, and keeps compiling until that producer changes its mind.
    """
    declared: dict[str, list[_Claim]] = {}
    for entry in resolved:
        for dependency in entry.sidecar.entries("contributes", "gradle_dependencies"):
            coordinate = dependency.get("coordinate")
            module = (
                coordinate.rsplit(":", 1)[0]
                if isinstance(coordinate, str)
                else dependency.get("module")
            )
            if not isinstance(module, str):
                continue
            declared.setdefault(module, []).append(
                _Claim(
                    entry.sidecar.distribution,
                    dependency.get("configuration", "implementation"),
                )
            )

    for module, claims in sorted(declared.items()):
        chosen = {claim.value for claim in claims}
        if len(chosen) < 2:
            continue
        findings.requirement(
            CONFIGURATION,
            *(claim.distribution for claim in claims),
            message=f"`{module}` is declared with two different configurations",
            where="android.contributes.gradle_dependencies",
            detail=[f"{claim.distribution} asks for `{claim.value}`" for claim in claims],
        )


# -- §6.4: overlapping repository scopes -------------------------------------


def _scope(repository: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    groups = {g for g in repository.get("groups", []) or [] if isinstance(g, str)}
    modules = {m for m in repository.get("modules", []) or [] if isinstance(m, str)}
    return groups, modules


def _intersects(
    first: tuple[set[str], set[str]], second: tuple[set[str], set[str]]
) -> set[str]:
    """§6.4: some coordinate is admitted by both.

    The same group in `groups`, the same pair in `modules`, or a `modules` entry
    whose group another repository names in `groups`. Exact strings throughout —
    prefix matching is the difference between admitting one vendor's artifacts
    and admitting every group anyone can register beneath a name the repository
    does not own.
    """
    groups, modules = first
    other_groups, other_modules = second
    contested = (groups & other_groups) | (modules & other_modules)
    contested |= {m for m in modules if m.split(":", 1)[0] in other_groups}
    contested |= {m for m in other_modules if m.split(":", 1)[0] in groups}
    return contested


def _repositories(resolved: Sequence[Resolved], findings: Findings) -> None:
    """A repository is the most powerful thing a sidecar can contribute.

    Two both claiming `com.vendor` means a coordinate under that group can be
    served by either, and which one wins is a resolution-order accident — which
    is precisely the substitution dependency confusion is.
    """
    declared: list[tuple[str, str, tuple[set[str], set[str]]]] = []
    for entry in resolved:
        for repository in entry.sidecar.entries("contributes", "gradle_repositories"):
            url = repository.get("url")
            if isinstance(url, str):
                declared.append((entry.sidecar.distribution, url, _scope(repository)))

    for index, (distribution, url, scope) in enumerate(declared):
        for other, other_url, other_scope in declared[index + 1 :]:
            # Two distributions declaring the same repository is a merge, not a
            # conflict: §6.4 says so, and identity is the url.
            if _same_url(url, other_url):
                continue
            contested = _intersects(scope, other_scope)
            if not contested:
                continue
            findings.requirement(
                REPOSITORY,
                distribution,
                other,
                message="two contributed repositories have intersecting scopes",
                where="android.contributes.gradle_repositories",
                detail=[
                    f"`{url}` and `{other_url}`",
                    "contested: " + ", ".join(f"`{c}`" for c in sorted(contested)),
                ],
            )


def _same_url(one: str, other: str) -> bool:
    """§6.4: the scheme compared case-insensitively, the rest byte for byte."""
    def split(url: str) -> tuple[str, str]:
        scheme, separator, rest = url.partition("://")
        return (scheme.lower(), rest) if separator else ("", url)

    return split(one) == split(other)


# -- §5.2, §6.8, §7.4: one key, two declarations -----------------------------


def _values(
    resolved: Sequence[Resolved],
    application: Application,
    findings: Findings,
    platform: str,
) -> None:
    """§5.2: two values targeting the same `(kind, key)`.

    Equal content coalesces; different content fails naming both. There is no
    order-independent winner — whichever the consumer writes, the other
    producer's SDK reads a key configured for someone else.
    """
    targeted: dict[tuple[str, str], list[_Claim]] = {}
    for entry in resolved:
        for declaration in entry.sidecar.entries("requires", "application_value"):
            kind, key = declaration.get("kind"), declaration.get("key")
            identifier = declaration.get("id")
            if not isinstance(kind, str) or not isinstance(key, str):
                continue  # `inline` carries no key, and targets nothing shared
            supplied = application.value(entry.sidecar.distribution, str(identifier))
            if supplied is None:
                continue
            targeted.setdefault((kind, key), []).append(
                _Claim(entry.sidecar.distribution, supplied)
            )

    for (kind, key), claims in sorted(targeted.items()):
        if len({claim.value for claim in claims}) < 2:
            continue
        findings.requirement(
            VALUE_CONFLICT,
            *(claim.distribution for claim in claims),
            message=f"two values target `{key}` with different content",
            where=f"{platform}.requires.application_value",
            detail=[f"kind `{kind}`", "the supplied strings differ"],
        )


def _meta_data(
    resolved: Sequence[Resolved], application: Application, findings: Findings
) -> None:
    """§6.8: one manifest entry, and equality by type as well as content.

    "`1` and `"1"` are different declarations of one key and MUST fail, even
    though `android:value` would render them the same way." The clause exists
    for the consumer that compares the rendered manifest text: both produce
    `android:value="1"`, so merging after rendering sees agreement and coalesces,
    and the two producers who disagreed about the type both believe they won.
    """
    keyed: dict[str, list[_Claim]] = {}
    contributed: set[str] = set()
    for entry in resolved:
        for declaration in entry.sidecar.entries("contributes", "meta_data"):
            key, value = declaration.get("key"), declaration.get("value")
            if isinstance(key, str):
                contributed.add(key)
                keyed.setdefault(key, []).append(
                    _Claim(entry.sidecar.distribution, (_type_of(value), value))
                )
        # §6.8 and §5.2 share one key space: a `manifest_meta_data` delivery is
        # the same manifest entry. An application-supplied value is always a
        # string, so it coalesces only with a string.
        for declaration in entry.sidecar.entries("requires", "application_value"):
            if declaration.get("kind") != "manifest_meta_data":
                continue
            key = declaration.get("key")
            supplied = application.value(
                entry.sidecar.distribution, str(declaration.get("id"))
            )
            if isinstance(key, str) and supplied is not None:
                keyed.setdefault(key, []).append(
                    _Claim(entry.sidecar.distribution, ("string", supplied))
                )

    for key, claims in sorted(keyed.items()):
        # A key claimed only through §5.2 is a disagreement between two values,
        # which is requirement 17's and already reported. This rule is §6.8's,
        # and needs a `meta_data` contribution on at least one side of it.
        if key not in contributed or len(claims) < 2:
            continue
        if len({claim.value for claim in claims}) < 2:
            continue
        findings.requirement(
            META_DATA,
            *(claim.distribution for claim in claims),
            message=f"one `<meta-data>` key is declared two ways: `{key}`",
            where="android.contributes.meta_data",
            detail=[
                f"{claim.distribution} declares {claim.value[0]} {claim.value[1]!r}"
                for claim in claims
            ],
        )


def _type_of(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    return "string"


# -- §7.5: one importable name -----------------------------------------------


def _python_modules(resolved: Sequence[Resolved], findings: Findings) -> None:
    """§7.5: two distributions registering the same `name` fail, naming both.

    The package is linked into the application binary rather than loaded from a
    `.so`, so the ordinary import machinery never sees it. Two registrations for
    one name means one extension module is reachable and the other is not,
    decided by registration order, with both producers believing theirs is
    installed — and the failure is an `ImportError` on device, or worse, a
    successful import of the wrong module.
    """
    registered: dict[str, list[str]] = {}
    for entry in resolved:
        for module in entry.sidecar.entries("contributes", "python_modules"):
            name = module.get("name")
            if isinstance(name, str):
                registered.setdefault(name, []).append(entry.sidecar.distribution)

    for name, distributions in sorted(registered.items()):
        if len(distributions) < 2:
            continue
        findings.requirement(
            PYTHON_MODULE,
            *distributions,
            message=f"two distributions register the Python module `{name}`",
            where="ios.contributes.python_modules",
            detail=["one of them is reachable, decided by registration order"],
        )


def _pairs(resolved: Sequence[Resolved]):
    for index, first in enumerate(resolved):
        for second in resolved[index + 1 :]:
            yield first, second
