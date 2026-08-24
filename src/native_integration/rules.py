"""The rule registry: every obligation this library enforces, declared once.

Each :class:`~native_integration.diagnostics.Rule` carries the specification
section it comes from and the §8 requirement numbers it discharges. Two things
follow from keeping them here rather than inline at the point of use:

* the mapping from *requirement* to *code path* is enumerable, which is what
  ``docs/REQUIREMENTS.md`` and its coverage test rest on;
* a rule's severity is stated in one place, so "MUST fail" cannot decay into a
  warning through an edit at a call site.
"""

from __future__ import annotations

from .diagnostics import Rule, Severity

RULES: dict[str, Rule] = {}


def _rule(code: str, section: str, severity: Severity, *requirements: int) -> Rule:
    rule = Rule(code=code, section=section, severity=severity, requirements=requirements)
    if code in RULES:  # pragma: no cover - guards against copy-paste in this file
        raise ValueError(f"duplicate rule code {code!r}")
    RULES[code] = rule
    return rule


ERROR = Severity.ERROR
WARN = Severity.WARNING
NOTE = Severity.NOTE

# --- discovery (§3) ---------------------------------------------------------
MULTIPLE_ENTRY_POINTS = _rule("multiple-entry-points", "§3.4", ERROR, 4)
ENTRY_POINT_VALUE_INVALID = _rule("entry-point-value-invalid", "§3.1", ERROR, 3, 4)
SIDECAR_MISSING = _rule("sidecar-missing", "§4.1", ERROR, 4)
RESOURCE_UNREADABLE = _rule("resource-unreadable", "§3.2", ERROR, 4)

# --- the sidecar file (§4) --------------------------------------------------
TOML_INVALID = _rule("toml-invalid", "§4.1", ERROR, 1)
RESOURCE_ESCAPES = _rule("resource-escapes", "§4.1", ERROR, 4)
RESOURCE_SYMLINK = _rule("resource-symlink", "§4.1", ERROR, 4)
RESOURCE_NOT_UTF8 = _rule("resource-not-utf8", "§4.1", ERROR, 4)
CONTRACT_MISSING = _rule("contract-missing", "§4.3", ERROR, 1)
CONTRACT_MALFORMED = _rule("contract-malformed", "§4.3", ERROR, 1)
CONTRACT_MAJOR_MISMATCH = _rule("contract-major-mismatch", "§4.3", ERROR, 1)
CONTRACT_TOO_NEW = _rule("contract-too-new", "§4.3", ERROR, 1)
CONTRACT_UNDER_DECLARED = _rule("contract-under-declared", "§4.3", ERROR, 1)
UNKNOWN_KEY = _rule("unknown-key", "§4.4", ERROR, 1)
UNKNOWN_TOP_LEVEL = _rule("unknown-top-level", "§4.4", WARN, 1)
TYPE_INVALID = _rule("type-invalid", "§4.4", ERROR, 1)
KEY_REQUIRED = _rule("key-required", "§4.4", ERROR, 1)
PLATFORMS_INVALID = _rule("platforms-invalid", "§4.5", ERROR, 18)
PLATFORMS_CONTRADICTION = _rule("platforms-contradiction", "§4.5", ERROR, 18)
PLATFORM_UNSUPPORTED = _rule("platform-unsupported", "§4.5", ERROR, 18)

# --- ownership (§6.1) -------------------------------------------------------
NAMESPACE_REQUIRED = _rule("namespace-required", "§6.1", ERROR, 5)
NAMESPACE_RESERVED = _rule("namespace-reserved", "§6.1", ERROR, 5, 17)
NAMESPACE_OVERLAP = _rule("namespace-overlap", "§6.1", ERROR, 5, 17)
NAMESPACE_SINGLE_LABEL = _rule("namespace-single-label", "§6.1", WARN, 5)
SOURCE_OUTSIDE_NAMESPACE = _rule("source-outside-namespace", "§6.1", ERROR, 5, 17)
COMPONENT_OUTSIDE_NAMESPACE = _rule("component-outside-namespace", "§6.1", ERROR, 5, 17)

# --- floors (§6.2, §7.2) ----------------------------------------------------
FLOOR_UNMET = _rule("floor-unmet", "§6.2", ERROR, 8)

# --- application values (§6.3) ---------------------------------------------
APPLICATION_VALUE_DUPLICATE = _rule("application-value-duplicate", "§6.3", ERROR, 1)
APPLICATION_VALUE_UNRESOLVED_REF = _rule("application-value-unresolved-ref", "§6.3", ERROR, 8)
APPLICATION_VALUE_UNSUPPLIED = _rule("application-value-unsupplied", "§6.3", ERROR, 8, 26)
META_DATA_CONFLICT = _rule("meta-data-conflict", "§6.3", ERROR, 8)
META_DATA_APPLICATION_OVERRIDE = _rule("meta-data-application-override", "§6.3", NOTE, 8)

# --- source (§6.4, §7.5) ----------------------------------------------------
SOURCE_ROOT_MISSING = _rule("source-root-missing", "§6.4", ERROR, 4)

# --- native dependencies (§6.5, §7.4) --------------------------------------
DEPENDENCY_FORM = _rule("dependency-form", "§6.5", ERROR, 12)
DEPENDENCY_VERSION_CHANGING = _rule("dependency-version-changing", "§6.5", ERROR, 12)
DEPENDENCY_VERSION_UNBOUNDED = _rule("dependency-version-unbounded", "§6.5", ERROR, 12)
DEPENDENCY_CONFIGURATION = _rule("dependency-configuration", "§6.5", ERROR, 12)
DEPENDENCY_VERSION_SUBSTITUTED = _rule("dependency-version-substituted", "§6.5", NOTE, 12)
DEPENDENCY_CHECKSUM_MISMATCH = _rule("dependency-checksum-mismatch", "§6.5", ERROR, 12)
RESOLUTION_FAILED = _rule("resolution-failed", "§6.5", ERROR, 16)
SWIFT_PACKAGE_DUPLICATE_NAME = _rule("swift-package-duplicate-name", "§7.4", ERROR, 1)
SWIFT_BRANCH_REQUIREMENT = _rule("swift-branch-requirement", "§7.4", ERROR, 12)
SWIFT_GRAPH_UNPINNABLE = _rule("swift-graph-unpinnable", "§7.4", ERROR, 12)
SWIFT_BINARY_CHECKSUM_MISMATCH = _rule("swift-binary-checksum-mismatch", "§7.4", ERROR, 12)
SWIFT_BINARY_UNCHECKSUMMED = _rule("swift-binary-unchecksummed", "§7.4", WARN, 12)

# --- repositories (§6.6) ----------------------------------------------------
REPOSITORY_SCOPE_MISSING = _rule("repository-scope-missing", "§6.6", ERROR, 10)
REPOSITORY_SCOPE_OVERLAP = _rule("repository-scope-overlap", "§6.6", ERROR, 10)
REPOSITORY_CREDENTIAL_IN_URL = _rule("repository-credential-in-url", "§6.6", ERROR, 10)
REPOSITORY_CREDENTIAL_SHAPED = _rule("repository-credential-shaped", "§6.6", WARN, 10)
REPOSITORY_CREDENTIALS_MISSING = _rule("repository-credentials-missing", "§6.6", ERROR, 25, 26)
REPOSITORY_CONTRIBUTED = _rule("repository-contributed", "§6.6", NOTE, 10)

# --- permissions and features (§6.7) ---------------------------------------
FEATURE_REQUIRED_FORBIDDEN = _rule("feature-required-forbidden", "§6.7", ERROR, 6)
PERMISSION_SUPPRESSED = _rule("permission-suppressed", "§6.7", NOTE, 7)

# --- components (§6.8) ------------------------------------------------------
COMPONENT_DUPLICATE = _rule("component-duplicate", "§6.8", ERROR, 8)
COMPONENT_EXPORT_UNAPPROVED = _rule("component-export-unapproved", "§6.8", ERROR, 8)
COMPONENT_EXPORT_FORBIDDEN_KEY = _rule("component-export-forbidden-key", "§6.8", ERROR, 6)
COMPONENT_DEPENDENCY_UNDECLARED = _rule("component-dependency-undeclared", "§6.8", ERROR, 1)
COMPONENT_CLASS_ABSENT = _rule("component-class-absent", "§6.8", WARN, 1)
VIEW_LINKS_INVALID = _rule("view-links-invalid", "§6.8", ERROR, 13)
INTENT_FILTER_INVALID = _rule("intent-filter-invalid", "§6.8", ERROR, 24)

# --- shrinker (§6.9) --------------------------------------------------------
KEEP_OUTSIDE_NAMESPACE = _rule("keep-outside-namespace", "§6.9", ERROR, 11, 17)
KEEP_DEPENDENCY_UNDECLARED = _rule("keep-dependency-undeclared", "§6.9", ERROR, 11)
KEEP_MATCHES_FOREIGN_CLASS = _rule("keep-matches-foreign-class", "§6.9", ERROR, 11)

# --- iOS prerequisites (§7.3) ----------------------------------------------
PREREQUISITE_UNSATISFIED = _rule("prerequisite-unsatisfied", "§7.3", ERROR, 8, 21, 23)
PREREQUISITE_CONDITIONAL = _rule("prerequisite-conditional", "§7.3", NOTE, 22)
PREREQUISITE_CONDITION_UNSTATED = _rule("prerequisite-condition-unstated", "§7.3", WARN, 1)
PREREQUISITE_ID_DUPLICATE = _rule("prerequisite-id-duplicate", "§7.3", ERROR, 26)
EXTENSION_KIND_UNIMPLEMENTED = _rule("extension-kind-unimplemented", "§7.3", ERROR, 1)

# --- Info.plist (§7.6) ------------------------------------------------------
PLIST_USAGE_DESCRIPTION = _rule("plist-usage-description", "§7.6", ERROR, 6)
PLIST_CAPABILITY_KEY = _rule("plist-capability-key", "§7.6", ERROR, 6)
SKADNETWORK_IDENTIFIER_INVALID = _rule("skadnetwork-identifier-invalid", "§7.6", ERROR, 1)
SKADNETWORK_ITEMS_KEY = _rule("skadnetwork-items-key", "§7.6", ERROR, 1)
META_DATA_RESOURCE_REFERENCE = _rule("meta-data-resource-reference", "§6.10", ERROR, 1)
QUERY_FORM = _rule("query-form", "§6.12", ERROR, 1)
ACCESSED_API_WITHOUT_SOURCE = _rule("accessed-api-without-source", "§7.5", ERROR, 1)
FOREGROUND_TYPE_ON_NON_SERVICE = _rule("foreground-type-on-non-service", "§6.8", ERROR, 1)
FOREGROUND_TYPE_WITHOUT_PERMISSION = _rule(
    "foreground-type-without-permission", "§6.8", WARN, 1
)
PLIST_VALUE_CONFLICT = _rule("plist-value-conflict", "§7.6", ERROR, 1)
PLIST_CONSUMER_MANAGED = _rule("plist-consumer-managed", "§7.6", ERROR, 1)

# --- Python modules (§7.7) --------------------------------------------------
PYTHON_MODULE_NAME_INVALID = _rule("python-module-name-invalid", "§7.7", ERROR, 20)
PYTHON_MODULE_PACKAGE_UNDECLARED = _rule("python-module-package-undeclared", "§7.7", ERROR, 20)
PYTHON_MODULE_DUPLICATE = _rule("python-module-duplicate", "§7.7", ERROR, 20)
PYTHON_MODULE_INIT_INVALID = _rule("python-module-init-invalid", "§7.7", ERROR, 20)

# --- the record (§9) --------------------------------------------------------
RECORD_ABSENT = _rule("record-absent", "§9", ERROR, 9)
RECORD_DRIFT = _rule("record-drift", "§9", ERROR, 9)
ARTIFACT_PERMISSION = _rule("artifact-permission", "§9", NOTE, 19)
ARTIFACT_FEATURE_OVERRIDDEN = _rule("artifact-feature-overridden", "§9", WARN, 19)
ARTIFACT_EXPORTED_COMPONENT = _rule("artifact-exported-component", "§9", WARN, 19)
ARTIFACT_PROGUARD_RULES = _rule("artifact-proguard-rules", "§9", WARN, 19)
PACKAGING_COLLISION = _rule("packaging-collision", "§9.1", ERROR, 30)
PACKAGING_COLLISION_RESOLVED = _rule("packaging-collision-resolved", "§9.1", NOTE, 30)
SECRET_WITHHELD = _rule("secret-withheld", "§9", NOTE, 25)


#: Requirements discharged by the shape of the API rather than by a diagnostic.
#: A requirement that is *not* enforceable by a check still has to be somewhere;
#: naming the code path here keeps ``docs/REQUIREMENTS.md`` honest, and the
#: coverage test refuses to let a requirement fall out of both tables.
STRUCTURAL: dict[int, str] = {
    2: "discovery.discover() takes a Closure and refuses candidates outside it",
    3: "discovery reads entry points and files only — the module is never imported",
    7: "answers.AnswerSource.permission_suppressed() + EffectiveSet.manifest_removals()",
    9: "record.IntegrationRecord / Delta / Integration.accept()",
    12: "ports.GradleResolver + ports.SwiftResolver, with recorded checksums",
    14: "resources.SidecarSource.payload_exclusions()",
    15: "diagnostics.Diagnostic requires a non-empty distribution tuple",
    16: "resolution reports every declared coordinate with its declaring distribution",
    19: "ports.ArtifactInspector.manifest_of() drives the §9 artifact rules",
    20: "EffectiveSet.python_payload_exclusions() drops <name>.py and <name>.pyi",
    26: "answers.AnswerSource — every requires is answered under (distribution, key)",
}


#: Requirements this library cannot discharge, because they bind a consumer at
#: the point where it **generates a project** — compiling contributed source,
#: writing the application's Android activity, writing its iOS app delegate.
#: This library reads sidecars and computes an effective set; it builds nothing.
#: Naming them is the same discipline as :data:`ADVISORY`'s "not implemented"
#: entries: a requirement that is silently outside a test's range is how
#: coverage decays one addition at a time.
BEYOND_THE_READER: dict[int, str] = {
    27: "compiling contributed `.java` is the consumer's own build step (§6.4)",
    28: "generating the application's Android activity (§2.3)",
    29: "generating the application's iOS app delegate (§2.3)",
}


#: §8's **SHOULD** obligations, by the stable identifier the specification gives
#: them, against the rule that discharges each — or a plain statement that this
#: library does not. An advisory obligation quietly unimplemented is how a
#: conformance claim overstates itself, so "not implemented" is a value here
#: rather than an absence.
ADVISORY: dict[str, str] = {
    "S1": "unknown-top-level",
    "S2": "component-class-absent",
    "S4": "foreground-type-without-permission",
    "S3": (
        "not implemented — the fully merged manifest delta needs a manifest merger, "
        "which belongs to the consumer's build system; this library reports the "
        "per-artifact declarations of requirement 8.19 instead, and a consumer "
        "stopping there must say so in its own documentation (§9)"
    ),
}


def rules_for_requirement(number: int) -> tuple[Rule, ...]:
    """Every rule that discharges §8 requirement ``number``."""
    return tuple(sorted((r for r in RULES.values() if number in r.requirements), key=lambda r: r.code))
