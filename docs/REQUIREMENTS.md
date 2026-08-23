# Where each consumer obligation lives

Every requirement in [§8 of the specification](../SPEC.md#8-consuming-tool-requirements),
against the code path in [`native_integration`](../src/native_integration/) that
discharges it.

**Generated** by `python3 tools/requirements_table.py` from SPEC.md and
`native_integration.rules`; CI fails if it drifts. A requirement that appears in
neither column fails `tests/test_integration.py::test_every_requirement_is_discharged_somewhere`.

Severity is not the reader's invention: §8 names three outcomes — **blocking**,
**advisory**, **recorded** — and each rule below is registered at one of them,
in one place, so "MUST fail" cannot decay into a warning through an edit at a
call site.

Three kinds of entry:

- a **rule code** is a check that produces a diagnostic.
- a **structural** entry is an obligation discharged by the shape of the API
  rather than by a check — you cannot construct a `Diagnostic` without naming a
  distribution, so requirement 8.15 has no rule and cannot be forgotten either.
- **beyond this reader** marks an obligation that binds a consumer where it
  *generates a project* — compiling contributed source, writing the
  application's activity or app delegate. This library reads sidecars and
  computes an effective set; it builds nothing, so those are named rather than
  left as a blank a later reader would mistake for an oversight.

Four requirements need something only a build tool has: a resolved dependency
graph, an archive listing, the manifest inside a resolved `.aar`. Those are
[ports](../src/native_integration/ports.py), and a sidecar that needs one when
the consumer supplied none raises `UnimplementedObligation` rather than
returning a clean result.

| §8 | The requirement | Discharged by |
| --- | --- | --- |
| 8.1 | Enforce the contract version gate, including the minor (§4.3), and fail closed on unrecognized keys in platform tables it builds (§4.4). | `application-value-duplicate`, `component-class-absent`, `component-dependency-undeclared`, `contract-major-mismatch`, `contract-malformed`, `contract-missing`, `contract-too-new`, `contract-under-declared`, `extension-kind-unimplemented`, `key-required`, `meta-data-resource-reference`, `plist-consumer-managed`, `plist-value-conflict`, `prerequisite-condition-unstated`, `skadnetwork-identifier-invalid`, `skadnetwork-items-key`, `swift-package-duplicate-name`, `toml-invalid`, `type-invalid`, `unknown-key`, `unknown-top-level` |
| 8.2 | Restrict candidate producers to the application's dependency closure (§3.2). | *structural* — discovery.discover() takes a Closure and refuses candidates outside it |
| 8.3 | Discover by iterating the group, ignoring the entry-point name (§3.3), and never import the producing package or execute declared content (§2.1, §3.2). | `entry-point-value-invalid`<br>*structural* — discovery reads entry points and files only — the module is never imported |
| 8.4 | Fail when a distribution declares multiple entries (§3.4), when a declared resource cannot be read (§3.2), or when a resource violates the containment and symlink rules (§4.1). | `entry-point-value-invalid`, `multiple-entry-points`, `resource-escapes`, `resource-not-utf8`, `resource-symlink`, `resource-unreadable`, `sidecar-missing`, `source-root-missing` |
| 8.5 | Enforce ownership and fail on collision, never resolving by order (§6.1). | `component-outside-namespace`, `namespace-overlap`, `namespace-required`, `namespace-reserved`, `namespace-single-label`, `source-outside-namespace` |
| 8.6 | Never promote a feature to `required` (§6.7), never register a component as exported without explicit application approval (§6.8), and never write a required entitlement or usage description (§7.3) — including rejecting a usage description offered as an `info_plist` value (§7.6). | `component-export-forbidden-key`, `feature-required-forbidden`, `plist-capability-key`, `plist-usage-description` |
| 8.7 | Provide application-side permission suppression, ensure a suppressed permission is absent from the effective merged manifest — emitting a merger removal rule when a resolved dependency contributes it — and report it (§6.7). | `permission-suppressed`<br>*structural* — answers.AnswerSource.permission_suppressed() + EffectiveSet.manifest_removals() |
| 8.8 | Fail when a producer's `requires` exceeds the application's configuration (§6.2, §7.2), when a declared application value is unsupplied or an inline reference names no declared `id` (§6.3), when an unconditional §7.3 prerequisite is unsatisfied — judged by that section's satisfaction table — or when a component declaring `exported_required` has no application approval (§6.8). | `application-value-unresolved-ref`, `application-value-unsupplied`, `component-duplicate`, `component-export-unapproved`, `floor-unmet`, `meta-data-application-override`, `meta-data-conflict`, `prerequisite-unsatisfied` |
| 8.9 | Record each distribution's resolved contribution durably and in reviewable form, per the lifecycle of §9, and fail the build when the effective set drifts from the last accepted record. | `record-absent`, `record-drift`<br>*structural* — record.IntegrationRecord / Delta / Integration.accept() |
| 8.10 | Restrict contributed repositories to their declared groups/modules, reject two whose scopes overlap at different URLs, report them with distinct prominence, and reject a credential in a syntactically identifiable location such as URL user-info (§6.6). | `repository-contributed`, `repository-credential-in-url`, `repository-credential-shaped`, `repository-scope-missing`, `repository-scope-overlap` |
| 8.11 | Validate `keep_classes` against owned namespaces, and reject a `from_dependency` keep whose pattern matches any class on the effective classpath originating outside that dependency's resolved artifacts (§6.9). | `keep-dependency-undeclared`, `keep-matches-foreign-class`, `keep-outside-namespace` |
| 8.12 | Enforce reproducible native dependency resolution: reject unbounded and changing versions, and lock the fully resolved graph, transitives included — Gradle and SwiftPM alike, recording the resolved *revision* for Swift packages — in the record, resolving from it thereafter (§6.5, §7.4). Never convert a declared Gradle version into a `strictly` constraint, and show requested-versus-resolved where they differ. Verify each resolved artifact against its recorded checksum on every subsequent build, failing on a mismatch (§6.5). Reject a resolved Swift graph containing a branch or path dependency, and record and verify the checksum of every binary target in it, which the package's revision does not pin (§7.4). | `dependency-checksum-mismatch`, `dependency-configuration`, `dependency-form`, `dependency-version-changing`, `dependency-version-substituted`, `dependency-version-unbounded`, `swift-binary-checksum-mismatch`, `swift-binary-unchecksummed`, `swift-branch-requirement`, `swift-graph-unpinnable`<br>*structural* — ports.GradleResolver + ports.SwiftResolver, with recorded checksums |
| 8.13 | Validate `view_links` (activity-only, export-gated) and generate their filters (§6.8). | `view-links-invalid` |
| 8.14 | Exclude sidecar directories from any Python payload it assembles. | *structural* — resources.SidecarSource.payload_exclusions() |
| 8.15 | Name the contributing distribution in every diagnostic. | *structural* — diagnostics.Diagnostic requires a non-empty distribution tuple |
| 8.16 | When native dependency resolution fails, report every declared coordinate, module, and Swift package with the distribution that declared it (§6.5, §7.4). | `resolution-failed`<br>*structural* — resolution reports every declared coordinate with its declaring distribution |
| 8.17 | Compute every namespace and reserved-prefix containment test on dot-separated segments (§6.1). | `component-outside-namespace`, `keep-outside-namespace`, `namespace-overlap`, `namespace-reserved`, `source-outside-namespace` |
| 8.18 | Fail when building for a platform a sidecar's `platforms` key omits, naming the distribution (§4.5). | `platform-unsupported`, `platforms-contradiction`, `platforms-invalid` |
| 8.19 | Record and report the permissions, features, and components declared by resolved Android artifacts' own manifests, attributed to the artifact; never let a resolved artifact silently promote a feature to `required`, and report its exported components with contribution-level prominence (§9). | `artifact-exported-component`, `artifact-feature-overridden`, `artifact-permission`, `artifact-proguard-rules`<br>*structural* — ports.ArtifactInspector.manifest_of() drives the §9 artifact rules |
| 8.20 | Register declared Python modules against a Swift package the same sidecar declares, reject a non-identifier or dotted `name`, fail on a duplicate module name, and exclude `<name>.py` and `<name>.pyi` from the Python payload (§7.7). | `python-module-duplicate`, `python-module-init-invalid`, `python-module-name-invalid`, `python-module-package-undeclared`<br>*structural* — EffectiveSet.python_payload_exclusions() drops <name>.py and <name>.pyi |
| 8.21 | Report required app extensions as prerequisites, and never create a build target to satisfy one (§7.3). | `prerequisite-unsatisfied` |
| 8.22 | Record an unsatisfied conditional prerequisite in the integration record, attributed to its distribution, without failing the build (§7.3). | `prerequisite-conditional` |
| 8.23 | Report required application files and URL schemes as prerequisites, and never create, fetch, or register one (§7.3). | `prerequisite-unsatisfied` |
| 8.24 | Generate `intent_filters` only on components that are neither exported nor declaring `view_links`, and show each action in the record (§6.8). | `intent-filter-invalid` |
| 8.25 | Fail when a repository declaring `credentials_required` has no credentials configured, and never write a supplied credential into the generated project, the record, or a diagnostic (§6.6, §9). | `repository-credentials-missing`, `secret-withheld` |
| 8.26 | Provide a means for the application to answer every `requires`, joined to the declaration by the key §2.2 names, and accept a build-time credential by indirection rather than only as a literal in a committed file (§2.2). Reject a sidecar declaring two `app_extensions` or `url_schemes` entries under one `id`, which the application could not answer separately (§7.3). | `application-value-unsupplied`, `prerequisite-id-duplicate`, `repository-credentials-missing`<br>*structural* — answers.AnswerSource — every requires is answered under (distribution, key) |
| 8.27 | Compile contributed `.java` sources with UTF-8 forced, never the platform default (§6.4). | *beyond this reader* — compiling contributed `.java` is the consumer's own build step (§6.4) |
| 8.28 | When it generates the application's Android activity, make it an `androidx.activity.ComponentActivity` or a subclass (§2.3). | *beyond this reader* — generating the application's Android activity (§2.3) |
| 8.29 | When it generates the application's iOS app delegate, provide a documented means for application code to observe a URL callback delivered to `application(_:open:options:)`, rather than consuming it (§2.3). | *beyond this reader* — generating the application's iOS app delegate (§2.3) |

## Advisory obligations (§8's SHOULD list)

Reported, never blocking. One is deliberately not implemented, and says so — an advisory obligation quietly skipped is how a conformance claim overstates itself.

| §8 | The obligation | Discharged by |
| --- | --- | --- |
| 8.S1 | Warn on unrecognized top-level tables (§4.4). | `unknown-top-level` |
| 8.S2 | Verify `from_dependency` component classes against the resolved artifact (§6.8). | `component-class-absent` |
| 8.S3 | Report the delta of the fully merged Android manifest, beyond the per-artifact declarations required by requirement 8.19, and the native effects of Swift packages' binary targets (§9, §11). | *not implemented — the fully merged manifest delta needs a manifest merger, which belongs to the consumer's build system; this library reports the per-artifact declarations of requirement 8.19 instead, and a consumer stopping there must say so in its own documentation (§9)* |

## Rules with no requirement number

Checks the specification states in §§3–9 without giving them a numbered line in §8. They are enforced the same way.

| Rule | Section | Severity |
| --- | --- | --- |
