"""Typed declarations: what a sidecar says, after it has been found valid.

Nothing here validates. These are built only from a document that already
passed :mod:`native_integration.schema`, which is why the field types can be
trusted — §4.3's "never by parsing it partially" applies to the model too.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .contract import ContractVersion
from .naming import Module, split_coordinate
from .resources import SidecarSource


class Platform(str, enum.Enum):
    ANDROID = "android"
    IOS = "ios"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


# --- shared -----------------------------------------------------------------


@dataclass(frozen=True)
class Ref:
    """A literal, or §6.3's inline reference to an application value."""

    literal: str | None = None
    application_value: str | None = None

    @classmethod
    def of(cls, raw: Any) -> "Ref":
        if isinstance(raw, dict):
            return cls(application_value=raw["application_value"])
        return cls(literal=raw)

    @property
    def is_reference(self) -> bool:
        return self.application_value is not None

    def render(self) -> str:
        return self.literal if self.literal is not None else "${%s}" % self.application_value


# --- Android ----------------------------------------------------------------


@dataclass(frozen=True)
class ApplicationValue:
    id: str
    reason: str
    manifest_meta_data: str | None = None
    #: §6.3 — an AGP manifest placeholder, for a value a declared dependency's
    #: own manifest reads. Build-global like `manifest_meta_data`, so the two
    #: share one coalescing rule.
    manifest_placeholder: str | None = None


@dataclass(frozen=True)
class GradleDependency:
    """§6.5's two forms, kept distinguishable after parsing."""

    module: Module
    exact_version: str | None = None
    at_least: str | None = None
    below: str | None = None
    configuration: str = "implementation"

    @property
    def is_range(self) -> bool:
        return self.exact_version is None

    @property
    def requested(self) -> str:
        if self.exact_version is not None:
            return self.exact_version
        return f"[{self.at_least}, {self.below})"

    def render(self) -> str:
        return f"{self.module}:{self.requested}"


@dataclass(frozen=True)
class GradleRepository:
    url: str
    reason: str
    groups: tuple[str, ...] = ()
    modules: tuple[str, ...] = ()
    credentials_required: bool = False

    @property
    def scope(self) -> tuple[str, ...]:
        return (*self.groups, *self.modules)

    def serves(self, module: Module) -> bool:
        return str(module) in self.modules or module.group in self.groups


@dataclass(frozen=True)
class AccessedApiType:
    """§7.5 — a required-reason API the contributed Swift touches."""

    type: str
    reasons: tuple[str, ...]
    reason: str | None = None


@dataclass(frozen=True)
class Query:
    """§6.12 — one `<queries>` entry: a package, or a provider authority."""

    reason: str
    package: str | None = None
    provider_authority: str | None = None

    @property
    def target(self) -> str:
        return self.package or self.provider_authority or ""


@dataclass(frozen=True)
class ContributedMetaData:
    """§6.10 — a `<meta-data>` entry whose value the producer knows."""

    key: str
    value: str | int | bool
    reason: str

    @property
    def rendered(self) -> str:
        """The literal written to `android:value` (§6.10's mapping)."""
        if isinstance(self.value, bool):
            return "true" if self.value else "false"
        return str(self.value)


@dataclass(frozen=True)
class Permission:
    name: str
    reason: str | None = None
    #: §6.7 — `android:maxSdkVersion`, above which the permission is not needed.
    max_sdk_version: int | None = None
    #: §6.7 — `android:usesPermissionFlags="neverForLocation"`.
    never_for_location: bool = False


@dataclass(frozen=True)
class Feature:
    name: str
    #: §6.7 — every producer-declared feature is `required = false`, always.
    required: bool = False


@dataclass(frozen=True)
class ViewLink:
    scheme: Ref
    host: Ref | None = None
    path_prefix: Ref | None = None

    def refs(self) -> tuple[Ref, ...]:
        return tuple(r for r in (self.scheme, self.host, self.path_prefix) if r is not None)


@dataclass(frozen=True)
class IntentFilter:
    action: str


@dataclass(frozen=True)
class Component:
    kind: str
    name: str
    from_dependency: str | None = None
    exported_required: bool = False
    reason: str | None = None
    #: §6.8 — `android:foregroundServiceType`, mandatory on Android 14+ for a
    #: foreground service and valid on nothing else.
    foreground_service_type: str | None = None
    view_links: tuple[ViewLink, ...] = ()
    intent_filters: tuple[IntentFilter, ...] = ()

    @property
    def producer_sourced(self) -> bool:
        return self.from_dependency is None


@dataclass(frozen=True)
class DependencyKeep:
    pattern: str
    from_dependency: str


@dataclass(frozen=True)
class AndroidSection:
    java_namespaces: tuple[str, ...] = ()
    compile_sdk: int | None = None
    min_sdk: int | None = None
    target_sdk: int | None = None
    #: §6.2 — a floor whose axis is boolean: the application has enabled core
    #: library desugaring, and the consumer never enables it for the producer.
    core_library_desugaring: bool = False
    application_values: tuple[ApplicationValue, ...] = ()
    src_java: tuple[str, ...] = ()
    src_kotlin: tuple[str, ...] = ()
    gradle_dependencies: tuple[GradleDependency, ...] = ()
    gradle_repositories: tuple[GradleRepository, ...] = ()
    permissions: tuple[Permission, ...] = ()
    features: tuple[Feature, ...] = ()
    meta_data: tuple[ContributedMetaData, ...] = ()
    #: §6.11 — application_files, resources, application_classes and app_links.
    prerequisites: tuple[Prerequisite, ...] = ()
    #: §6.12 — package visibility for the producer's own code.
    queries: tuple[Query, ...] = ()
    components: tuple[Component, ...] = ()
    keep_classes: tuple[str, ...] = ()
    dependency_keeps: tuple[DependencyKeep, ...] = ()

    @property
    def floors(self) -> dict[str, int]:
        return {
            name: value
            for name, value in (
                ("compile_sdk", self.compile_sdk),
                ("min_sdk", self.min_sdk),
                ("target_sdk", self.target_sdk),
            )
            if value is not None
        }

    @property
    def declared_modules(self) -> tuple[str, ...]:
        return tuple(str(d.module) for d in self.gradle_dependencies)


# --- iOS --------------------------------------------------------------------


class PrerequisiteKind(str, enum.Enum):
    ENTITLEMENT = "entitlements"
    USAGE_DESCRIPTION = "usage_descriptions"
    APP_EXTENSION = "app_extensions"
    APPLICATION_FILE = "application_files"
    URL_SCHEME = "url_schemes"
    PLIST_CAPABILITY = "plist_capabilities"
    APPLICATION_VALUE = "application_values"
    ANDROID_FILE = "android:application_files"
    RESOURCE = "resources"
    APPLICATION_CLASS = "application_classes"
    APP_LINK = "app_links"

    @property
    def table(self) -> str:
        """The TOML table this kind is declared in.

        ANDROID_FILE and APPLICATION_FILE share the spelling `application_files`
        and differ only in where the file goes — a bundle on iOS, the assets
        directory on Android. Identical enum *values* would make one a silent
        alias of the other, so the value carries a platform prefix and this is
        what a sidecar and a diagnostic use.
        """
        _, _, name = self.value.rpartition(":")
        return name

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.table


#: Which tables are joined on a key the platform supplies, and which on an `id`
#: the producer invents. §2.2: both are scoped by the declaring distribution;
#: only the source of the local part differs.
PRODUCER_LOCAL_IDS = (
    PrerequisiteKind.APP_EXTENSION,
    PrerequisiteKind.URL_SCHEME,
    PrerequisiteKind.APPLICATION_VALUE,
    PrerequisiteKind.APPLICATION_CLASS,
    PrerequisiteKind.APP_LINK,
)


@dataclass(frozen=True)
class Prerequisite:
    """One §7.3 entry. ``key`` is the join key, whatever the table calls it."""

    kind: PrerequisiteKind
    key: str
    reason: str
    conditional: bool = False
    extension_kind: str | None = None
    #: The single plist array entry a `plist_capabilities` prerequisite needs.
    value: str | None = None
    #: §7.3 — where an `application_values` answer is written. Required there,
    #: because iOS has no inline reference site for a value with no key.
    info_plist_key: str | None = None
    #: §6.11 — a resource type, for a `resources` entry.
    resource_type: str | None = None
    #: §6.11 — the vendor-fixed path of an application-owned class, relative to
    #: the application's own ID. Both halves are optional: some vendors fix only
    #: the behaviour.
    package_suffix: str | None = None
    class_name: str | None = None

    @property
    def producer_local(self) -> bool:
        return self.kind in PRODUCER_LOCAL_IDS

    @property
    def field_name(self) -> str:
        if self.producer_local:
            return "id"
        return "name" if self.kind is PrerequisiteKind.APPLICATION_FILE else "key"

    @property
    def join_key(self) -> str:
        """How the application's answer is looked up (§2.2)."""
        if self.kind is PrerequisiteKind.PLIST_CAPABILITY:
            return f"{self.key}={self.value}"
        if self.kind is PrerequisiteKind.RESOURCE:
            return f"{self.resource_type}/{self.key}"
        return self.key


@dataclass(frozen=True)
class SwiftPackage:
    name: str
    url: str
    requirement_kind: str  # exact | from | revision | branch
    requirement_value: str
    products: tuple[str, ...] = ()

    def render(self) -> str:
        return f"{self.name} ({self.url}, {self.requirement_kind} {self.requirement_value})"


@dataclass(frozen=True)
class PythonModule:
    name: str
    swift_package: str
    init: str | None = None

    @property
    def init_symbol(self) -> str:
        return self.init or f"PyInit_{self.name}"


@dataclass(frozen=True)
class IosSection:
    swift_symbol_prefixes: tuple[str, ...] = ()
    deployment_target: str | None = None
    prerequisites: tuple[Prerequisite, ...] = ()
    swift_packages: tuple[SwiftPackage, ...] = ()
    src_swift: tuple[str, ...] = ()
    info_plist_values: Mapping[str, Any] = field(default_factory=dict)
    info_plist_append: Mapping[str, Sequence[Any]] = field(default_factory=dict)
    #: §7.6 — ad network identifiers the consumer renders SKAdNetworkItems from.
    skadnetwork_identifiers: tuple[str, ...] = ()
    #: §7.8 — link so Objective-C categories in static libraries are loaded.
    objc_categories: bool = False
    #: §7.5 — required-reason APIs, merged into the application's manifest.
    accessed_api_types: tuple[AccessedApiType, ...] = ()
    python_modules: tuple[PythonModule, ...] = ()

    def of_kind(self, kind: PrerequisiteKind) -> tuple[Prerequisite, ...]:
        return tuple(p for p in self.prerequisites if p.kind is kind)


# --- the sidecar ------------------------------------------------------------


@dataclass(frozen=True)
class Sidecar:
    distribution: str
    version: str
    contract: ContractVersion
    platforms: tuple[str, ...] | None
    android: AndroidSection | None = None
    ios: IosSection | None = None
    source: SidecarSource | None = None

    @property
    def name(self) -> str:
        return self.distribution

    def section(self, platform: Platform) -> AndroidSection | IosSection | None:
        return self.android if platform is Platform.ANDROID else self.ios


# --- construction from a validated document ---------------------------------


def _refs(entry: Mapping[str, Any], key: str) -> Ref | None:
    return Ref.of(entry[key]) if key in entry else None


def build_android(table: Mapping[str, Any]) -> AndroidSection:
    owns = table.get("owns", {})
    requires = table.get("requires", {})
    contributes = table.get("contributes", {})
    src = contributes.get("src", {})
    r8 = contributes.get("r8", {})

    dependencies: list[GradleDependency] = []
    for entry in contributes.get("gradle_dependencies", []):
        configuration = entry.get("configuration", "implementation")
        if "coordinate" in entry:
            module, version = split_coordinate(entry["coordinate"])
            dependencies.append(
                GradleDependency(module=module, exact_version=version, configuration=configuration)
            )
        else:
            bounds = entry.get("version", {})
            dependencies.append(
                GradleDependency(
                    module=Module.parse(entry["module"]),
                    at_least=bounds.get("at_least"),
                    below=bounds.get("below"),
                    configuration=configuration,
                )
            )

    components: list[Component] = []
    for entry in contributes.get("components", []):
        components.append(
            Component(
                kind=entry["kind"],
                name=entry["name"],
                from_dependency=entry.get("from_dependency"),
                exported_required=bool(entry.get("exported_required", False)),
                reason=entry.get("reason"),
                foreground_service_type=entry.get("foreground_service_type"),
                view_links=tuple(
                    ViewLink(
                        scheme=Ref.of(link["scheme"]),
                        host=_refs(link, "host"),
                        path_prefix=_refs(link, "path_prefix"),
                    )
                    for link in entry.get("view_links", [])
                ),
                intent_filters=tuple(
                    IntentFilter(action=flt["action"]) for flt in entry.get("intent_filters", [])
                ),
            )
        )

    android_prerequisites: list[Prerequisite] = []
    for kind in (
        PrerequisiteKind.ANDROID_FILE,
        PrerequisiteKind.RESOURCE,
        PrerequisiteKind.APPLICATION_CLASS,
        PrerequisiteKind.APP_LINK,
    ):
        for entry in requires.get(kind.table, []):
            android_prerequisites.append(
                Prerequisite(
                    kind=kind,
                    key=entry[_PREREQUISITE_KEY[kind]],
                    reason=entry["reason"],
                    conditional=bool(entry.get("conditional", False)),
                    resource_type=entry.get("type"),
                    package_suffix=entry.get("package_suffix"),
                    class_name=entry.get("name") if kind is PrerequisiteKind.APPLICATION_CLASS else None,
                )
            )

    return AndroidSection(
        java_namespaces=tuple(owns.get("java_namespaces", [])),
        prerequisites=tuple(android_prerequisites),
        compile_sdk=requires.get("compile_sdk"),
        min_sdk=requires.get("min_sdk"),
        target_sdk=requires.get("target_sdk"),
        core_library_desugaring=bool(requires.get("core_library_desugaring", False)),
        application_values=tuple(
            ApplicationValue(
                id=v["id"],
                reason=v["reason"],
                manifest_meta_data=v.get("manifest_meta_data"),
                manifest_placeholder=v.get("manifest_placeholder"),
            )
            for v in requires.get("application_values", [])
        ),
        src_java=tuple(src.get("java", [])),
        src_kotlin=tuple(src.get("kotlin", [])),
        gradle_dependencies=tuple(dependencies),
        gradle_repositories=tuple(
            GradleRepository(
                url=r["url"],
                reason=r["reason"],
                groups=tuple(r.get("groups", [])),
                modules=tuple(r.get("modules", [])),
                credentials_required=bool(r.get("credentials_required", False)),
            )
            for r in contributes.get("gradle_repositories", [])
        ),
        permissions=tuple(
            Permission(
                name=p["name"],
                reason=p.get("reason"),
                max_sdk_version=p.get("max_sdk_version"),
                never_for_location=bool(p.get("never_for_location", False)),
            )
            for p in contributes.get("permissions", [])
        ),
        features=tuple(Feature(name=f["name"]) for f in contributes.get("features", [])),
        meta_data=tuple(
            ContributedMetaData(key=m["key"], value=m["value"], reason=m["reason"])
            for m in contributes.get("meta_data", [])
        ),
        queries=tuple(
            Query(
                reason=q["reason"],
                package=q.get("package"),
                provider_authority=q.get("provider_authority"),
            )
            for q in contributes.get("queries", [])
        ),
        components=tuple(components),
        keep_classes=tuple(r8.get("keep_classes", [])),
        dependency_keeps=tuple(
            DependencyKeep(pattern=k["pattern"], from_dependency=k["from_dependency"])
            for k in r8.get("keep", [])
        ),
    )


_PREREQUISITE_KEY = {
    PrerequisiteKind.ENTITLEMENT: "key",
    PrerequisiteKind.USAGE_DESCRIPTION: "key",
    PrerequisiteKind.APP_EXTENSION: "id",
    PrerequisiteKind.APPLICATION_FILE: "name",
    PrerequisiteKind.URL_SCHEME: "id",
    PrerequisiteKind.PLIST_CAPABILITY: "key",
    PrerequisiteKind.APPLICATION_VALUE: "id",
    PrerequisiteKind.ANDROID_FILE: "name",
    PrerequisiteKind.RESOURCE: "name",
    PrerequisiteKind.APPLICATION_CLASS: "id",
    PrerequisiteKind.APP_LINK: "id",
}


def build_ios(table: Mapping[str, Any]) -> IosSection:
    requires = table.get("requires", {})
    contributes = table.get("contributes", {})
    plist = contributes.get("info_plist", {})

    prerequisites: list[Prerequisite] = []
    for kind, key_field in _PREREQUISITE_KEY.items():
        for entry in requires.get(kind.value, []):
            prerequisites.append(
                Prerequisite(
                    kind=kind,
                    key=entry[key_field],
                    reason=entry["reason"],
                    conditional=bool(entry.get("conditional", False)),
                    extension_kind=entry.get("kind"),
                    info_plist_key=entry.get("info_plist_key"),
                    value=entry.get("value"),
                )
            )

    return IosSection(
        swift_symbol_prefixes=tuple(table.get("swift_symbol_prefixes", [])),
        deployment_target=requires.get("deployment_target"),
        prerequisites=tuple(prerequisites),
        swift_packages=tuple(
            SwiftPackage(
                name=p["name"],
                url=p["url"],
                requirement_kind=next(iter(p["requirement"])),
                requirement_value=next(iter(p["requirement"].values())),
                products=tuple(p.get("products", [])),
            )
            for p in contributes.get("swift_packages", [])
        ),
        src_swift=tuple(contributes.get("src", {}).get("swift", [])),
        info_plist_values=dict(plist.get("values", {})),
        info_plist_append={k: tuple(v) for k, v in plist.get("append", {}).items()},
        skadnetwork_identifiers=tuple(plist.get("skadnetwork_identifiers", [])),
        objc_categories=bool(contributes.get("objc_categories", False)),
        accessed_api_types=tuple(
            AccessedApiType(
                type=a["type"],
                reasons=tuple(a["reasons"]),
                reason=a.get("reason"),
            )
            for a in contributes.get("accessed_api_types", [])
        ),
        python_modules=tuple(
            PythonModule(name=m["name"], swift_package=m["swift_package"], init=m.get("init"))
            for m in contributes.get("python_modules", [])
        ),
    )
