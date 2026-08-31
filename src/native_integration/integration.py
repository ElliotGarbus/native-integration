"""Resolving one platform's build, and recording what it resolved to.

§5.4's table is three lines long and the whole of what the application owes:
a floor is met by configuration, a value by a non-empty string that is not the
placeholder, an action by an acknowledgement *plus* every value it `uses`. The
last conjunct is the one a consumer that checks "acknowledged?" gets wrong, and
§5.3 says why it exists: the value it waits on may be conditional, so on its own
it never fails a build, and without the rule an unconditional action could pass
while the input it depends on never arrived.

What is resolved here is one sidecar against one application. Rules that need
the whole closure — collision, merge, cross-distribution conflict — are not
here, because they cannot be decided a sidecar at a time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping

from .application import Application, meets
from .document import Sidecar
from .findings import Findings
from .recording import Record, normalize_name, text_of
from .resources import ResourceError, sha256_bytes

#: §8.4, by number: the obligations this module discharges.
FLOOR = 12
VALUE = 13
ACTION = 14
UNREADABLE = 4

#: §5.1's floors, per platform, in the order §5.1 gives them.
FLOORS: Mapping[str, tuple[str, ...]] = {
    "android": ("min_sdk", "compile_sdk", "target_sdk", "core_library_desugaring"),
    "ios": ("deployment_target",),
}

#: §6.2 and §7.3: from each listed directory the consumer stages exactly the
#: files with the matching extension, and ignores the rest. Android lists two
#: languages under one `src` table; iOS lists one.
LANGUAGES: Mapping[str, tuple[tuple[str, str], ...]] = {
    "android": (("java", ".java"), ("kotlin", ".kt")),
    "ios": (("swift", ".swift"),),
}
#: The record spells a contribution by platform, not by language.
SOURCE_VERB: Mapping[str, str] = {"android": "source", "ios": "swift-source"}


@dataclass(frozen=True)
class Resolved:
    """What one sidecar resolved to, for the rules that need the whole closure."""

    sidecar: Sidecar
    #: Every contributed source file, normalized and sorted.
    sources: tuple[str, ...] = ()
    #: Java namespaces this distribution claims exclusively (§6.1).
    owns: tuple[str, ...] = ()
    #: Values by id, with the state §5.4 puts them in.
    values: Mapping[str, str] = field(default_factory=dict)

    @property
    def distribution(self) -> str:
        return normalize_name(self.sidecar.distribution)


def resolve(
    sidecar: Sidecar,
    *,
    application: Application,
    findings: Findings,
    record: Record,
    origin: str = "direct",
    via: Iterable[str] = (),
) -> Resolved:
    """One sidecar, against one application, onto the record."""
    name = normalize_name(sidecar.distribution)

    record.add("dist", name, "version", sidecar.version)
    record.add("dist", name, "contract", str(sidecar.document.get("contract", "")))
    record.add("dist", name, "origin", origin, via=sorted(set(via)) or None)

    sources = _sources(sidecar, findings, record)
    _inputs(sidecar, sources, findings, record)
    owns = _ownership(sidecar, record)
    _floors(sidecar, application, findings, record)
    values = _values(sidecar, application, findings, record)
    _actions(sidecar, application, values, findings, record)
    if sidecar.platform == "android":
        _android(sidecar, application, record)
    else:
        _ios(sidecar, record)

    return Resolved(sidecar=sidecar, sources=sources, owns=owns, values=values)


# -- §6.2, §7.3: contributed source ----------------------------------------


def _sources(sidecar: Sidecar, findings: Findings, record: Record) -> tuple[str, ...]:
    """Every file staged from the listed directories, and the fact for each.

    A directory is listed; the *files* are what the record names, because a
    reviewer comparing two runs wants to see a file appear rather than a
    directory stay the same.
    """
    verb = SOURCE_VERB[sidecar.platform]
    src = sidecar.section("contributes", "src")
    found: list[str] = []
    for language, suffix in LANGUAGES[sidecar.platform]:
        listed = src.get(language, [])
        if not isinstance(listed, list):
            continue
        for directory in listed:
            if not isinstance(directory, str):
                continue
            try:
                staged = sidecar.source.walk(directory, suffix)
            except ResourceError as exc:
                findings.requirement(
                    _obligation_for(exc),
                    sidecar.distribution,
                    message=f"the contributed source directory {exc.reason}",
                    where=exc.relpath,
                )
                continue
            for path in staged:
                found.append(path)
                record.add("dist", normalize_name(sidecar.distribution),
                           "contributes", verb, path)

    if sidecar.platform == "ios":
        for prefix in src.get("symbol_prefixes", []) or []:
            if isinstance(prefix, str):
                record.add("dist", normalize_name(sidecar.distribution),
                           "contributes", "symbol-prefix", prefix)

    return tuple(sorted(set(found)))


def _obligation_for(exc: ResourceError) -> int:
    """§4.1's two failures answer to different requirements."""
    return 5 if exc.kind in ("escapes", "symlink") else UNREADABLE


# -- §9.3: hashed inputs ----------------------------------------------------


def _inputs(
    sidecar: Sidecar, sources: Iterable[str], findings: Findings, record: Record
) -> None:
    """A SHA-256 per file, covering `native.toml` and every resource it references.

    Every producer, not only path and editable installs: the useful identity is
    the material the integration was computed from, so a diagnostic can say
    which file changed rather than that the producer's hash did.
    """
    name = normalize_name(sidecar.distribution)
    for relpath in ("native.toml", *sources):
        try:
            data = sidecar.source.read_bytes(relpath)
        except ResourceError as exc:
            findings.requirement(
                _obligation_for(exc),
                sidecar.distribution,
                message=f"a hashed input {exc.reason}",
                where=exc.relpath,
            )
            continue
        record.add(
            "dist", name, "input", relpath,
            sha256=sha256_bytes(data).removeprefix("sha256:"),
        )


# -- §6.1: ownership --------------------------------------------------------


def _ownership(sidecar: Sidecar, record: Record) -> tuple[str, ...]:
    claimed = sidecar.section("owns").get("java_namespaces", [])
    if not isinstance(claimed, list):
        return ()
    owned = tuple(sorted({n for n in claimed if isinstance(n, str)}))
    for namespace in owned:
        record.add(
            "dist", normalize_name(sidecar.distribution),
            "owns", "java-namespace", namespace,
        )
    return owned


# -- §5.1: floors -----------------------------------------------------------


def _floors(
    sidecar: Sidecar, application: Application, findings: Findings, record: Record
) -> None:
    """§5.1, and requirement 12's insistence on both values in the diagnostic.

    A floor carries no `reason`, so the declared and the configured values are
    the whole of what a report can say. A consumer never raises the
    application's configuration to satisfy one.
    """
    requires = sidecar.section("requires")
    for key in FLOORS[sidecar.platform]:
        if key not in requires:
            continue
        declared = requires[key]
        configured = application.configured_floor(key)
        satisfied = meets(declared, configured, key)
        record.add(
            "dist", normalize_name(sidecar.distribution), "floor", key,
            declared=declared,
            configured=configured if configured is not None else None,
            state="met" if satisfied else "unmet",
        )
        if satisfied:
            continue
        findings.requirement(
            FLOOR,
            sidecar.distribution,
            message=f"the application's `{key}` is below the declared floor",
            where=f"{sidecar.platform}.requires.{key}",
            detail=[
                f"declared {text_of(declared)}",
                f"configured {text_of(configured)}" if configured is not None
                else "the application configures none",
            ],
        )


# -- §5.2: values -----------------------------------------------------------


def _values(
    sidecar: Sidecar, application: Application, findings: Findings, record: Record
) -> dict[str, str]:
    """Each declared value, in one of §5.4's three states.

    "Has supplied a non-empty string that is not the placeholder" — the second
    half is requirement 13's, and it is the reason a scaffold is safe to write:
    a consumer that accepted its own placeholder back would report a value as
    answered on the strength of text it printed itself.
    """
    states: dict[str, str] = {}
    name = normalize_name(sidecar.distribution)
    for entry in sidecar.entries("requires", "application_value"):
        identifier = entry.get("id")
        kind = entry.get("kind")
        if not isinstance(identifier, str) or not isinstance(kind, str):
            continue  # structurally invalid, and already reported as that
        conditional = entry.get("conditional") is True
        placeholder = entry.get("placeholder")
        supplied = application.value(sidecar.distribution, identifier)
        dismissal = application.dismissal(sidecar.distribution, identifier)

        if supplied is not None and supplied != placeholder:
            state = "supplied"
        elif conditional and dismissal is not None:
            state = "dismissed"
        else:
            state = "unresolved"
        states[identifier] = state

        answer = dismissal if state == "dismissed" else None
        record.add(
            "dist", name, "value", identifier,
            kind=kind,
            key=entry.get("key"),
            conditional=True if conditional else None,
            state=state,
            date=answer.date if answer and answer.date else None,
            version=sidecar.version if answer else None,
        )

        if state == "supplied" or conditional:
            continue
        detail = [str(entry["reason"])] if isinstance(entry.get("reason"), str) else []
        if supplied is not None and supplied == placeholder:
            detail.append("the scaffolded placeholder is still in place, and is not an answer")
        findings.requirement(
            VALUE,
            sidecar.distribution,
            message=f"`{identifier}` is unsupplied",
            where=f"{sidecar.platform}.requires.application_value",
            detail=detail,
        )
    return states


# -- §5.3: actions ----------------------------------------------------------


def _actions(
    sidecar: Sidecar,
    application: Application,
    values: Mapping[str, str],
    findings: Findings,
    record: Record,
) -> None:
    """Each declared action, and the conjunct that holds an acknowledged one open."""
    name = normalize_name(sidecar.distribution)
    for entry in sidecar.entries("requires", "application_action"):
        identifier = entry.get("id")
        if not isinstance(identifier, str):
            continue
        conditional = entry.get("conditional") is True
        uses = tuple(u for u in entry.get("uses", []) or [] if isinstance(u, str))
        acknowledgement = application.acknowledgement(sidecar.distribution, identifier)
        dismissal = application.dismissal(sidecar.distribution, identifier)

        if acknowledgement is not None:
            state, answer = "acknowledged", acknowledgement
        elif conditional and dismissal is not None:
            state, answer = "dismissed", dismissal
        else:
            state, answer = "unresolved", None

        held = tuple(u for u in uses if values.get(u) != "supplied")
        record.add(
            "dist", name, "action", identifier,
            state=state,
            conditional=True if conditional else None,
            slot=entry.get("slot"),
            uses=uses or None,
            date=answer.date if answer and answer.date else None,
            version=sidecar.version if answer else None,
        )

        satisfied = state == "acknowledged" and not held
        if satisfied or state == "dismissed" or conditional:
            continue
        detail = [str(entry["reason"])] if isinstance(entry.get("reason"), str) else []
        if held:
            # §5.3, and the half requirement 14 exists for. Both ids, because a
            # report naming only the action sends an author to work they have
            # already done.
            detail.append(
                "acknowledged, and held open by "
                + ", ".join(f"`{u}`" for u in held)
                + (" which is unsupplied" if len(held) == 1 else " which are unsupplied")
            )
        findings.requirement(
            ACTION,
            sidecar.distribution,
            message=(
                f"`{identifier}` is acknowledged but unsatisfied"
                if held
                else f"`{identifier}` is unacknowledged"
            ),
            where=f"{sidecar.platform}.requires.application_action",
            detail=detail,
        )


# -- §6, §7: contributions ---------------------------------------------------
#
# One verb-phrase per contribution kind, so that a set difference over these
# lines *is* the delta a reviewer reads. What a declaration says is recorded;
# what the application answered about it is not, because §9.1 splits the record
# in two and gates only the first half.


def _scalar_kind(value: object) -> str | None:
    """§6.8's and §7.4's type tags. Booleans first: in Python they are integers."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    return None


def _attribute(value: object, sidecar: Sidecar, application: Application) -> object:
    """A `view_links` attribute, which §5.2 lets be an inline application value.

    Substituted rather than recorded as a reference: the record states what the
    integration resolved to, and an unsupplied value has already failed the
    build on its own requirement.
    """
    if isinstance(value, dict) and set(value) == {"application_value"}:
        return application.value(sidecar.distribution, value["application_value"]) or ""
    return value


def _requested(entry: Mapping[str, object]) -> str | None:
    """§6.3's two dependency forms, each spelled one way."""
    coordinate = entry.get("coordinate")
    if isinstance(coordinate, str):
        return f"exact:{coordinate.rsplit(':', 1)[-1]}"
    version = entry.get("version")
    if isinstance(version, dict):
        return f"range:{version.get('at_least')}:{version.get('below')}"
    return None


def _requirement_of(entry: Mapping[str, object]) -> str | None:
    """§7.2's three requirement forms. `branch` has no spelling here."""
    held = entry.get("requirement")
    if not isinstance(held, dict):
        return None
    for form in ("exact", "from", "revision"):
        if isinstance(held.get(form), str):
            return f"{form}:{held[form]}"
    return None


def _android(sidecar: Sidecar, application: Application, record: Record) -> None:
    name = normalize_name(sidecar.distribution)

    def fact(*positionals: object, **keyed: object) -> None:
        record.add("dist", name, "contributes", *positionals, **keyed)  # type: ignore[arg-type]

    for entry in sidecar.entries("contributes", "gradle_dependencies"):
        module = entry.get("module")
        coordinate = entry.get("coordinate")
        if isinstance(coordinate, str):
            module = coordinate.rsplit(":", 1)[0]
        if not isinstance(module, str):
            continue
        fact(
            "gradle-dependency", module,
            configuration=entry.get("configuration", "implementation"),
            requested=_requested(entry),
        )

    for entry in sidecar.entries("contributes", "gradle_repositories"):
        if not isinstance(entry.get("url"), str):
            continue
        fact(
            "gradle-repository", entry["url"],
            authenticated=entry.get("credentials_required") is True,
            reason=entry.get("reason"),
            groups=entry.get("groups"),
            modules=entry.get("modules"),
        )

    for entry in sidecar.entries("contributes", "permissions"):
        if not isinstance(entry.get("name"), str):
            continue
        fact(
            "permission", entry["name"],
            reason=entry.get("reason"),
            max_sdk=entry.get("max_sdk_version"),
            never_for_location=entry.get("never_for_location"),
        )

    for entry in sidecar.entries("contributes", "features"):
        if isinstance(entry.get("name"), str):
            # §6.5: always registered `required="false"`; only the application
            # may promote a feature.
            fact("feature", entry["name"], required=False)

    for entry in sidecar.entries("contributes", "components"):
        component = entry.get("name")
        if not isinstance(component, str):
            continue
        fact(
            "component", component,
            kind=entry.get("kind"),
            exported_required=True if entry.get("exported_required") is True else None,
            from_dependency=entry.get("from_dependency"),
            foreground_service_type=entry.get("foreground_service_type"),
        )
        for link in entry.get("view_links", []) or []:
            if not isinstance(link, dict):
                continue
            fact(
                "view-link", component,
                verbatim={
                    key: _attribute(value, sidecar, application)
                    for key, value in link.items()
                },
            )
        for filtered in entry.get("intent_filters", []) or []:
            if isinstance(filtered, dict) and isinstance(filtered.get("action"), str):
                fact("intent-filter", component, action=filtered["action"])

    r8 = sidecar.section("contributes", "r8")
    for pattern in r8.get("keep_classes", []) or []:
        if isinstance(pattern, str):
            fact("keep", pattern)
    for entry in r8.get("keep", []) or []:
        if isinstance(entry, dict) and isinstance(entry.get("pattern"), str):
            fact("keep", entry["pattern"], from_dependency=entry.get("from_dependency"))

    for entry in sidecar.entries("contributes", "meta_data"):
        key, value = entry.get("key"), entry.get("value")
        kind = _scalar_kind(value)
        if isinstance(key, str) and kind in ("string", "integer", "boolean"):
            fact("meta-data", key, type=kind, value=value)

    for entry in sidecar.entries("contributes", "queries"):
        for field_name, kind in (("package", "package"),
                                 ("provider_authority", "provider-authority")):
            if isinstance(entry.get(field_name), str):
                fact("query", entry[field_name], kind=kind, reason=entry.get("reason"))


def _ios(sidecar: Sidecar, record: Record) -> None:
    name = normalize_name(sidecar.distribution)

    def fact(*positionals: object, **keyed: object) -> None:
        record.add("dist", name, "contributes", *positionals, **keyed)  # type: ignore[arg-type]

    for entry in sidecar.entries("contributes", "swift_packages"):
        if not isinstance(entry.get("name"), str):
            continue
        fact(
            "swift-package", entry["name"],
            products=entry.get("products"),
            requirement=_requirement_of(entry),
            url=entry.get("url"),
            credentials_required=True if entry.get("credentials_required") is True else None,
            reason=entry.get("reason"),
        )

    for entry in sidecar.entries("contributes", "accessed_api_types"):
        if isinstance(entry.get("type"), str):
            fact("accessed-api", entry["type"], reasons=entry.get("reasons"))

    info_plist = sidecar.section("contributes", "info_plist")
    for key, value in (info_plist.get("values") or {}).items():
        kind = _scalar_kind(value)
        if kind:
            fact("plist-value", key, type=kind, value=value)
    for key, members in (info_plist.get("append") or {}).items():
        if not isinstance(members, list):
            continue
        # §7.4's one-mode rule: the key is claimed as array-valued by being
        # declared here, and the claim stands even where the array is empty —
        # which is why it is its own fact.
        fact("plist-array-key", key)
        for member in members:
            fact("plist-append", key, value=member)
    for identifier in info_plist.get("skadnetwork_identifiers", []) or []:
        if isinstance(identifier, str):
            fact("skadnetwork", identifier)

    for entry in sidecar.entries("contributes", "python_modules"):
        module = entry.get("name")
        if not isinstance(module, str):
            continue
        fact(
            "python-module", module,
            init=entry.get("init") or f"PyInit_{module}",
            swift_package=entry.get("swift_package"),
        )

    if sidecar.section("contributes").get("objc_categories") is True:
        fact("objc-categories")


def build_facts(record: Record, *, contract: str, platform: str) -> None:
    """The two facts that describe the build rather than any distribution."""
    record.add("build", "contract", contract)
    record.add("build", "platform", platform)


# -- §2.2's other answers ----------------------------------------------------
#
# The answers joined by something other than `(distribution, id)`. They are
# integration-wide, so they carry no `dist` subject and name the distributions
# they affected instead — and they need every sidecar at once, which is why they
# are not part of resolving one.

EXPORT = 29
CREDENTIALS = 27


def decisions(
    resolved: Iterable[Resolved],
    *,
    application: Application,
    findings: Findings,
    record: Record,
) -> None:
    """What the application answered about names and URLs, and what it has not."""
    _exports(resolved, application, findings, record)
    _suppressions(resolved, application, record)
    _credentials(resolved, application, findings, record)


def _exports(
    resolved: Iterable[Resolved],
    application: Application,
    findings: Findings,
    record: Record,
) -> None:
    """§6.6, and the case with two wrong answers rather than one.

    Exporting without approval hands every other app on the device a surface the
    application never agreed to. Registering the component unexported instead
    builds something that compiles, installs and does not work — the producer has
    already said it is useless unless reachable. So neither, and the build fails.
    """
    for entry in resolved:
        sidecar = entry.sidecar
        for component in sidecar.entries("contributes", "components"):
            if component.get("exported_required") is not True:
                continue
            component_name = component.get("name")
            if not isinstance(component_name, str):
                continue
            approval = application.export(component_name)
            record.add(
                "decision", "approve-export", component_name,
                distribution=entry.distribution,
                state="approved" if approval.approved else "pending",
                date=approval.date if approval.approved and approval.date else None,
            )
            if approval.approved:
                continue
            reason = component.get("reason")
            findings.requirement(
                EXPORT,
                sidecar.distribution,
                message=f"`{component_name}` requests export, and is unapproved",
                where=f"{sidecar.platform}.contributes.components",
                detail=[str(reason)] if isinstance(reason, str) else [],
            )


def _suppressions(
    resolved: Iterable[Resolved], application: Application, record: Record
) -> None:
    """§6.5, joined by the permission name and applying to every contributor.

    Requirement 10 is explicit that an answer joined by something other than
    `(distribution, id)` reaches every contributor of the name it addresses, so
    the fact names all of them rather than the one that happened to be read
    first.
    """
    contributors: dict[str, set[str]] = {}
    for entry in resolved:
        for permission in entry.sidecar.entries("contributes", "permissions"):
            named = permission.get("name")
            if isinstance(named, str):
                contributors.setdefault(named, set()).add(entry.distribution)
    for permission_name, withdrew in sorted(contributors.items()):
        answer = application.suppression(permission_name)
        if answer is None:
            continue
        record.add(
            "decision", "suppress-permission", permission_name,
            date=answer.date or None,
            withdrew=sorted(withdrew),
        )


def _credentials(
    resolved: Iterable[Resolved],
    application: Application,
    findings: Findings,
    record: Record,
) -> None:
    """§6.4 and §7.2: an authenticated repository or package needs a credential.

    "Naming the distribution, rather than attempting resolution and surfacing a
    bare `401`" — a 401 names a host, and not the Python distribution that added
    the repository, the credential needed, or where to get one.
    """
    for entry in resolved:
        sidecar = entry.sidecar
        wanted: list[tuple[str, str, object]] = []
        for repository in sidecar.entries("contributes", "gradle_repositories"):
            if repository.get("credentials_required") is True:
                wanted.append(("repository", str(repository.get("url")), repository.get("reason")))
        for package in sidecar.entries("contributes", "swift_packages"):
            if package.get("credentials_required") is True:
                wanted.append(("package", str(package.get("url")), package.get("reason")))

        for kind, url, reason in wanted:
            # §9.5: that one is required is a fact about the integration; the
            # credential is not, and never appears.
            record.add("decision", "credential-required", url, kind=kind)
            if application.credential(url) is not None:
                continue
            findings.requirement(
                CREDENTIALS,
                sidecar.distribution,
                message=f"{url} is authenticated, and no credentials are configured",
                where=f"{sidecar.platform}.contributes",
                detail=[str(reason)] if isinstance(reason, str) else [],
            )
