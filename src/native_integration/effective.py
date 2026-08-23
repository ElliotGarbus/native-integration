"""The effective set: what the application actually acquires, after its answers.

This is where a *declaration* becomes a *contribution*. A permission the
application suppressed is still declared and is no longer effective; an
application value that was supplied is substituted into the filters that
referenced it; a component whose export was not approved blocks the build
rather than quietly registering unexported.

Everything here is computed, never written: staging files into a Gradle or
Xcode project is the consumer's job, and this is the description it stages from.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Mapping, Sequence

from . import rules
from .answers import CredentialReference
from .context import Application
from .diagnostics import DiagnosticBag
from .discovery import Closure, Origin, normalize_name
from .model import (
    Component,
    GradleDependency,
    GradleRepository,
    Platform,
    Prerequisite,
    PrerequisiteKind,
    PythonModule,
    Ref,
    Sidecar,
    SwiftPackage,
    ViewLink,
)
from .resources import SidecarSource


@dataclass(frozen=True)
class PermissionEntry:
    distribution: str
    name: str
    reason: str | None
    suppressed: bool = False
    #: §6.7 — `android:maxSdkVersion`; None means "needed at every level".
    max_sdk_version: int | None = None
    #: §6.7 — `android:usesPermissionFlags="neverForLocation"`.
    never_for_location: bool = False


@dataclass(frozen=True)
class FeatureEntry:
    distribution: str
    name: str
    #: Always false. Only the application may promote a feature (§6.7).
    required: bool = False


@dataclass(frozen=True)
class MetaDataEntry:
    key: str
    value: str
    distributions: tuple[str, ...]
    overridden_by_application: bool = False


@dataclass(frozen=True)
class GeneratedViewLink:
    """A resolved ``view_links`` entry: the consumer generates the filter itself.

    A field is ``None`` when it referenced an application value the application
    has not supplied. That is deliberately not a placeholder string: the build
    is already blocked by ``application-value-unsupplied``, and a consumer that
    stages before checking should hit a missing value rather than write
    ``${some_id}`` into a manifest, where it would look like a filter that
    merely never matches.
    """

    scheme: str | None = None
    host: str | None = None
    path_prefix: str | None = None
    #: The application-value ids this filter referenced and did not get.
    unresolved: tuple[str, ...] = ()
    #: ``android.intent.action.VIEW`` plus DEFAULT and BROWSABLE are implied by
    #: the type and are not spellable, which is what removes the classic
    #: missing-DEFAULT silent failure.
    action: str = "android.intent.action.VIEW"
    categories: tuple[str, ...] = ("android.intent.category.DEFAULT", "android.intent.category.BROWSABLE")

    @property
    def complete(self) -> bool:
        """True when every referenced value was supplied and this can be staged."""
        return self.scheme is not None and not self.unresolved

    def render(self) -> str:
        parts = [f"scheme {self.scheme}" if self.scheme is not None else "scheme <unsupplied>"]
        if self.host:
            parts.append(f"host {self.host}")
        if self.path_prefix:
            parts.append(f"pathPrefix {self.path_prefix}")
        if self.unresolved:
            parts.append("unsupplied: " + ", ".join(self.unresolved))
        return ", ".join(parts)


@dataclass(frozen=True)
class ComponentEntry:
    distribution: str
    component: Component
    exported: bool
    view_links: tuple[GeneratedViewLink, ...] = ()
    actions: tuple[str, ...] = ()

    @property
    def name(self) -> str:
        return self.component.name

    @property
    def kind(self) -> str:
        return self.component.kind


@dataclass(frozen=True)
class RepositoryEntry:
    distribution: str
    repository: GradleRepository
    credentials_configured: bool = False
    #: A record-safe description of *how* a credential arrives. Never the value:
    #: §9 forbids writing an application-supplied credential into the record, a
    #: report, or a diagnostic.
    credential_note: str | None = None


@dataclass(frozen=True)
class PrerequisiteStatus:
    distribution: str
    prerequisite: Prerequisite
    satisfied: bool

    @property
    def blocking(self) -> bool:
        return not self.satisfied and not self.prerequisite.conditional

    @property
    def unresolved_conditional(self) -> bool:
        return not self.satisfied and self.prerequisite.conditional

    def render(self) -> str:
        mark = "✓" if self.satisfied else ("~" if self.prerequisite.conditional else "✗")
        tail = "" if self.satisfied else f"  — {self.prerequisite.reason}"
        conditional = " (conditional)" if self.prerequisite.conditional else ""
        return f"{mark} {self.prerequisite.kind.value} {self.prerequisite.key}{conditional}{tail}"


@dataclass(frozen=True)
class Contribution:
    """One distribution's effective contribution, with its provenance."""

    distribution: str
    version: str
    origin: Origin
    contract: str
    permissions: tuple[PermissionEntry, ...] = ()
    features: tuple[FeatureEntry, ...] = ()
    components: tuple[ComponentEntry, ...] = ()
    meta_data: tuple[MetaDataEntry, ...] = ()
    #: §6.3 — application values delivered as AGP manifest placeholders. Same
    #: shape and same coalescing rule as `meta_data`; a different destination.
    placeholders: tuple[MetaDataEntry, ...] = ()
    dependencies: tuple[GradleDependency, ...] = ()
    repositories: tuple[RepositoryEntry, ...] = ()
    keep_patterns: tuple[str, ...] = ()
    swift_packages: tuple[SwiftPackage, ...] = ()
    python_modules: tuple[PythonModule, ...] = ()
    info_plist_values: Mapping[str, object] = field(default_factory=dict)
    info_plist_append: Mapping[str, Sequence[object]] = field(default_factory=dict)
    #: §7.6 — ad network identifiers; the consumer renders the dictionaries.
    skadnetwork_identifiers: tuple[str, ...] = ()
    #: §7.3 — application values delivered to `Info.plist` keys. Same shape and
    #: same coalescing rule as §6.3's `meta_data`; a different destination.
    plist_deliveries: tuple[MetaDataEntry, ...] = ()
    source_files: tuple[str, ...] = ()
    prerequisites: tuple[PrerequisiteStatus, ...] = ()
    #: SHA-256 per integration input, keyed by normalized relative path (§9).
    inputs: Mapping[str, str] = field(default_factory=dict)
    payload_exclusions: tuple[str, ...] = ()


@dataclass(frozen=True)
class EffectiveSet:
    platform: Platform
    contributions: tuple[Contribution, ...] = ()

    # --- merged views -------------------------------------------------------

    def permissions(self) -> tuple[PermissionEntry, ...]:
        """Permissions that reach the effective merged manifest.

        §6.7 — one permission is a single fact about the built application, so
        where two distributions declare it with different attributes the merged
        form carries the **widest** need any of them stated: no
        ``max_sdk_version`` defeats one that has it, a higher bound wins, and
        ``never_for_location`` holds only when every declaration asserts it.
        The first declaring distribution is kept as the entry's attribution;
        :meth:`permission_provenance` names them all.
        """
        merged: dict[str, PermissionEntry] = {}
        for contribution in self.contributions:
            for entry in contribution.permissions:
                if entry.suppressed:
                    continue
                previous = merged.get(entry.name)
                if previous is None:
                    merged[entry.name] = entry
                    continue
                if previous.max_sdk_version is None or entry.max_sdk_version is None:
                    ceiling = None
                else:
                    ceiling = max(previous.max_sdk_version, entry.max_sdk_version)
                merged[entry.name] = replace(
                    previous,
                    max_sdk_version=ceiling,
                    never_for_location=previous.never_for_location and entry.never_for_location,
                )
        return tuple(merged[name] for name in sorted(merged))

    def permission_provenance(self, name: str) -> tuple[str, ...]:
        """Every distribution that declared ``name``, for §9's report."""
        return tuple(
            sorted(
                {
                    c.distribution
                    for c in self.contributions
                    for p in c.permissions
                    if p.name == name and not p.suppressed
                }
            )
        )

    def manifest_removals(self) -> tuple[str, ...]:
        """Permissions needing an explicit ``tools:node="remove"`` (§6.7).

        Omitting a suppressed permission from the generated manifest is not
        sufficient: a resolved ``.aar`` carries its own manifest, which AGP
        merges, so a permission the consumer never wrote can still arrive.
        """
        return tuple(
            sorted({p.name for c in self.contributions for p in c.permissions if p.suppressed})
        )

    def exported_components(self) -> tuple[ComponentEntry, ...]:
        return tuple(e for c in self.contributions for e in c.components if e.exported)

    def info_plist(self, application: Application) -> dict[str, object]:
        """The merged ``Info.plist`` contribution, in §7.6's deterministic order.

        ``append`` keys concatenate the application's entries first, then each
        distribution's in normalized distribution-name order, de-duplicated.
        """
        merged: dict[str, object] = {}
        for contribution in self.contributions:
            merged.update(contribution.info_plist_values)
        # §7.3's application values, whose destination is a plist key. The
        # entry already carries the application's own value where it set one.
        for contribution in self.contributions:
            for delivery in contribution.plist_deliveries:
                merged[delivery.key] = delivery.value

        appended: dict[str, list[object]] = {
            key: list(values) for key, values in application.info_plist_append.items()
        }
        for contribution in sorted(
            self.contributions, key=lambda c: normalize_name(c.distribution)
        ):
            for key, values in contribution.info_plist_append.items():
                appended.setdefault(key, [])
                appended[key].extend(values)
        for key, values in appended.items():
            deduplicated: list[object] = []
            for value in values:
                if value not in deduplicated:
                    deduplicated.append(value)
            merged[key] = deduplicated
        return merged

    def skadnetwork_items(self, application: Application) -> tuple[dict[str, str], ...]:
        """§7.6 — `SKAdNetworkItems`, rendered from the declared identifiers.

        Merged on `append`'s rule: the application's own entries first, then
        each distribution's in normalized distribution-name order,
        de-duplicated. The dictionary shape is the consumer's to render, which
        is what keeps this a narrow primitive rather than dictionary support.
        """
        ordered: list[str] = list(application.skadnetwork_identifiers)
        for contribution in sorted(
            self.contributions, key=lambda c: normalize_name(c.distribution)
        ):
            ordered.extend(contribution.skadnetwork_identifiers)
        seen: list[str] = []
        for identifier in ordered:
            if identifier not in seen:
                seen.append(identifier)
        return tuple({"SKAdNetworkIdentifier": identifier} for identifier in seen)

    def python_payload_exclusions(self) -> tuple[str, ...]:
        """What must not reach the device (requirement 8.14, §7.7).

        Sidecar directories, because their contents have already been consumed
        at build time — and ``<name>.py`` / ``<name>.pyi`` for every registered
        module, because a ``.py`` stub on ``sys.path`` turns a failed
        registration into an application that imports successfully and does
        nothing.
        """
        out: set[str] = set()
        for contribution in self.contributions:
            out.update(contribution.payload_exclusions)
            for module in contribution.python_modules:
                out.add(f"{module.name}.py")
                out.add(f"{module.name}.pyi")
        return tuple(sorted(out))

    def prerequisites(self) -> tuple[PrerequisiteStatus, ...]:
        return tuple(p for c in self.contributions for p in c.prerequisites)

    def unresolved_conditionals(self) -> tuple[PrerequisiteStatus, ...]:
        return tuple(p for p in self.prerequisites() if p.unresolved_conditional)

    def for_distribution(self, name: str) -> Contribution | None:
        for contribution in self.contributions:
            if normalize_name(contribution.distribution) == normalize_name(name):
                return contribution
        return None


# --- computation ------------------------------------------------------------


def compute(
    sidecars: Sequence[Sidecar],
    *,
    platform: Platform,
    closure: Closure,
    application: Application,
    bag: DiagnosticBag,
) -> EffectiveSet:
    contributions = [
        _one(sidecar, platform=platform, closure=closure, application=application, bag=bag)
        for sidecar in sorted(sidecars, key=lambda s: normalize_name(s.distribution))
    ]
    effective = EffectiveSet(platform=platform, contributions=tuple(contributions))
    _meta_data_conflicts(effective, bag)
    return effective


def _one(
    sidecar: Sidecar,
    *,
    platform: Platform,
    closure: Closure,
    application: Application,
    bag: DiagnosticBag,
) -> Contribution:
    name = sidecar.distribution
    answers = application.answers
    origin = closure.origin(name)

    permissions: list[PermissionEntry] = []
    features: list[FeatureEntry] = []
    components: list[ComponentEntry] = []
    meta_data: list[MetaDataEntry] = []
    placeholders: list[MetaDataEntry] = []
    repositories: list[RepositoryEntry] = []
    dependencies: tuple[GradleDependency, ...] = ()
    keep_patterns: tuple[str, ...] = ()
    swift_packages: tuple[SwiftPackage, ...] = ()
    python_modules: tuple[PythonModule, ...] = ()
    plist_values: Mapping[str, object] = {}
    plist_append: Mapping[str, Sequence[object]] = {}
    skadnetwork: tuple[str, ...] = ()
    plist_deliveries: list[MetaDataEntry] = []
    statuses: list[PrerequisiteStatus] = []
    source_files: list[str] = []

    if sidecar.android is not None and platform is Platform.ANDROID:
        android = sidecar.android

        for key, required in android.floors.items():
            configured = application.configured(key)
            if configured is None or configured < required:
                bag.add(
                    rules.FLOOR_UNMET,
                    f"requires {key} ≥ {required}; the application is configured at "
                    f"{configured if configured is not None else 'nothing'}. A floor is "
                    "never raised for you",
                    name,
                )

        if android.core_library_desugaring and not application.core_library_desugaring:
            bag.add(
                rules.FLOOR_UNMET,
                "requires core library desugaring, which the application has not "
                "enabled. A floor is never raised for you",
                name,
            )

        supplied: dict[str, str] = {}
        for value in android.application_values:
            answer = answers.application_value(name, value.id)
            if answer is None:
                bag.add(
                    rules.APPLICATION_VALUE_UNSUPPLIED,
                    f"needs application value `{value.id}`: {value.reason}",
                    name,
                )
                continue
            supplied[value.id] = answer
            if value.manifest_meta_data:
                override = application.manifest_meta_data.get(value.manifest_meta_data)
                if override is not None:
                    bag.add(
                        rules.META_DATA_APPLICATION_OVERRIDE,
                        f"<meta-data {value.manifest_meta_data}> is also set by the "
                        "application, whose value is kept",
                        name,
                    )
                meta_data.append(
                    MetaDataEntry(
                        key=value.manifest_meta_data,
                        value=override if override is not None else answer,
                        distributions=(name,),
                        overridden_by_application=override is not None,
                    )
                )
            if value.manifest_placeholder:
                # §6.3 — the same supplied value, delivered where a declared
                # dependency's own manifest can read it.
                override = application.manifest_placeholders.get(value.manifest_placeholder)
                if override is not None:
                    bag.add(
                        rules.META_DATA_APPLICATION_OVERRIDE,
                        f"manifest placeholder `{value.manifest_placeholder}` is also set "
                        "by the application, whose value is kept",
                        name,
                    )
                placeholders.append(
                    MetaDataEntry(
                        key=value.manifest_placeholder,
                        value=override if override is not None else answer,
                        distributions=(name,),
                        overridden_by_application=override is not None,
                    )
                )

        for entry in android.meta_data:
            # §6.10 — one key space with §6.3's delivery, so the same override
            # rule applies: a key the application sets itself is the
            # application's, kept and reported.
            override = application.manifest_meta_data.get(entry.key)
            if override is not None:
                bag.add(
                    rules.META_DATA_APPLICATION_OVERRIDE,
                    f"<meta-data {entry.key}> is also set by the application, whose "
                    "value is kept",
                    name,
                )
            meta_data.append(
                MetaDataEntry(
                    key=entry.key,
                    value=override if override is not None else entry.rendered,
                    distributions=(name,),
                    overridden_by_application=override is not None,
                )
            )

        for permission in android.permissions:
            permissions.append(
                PermissionEntry(
                    max_sdk_version=permission.max_sdk_version,
                    never_for_location=permission.never_for_location,
                    distribution=name,
                    name=permission.name,
                    reason=permission.reason,
                    suppressed=answers.permission_suppressed(permission.name),
                )
            )
            if permissions[-1].suppressed:
                bag.add(
                    rules.PERMISSION_SUPPRESSED,
                    f"{permission.name} suppressed by application; the producer's code may "
                    "fail at runtime or degrade silently without it",
                    name,
                )

        features = [FeatureEntry(distribution=name, name=f.name) for f in android.features]

        for component in android.components:
            exported = False
            if component.exported_required:
                exported = answers.export_approved(name, component.name)
                if not exported:
                    bag.add(
                        rules.COMPONENT_EXPORT_UNAPPROVED,
                        f"`{component.name}` needs explicit application approval to be "
                        f"exported: {component.reason or 'no reason given'}. Without it the "
                        "integration cannot proceed — it is not registered unexported",
                        name,
                    )
            links = tuple(_generate_link(link, supplied) for link in component.view_links)
            components.append(
                ComponentEntry(
                    distribution=name,
                    component=component,
                    exported=exported,
                    view_links=links,
                    actions=tuple(f.action for f in component.intent_filters),
                )
            )

        for repository in android.gradle_repositories:
            credential: CredentialReference | None = None
            if repository.credentials_required:
                credential = answers.repository_credentials(repository.url)
                if credential is None:
                    bag.add(
                        rules.REPOSITORY_CREDENTIALS_MISSING,
                        f"repository {repository.url} is authenticated and no credentials "
                        f"are configured: {repository.reason}",
                        name,
                    )
                else:
                    bag.add(
                        rules.SECRET_WITHHELD,
                        f"credentials for {repository.url} {credential.describe()}; the "
                        "value is never written to the record, a report, or a diagnostic",
                        name,
                    )
            repositories.append(
                RepositoryEntry(
                    distribution=name,
                    repository=repository,
                    credentials_configured=credential is not None,
                    credential_note=credential.describe() if credential else None,
                )
            )
            bag.add(
                rules.REPOSITORY_CONTRIBUTED,
                f"REPOSITORY {repository.url} → {', '.join(repository.scope)}: "
                f"{repository.reason}",
                name,
            )

        dependencies = android.gradle_dependencies
        keep_patterns = android.keep_classes

    if sidecar.ios is not None and platform is Platform.IOS:
        ios = sidecar.ios
        if ios.deployment_target and application.deployment_target:
            if _version_tuple(application.deployment_target) < _version_tuple(ios.deployment_target):
                bag.add(
                    rules.FLOOR_UNMET,
                    f"requires deployment_target ≥ {ios.deployment_target}; the application "
                    f"is configured at {application.deployment_target}",
                    name,
                )
        elif ios.deployment_target and application.deployment_target is None:
            bag.add(
                rules.FLOOR_UNMET,
                f"requires deployment_target ≥ {ios.deployment_target}; the application "
                "declares none",
                name,
            )

        for prerequisite in ios.prerequisites:
            satisfied = _satisfied(prerequisite, distribution=name, application=application)
            statuses.append(PrerequisiteStatus(name, prerequisite, satisfied))
            if (
                satisfied
                and prerequisite.kind is PrerequisiteKind.APPLICATION_VALUE
                and prerequisite.info_plist_key
            ):
                answer = application.answers.application_value(name, prerequisite.key)
                override = application.info_plist_values.get(prerequisite.info_plist_key)
                if override is not None:
                    bag.add(
                        rules.META_DATA_APPLICATION_OVERRIDE,
                        f"Info.plist `{prerequisite.info_plist_key}` is also set by the "
                        "application, whose value is kept",
                        name,
                    )
                plist_deliveries.append(
                    MetaDataEntry(
                        key=prerequisite.info_plist_key,
                        value=override if override is not None else (answer or ""),
                        distributions=(name,),
                        overridden_by_application=override is not None,
                    )
                )
            if satisfied:
                continue
            if prerequisite.conditional:
                bag.add(
                    rules.PREREQUISITE_CONDITIONAL,
                    f"{prerequisite.kind.value} `{prerequisite.key}` unresolved "
                    f"(conditional): {prerequisite.reason}",
                    name,
                )
            else:
                bag.add(
                    rules.PREREQUISITE_UNSATISFIED,
                    f"{prerequisite.kind.value} `{prerequisite.key}` is not satisfied: "
                    f"{prerequisite.reason}",
                    name,
                )

        swift_packages = ios.swift_packages
        python_modules = ios.python_modules
        plist_values = dict(ios.info_plist_values)
        plist_append = dict(ios.info_plist_append)
        skadnetwork = tuple(ios.skadnetwork_identifiers)

    source_files = list(_staged_sources(sidecar, platform))
    inputs = _hash_inputs(sidecar, source_files)

    return Contribution(
        distribution=name,
        version=sidecar.version,
        origin=origin,
        contract=sidecar.contract.canonical,
        permissions=tuple(permissions),
        features=tuple(features),
        components=tuple(components),
        meta_data=tuple(meta_data),
        placeholders=tuple(placeholders),
        dependencies=dependencies,
        repositories=tuple(repositories),
        keep_patterns=keep_patterns,
        swift_packages=swift_packages,
        python_modules=python_modules,
        info_plist_values=plist_values,
        info_plist_append=plist_append,
        skadnetwork_identifiers=skadnetwork,
        plist_deliveries=tuple(plist_deliveries),
        source_files=tuple(source_files),
        prerequisites=tuple(statuses),
        inputs=inputs,
        payload_exclusions=sidecar.source.payload_exclusions() if sidecar.source else (),
    )


def _generate_link(link: ViewLink, supplied: Mapping[str, str]) -> GeneratedViewLink:
    """Substitute the application's answers into one ``view_links`` entry (§6.3)."""
    unresolved: list[str] = []

    def value(ref: Ref | None) -> str | None:
        if ref is None:
            return None
        if not ref.is_reference:
            return ref.literal
        supplied_value = supplied.get(ref.application_value or "")
        if supplied_value is None:
            unresolved.append(ref.application_value or "")
            return None
        return supplied_value

    scheme = value(link.scheme)
    host = value(link.host)
    path_prefix = value(link.path_prefix)
    return GeneratedViewLink(
        scheme=scheme,
        host=host,
        path_prefix=path_prefix,
        unresolved=tuple(dict.fromkeys(unresolved)),
    )


def _version_tuple(text: str) -> tuple[int, ...]:
    parts = []
    for chunk in text.split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _satisfied(prerequisite: Prerequisite, *, distribution: str, application: Application) -> bool:
    """§7.3's satisfaction table, stated once because two readers would diverge."""
    answers = application.answers
    kind = prerequisite.kind
    if kind is PrerequisiteKind.ENTITLEMENT:
        return answers.entitlement_configured(prerequisite.key)
    if kind is PrerequisiteKind.USAGE_DESCRIPTION:
        return answers.usage_description(prerequisite.key) is not None
    if kind is PrerequisiteKind.APPLICATION_FILE:
        return answers.application_file_configured(prerequisite.key)
    if kind is PrerequisiteKind.APP_EXTENSION:
        # Both halves: a target of the requested kind exists, *and* this entry is
        # acknowledged — one existing target cannot be assumed to serve two
        # producers that need different code inside it.
        return bool(prerequisite.extension_kind) and answers.extension_target_exists(
            prerequisite.extension_kind
        ) and answers.acknowledged(distribution, prerequisite.key)
    if kind is PrerequisiteKind.URL_SCHEME:
        return answers.acknowledged(distribution, prerequisite.key)
    if kind is PrerequisiteKind.APPLICATION_VALUE:
        return answers.application_value(distribution, prerequisite.key) is not None
    if kind is PrerequisiteKind.PLIST_CAPABILITY:
        return bool(prerequisite.value) and answers.plist_capability_configured(
            prerequisite.key, prerequisite.value
        )
    return False  # pragma: no cover - the enum is closed


def _staged_sources(sidecar: Sidecar, platform: Platform) -> list[str]:
    source: SidecarSource | None = sidecar.source
    if source is None:
        return []
    staged: list[str] = []
    roots: list[tuple[tuple[str, ...], str]] = []
    if platform is Platform.ANDROID and sidecar.android is not None:
        roots = [(sidecar.android.src_java, ".java"), (sidecar.android.src_kotlin, ".kt")]
    elif platform is Platform.IOS and sidecar.ios is not None:
        roots = [(sidecar.ios.src_swift, ".swift")]
    for paths, suffix in roots:
        for path in paths:
            try:
                staged.extend(source.walk(path, suffix))
            except Exception:  # already reported during parse
                continue
    return sorted(set(staged))


def _hash_inputs(sidecar: Sidecar, source_files: Sequence[str]) -> dict[str, str]:
    """§9 — a SHA-256 per integration input, ``native.toml`` and every resource."""
    source = sidecar.source
    if source is None:
        return {}
    try:
        return source.hash_all(["native.toml", *source_files])
    except Exception:  # pragma: no cover - already reported during parse
        return {}


def _meta_data_conflicts(effective: EffectiveSet, bag: DiagnosticBag) -> None:
    """§6.3 — equal values coalesce, preserving both provenance records; different values fail.

    Both delivery destinations take the same rule, because both names are
    build-global rather than scoped by distribution: two distributions naming
    one ``<meta-data>`` key, or one manifest placeholder, are necessarily
    talking about the same entry.
    """
    _delivery_conflicts(
        [e for c in effective.contributions for e in c.meta_data],
        describe=lambda key: f"<meta-data {key}>",
        bag=bag,
    )
    _delivery_conflicts(
        [e for c in effective.contributions for e in c.placeholders],
        describe=lambda key: f"manifest placeholder `{key}`",
        bag=bag,
    )
    _delivery_conflicts(
        [e for c in effective.contributions for e in c.plist_deliveries],
        describe=lambda key: f"Info.plist `{key}`",
        bag=bag,
    )


def _delivery_conflicts(entries_in, *, describe, bag: DiagnosticBag) -> None:
    by_key: dict[str, list[MetaDataEntry]] = {}
    for entry in entries_in:
        by_key.setdefault(entry.key, []).append(entry)

    for key, entries in sorted(by_key.items()):
        values = {entry.value for entry in entries}
        if len(values) > 1 and not any(e.overridden_by_application for e in entries):
            bag.add(
                rules.META_DATA_CONFLICT,
                f"deliver different values to {describe(key)}",
                *sorted({d for entry in entries for d in entry.distributions}),
                detail=tuple(f"{e.distributions[0]}  →  {e.value}" for e in entries),
            )
