"""What a sidecar means, once its shape is known (§5.2, §6.1, §6.3–§6.8, §7.5).

Most of this is the rules no single sidecar can break. Each is valid on its own,
and only a consumer holding the whole closure sees the conflict — Gradle sees one
module, the manifest shows one entry, and the application author sees a build
that works until the day the order changes. That is why those rules name *both*
distributions: a diagnostic naming the merged result describes a symptom the
author cannot act on, since they do not choose the manifest, they choose the
dependencies.

§6.1 is the exception and is here whole rather than split, because its five rules
are one subject. Rules 1 to 3 are answerable from a single sidecar — what it
staged, what it declared, what it claims to own — and rules 4 and 5 need the
closure. Separating them by which needs a neighbour would put the definition of
ownership in one file and half its consequences in another.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .application import Application, url_identity
from .findings import Findings
from .integration import Resolved
from .recording import Record
from .resources import ResourceError, normalize

#: §8.4, by number.
OWNERSHIP = 23
UNREADABLE = 4
SLOT = 22
CONFIGURATION = 25
REPOSITORY = 27
KEEP = 31
META_DATA = 32
PLIST = 35
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
    #: Whether the claim is an application's answer to a §5.2 value rather than
    #: something the sidecar itself declares. It counts for agreement and never
    #: for content: requirement 42 forbids writing an application-supplied
    #: secret into the record, and a supplied string is the one kind of claim
    #: here that could be one — `analytics_key` and `api_key` are what §5.2 is
    #: mostly used for. A producer's own declaration is public by construction.
    answer: bool = False


def check(
    resolved: Sequence[Resolved],
    *,
    application: Application,
    findings: Findings,
    record: Record,
    platform: str,
    reserved: Iterable[str] = RESERVED,
) -> None:
    """Every closure-wide rule, over the sidecars that survived validation.

    The record is here because two of §6 and §7's rules do not merely reject a
    closure — they merge one, and §6.5 and §7.4 both require the merged result
    to be recorded. Computing the merge to find the conflict and then computing
    it again elsewhere to write it down is how the two come to disagree.
    """
    if platform == "android":
        _ownership(resolved, findings, tuple(reserved))
        _contributed_files(resolved, findings)
        _component_names(resolved, findings)
        _keep_patterns(resolved, findings)
        _configurations(resolved, findings)
        _duplicate_modules(resolved, findings)
        _repositories(resolved, findings, record)
        _permissions(resolved, application, record)
        _meta_data(resolved, application, findings, record)
    else:
        _python_modules(resolved, findings)
        _info_plist(resolved, application, findings, record)
    _values(resolved, application, findings, platform)
    _slots(resolved, findings, platform)


# -- §6.1: ownership ---------------------------------------------------------


#: §6.1: "a path segment that is not a valid Java identifier ... since it cannot
#: name a package". Kotlin permits more in a backticked identifier; the rule is
#: stated over Java identifiers for both languages, and is what a package name
#: has to be to survive the round trip through a directory name.
IDENTIFIER = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")

#: The `package` a source file declares. Java terminates it with `;` and Kotlin
#: does not, so the terminator is optional. Anchored to a line start because a
#: `package` appearing anywhere else is not the declaration.
PACKAGE = re.compile(
    r"^[ \t]*package[ \t]+([A-Za-z_$][\w$]*(?:[ \t]*\.[ \t]*[A-Za-z_$][\w$]*)*)[ \t]*;?",
    re.M,
)

#: Comments, so that a commented-out `package` is not read as one. Strings are
#: not stripped: a `package` declaration cannot appear inside one at line start
#: in either language without the file already failing to compile.
COMMENTS = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)


def declared_package(text: str) -> str | None:
    """The package a Java or Kotlin file declares, or `None` for the default one."""
    found = PACKAGE.search(COMMENTS.sub(lambda m: "\n" * m.group(0).count("\n"), text))
    return re.sub(r"[ \t]+", "", found.group(1)) if found else None


def path_namespace(root: str, path: str) -> str:
    """§6.1's derivation: the file's directory, relative to its source root.

    `java/org/example/mypkg/Bridge.java` under root `java` yields
    `org.example.mypkg`, and a file directly in the root yields the empty
    string — the default package, which is contained by nothing.
    """
    prefix = f"{normalize(root)}/"
    inside = path[len(prefix):] if path.startswith(prefix) else path
    return ".".join(inside.split("/")[:-1])


def _contributed_files(
    resolved: Sequence[Resolved], findings: Findings
) -> None:
    """§6.1 rule 1, over every file staged from a declared source root.

    Two namespaces are derived per file and both are checked, which the note
    under the rule explains is not redundancy: `javac` enforces the
    correspondence between them and `kotlinc` does not, so a Kotlin file at
    `kotlin/org/example/mypkg/Bridge.kt` declaring `package org.other` compiles
    cleanly and lands a class outside the namespace its distribution claimed.
    Checking the path alone misses it; checking the declaration alone lets a
    file sit anywhere in the tree.

    Comparison is case-sensitive throughout, as the platform's own is.
    """
    for entry in resolved:
        owned = entry.owns
        for root, path in entry.staged:
            where = path
            derived = path_namespace(root, path)
            if not derived:
                _reject(findings, entry, where,
                        "sits directly in its source root, so its path names no package",
                        ["the default package is contained by nothing, and cannot be owned"])
                continue
            bad = [s for s in derived.split(".") if not IDENTIFIER.fullmatch(s)]
            if bad:
                _reject(findings, entry, where,
                        "has a path segment that cannot name a package",
                        [f"`{s}` is not a Java identifier" for s in bad])
                continue

            try:
                text = entry.sidecar.source.read_text(path)
            except ResourceError as problem:
                # §4.1's UTF-8 rule, reached here because the file is being read
                # rather than merely listed. Requirement 4's obligation, not
                # this one's, so it is reported as that.
                findings.requirement(
                    UNREADABLE, entry.sidecar.distribution,
                    message=f"a contributed source file {problem.reason}",
                    where=problem.relpath,
                )
                continue

            stated = declared_package(text)
            if stated is None:
                _reject(findings, entry, where,
                        "declares no `package`",
                        [f"its path says `{derived}`",
                         "the default package is contained by nothing"])
                continue
            if stated != derived:
                _reject(findings, entry, where,
                        "declares a `package` its path disagrees with",
                        [f"the path says `{derived}`", f"the file says `{stated}`",
                         "`kotlinc` compiles this cleanly, which is why the rule is "
                         "stated rather than left to the toolchain"])
                continue
            for namespace, source in ((derived, "its path"), (stated, "its `package`")):
                if not any(contains(owner, namespace) for owner in owned):
                    _reject(findings, entry, where,
                            f"is outside every namespace its distribution owns, by {source}",
                            [f"{source} says `{namespace}`",
                             "owned: " + (", ".join(f"`{n}`" for n in owned) or "nothing")])


def _reject(
    findings: Findings, entry: Resolved, where: str, what: str, detail: Sequence[str]
) -> None:
    findings.requirement(
        OWNERSHIP,
        entry.sidecar.distribution,
        message=f"`{where}` {what}",
        where=where,
        detail=detail,
    )


def _component_names(resolved: Sequence[Resolved], findings: Findings) -> None:
    """§6.1 rule 2: a producer-sourced component name is under an owned namespace.

    "A component attributed to a declared dependency is exempt; the class is not
    the producer's." That is the whole of the exemption — `from_dependency` says
    the class ships in someone else's artifact, and requiring the producer to own
    a namespace it does not write into would make the declaration unusable.
    """
    for entry in resolved:
        for component in entry.sidecar.entries("contributes", "components"):
            name = component.get("name")
            if not isinstance(name, str) or component.get("from_dependency"):
                continue
            if any(contains(owner, name) for owner in entry.owns):
                continue
            findings.requirement(
                OWNERSHIP,
                entry.sidecar.distribution,
                message=f"the component `{name}` is outside every namespace it owns",
                where="android.contributes.components",
                detail=[
                    "owned: " + (", ".join(f"`{n}`" for n in entry.owns) or "nothing"),
                    "a component from a declared dependency is exempt, and this one "
                    "declares no `from_dependency`",
                ],
            )


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
            module = _module_of(dependency)
            if module is None:
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


def _module_of(dependency: Mapping[str, Any]) -> str | None:
    """`group:artifact`, from either of §6.3's two forms."""
    coordinate = dependency.get("coordinate")
    if isinstance(coordinate, str):
        return coordinate.rsplit(":", 1)[0]
    module = dependency.get("module")
    return module if isinstance(module, str) else None


def _canonical(value: Any) -> Any:
    """A declaration in a form two of them can be compared by.

    §6.3's exception is "identical in **every** field", so the comparison is
    over the whole entry rather than over the fields this reader happens to
    read — a `version` table, a `configuration`, and anything a later minor
    adds. Nested tables and lists are ordered, because a producer writing the
    same two fields in the other order has written the same declaration.
    """
    if isinstance(value, Mapping):
        return tuple(sorted((key, _canonical(held)) for key, held in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_canonical(held) for held in value)
    return value


def _duplicate_modules(resolved: Sequence[Resolved], findings: Findings) -> None:
    """§6.3: "Within one sidecar, a module is declared once."

    Two entries naming the same `group:artifact` — "in either form, or one of
    each" — are rejected unless identical in every field, in which case the
    duplicate coalesces. §6.3 gives the reason for treating this differently
    from the cross-sidecar case one paragraph below it: "A producer
    contradicting itself is a mistake to report, not a composition to resolve,
    and it is the one duplicate case with a single author who can fix it."

    So this is per sidecar, and `_configurations` is not. Two distributions may
    name one module in two forms and Gradle selects between them; one
    distribution naming it twice has stated two versions of its own intent, and
    no resolver can tell which it meant.
    """
    for entry in resolved:
        declared: dict[str, list[Mapping[str, Any]]] = {}
        for dependency in entry.sidecar.entries("contributes", "gradle_dependencies"):
            module = _module_of(dependency)
            if module is not None:
                declared.setdefault(module, []).append(dependency)

        for module, entries in sorted(declared.items()):
            if len(entries) < 2:
                continue
            if len({_canonical(dependency) for dependency in entries}) == 1:
                continue  # identical in every field, so the duplicate coalesces
            findings.requirement(
                CONFIGURATION,
                entry.sidecar.distribution,
                message=f"`{module}` is declared more than once in one sidecar",
                where="android.contributes.gradle_dependencies",
                detail=[
                    "the entries differ, and a producer contradicting itself is a "
                    "mistake to report rather than a composition to resolve",
                    *(
                        "- "
                        + ", ".join(
                            f"{key} = {held!r}" for key, held in sorted(dependency.items())
                        )
                        for dependency in entries
                    ),
                ],
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


def _repositories(
    resolved: Sequence[Resolved], findings: Findings, record: Record
) -> None:
    """A repository is the most powerful thing a sidecar can contribute.

    Two both claiming `com.vendor` means a coordinate under that group can be
    served by either, and which one wins is a resolution-order accident — which
    is precisely the substitution dependency confusion is.

    Two declaring the same `url` is the opposite case, and §6.4 makes it a merge
    rather than a conflict: `groups` and `modules` union, and any
    `credentials_required = true` wins. That result is recorded, for §6.5's
    reason one section later — the merge widens what a repository may serve and
    can turn an open one authenticated, and a record holding only the two
    requests leaves a reviewer to work that out. Which is where it goes unworked.
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

    _merged_repositories(resolved, record)


def _merged_repositories(resolved: Sequence[Resolved], record: Record) -> None:
    """§6.4's table, applied. Identity is the url, and the rest unions.

    Grouped by the identity §6.4 fixes rather than by the string: the scheme is
    compared case-insensitively, so `HTTPS://` and `https://` are one
    repository, and the section forbids normalizing any further because a
    trailing path segment is a different repository.
    """
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in resolved:
        for repository in entry.sidecar.entries("contributes", "gradle_repositories"):
            url = repository.get("url")
            if not isinstance(url, str):
                continue
            identity = url_identity(url)
            groups, modules = _scope(repository)
            held = merged.setdefault(
                identity,
                {"distributions": set(), "groups": set(), "modules": set(),
                 "authenticated": False},
            )
            held["distributions"].add(entry.distribution)
            held["groups"] |= groups
            held["modules"] |= modules
            held["authenticated"] |= bool(repository.get("credentials_required"))

    for identity, held in sorted(merged.items()):
        # The identity, not the spelling either sidecar happened to use. The
        # per-distribution lines above record what each one declared, verbatim;
        # this one records the repository, and taking the first spelling seen
        # would make the record depend on the order the closure was read in.
        scheme, rest = identity
        record.add(
            "effective", "gradle-repository", f"{scheme}://{rest}" if scheme else rest,
            distributions=sorted(held["distributions"]),
            groups=sorted(held["groups"]) or None,
            modules=sorted(held["modules"]) or None,
            credentials_required=True if held["authenticated"] else None,
        )


def _same_url(one: str, other: str) -> bool:
    """§6.4: the scheme compared case-insensitively, the rest byte for byte."""
    return url_identity(one) == url_identity(other)


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


# -- §5.7: one surface, two claimants ----------------------------------------


def _slots(resolved: Sequence[Resolved], findings: Findings, platform: str) -> None:
    """§5.7: two actions claiming a surface the platform allows one of.

    The failure this catches is not a conflict anyone can see in a sidecar.
    §5.7's example is two push SDKs each asking the application to create a
    notification service extension: "nothing about either action alone reveals
    the conflict: each reads as a reasonable, self-contained request, and an
    application author acting on them one at a time creates two extension
    targets — which iOS does not run side by side — or overwrites one vendor's
    handler with the other's, and finds out only when that vendor's feature
    silently stops working."

    So the report has to arrive *before* the author starts, which is why it is
    made from the declarations rather than from anything they resolved to.

    The slot is compared for equality and never read. It is an opaque string,
    and the note under §5.7's table is explicit that a consumer treating those
    identifiers as a vocabulary would be interpreting them — equality can miss a
    collision between two producers who chose different spellings, and cannot
    invent one.
    """
    claimed: dict[str, list[_Claim]] = {}
    for entry in resolved:
        for action in entry.sidecar.entries("requires", "application_action"):
            slot, identifier = action.get("slot"), action.get("id")
            if isinstance(slot, str) and isinstance(identifier, str):
                claimed.setdefault(slot, []).append(
                    _Claim(entry.sidecar.distribution, identifier)
                )

    for slot, claims in sorted(claimed.items()):
        if len(claims) < 2:
            continue
        findings.requirement(
            SLOT,
            *(claim.distribution for claim in claims),
            message=f"two actions claim the slot `{slot}`",
            where=f"{platform}.requires.application_action",
            detail=[
                *(f"{claim.distribution} asks for it as `{claim.value}`" for claim in claims),
                "the platform allows one, and satisfying these one at a time "
                "silently leaves one of them broken",
            ],
        )


def _permissions(
    resolved: Sequence[Resolved], application: Application, record: Record
) -> None:
    """§6.5's merge, which the record has to carry rather than imply.

    "A consumer **MUST** register a permission with the widest need any
    distribution stated: an entry with no `max_sdk_version` defeats one that has
    it, a lower `max_sdk_version` gives way to a higher, and
    `never_for_location` holds only when **every** declaration of that
    permission asserts it. The result **MUST** appear in the record and report
    with the distributions that produced it."

    Both directions of the merge lose information a reviewer needs. A permission
    bounded to API 30 by one distribution and unbounded by another is registered
    unbounded, and the record that showed only the two requests would leave
    whoever reads it to work that out — which is the step where a widening gets
    missed, because the bounded declaration is the one that looks careful.

    A suppressed permission is absent entirely: §6.5 requires it to be absent
    from the effective merged manifest, and this is what the record says that
    manifest will contain.
    """
    declared: dict[str, list[_Claim]] = {}
    for entry in resolved:
        for permission in entry.sidecar.entries("contributes", "permissions"):
            name = permission.get("name")
            if isinstance(name, str):
                declared.setdefault(name, []).append(
                    _Claim(entry.distribution, permission)
                )

    for name, claims in sorted(declared.items()):
        if application.suppression(name) is not None:
            continue
        bounds = [claim.value.get("max_sdk_version") for claim in claims]
        # An absent bound is unbounded, and unbounded is the widest need there
        # is — so one omission defeats every stated ceiling.
        widest = (
            None
            if any(not isinstance(b, int) or isinstance(b, bool) for b in bounds)
            else max(int(b) for b in bounds)  # type: ignore[arg-type]
        )
        record.add(
            "effective", "permission", name,
            distributions=sorted({claim.distribution for claim in claims}),
            max_sdk=widest,
            never_for_location=(
                True
                if all(claim.value.get("never_for_location") is True for claim in claims)
                else None
            ),
        )


def _meta_data(
    resolved: Sequence[Resolved],
    application: Application,
    findings: Findings,
    record: Record,
) -> None:
    """§6.8: one manifest entry, and equality by type as well as content.

    "`1` and `"1"` are different declarations of one key and MUST fail, even
    though `android:value` would render them the same way." The clause exists
    for the consumer that compares the rendered manifest text: both produce
    `android:value="1"`, so merging after rendering sees agreement and coalesces,
    and the two producers who disagreed about the type both believe they won.

    §6.8's table gives the third outcome: "the application's own value always
    wins". Where the application sets the key itself there is no disagreement
    left to report — it is settled, not resolved by the consumer — so the
    producers' values do not fail the build, and requirement 32's "keeping and
    reporting the application's own entry" is what the record carries.
    """
    keyed: dict[str, list[_Claim]] = {}
    contributed: set[str] = set()
    for entry in resolved:
        for declaration in entry.sidecar.entries("contributes", "meta_data"):
            key, value = declaration.get("key"), declaration.get("value")
            if isinstance(key, str):
                contributed.add(key)
                keyed.setdefault(key, []).append(
                    _Claim(entry.distribution, (_type_of(value), value))
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
                    _Claim(entry.distribution, ("string", supplied), answer=True)
                )

    _settle(
        keyed,
        owned=application.manifest_meta_data,
        findings=findings,
        record=record,
        verb="meta-data",
        obligation=META_DATA,
        where="android.contributes.meta_data",
        subject="`<meta-data>` key",
        # A key claimed only through §5.2 is a disagreement between two values,
        # which is requirement 17's and already reported. This rule is §6.8's,
        # and needs a `meta_data` contribution on at least one side of it.
        reportable=contributed,
    )


# -- §7.4: one Info.plist key, one mode --------------------------------------


def _info_plist(
    resolved: Sequence[Resolved],
    application: Application,
    findings: Findings,
    record: Record,
) -> None:
    """§7.4's two rules that need the whole closure, and the mode conflict.

    "A key belongs to one mode, and the requirement side counts." A key under
    `append` is an array key; a key under `values`, *or delivered by a value of
    kind `info_plist`*, is a scalar one. One key claimed both ways has "no
    unambiguous plist form and no order-independent winner", so it fails naming
    both declarers — and a consumer must not merge a scalar into an array or an
    array into a scalar to make the problem go away.

    §7.4's note names the case this actually catches: `LSApplicationQueriesSchemes`
    is the array key producers really do contribute, and a value of kind
    `info_plist` naming it asks the consumer to write one string where a list
    belongs.

    Which keys hold arrays is not knowledge this reader has, and §7.4 is
    explicit that it should not be: "it deliberately requires no list of which
    Apple keys hold arrays. The declarations say which."
    """
    scalars: dict[str, list[_Claim]] = {}
    arrays: dict[str, list[_Claim]] = {}
    contributed: set[str] = set()
    for entry in resolved:
        plist = entry.sidecar.section("contributes", "info_plist")
        for key, value in (plist.get("values") or {}).items():
            if isinstance(key, str):
                contributed.add(key)
                scalars.setdefault(key, []).append(
                    _Claim(entry.distribution, (_type_of(value), value), "values")
                )
        for key in plist.get("append") or {}:
            if isinstance(key, str):
                arrays.setdefault(key, []).append(
                    _Claim(entry.distribution, None, "append")
                )
        for declaration in entry.sidecar.entries("requires", "application_value"):
            if declaration.get("kind") != "info_plist":
                continue
            key = declaration.get("key")
            supplied = application.value(
                entry.distribution, str(declaration.get("id"))
            )
            if isinstance(key, str) and supplied is not None:
                scalars.setdefault(key, []).append(
                    _Claim(
                        entry.distribution,
                        ("string", supplied),
                        "requires.application_value",
                        answer=True,
                    )
                )

    for key in sorted(set(scalars) & set(arrays)):
        findings.requirement(
            PLIST,
            *(claim.distribution for claim in scalars[key] + arrays[key]),
            message=f"`{key}` is claimed as both a scalar and an array",
            where="ios.contributes.info_plist",
            detail=[
                *(f"{claim.distribution} sets it as a scalar, in `{claim.where}`"
                  for claim in scalars[key]),
                *(f"{claim.distribution} appends to it, in `append`"
                  for claim in arrays[key]),
                "one key has one plist form, and neither mode may absorb the other",
            ],
        )

    _settle(
        {key: claims for key, claims in scalars.items() if key not in arrays},
        owned=application.info_plist,
        findings=findings,
        record=record,
        verb="plist-value",
        obligation=PLIST,
        where="ios.contributes.info_plist.values",
        subject="`Info.plist` key",
        # As with §6.8: a key claimed only through §5.2 is two supplied values
        # disagreeing, which is requirement 17's and reported there. This rule
        # needs a `values` contribution on at least one side of it.
        reportable=contributed,
    )


def _settle(
    keyed: Mapping[str, Sequence[_Claim]],
    *,
    owned: Mapping[str, Any],
    findings: Findings,
    record: Record,
    verb: str,
    obligation: int,
    where: str,
    subject: str,
    reportable: set[str] | None = None,
) -> None:
    """One key space, resolved: the application's value, agreement, or a failure.

    §6.8 and §7.4 state the same three outcomes in the same order, and the
    ordering is the rule. Equal content coalesces. Differing content fails,
    because there is no order-independent winner and whichever the consumer
    wrote, the other producer's SDK would read a key configured for someone
    else. And the application's own value beats both, since it is the one party
    to the integration entitled to settle what its own manifest says.
    """
    for key, claims in sorted(keyed.items()):
        who = sorted({claim.distribution for claim in claims})
        if key in owned:
            value = owned[key]
            record.add(
                "effective", verb, key,
                type=_type_of(value), value=value,
                distributions=who,
                source="application",
            )
            continue

        if len({claim.value for claim in claims}) > 1:
            if reportable is not None and key not in reportable:
                continue
            findings.requirement(
                obligation,
                *(claim.distribution for claim in claims),
                message=f"one {subject} is declared two ways: `{key}`",
                where=where,
                detail=[
                    f"{claim.distribution} declares {claim.value[0]} {claim.value[1]!r}"
                    for claim in claims
                ],
            )
            continue

        # The agreed content, taken from a declaration rather than an answer.
        # A key whose only claimant is a supplied value is already recorded as
        # `state=supplied` against the requirement that asked for it, and the
        # string itself stays out: see `_Claim.answer`.
        declared = [claim for claim in claims if not claim.answer]
        if not declared:
            continue
        kind, value = declared[0].value
        record.add(
            "effective", verb, key, type=kind, value=value, distributions=who
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
