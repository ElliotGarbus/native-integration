"""Reading one sidecar: the contract gate, the schema walk, and §§6–7's own rules.

The order matters. §4.3 requires a consumer to reject a sidecar declaring an
unimplementable contract "never by parsing it partially", so the gate runs
before the schema walk, and the schema walk before anything reads a value. A
sidecar that fails either produces no declaration at all — the caller gets
``None`` and a bag full of reasons, not a half-built object.

Everything checkable from *one* sidecar lives here. Rules that need to compare
two distributions — overlapping namespaces, duplicate module names, contested
repository scopes — are in :mod:`native_integration.crossrules`, because they
are not properties of any single declaration.
"""

from __future__ import annotations

import re
import tomllib
from typing import Any, Mapping

from . import naming, rules, schema
from .context import ConsumerProfile
from .contract import ContractVersion
from .diagnostics import DiagnosticBag
from .model import (
    AndroidSection,
    IosSection,
    Platform,
    Prerequisite,
    PrerequisiteKind,
    Sidecar,
    build_android,
    build_ios,
)
from .naming import contains, is_single_label, reserved_prefix
from .resources import ResourceError, SidecarSource, normalize

#: §6.5 — configurations that make the build run code from the artifact, which
#: §2.1 excludes however it arrives. Not profile-driven: a consumer rejects
#: these whether or not it implements them.
PROCESSOR_CONFIGURATIONS = frozenset({"annotationProcessor", "kapt", "ksp"})

#: §6.6 — what a consumer can reject deterministically it must; the rest is a
#: warning, because "is `abc123` a secret?" has no general algorithm and an
#: unsatisfiable MUST teaches implementers to skim the rest.
CREDENTIAL_SHAPED = re.compile(
    r"(password\s*=\s*\"|secret\s*=\s*\"|token\s*=\s*\"[^\"]{8,}|sk\.[A-Za-z0-9]{8})", re.I
)

_JAVA_PACKAGE = re.compile(r"^\s*package\s+([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*;", re.M)
_KOTLIN_PACKAGE = re.compile(r"^\s*package\s+([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*$", re.M)
_C_IDENTIFIER = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]*\Z")
_PYTHON_IDENTIFIER = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]*\Z")


def parse(
    source: SidecarSource,
    *,
    platform: Platform,
    profile: ConsumerProfile,
    bag: DiagnosticBag,
) -> Sidecar | None:
    """Read, gate, validate and build one sidecar. ``None`` when it is rejected."""
    name = source.distribution

    try:
        raw = source.sidecar_bytes()
    except ResourceError as exc:
        rule = rules.SIDECAR_MISSING if exc.kind == "unreadable" else rules.RESOURCE_UNREADABLE
        bag.add(rule, f"native.toml could not be read: {exc.reason}", name)
        return None

    try:
        doc = tomllib.loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        bag.add(rules.RESOURCE_NOT_UTF8, "native.toml is not UTF-8 encoded", name)
        return None
    except tomllib.TOMLDecodeError as exc:
        bag.add(rules.TOML_INVALID, f"native.toml does not parse: {exc}", name)
        return None

    declared = _gate(doc, name=name, profile=profile, bag=bag)
    if declared is None:
        return None

    before = len(bag.errors)
    schema.validate_document(
        doc,
        distribution=name,
        platform=platform.value,
        declared=declared,
        implemented=profile.contract,
        bag=bag,
    )
    if len(bag.errors) > before:
        return None

    before = len(bag.errors)
    _shapes(doc, name=name, platform=platform, bag=bag)
    if len(bag.errors) > before:
        return None

    platforms = _platforms(doc, name=name, platform=platform, bag=bag)
    if platforms is False:
        return None

    android = build_android(doc["android"]) if platform is Platform.ANDROID and "android" in doc else None
    ios = build_ios(doc["ios"]) if platform is Platform.IOS and "ios" in doc else None

    sidecar = Sidecar(
        distribution=name,
        version=source.version,
        contract=declared,
        platforms=platforms or None,
        android=android,
        ios=ios,
        source=source,
    )

    text = raw.decode("utf-8", errors="replace")
    if CREDENTIAL_SHAPED.search(text):
        bag.add(
            rules.REPOSITORY_CREDENTIAL_SHAPED,
            "native.toml contains something credential-shaped; a sidecar is package data, "
            "readable by everyone who installs the distribution",
            name,
        )

    if android is not None:
        _check_android(sidecar, android, profile=profile, bag=bag)
    if ios is not None:
        _check_ios(sidecar, ios, profile=profile, bag=bag)
    return sidecar


# --- the gate ---------------------------------------------------------------


def _gate(
    doc: Mapping[str, Any], *, name: str, profile: ConsumerProfile, bag: DiagnosticBag
) -> ContractVersion | None:
    if "contract" not in doc:
        bag.add(rules.CONTRACT_MISSING, "native.toml declares no `contract`", name)
        return None
    try:
        declared = ContractVersion.parse(doc["contract"])
    except ValueError as exc:
        bag.add(rules.CONTRACT_MALFORMED, str(exc), name)
        return None

    implemented = profile.contract
    if declared.major != implemented.major:
        bag.add(
            rules.CONTRACT_MAJOR_MISMATCH,
            f"declares contract {declared.canonical}; this consumer implements "
            f"{implemented.canonical} and cannot read a different major",
            name,
        )
        return None
    if declared.minor > implemented.minor:
        bag.add(
            rules.CONTRACT_TOO_NEW,
            f"requires contract {declared.canonical}; this consumer implements "
            f"{implemented.canonical}",
            name,
        )
        return None
    return declared


def _shapes(doc: Mapping[str, Any], *, name: str, platform: Platform, bag: DiagnosticBag) -> None:
    """Choices between keys, which a per-key schema cannot express.

    Run after the schema walk and before anything is built, because the model
    reads one of the two forms and a document that declares both has not said
    which.
    """
    if platform is not Platform.ANDROID:
        return
    contributes = doc.get("android", {}).get("contributes", {})
    for entry in contributes.get("gradle_dependencies", []):
        has_coordinate, has_module = "coordinate" in entry, "module" in entry
        if has_coordinate == has_module:
            bag.add(
                rules.DEPENDENCY_FORM,
                "a Gradle dependency declares "
                + ("both `coordinate` and `module`" if has_coordinate else "neither `coordinate` nor `module`")
                + "; the two forms are mutually exclusive and exactly one is required",
                name,
            )
            continue
        if has_coordinate:
            try:
                naming.split_coordinate(entry["coordinate"])
            except ValueError as exc:
                bag.add(rules.DEPENDENCY_FORM, f"`coordinate`: {exc}", name)
        else:
            try:
                naming.Module.parse(entry["module"])
            except ValueError as exc:
                bag.add(rules.DEPENDENCY_FORM, f"`module`: {exc}", name)
            if "version" not in entry:
                bag.add(
                    rules.DEPENDENCY_FORM,
                    f"`module = \"{entry['module']}\"` needs a bounded `version` "
                    "{ at_least, below }",
                    name,
                )


def _platforms(
    doc: Mapping[str, Any], *, name: str, platform: Platform, bag: DiagnosticBag
) -> tuple[str, ...] | bool:
    """Returns the declared platforms, or ``False`` when the sidecar is rejected."""
    if "platforms" not in doc:
        return ()  # omitting the key makes no claim, and is the default

    values = tuple(doc["platforms"])
    known = {p.value for p in Platform}
    unknown = [v for v in values if v not in known]
    if unknown:
        bag.add(
            rules.PLATFORMS_INVALID,
            "`platforms` names " + ", ".join(repr(u) for u in unknown)
            + "; the platforms this specification defines are android, ios",
            name,
        )
        return False

    for table in sorted(known & set(doc)):
        if table not in values:
            bag.add(
                rules.PLATFORMS_CONTRADICTION,
                f"declares an [{table}] table but omits {table!r} from `platforms`",
                name,
            )
            return False

    if platform.value not in values:
        bag.add(
            rules.PLATFORM_UNSUPPORTED,
            f"does not function on {platform.value} — it declares platforms "
            + ", ".join(values),
            name,
        )
        return False
    return values


# --- Android ----------------------------------------------------------------


def _check_android(
    sidecar: Sidecar, android: AndroidSection, *, profile: ConsumerProfile, bag: DiagnosticBag
) -> None:
    name = sidecar.distribution
    owned = android.java_namespaces

    _check_namespaces(sidecar, android, profile=profile, bag=bag)
    _check_application_values(sidecar, android, bag=bag)
    _check_dependencies(sidecar, android, profile=profile, bag=bag)
    _check_repositories(sidecar, android, bag=bag)
    _check_components(sidecar, android, bag=bag)
    _check_keeps(sidecar, android, bag=bag)
    if profile.verify_resources:
        _check_sources(sidecar, android, bag=bag)

    for pattern in android.keep_classes:
        base = naming.keep_pattern_base(pattern)
        if not base or not any(contains(o, base) for o in owned):
            bag.add(
                rules.KEEP_OUTSIDE_NAMESPACE,
                f"keep pattern `{pattern}` is not within an owned namespace "
                f"({', '.join(owned) if owned else 'none declared'}) — a dependency's "
                "classes need a [[android.contributes.r8.keep]] entry naming it",
                name,
            )


def _check_namespaces(
    sidecar: Sidecar, android: AndroidSection, *, profile: ConsumerProfile, bag: DiagnosticBag
) -> None:
    name = sidecar.distribution
    owned = android.java_namespaces

    needs_ownership = bool(
        android.src_java
        or android.src_kotlin
        or any(c.producer_sourced for c in android.components)
        or android.keep_classes
    )
    if needs_ownership and not owned:
        bag.add(
            rules.NAMESPACE_REQUIRED,
            "contributes Java/Kotlin source, a producer-sourced component or a keep "
            "pattern, so [android.owns].java_namespaces is required",
            name,
        )

    for namespace in owned:
        reserved = reserved_prefix(namespace, profile.reserved_namespaces)
        if reserved is not None:
            bag.add(
                rules.NAMESPACE_RESERVED,
                f"claims `{namespace}`, which falls under the reserved namespace "
                f"`{reserved}` — a toolchain's bootstrap namespace is not claimable",
                name,
            )
        if is_single_label(namespace):
            bag.add(
                rules.NAMESPACE_SINGLE_LABEL,
                f"claims the single-label namespace `{namespace}`; it is ownable, but it "
                "claims a top-level name and makes accidental overlap likelier",
                name,
            )

    for index, first in enumerate(owned):
        for second in owned[index + 1 :]:
            if naming.overlaps(first, second):
                bag.add(
                    rules.NAMESPACE_OVERLAP,
                    f"claims `{first}` and `{second}`, which overlap",
                    name,
                )


def _check_application_values(sidecar: Sidecar, android: AndroidSection, *, bag: DiagnosticBag) -> None:
    name = sidecar.distribution
    seen: set[str] = set()
    for value in android.application_values:
        if value.id in seen:
            bag.add(
                rules.APPLICATION_VALUE_DUPLICATE,
                f"declares application value `{value.id}` more than once; ids are unique "
                "within a sidecar",
                name,
            )
        seen.add(value.id)

    for component in android.components:
        for link in component.view_links:
            for ref in link.refs():
                if ref.is_reference and ref.application_value not in seen:
                    bag.add(
                        rules.APPLICATION_VALUE_UNRESOLVED_REF,
                        f"`{component.name}` references application value "
                        f"`{ref.application_value}`, which this sidecar does not declare — "
                        "inline use declares nothing, and an implicit declaration would "
                        "have no `reason`",
                        name,
                    )


def _check_dependencies(
    sidecar: Sidecar, android: AndroidSection, *, profile: ConsumerProfile, bag: DiagnosticBag
) -> None:
    name = sidecar.distribution
    foreground_permissions = [
        p.name
        for p in android.permissions
        if p.name.startswith("android.permission.FOREGROUND_SERVICE")
    ]
    for component in android.components:
        if not component.foreground_service_type:
            continue
        if component.kind != "service":
            bag.add(
                rules.FOREGROUND_TYPE_ON_NON_SERVICE,
                f"declares foreground_service_type on {component.kind} "
                f"`{component.name}`; only a service runs in the foreground",
                name,
            )
        elif not foreground_permissions:
            # 8.S4 — the platform requires the pair, and refuses at service
            # start with a message naming neither half.
            bag.add(
                rules.FOREGROUND_TYPE_WITHOUT_PERMISSION,
                f"`{component.name}` declares foreground_service_type "
                f"`{component.foreground_service_type}` and this distribution "
                "contributes no android.permission.FOREGROUND_SERVICE_* permission",
                name,
            )

    for query in android.queries:
        # §6.12 — exactly one target. Both is ambiguous; neither declares
        # visibility of nothing while reading as though it declared something.
        declared = [bool(query.package), bool(query.provider_authority)]
        if sum(declared) != 1:
            bag.add(
                rules.QUERY_FORM,
                "declares a <queries> entry with "
                + ("both `package` and `provider_authority`" if all(declared) else "neither")
                + "; exactly one is required",
                name,
            )

    for entry in android.meta_data:
        # §6.10 — a resource reference names something the producer cannot
        # supply and the application has not been asked for; it fails in AAPT
        # with no trace back to the sidecar.
        declared_resources = {
            f"@{p.resource_type}/{p.key}"
            for p in android.prerequisites
            if p.kind is PrerequisiteKind.RESOURCE
        }
        if (
            isinstance(entry.value, str)
            and entry.value[:1] in ("@", "?")
            and entry.value not in declared_resources
        ):
            bag.add(
                rules.META_DATA_RESOURCE_REFERENCE,
                f"sets <meta-data {entry.key}> to `{entry.value}`, a resource "
                "reference; contributed resources are out of scope (§11), so the "
                "value must be a literal",
                name,
            )

    for dependency in android.gradle_dependencies:
        versions = [v for v in (dependency.exact_version, dependency.at_least, dependency.below) if v]
        for version in versions:
            if naming.is_changing_version(version):
                bag.add(
                    rules.DEPENDENCY_VERSION_CHANGING,
                    f"`{dependency.render()}` uses a changing version; a version whose "
                    "content can change under a fixed spelling defeats the record of §9",
                    name,
                )
            elif naming.is_dynamic_version(version):
                bag.add(
                    rules.DEPENDENCY_VERSION_UNBOUNDED,
                    f"`{dependency.render()}` uses a dynamic or range version; use an exact "
                    "`coordinate`, or `module` with a bounded { at_least, below }",
                    name,
                )
        if dependency.configuration in PROCESSOR_CONFIGURATIONS:
            # §6.5 — closed set, and this is why. A coordinate on a processor
            # configuration is code the build runs, which §2.1 excludes however
            # it arrives; a consumer rejects it whether or not it implements it.
            bag.add(
                rules.DEPENDENCY_CONFIGURATION,
                f"`{dependency.render()}` asks for configuration "
                f"`{dependency.configuration}`, which makes the build run code from "
                "that artifact; processor configurations may not be declared (§2.1)",
                name,
            )
        elif dependency.configuration not in profile.gradle_configurations:
            bag.add(
                rules.DEPENDENCY_CONFIGURATION,
                f"`{dependency.render()}` asks for configuration "
                f"`{dependency.configuration}`, which this consumer does not implement",
                name,
            )


def _check_repositories(sidecar: Sidecar, android: AndroidSection, *, bag: DiagnosticBag) -> None:
    name = sidecar.distribution
    for repository in android.gradle_repositories:
        if not repository.scope:
            bag.add(
                rules.REPOSITORY_SCOPE_MISSING,
                f"repository {repository.url} declares neither `groups` nor `modules`; a "
                "contributed repository must not participate in resolution for anything "
                "outside a declared scope",
                name,
            )
        if "@" in repository.url.split("//", 1)[-1].split("/", 1)[0]:
            bag.add(
                rules.REPOSITORY_CREDENTIAL_IN_URL,
                f"repository url {repository.url!r} carries user-info; a credential must "
                "never appear in a sidecar, in any field",
                name,
            )


def _check_components(sidecar: Sidecar, android: AndroidSection, *, bag: DiagnosticBag) -> None:
    name = sidecar.distribution
    owned = android.java_namespaces
    declared_modules = set(android.declared_modules)
    seen: set[str] = set()

    for component in android.components:
        if component.name in seen:
            bag.add(
                rules.COMPONENT_DUPLICATE,
                f"registers `{component.name}` more than once",
                name,
            )
        seen.add(component.name)

        if component.producer_sourced:
            if not any(contains(o, component.name) for o in owned):
                bag.add(
                    rules.COMPONENT_OUTSIDE_NAMESPACE,
                    f"component `{component.name}` is not under an owned namespace "
                    f"({', '.join(owned) if owned else 'none declared'}); a class from a "
                    "declared dependency needs `from_dependency`",
                    name,
                )
        elif component.from_dependency not in declared_modules:
            bag.add(
                rules.COMPONENT_DEPENDENCY_UNDECLARED,
                f"component `{component.name}` names `from_dependency = "
                f"\"{component.from_dependency}\"`, which this sidecar does not declare "
                "as a Gradle dependency",
                name,
            )

        if component.exported_required and not component.reason:
            bag.add(
                rules.KEY_REQUIRED,
                f"component `{component.name}` declares `exported_required` without a "
                "`reason`, which is required when present",
                name,
            )

        if component.view_links:
            if component.kind != "activity" or not component.exported_required:
                bag.add(
                    rules.VIEW_LINKS_INVALID,
                    f"`{component.name}` declares view_links but is not an exported "
                    "activity; a link target that is not exported is unreachable",
                    name,
                )
        if component.intent_filters:
            if component.exported_required or component.view_links:
                bag.add(
                    rules.INTENT_FILTER_INVALID,
                    f"`{component.name}` declares intent_filters alongside "
                    "`exported_required` or `view_links`; a vendor action is valid only "
                    "on a component that is not exported",
                    name,
                )


def _check_keeps(sidecar: Sidecar, android: AndroidSection, *, bag: DiagnosticBag) -> None:
    name = sidecar.distribution
    declared_modules = set(android.declared_modules)
    for keep in android.dependency_keeps:
        if keep.from_dependency not in declared_modules:
            bag.add(
                rules.KEEP_DEPENDENCY_UNDECLARED,
                f"keep pattern `{keep.pattern}` names `{keep.from_dependency}`, which this "
                "sidecar does not declare as a Gradle dependency",
                name,
            )


def _check_sources(sidecar: Sidecar, android: AndroidSection, *, bag: DiagnosticBag) -> None:
    """§4.1's path rules, and §6.1 rule 1 on both the path and the declared package."""
    source = sidecar.source
    if source is None:  # pragma: no cover - only in synthesized sidecars
        return
    name = sidecar.distribution
    owned = android.java_namespaces

    for roots, suffix, pattern in (
        (android.src_java, ".java", _JAVA_PACKAGE),
        (android.src_kotlin, ".kt", _KOTLIN_PACKAGE),
    ):
        for root in roots:
            try:
                files = source.walk(root, suffix)
            except ResourceError as exc:
                bag.add(_resource_rule(exc), f"source root `{root}` {exc.reason}", name)
                continue
            for relpath in files:
                inner = relpath[len(normalize(root)) :].strip("/")
                path_namespace = ".".join(inner.split("/")[:-1])
                if path_namespace and not any(contains(o, path_namespace) for o in owned):
                    bag.add(
                        rules.SOURCE_OUTSIDE_NAMESPACE,
                        f"`{relpath}` sits at package path `{path_namespace}`, outside "
                        f"({', '.join(owned) if owned else 'no owned namespace'})",
                        name,
                    )
                try:
                    text = source.read_text(relpath)
                except ResourceError as exc:
                    bag.add(_resource_rule(exc), f"`{relpath}` {exc.reason}", name)
                    continue
                match = pattern.search(text)
                declared_package = match.group(1) if match else ""
                if declared_package and not any(contains(o, declared_package) for o in owned):
                    bag.add(
                        rules.SOURCE_OUTSIDE_NAMESPACE,
                        f"`{relpath}` declares `package {declared_package}`, outside "
                        f"({', '.join(owned) if owned else 'no owned namespace'})",
                        name,
                    )


def _resource_rule(exc: ResourceError):
    return {
        "escapes": rules.RESOURCE_ESCAPES,
        "symlink": rules.RESOURCE_SYMLINK,
        "encoding": rules.RESOURCE_NOT_UTF8,
    }.get(exc.kind, rules.SOURCE_ROOT_MISSING)


# --- iOS --------------------------------------------------------------------


def _check_ios(
    sidecar: Sidecar, ios: IosSection, *, profile: ConsumerProfile, bag: DiagnosticBag
) -> None:
    name = sidecar.distribution

    for kind in PrerequisiteKind:
        entries = ios.of_kind(kind)
        if kind is PrerequisiteKind.APPLICATION_VALUE:
            # §7.3 — an account identifier is neither application-authored text
            # nor an application-granted capability; both have their own table.
            for entry in entries:
                key = entry.info_plist_key or ""
                if key.endswith("UsageDescription"):
                    bag.add(
                        rules.PLIST_USAGE_DESCRIPTION,
                        f"delivers an application value to `{key}`; a purpose string is "
                        "user-facing text the application authors — declare it under "
                        "[[ios.requires.usage_descriptions]] instead",
                        name,
                    )
                elif key in schema.CAPABILITY_KEYS:
                    bag.add(
                        rules.PLIST_CAPABILITY_KEY,
                        f"delivers an application value to `{key}`, which grants the "
                        "application a capability or restricts who may install it — "
                        "declare it under [[ios.requires.plist_capabilities]] instead",
                        name,
                    )

        if kind is PrerequisiteKind.APP_EXTENSION:
            # §7.3 — an open vocabulary (§4.4): the consumer rejects an
            # extension point it cannot check for, rather than dropping it.
            for entry in entries:
                if entry.extension_kind not in profile.extension_kinds:
                    bag.add(
                        rules.EXTENSION_KIND_UNIMPLEMENTED,
                        f"declares app extension kind `{entry.extension_kind}`, which "
                        "this consumer does not implement",
                        name,
                    )
        if kind in (PrerequisiteKind.APP_EXTENSION, PrerequisiteKind.URL_SCHEME):
            seen: set[str] = set()
            for entry in entries:
                if entry.key in seen:
                    bag.add(
                        rules.PREREQUISITE_ID_DUPLICATE,
                        f"declares {kind.value} id `{entry.key}` more than once; the "
                        "application answers on (distribution, id), so two entries "
                        "sharing an id cannot be answered separately",
                        name,
                    )
                seen.add(entry.key)
        for entry in entries:
            _check_conditional_reason(name, entry, bag)

    packages: set[str] = set()
    for package in ios.swift_packages:
        if package.name in packages:
            bag.add(
                rules.SWIFT_PACKAGE_DUPLICATE_NAME,
                f"declares two Swift packages named `{package.name}`; the name is a local "
                "handle other tables refer to, so it must be unique within the sidecar",
                name,
            )
        packages.add(package.name)
        if package.requirement_kind == "branch":
            bag.add(
                rules.SWIFT_BRANCH_REQUIREMENT,
                f"`{package.name}` declares a branch requirement, which must not appear in "
                "a distribution published to a package index",
                name,
            )

    registered: set[str] = set()
    for module in ios.python_modules:
        if module.name in registered:
            # §7.7 states the cross-distribution case, but one sidecar
            # registering a name twice is the same ambiguity with a shorter
            # path to it: the second registration has no defined meaning.
            bag.add(
                rules.PYTHON_MODULE_DUPLICATE,
                f"registers the Python module `{module.name}` more than once; a module "
                "name is registered against exactly one implementation",
                name,
            )
        registered.add(module.name)
        if not _PYTHON_IDENTIFIER.match(module.name):
            bag.add(
                rules.PYTHON_MODULE_NAME_INVALID,
                f"python module `{module.name}` must be a single ASCII identifier; dotted "
                "names are not permitted",
                name,
            )
        if module.swift_package not in packages:
            bag.add(
                rules.PYTHON_MODULE_PACKAGE_UNDECLARED,
                f"python module `{module.name}` names Swift package "
                f"`{module.swift_package}`, which this sidecar does not declare",
                name,
            )
        if module.init is not None and not _C_IDENTIFIER.match(module.init):
            bag.add(
                rules.PYTHON_MODULE_INIT_INVALID,
                f"python module `{module.name}` declares init `{module.init}`, which is not "
                "a valid C identifier",
                name,
            )

    if ios.accessed_api_types and not ios.src_swift:
        # §7.5 — a Swift package carries its own PrivacyInfo.xcprivacy, which is
        # both the better answer and the one Apple documents. This table exists
        # only for source that has no target of its own.
        bag.add(
            rules.ACCESSED_API_WITHOUT_SOURCE,
            "declares accessed_api_types without contributing Swift; a Swift "
            "package (§7.4) carries its own privacy manifest and needs no "
            "declaration here",
            name,
        )

    for identifier in ios.skadnetwork_identifiers:
        # §7.6 — a mistyped identifier does not fail; it silently matches no
        # network and loses that network's attribution, which is exactly the
        # quiet wrong answer this specification converts into a diagnostic.
        if identifier != identifier.lower() or not identifier.endswith(".skadnetwork"):
            bag.add(
                rules.SKADNETWORK_IDENTIFIER_INVALID,
                f"declares SKAdNetwork identifier `{identifier}`, which is not an "
                "ad network identifier: Apple's form is lowercase and ends "
                "`.skadnetwork`",
                name,
            )

    for key in (*ios.info_plist_values, *ios.info_plist_append):
        if key == "SKAdNetworkItems":
            bag.add(
                rules.SKADNETWORK_ITEMS_KEY,
                "contributes `SKAdNetworkItems` directly; declare the identifiers "
                "under [ios.contributes.info_plist] skadnetwork_identifiers and let "
                "the consumer render the dictionaries",
                name,
            )
        if key in schema.CAPABILITY_KEYS:
            bag.add(
                rules.PLIST_CAPABILITY_KEY,
                f"contributes `{key}`, which grants the application a capability or "
                "restricts who may install it; that is the application's to declare — "
                "use [[ios.requires.plist_capabilities]] instead",
                name,
            )

    for key, value in ios.info_plist_values.items():
        if key in schema.CAPABILITY_KEYS:
            continue  # already reported, with the rule that says why
        if key.endswith("UsageDescription"):
            bag.add(
                rules.PLIST_USAGE_DESCRIPTION,
                f"sets `{key}` as an info_plist value; a purpose string is user-facing, "
                "localized and read by App Store review, so it belongs to the application "
                "— declare it under [[ios.requires.usage_descriptions]] instead",
                name,
            )
        elif key in profile.managed_plist_keys:
            bag.add(
                rules.PLIST_CONSUMER_MANAGED,
                f"sets `{key}`, which this consumer manages itself",
                name,
            )

    if sidecar.source is not None and profile.verify_resources:
        for root in ios.src_swift:
            try:
                sidecar.source.walk(root, ".swift")
            except ResourceError as exc:
                bag.add(_resource_rule(exc), f"swift source root `{root}` {exc.reason}", name)


def _check_conditional_reason(name: str, entry: Prerequisite, bag: DiagnosticBag) -> None:
    """§7.3: a conditional entry's ``reason`` must state the condition that applies it.

    A warning rather than an error: "states the condition" is a property of
    English prose, and this can only observe a missing hedge. §12.1's real
    remedy is review — a requirement wrongly marked conditional converts a build
    failure that names the problem into a line in a report.
    """
    if not entry.conditional:
        return
    lowered = entry.reason.lower()
    if not any(hint in lowered for hint in ("only if", "only when", "if you", "when you")):
        bag.add(
            rules.PREREQUISITE_CONDITION_UNSTATED,
            f"conditional {entry.kind.value} `{entry.key}` does not state the condition "
            "that makes it apply; a conditional prerequisite is only useful if a reader "
            "can tell whether it applies to them",
            name,
        )
