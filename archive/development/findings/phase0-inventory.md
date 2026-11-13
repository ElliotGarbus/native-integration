# Phase 0 — read and report

Inventory of `SPEC.md` as it stands, for the registry, conformance corpus and
reader rewrite that follow. **No code was written in this phase**, and nothing
here proposes a change. Section anchors are `SPEC.md`'s own.

Read: `README.md`; `SPEC.md` end to end; `src/README.md` and every module under
`src/native_integration/`; `docs/REQUIREMENTS.md`; `tools/check_spec.py`,
`tools/requirements_table.py`, `tools/toc.py`, `tools/record_example.py`;
`examples/`; `development/redesign/` (`README.md`, `CONVERSION.md`,
`outline.md`, `forward-test.md`, `review-01.md`, `examples/`). CI is green at
`661f799`: all 18 `check_spec.py` categories pass.

---

## 1. Declaration inventory

Every key [Appendix B](../../SPEC.md#appendix-b-declaration-reference) defines,
against the body section that governs it. **Where the two differ the body
governs** (Appendix B says so itself), and §3 below records where they do.

Columns: **Cardinality** is the TOML shape — `table` (a `[x]` header, at most
once), `array-of-tables` (`[[x]]`, repeatable), or `field`. **Closed** marks a
vocabulary §4.4 requires a consumer to reject unimplemented values from, and
which [§4.3](../../SPEC.md#43-contract-version) makes subject to the
under-declaration rule. Every entry is contract **1.0**; nothing carries a
*Since* mark.

### 1.1 Top level

| Path | Category | Platform | Type | Cardinality | Required | Closed | Section |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `contract` | — | both | string matching `(0\|[1-9][0-9]*)(\.(0\|[1-9][0-9]*))?` | field | **yes** | no | [§4.3](../../SPEC.md#43-contract-version) |
| `platforms` | — | both | array of enum | field | no | **yes** — `android`, `ios`; empty list invalid | [§4.5](../../SPEC.md#45-platform-support) |

### 1.2 `requires` — floors

Declared directly on `[<platform>.requires]`. §5.1 shows the Android four under
`[android.requires]` and `deployment_target` under `[ios.requires]`; Appendix B
groups all five under one `[<platform>.requires]` heading and distinguishes them
only in prose. See ambiguity **A1**.

| Path | Category | Platform | Type | Cardinality | Required | Closed | Section |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `android.requires.min_sdk` | requires | android | integer (TOML int; string and float rejected) | field | no | no | [§5.1](../../SPEC.md#51-build-floors) |
| `android.requires.compile_sdk` | requires | android | integer | field | no | no | [§5.1](../../SPEC.md#51-build-floors) |
| `android.requires.target_sdk` | requires | android | integer | field | no | no | [§5.1](../../SPEC.md#51-build-floors) |
| `android.requires.core_library_desugaring` | requires | android | boolean, **`true` only** — `false` rejected | field | no | no | [§5.1](../../SPEC.md#51-build-floors) |
| `ios.requires.deployment_target` | requires | ios | string matching `[0-9]+(\.[0-9]+){0,2}`, compared component-wise numerically | field | no | no | [§5.1](../../SPEC.md#51-build-floors) |

Floors take no `reason` and no `conditional`, and compose by maximum.

### 1.3 `requires` — values

`[[<platform>.requires.application_value]]`, array-of-tables, both platforms.
`id` is unique within one platform table **across values and actions alike**
(§5); identity is `(distribution, platform, id)`.

| Path | Type | Required | Closed | Section |
| --- | --- | --- | --- | --- |
| `id` | string | **yes** | no | [§5.2](../../SPEC.md#52-values) |
| `kind` | enum | **yes** | **yes** — `manifest_meta_data`, `manifest_placeholder` (android); `info_plist`, `usage_description` (ios); `inline` (both). The platform column is normative | [§5.5](../../SPEC.md#55-value-kinds) |
| `key` | string | **conditional** — required for every kind but `inline`, where it **MUST** be absent | no | [§5.2](../../SPEC.md#52-values), [§5.5](../../SPEC.md#55-value-kinds) |
| `reason` | string | **yes** | no | [§5.2](../../SPEC.md#52-values) |
| `placeholder` | string | SHOULD | no | [§5.2](../../SPEC.md#52-values) |
| `conditional` | boolean, default `false` | no | no | [§5.4](../../SPEC.md#54-how-a-requirement-is-satisfied) |

Constraints beyond the schema (code, not schema): a supplied value is a
non-empty string; two values on one `(kind, key)` coalesce on equal content and
fail otherwise; `info_plist` may not name a `*UsageDescription`, capability,
external-reach or consumer-managed key; `usage_description` may name only a
`*UsageDescription` key; an `inline` value must be consumed by a `view_links`
inline reference or an action's `uses`, and an inline reference resolves only to
a kind-`inline` value in the same sidecar and platform.

### 1.4 `requires` — actions

`[[<platform>.requires.application_action]]`, array-of-tables, both platforms.

| Path | Type | Required | Closed | Section |
| --- | --- | --- | --- | --- |
| `id` | string | **yes** | no | [§5.3](../../SPEC.md#53-actions) |
| `summary` | string | **yes** | no | [§5.3](../../SPEC.md#53-actions) |
| `reason` | string | **yes** | no | [§5.3](../../SPEC.md#53-actions) |
| `instructions` | string | no | no | [§5.3](../../SPEC.md#53-actions), [§5.6](../../SPEC.md#56-instructions-and-acceptance-criteria) |
| `acceptance` | array of strings | SHOULD | no | [§5.3](../../SPEC.md#53-actions), [§5.6](../../SPEC.md#56-instructions-and-acceptance-criteria) |
| `uses` | array of strings — value `id`s in the same sidecar and platform | no | no | [§5.3](../../SPEC.md#53-actions) |
| `slot` | string, opaque, compared only for equality | no | no — explicitly **not** a vocabulary | [§5.7](../../SPEC.md#57-slots) |
| `conditional` | boolean, default `false` | no | no | [§5.4](../../SPEC.md#54-how-a-requirement-is-satisfied) |

**No TOML type is stated for any action field** — §5.3's table gives a
description column only. Types above are read off §5.3's example and §5.6's
"each item in `acceptance`". See **A11**.

### 1.5 `owns` — Android

| Path | Category | Platform | Type | Cardinality | Required | Closed | Section |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `android.owns.java_namespaces` | **owns** | android | array of dotted namespaces | field of a `table` | **conditional** — REQUIRED when the distribution contributes Java/Kotlin source, producer-sourced components, or keep patterns under its own namespace | no | [§6.1](../../SPEC.md#61-ownership) |

There is no `[ios.owns]`; §7.1 states why (`symbol_prefixes` is guidance, not an
enforceable claim).

### 1.6 `contributes` — Android

| Path | Type | Cardinality | Required | Closed | Section |
| --- | --- | --- | --- | --- | --- |
| `android.contributes.src.java` | array of directory paths | table field | no | no | [§6.2](../../SPEC.md#62-java-and-kotlin-source) |
| `android.contributes.src.kotlin` | array of directory paths | table field | no | no | [§6.2](../../SPEC.md#62-java-and-kotlin-source) |
| `android.contributes.gradle_dependencies[].coordinate` | string `group:artifact:version` | array-of-tables | exactly one of `coordinate` / `module` | no | [§6.3](../../SPEC.md#63-gradle-dependencies) |
| `…gradle_dependencies[].module` | string `group:artifact` | | exactly one of `coordinate` / `module` | no | [§6.3](../../SPEC.md#63-gradle-dependencies) |
| `…gradle_dependencies[].version` | inline table `{ at_least, below }`, **both** required | | **yes** with `module` | no | [§6.3](../../SPEC.md#63-gradle-dependencies) |
| `…gradle_dependencies[].configuration` | enum | | no, default `implementation` | **yes** — `implementation`, `api`, `compileOnly`, `runtimeOnly` | [§6.3](../../SPEC.md#63-gradle-dependencies) |
| `android.contributes.gradle_repositories[].url` | `https` string, scheme compared case-insensitively | array-of-tables | **yes** | no | [§6.4](../../SPEC.md#64-maven-repositories) |
| `…gradle_repositories[].reason` | string | | **yes** | no | [§6.4](../../SPEC.md#64-maven-repositories) |
| `…gradle_repositories[].groups` | array of Maven group IDs, exact match | | at least one of `groups`/`modules` | no | [§6.4](../../SPEC.md#64-maven-repositories) |
| `…gradle_repositories[].modules` | array of `group:artifact` | | at least one of `groups`/`modules` | no | [§6.4](../../SPEC.md#64-maven-repositories) |
| `…gradle_repositories[].credentials_required` | boolean | | no | no | [§6.4](../../SPEC.md#64-maven-repositories) |
| `android.contributes.permissions[].name` | string, canonical manifest name | array-of-tables | **yes** | no | [§6.5](../../SPEC.md#65-permissions-and-features) |
| `…permissions[].reason` | string | | RECOMMENDED | no | [§6.5](../../SPEC.md#65-permissions-and-features) |
| `…permissions[].max_sdk_version` | integer | | no | no | [§6.5](../../SPEC.md#65-permissions-and-features) |
| `…permissions[].never_for_location` | boolean | | no | no | [§6.5](../../SPEC.md#65-permissions-and-features) |
| `android.contributes.features[].name` | string | array-of-tables | **yes** | no | [§6.5](../../SPEC.md#65-permissions-and-features) |
| `…features[].required` | — | | **FORBIDDEN**, with a diagnostic naming this rule rather than the generic unknown-key one | — | [§6.5](../../SPEC.md#65-permissions-and-features) |
| `android.contributes.components[].kind` | enum | array-of-tables | **yes** | **yes** — `service`, `activity`, `receiver`. `provider` deliberately absent | [§6.6](../../SPEC.md#66-manifest-components) |
| `…components[].name` | string, a class name | | **yes** | no | [§6.6](../../SPEC.md#66-manifest-components) |
| `…components[].from_dependency` | string `group:artifact`, matching a dependency the same sidecar declares | | no | no | [§6.6](../../SPEC.md#66-manifest-components) |
| `…components[].foreground_service_type` | string, **pass-through** (Android's vocabulary) | | no; valid only on `kind = "service"` | no — pass-through | [§6.6](../../SPEC.md#66-manifest-components) |
| `…components[].exported_required` | boolean | | no | no | [§6.6](../../SPEC.md#66-manifest-components) |
| `…components[].reason` | string | | REQUIRED when `exported_required` is present | no | [§6.6](../../SPEC.md#66-manifest-components) |
| `…components[].exported` | — | | **FORBIDDEN** — a producer MUST NOT declare it | — | [§6.6](../../SPEC.md#66-manifest-components) |
| `…components[].view_links[].scheme` | string, or `{ application_value = "<id>" }` | nested array-of-tables | **yes** | no | [§6.6](../../SPEC.md#66-manifest-components) |
| `…components[].view_links[].<attribute>` | string, or inline reference. Key **MUST** match `[a-z][a-z0-9]*(_[a-z0-9]+)*` and converts mechanically to `android:<camelCase>` | | no | **open** — the single §4.4 exception: an unrecognized attribute is written through | [§6.6](../../SPEC.md#66-manifest-components) |
| `…components[].intent_filters[].action` | string | nested array-of-tables | **yes**, exactly one per filter | no | [§6.6](../../SPEC.md#66-manifest-components) |
| `android.contributes.r8.keep_classes` | array of class patterns; literal prefix must fall in an owned namespace | table field | no | no | [§6.7](../../SPEC.md#67-shrinker-keep-patterns) |
| `android.contributes.r8.keep[].pattern` | string | nested array-of-tables | **yes** | no | [§6.7](../../SPEC.md#67-shrinker-keep-patterns) |
| `android.contributes.r8.keep[].from_dependency` | string `group:artifact` | | never marked REQUIRED — see **A9** | no | [§6.7](../../SPEC.md#67-shrinker-keep-patterns) |
| `android.contributes.meta_data[].key` | string, not scoped by distribution | array-of-tables | **yes** | no | [§6.8](../../SPEC.md#68-manifest-meta-data) |
| `…meta_data[].value` | string, integer or boolean; may be a `@`/`?` resource reference | | **yes** | no | [§6.8](../../SPEC.md#68-manifest-meta-data) |
| `…meta_data[].reason` | string | | **yes** | no | [§6.8](../../SPEC.md#68-manifest-meta-data) |
| `android.contributes.queries[].package` | string, an application ID | array-of-tables | exactly one of `package` / `provider_authority` | no | [§6.9](../../SPEC.md#69-package-visibility) |
| `…queries[].provider_authority` | string | | exactly one of the two | no | [§6.9](../../SPEC.md#69-package-visibility) |
| `…queries[].reason` | string | | **yes** | no | [§6.9](../../SPEC.md#69-package-visibility) |

### 1.7 `contributes` — iOS

| Path | Type | Cardinality | Required | Closed | Section |
| --- | --- | --- | --- | --- | --- |
| `ios.contributes.objc_categories` | boolean, **`true` only** — `false` rejected | field of `[ios.contributes]` | no | no | [§7.6](../../SPEC.md#76-objective-c-categories) |
| `ios.contributes.src.swift` | array of directory paths | table field | no | no | [§7.3](../../SPEC.md#73-swift-source) |
| `ios.contributes.src.symbol_prefixes` | array of strings | table field | no; **invalid in a sidecar contributing no Swift source** | no | [§7.1](../../SPEC.md#71-symbol-prefixes) |
| `ios.contributes.accessed_api_types[].type` | Apple's canonical string, **pass-through** | array-of-tables — a *sibling* of `src`, not a child | **yes** | no — pass-through | [§7.3](../../SPEC.md#73-swift-source) |
| `…accessed_api_types[].reasons` | array of Apple's canonical strings, **pass-through** | | **yes** | no — pass-through | [§7.3](../../SPEC.md#73-swift-source) |
| `…accessed_api_types[].reason` | string, prose | | RECOMMENDED | no | [§7.3](../../SPEC.md#73-swift-source) |
| `ios.contributes.swift_packages[].name` | string, local handle, unique within the sidecar | array-of-tables | **yes** | no | [§7.2](../../SPEC.md#72-swift-packages) |
| `…swift_packages[].url` | `https` string | | **yes** | no | [§7.2](../../SPEC.md#72-swift-packages) |
| `…swift_packages[].products` | array of product names, non-empty | | **yes** | no | [§7.2](../../SPEC.md#72-swift-packages) |
| `…swift_packages[].requirement` | inline table, exactly one of `{ exact }`, `{ from }`, `{ revision }` | | **yes** | **yes** — `branch` is invalid | [§7.2](../../SPEC.md#72-swift-packages) |
| `…swift_packages[].credentials_required` | boolean | | no | no | [§7.2](../../SPEC.md#72-swift-packages) |
| `…swift_packages[].reason` | string | | REQUIRED when `credentials_required` is set; "unused otherwise" — see **A10** | no | [§7.2](../../SPEC.md#72-swift-packages) |
| `ios.contributes.info_plist.values.<AppleKey>` | scalar: string, integer, float, boolean, or homogeneous array of those | table with **open key names** | no | key names open; a refusal list applies — see **A4**, **A5** | [§7.4](../../SPEC.md#74-infoplist) |
| `ios.contributes.info_plist.append.<AppleKey>` | homogeneous array of scalars | table with **open key names** | no | same | [§7.4](../../SPEC.md#74-infoplist) |
| `ios.contributes.info_plist.skadnetwork_identifiers` | array of strings, lowercase and ending `.skadnetwork` | table field | no | no | [§7.4](../../SPEC.md#74-infoplist) |
| `ios.contributes.python_modules[].name` | string matching `[A-Za-z_][A-Za-z0-9_]*`, no dots | array-of-tables | **yes** | no | [§7.5](../../SPEC.md#75-python-modules) |
| `…python_modules[].swift_package` | string, a package `name` the same sidecar declares | | **yes** | no | [§7.5](../../SPEC.md#75-python-modules) |
| `…python_modules[].init` | C identifier, default `PyInit_<name>` | | no | no | [§7.5](../../SPEC.md#75-python-modules) |

### 1.8 Closed vocabularies, gathered

Appendix B names six. Listed here with their members, since the registry needs
them enumerated and the [§4.3](../../SPEC.md#43-contract-version)
under-declaration rule is checked against them.

| Vocabulary | Members | Section |
| --- | --- | --- |
| Platform names | `android`, `ios` | [§4.5](../../SPEC.md#45-platform-support) |
| Value `kind` | `manifest_meta_data`, `manifest_placeholder`, `info_plist`, `usage_description`, `inline` | [§5.5](../../SPEC.md#55-value-kinds) |
| Gradle `configuration` | `implementation`, `api`, `compileOnly`, `runtimeOnly` | [§6.3](../../SPEC.md#63-gradle-dependencies) |
| Component `kind` | `service`, `activity`, `receiver` | [§6.6](../../SPEC.md#66-manifest-components) |
| Swift `requirement` forms | `exact`, `from`, `revision` | [§7.2](../../SPEC.md#72-swift-packages) |
| Capability / external-reach plist keys (a **refusal** list) | `UIBackgroundModes`, `UIRequiredDeviceCapabilities`, `CFBundleURLTypes`, `NSUserActivityTypes` | [§7.4](../../SPEC.md#74-infoplist) |

Three further fixed string lists carry normative weight and are **not** in
Appendix B's roll-call of closed vocabularies:

| List | Members | Section |
| --- | --- | --- |
| Consumer-managed plist keys | `CFBundleIdentifier`, `CFBundleShortVersionString`, `CFBundleVersion`, `MinimumOSVersion` | [§7.4](../../SPEC.md#74-infoplist) — but §5.5 spells the same set with "such as" (**A5**) |
| Reserved Java namespace prefixes | `org.kivy.android`, `org.libsdl.app`, `org.jnius`, `org.renpy.android`, `com.chaquo.python`, `org.beeware.android`, **plus the consumer's own bootstrap namespaces** | [§6.1](../../SPEC.md#61-ownership) |
| Packaging-metadata filenames a consumer may resolve itself | `MANIFEST.MF`, `INDEX.LIST`, `DEPENDENCIES`; `LICENSE`, `LICENSE.txt`, `LICENSE.md`, `NOTICE`, `NOTICE.txt`, `NOTICE.md` and the same with a `-*` suffix; `*.SF`, `*.DSA`, `*.RSA`, `*.EC` — **directly** under `META-INF/` only | [§9.7](../../SPEC.md#97-packaging-collisions) |

Pass-through vocabularies, which a consumer validates the *shape* of and writes
through: `foreground_service_type`, `view_links` `<data>` attribute names **and**
values, `accessed_api_types` `type` and `reasons`, `meta_data` `key`,
`info_plist` key names, permission and feature `name`, `slot`.

---

## 2. Requirement inventory

[§8.4](../../SPEC.md#84-requirements) numbers 46; [§8.5](../../SPEC.md#85-advisory-obligations)
adds S1–S15. [§8.1](../../SPEC.md#81-conformance-is-per-platform) partitions
1–46 across three profiles, each requirement in exactly one row (verified: core
29, android 11, ios 6 = 46).

**Disposition.** [§8.2](../../SPEC.md#82-dispositions-and-what-recording-is-not)
defines exactly two — **blocking** ("every numbered requirement below that says
*fail*") and **advisory** (the §8.5 SHOULD list). Roughly a third of the
numbered requirements state a MUST that names no failure: they oblige a consumer
to *provide*, *record*, *report*, *attribute*, *compile*, *link*, *exclude* or
*never do* something. Violating one is non-conformance, but §8.2 gives it no
disposition. That is recorded per row below as **obligation** and raised as
ambiguity **A13**, because Phase 2's `case.toml` vocabulary
(`accept`/`blocking`/`advisory`) has no cell for it.

| # | Profile | Disposition | Enforces |
| --- | --- | --- | --- |
| 1 | core | obligation (a filter, not a finding) | §3.2 |
| 2 | core | **blocking** | §3.3, §3.4 |
| 3 | core | obligation (prohibition) | §2.1, §3.2 |
| 4 | core | **blocking** | §3.2 |
| 5 | core | **blocking** | §4.1 |
| 6 | core | obligation | §4.1 |
| 7 | core | **blocking** (+ a capability clause) | §4.3 |
| 8 | core | **blocking** | §4.4, §5.5 |
| 9 | core | **blocking** | §4.5, §8.1 |
| 10 | core | obligation (capability) | §2.2, §5.4 |
| 11 | core | obligation (reporting) | §2.3, §5.1, §5.3 |
| 12 | core | **blocking** | §5.1 |
| 13 | core | **blocking** | §5.2, §5.4, §5.5 |
| 14 | core | **blocking** | §5.3, §5.4 |
| 15 | core | obligation (prohibition) | §5.4 |
| 16 | core | obligation (prohibition) | §2.1 |
| 17 | core | **blocking** | §5.2, §6.8, §7.4 |
| 18 | core | obligation (attribution) | §2.1 |
| 19 | core | obligation | §10 |
| 20 | core | obligation (prohibition) | §2.3 |
| 21 | core | obligation (prohibition + recording + attribution) | §5.6, §9.3 |
| 22 | core | **blocking** (+ a reporting clause for `slot`) | §5, §5.3, §5.7 |
| 23 | **android** | **blocking** | §6.1, §6.2 |
| 24 | core | obligation | §6.2, §7.3 |
| 25 | **android** | **blocking** | §6.3 |
| 26 | core | **blocking** | §6.3, §7.2 |
| 27 | **android** | **blocking** | §6.4 |
| 28 | **android** | **blocking** | §6.5 |
| 29 | **android** | **blocking** | §6.6 |
| 30 | **android** | **blocking** | §6.6 |
| 31 | **android** | **blocking** | §6.7 |
| 32 | **android** | **blocking** | §6.8, §6.9 |
| 33 | **ios** | **blocking** | §7.2 |
| 34 | **ios** | **blocking** | §7.1, §7.3 |
| 35 | **ios** | **blocking** | §7.4, §5.5 |
| 36 | **ios** | **blocking** | §7.5 |
| 37 | **ios** | **blocking** | §7.6 |
| 38 | core | **blocking** (an unaccepted change fails) | §9.1 |
| 39 | core | obligation (reporting) | §9.2 |
| 40 | core | obligation, with one **blocking** clause (reject a stored digest not in canonical form) | §9.3 |
| 41 | **android** | **blocking** | §9.4 |
| 42 | core | obligation (prohibition) | §9.5 |
| 43 | core | obligation (recording) | §9.6 |
| 44 | **android** | **blocking** | §9.7 |
| 45 | **android** | obligation (bootstrap property) | §2.4 |
| 46 | **ios** | obligation (bootstrap property) | §2.4 |

### 2.1 Advisory obligations

All fifteen are advisory by construction and carry no profile assignment in
§8.1 — see **A14**.

| # | Enforces | Platform in practice |
| --- | --- | --- |
| S1 | §4.4 | both |
| S2 | §4.4 | both |
| S3 | §4.3 | both |
| S4 | §2.3 | both |
| S5 | §6.1 | android |
| S6 | §6.6 | android |
| S7 | §6.5 | android |
| S8 | §6.5 | android |
| S9 | §6.4 | android |
| S10 | §7.1 | ios |
| S11 | §9.4 | android |
| S12 | §9.4 | android |
| S13 | §6.6 | android |
| S14 | §9.7 | ios |
| S15 | §7.5 | ios |

S11 carries a *conditional MUST*: §9.4 requires a consumer that stops at
per-artifact declarations to say so in its own documentation. An advisory
obligation with a MUST attached to declining it is the only one of its shape.

---

## 3. Drift list

Everything below describes `development/first-attempt.md` rather than `SPEC.md`.
`README.md` and `src/README.md` both already say the reader implements the first
attempt; what follows is the enumeration, not the discovery.

### D1 — `docs/REQUIREMENTS.md` documents the first attempt end to end

Its header links "§8 of the specification" to `development/first-attempt.md`.
It maps **41** requirements (8.1–8.41) and **four** advisory obligations
(8.S1–8.S4); `SPEC.md` has 46 and fifteen. Numbering does not correspond: the
attribution requirement is 8.15 there and **18** in `SPEC.md`; the ownership
requirement is 8.5 there and **23** here. Section citations throughout are the
first attempt's (`§6.7` permissions, `§6.8` components, `§7.6` Info.plist,
`§7.3` prerequisites).

### D2 — `tools/requirements_table.py` reads the wrong document, and the wrong shape

`requirement_text()` and `advisory_text()` both open
`development/first-attempt.md`. `advisory_text()`'s regex expects
`- **S1.** …` bullets; `SPEC.md` §8.5 is a **table** (`| **S1** | … |`), so
pointing the generator at `SPEC.md` unchanged yields an empty advisory map
rather than an error.

### D3 — `src/README.md` cites the first attempt

Its opening link — "a reader for [the specification]" — resolves to
`../development/first-attempt.md`. The module table cites first-attempt section
numbers (`§6.5/§7.4` dependencies, `§6.7` permissions, `§7.4` Info.plist,
`§6.9` queries) and names requirement **8.15** for the attribution invariant,
which is 18 in `SPEC.md`.

### D4 — `src/native_integration/schema.py` encodes the first attempt's vocabulary

The largest single body of drift. Concretely:

- `[[<platform>.requires.application_values]]` (plural), whose delivery site is
  an optional `manifest_meta_data` / `manifest_placeholder` / `info_plist_key`
  field. `SPEC.md` has `[[…application_value]]` (singular) with a **required**,
  **closed** `kind` and a `key` whose presence depends on it.
- **No `application_action` table at all.** In its place stand the first
  attempt's prerequisite tables: `application_files`, `resources`,
  `application_classes`, `app_links` under `[android.requires]`, and
  `entitlements`, `usage_descriptions`, `app_extensions`, `url_schemes`,
  `plist_capabilities`, `application_files`, `application_values` under
  `[ios.requires]`. None exists in `SPEC.md`.
- No `summary`, `instructions`, `acceptance`, `uses`, `slot`, `placeholder`.
- `swift_symbol_prefixes` is a field of `[ios]`; `SPEC.md` has
  `symbol_prefixes` inside `[ios.contributes.src]` (§7.1).
- Component `kind` admits `provider`, which §6.6 deliberately excludes and
  argues at length.
- `CAPABILITY_KEYS` holds two members; §7.4's closed list holds **four**, and
  the four consumer-managed keys are a separate list the schema does not carry.
- `view_links` attributes are an **enumerated closed set** of eight; §6.6 makes
  the attribute *names* open — the single §4.4 exception — with a mechanical
  snake-case-to-`android:` conversion and a `[a-z][a-z0-9]*(_[a-z0-9]+)*`
  well-formedness rule the schema has no equivalent of.
- `swift_packages` carries no `credentials_required` and no `reason`;
  `gradle_repositories` carries `credentials_required` but no rule tying
  `reason` to it.
- Neither `core_library_desugaring = false` nor `objc_categories = false` is
  rejected anywhere in the reader; `SPEC.md` §5.1 and §7.6 require both.

### D5 — `src/native_integration/rules.py` is keyed to the first attempt

All 93 rules carry first-attempt section strings (`§6.2` floors, `§6.3`
application values, `§6.5` dependencies, `§6.6` repositories, `§6.7`
permissions, `§6.8` components, `§6.9` shrinker, `§6.10` meta-data, `§6.11`
and `§7.3` prerequisites, `§6.12` queries, `§7.4` Swift, `§7.5` accessed-API,
`§7.6` plist, `§7.7` Python modules, `§7.8` `objc_categories`). Their
`requirements=(…)` tuples are first-attempt numbers 1–41. `STRUCTURAL`,
`BEYOND_THE_READER` and `ADVISORY` (S1–S4 only) are keyed the same way. Rule
families with no counterpart in `SPEC.md` include `prerequisite-*`,
`extension-kind-unimplemented` and `meta-data-resource-reference`.

### D6 — the test suite reads the first attempt

`tests/test_examples.py:125` and `tests/test_integration.py:1934,1969` open
`development/first-attempt.md`; the requirement-count test derives its number
from that document. `tests/test_examples.py:147` carries an explicit
`@pytest.mark.skip` whose reason reads "README.md documents SPEC.md, and this
reader implements development/first-attempt.md."

### D7 — `examples/` holds a first-attempt sidecar, and `README.md` presents it as current

`examples/pystripe/native.toml` declares `[[android.requires.application_values]]`
with no `kind`, and `[[ios.requires.url_schemes]]` — neither exists in
`SPEC.md`. `examples/pystripe/app-pyproject.toml` answers under
`application_values`, `allow_exported` and `acknowledged`, and cites `§6.2`,
`§6.3`, `§6.8`, `§7.3`. `examples/README.md` links §2.2 to
`development/first-attempt.md`. `README.md`'s repository table nevertheless
lists `examples/` as "one integration in full, both halves" beside `SPEC.md`.

The current-specification pair is `development/redesign/examples/pystripe/`,
which `CONVERSION.md` says will graduate to `examples/` "when the reader
implements this specification."

**This bears directly on a Phase 1 acceptance criterion** — *"a valid
`examples/` sidecar validates against the generated schema"* — which cannot hold
against the file that is there today. Flagged, not acted on.

### D8 — `tools/check_spec.py` validates the two example sets against different documents

`EXAMPLES` (which is `examples/**` and `development/examples/**`) is checked
against `development/first-attempt.md` in check 7. `check_v1_sidecar` — the
function that encodes `SPEC.md`'s rules — runs only over
`development/redesign/examples/**` and `README.md`'s TOML blocks (checks 14, 15).
Nothing under `examples/` is checked against `SPEC.md`.

### D9 — `tools/record_example.py` writes first-attempt records

It builds `development/examples/mediated-ads/record-{android,ios}.json` by
running the first-attempt reader over first-attempt sidecars. Its docstring
already reconciles the numbering by hand: "The first attempt's Appendix E —
`SPEC.md`'s Appendix C".

### D10 — `docs/REQUIREMENTS.md`'s last table is empty

"Rules with no requirement number" emits a header and no rows: every one of the
93 rules carries at least one requirement number. Cosmetic, and worth knowing
before Phase 1 writes generators against the same delimited-region pattern.

### D11 — the redesign probe's schema sketch is superseded, and says so

`development/redesign/README.md`'s "model under test" block shows actions
carrying `kind`, `key` and `value`, and `instructions` as a *path*. The same
file marks all of that as not surviving review, and `CONVERSION.md` V25 records
the probe's own Airship sidecar going stale the same way. Noted so the registry
is built from `SPEC.md` and Appendix B, never from the probe.

---

## 4. Ambiguity list

Each entry states the two readings and cites anchors. **Nothing is proposed.**
The first ones are those a registry or a schema cannot be written without
resolving.

### A1 — a floor's platform is stated by example and by prose, never by rule

[§5.1](../../SPEC.md#51-build-floors) shows `min_sdk`, `compile_sdk`,
`target_sdk` and `core_library_desugaring` under `[android.requires]`, and
`deployment_target` under `[ios.requires]`. [Appendix B](../../SPEC.md#appendix-b-declaration-reference)
heads them all `[<platform>.requires]` and separates them only in the
description column ("Android floors", "iOS floor").

[§5.5](../../SPEC.md#55-value-kinds) makes exactly this distinction normative
for value kinds — "**The Platform column is normative.** A `kind` is valid only
in a table for the platform its row names" — and argues at length why leaving it
implicit would let two consumers disagree. Nothing equivalent is said for floors.

- **Reading 1:** floors are platform-bound like kinds; `deployment_target`
  inside `[android.requires]` is an unrecognized key in a platform table and
  §4.4 requires rejection.
- **Reading 2:** the path `[<platform>.requires]` is the declaration and the
  platform column is descriptive; `deployment_target` under `[android.requires]`
  is recognized and simply never satisfied by an Android build.

A registry must encode one of these as `platform = "android"` or
`platform = "both"`.

### A2 — a `usage_description` key is refused in `values` and unaddressed in `append`

[§7.4](../../SPEC.md#74-infoplist) heads the paragraph "**Usage descriptions are
not contributable**" and then states the rule narrowly: "A consumer **MUST**
reject any `values` key whose name ends in `UsageDescription`". The paragraph
immediately following handles capability keys and is explicit about covering
both modes — "A consumer **MUST** reject these keys in `values` and in `append`
alike". Requirement 35 repeats the narrow form: "reject a usage-description key
in `values`".

- **Reading 1:** the asymmetry is deliberate — a purpose string is a scalar, so
  only `values` can carry one, and `NSCameraUsageDescription` under `append`
  fails later on §7.4's one-key-one-mode rule if anything else claims it as a
  scalar, and otherwise stands.
- **Reading 2:** the heading governs, the omission is an oversight, and a
  producer contributing `NSCameraUsageDescription = ["…"]` under `append` writes
  the user-facing App Store text §5.5 and §7.4 exist to keep out of a producer's
  hands.

This one has a security shape: the party at risk is App Store review, and
Reading 1 leaves a channel open that every neighbouring rule closes.

### A3 — does a `usage_description` value claim its key as a scalar?

[§7.4](../../SPEC.md#74-infoplist)'s mode rule names two scalar sources: "a key
declared under `values`, **or delivered by a value of kind `info_plist`**". A
value of kind `usage_description` also writes one string to one plist key, and
is not named.

- **Reading 1:** the omission is harmless because §5.5 already partitions the
  key space — `info_plist` may not name a `*UsageDescription` key and
  `usage_description` may name only one — so a `usage_description` can never
  collide with a `values` entry.
- **Reading 2:** it can collide with an `append` entry (see **A2**), which is
  precisely the case the mode rule exists for, and the list of scalar sources is
  incomplete.

### A4 — §4.4 declares one exception and the document contains two

[§4.4](../../SPEC.md#44-unknown-declarations-fail-closed): "Within a platform
table the consumer is **building for**, an unrecognized key **MUST** be
rejected" and "**One exception exists, and this document contains no other.**
The `<data>` attributes of a `view_links` entry".

`[ios.contributes.info_plist.values]` and `[ios.contributes.info_plist.append]`
are tables inside a platform table whose **key names are Apple's**, open by
design — §7.4 never enumerates a permitted key and could not. Structurally those
are unrecognized keys in a platform table.

- **Reading 1:** `values` and `append` are recognized keys whose *contents* are
  values, not keys, so §4.4's rule never reaches them and the "no other
  exception" claim holds.
- **Reading 2:** they are keys by any TOML reading, and §4.4's exclusivity claim
  is inaccurate — there are two open key spaces, of which it names one.

A schema generator must decide whether to emit `additionalProperties: false`
somewhere under `info_plist`.

### A5 — the consumer-managed plist key list is closed in §7.4 and open in §5.5

[§7.4](../../SPEC.md#74-infoplist) enumerates four: "`CFBundleIdentifier`,
`CFBundleShortVersionString`, `CFBundleVersion`, `MinimumOSVersion` — are the
consumer's to write."

[§5.5](../../SPEC.md#55-value-kinds) writes the same rule as "nor a key the
consumer manages itself, **such as** `CFBundleIdentifier` or
`CFBundleShortVersionString`."

- **Reading 1:** four keys, closed, and §5.5's "such as" is loose prose citing
  two of them.
- **Reading 2:** the set is whatever a given consumer manages, which makes it
  consumer-dependent — and two consumers would then reject different sidecars,
  the outcome §5.5's own platform-column note says these rules exist to prevent.

Appendix B's roll-call of closed vocabularies lists the capability keys and
**not** the consumer-managed ones, so the §4.3 under-declaration rule has no
registry entry to check them against under either reading.

### A6 — extending a refusal list by minor contradicts §10

[§7.4](../../SPEC.md#74-infoplist), of the capability and external-reach keys:
"The list is closed, and **a minor revision may extend it**."

[§10](../../SPEC.md#10-versioning): "Any change that would alter the meaning of
an existing key, or **make a previously valid sidecar invalid, requires a new
major version and a new group name**."

Adding a fifth key to the refusal list makes a sidecar that contributed that key
under 1.0 invalid. The same shape applies to §6.1's reserved-prefix list and to
§7.4's consumer-managed keys.

- **Reading 1:** §10's rule is about the *declaration* vocabulary and a refusal
  list is not part of it, so §7.4's minor stands.
- **Reading 2:** §10 says what it says, and extending a refusal list is a major.

Note that §10 binds "from the moment the draft marker at the top of this
document is removed, and not before", so this is latent rather than live —
but it is a rule the registry has to encode a `since` policy for.

### A7 — empty arrays are forbidden twice and unaddressed elsewhere

[§4.5](../../SPEC.md#45-platform-support) says an empty `platforms` list is
invalid. [§7.2](../../SPEC.md#72-swift-packages) says `products` **MUST** be
non-empty. Nothing is said for `java_namespaces`, `java`, `kotlin`, `swift`,
`symbol_prefixes`, `groups`, `modules`, `keep_classes`,
`skadnetwork_identifiers`, `acceptance`, `uses`, or `reasons`.

- **Reading 1:** the two explicit rules are the exceptions; every other array
  admits `[]`, which declares nothing and is harmless.
- **Reading 2:** the two are illustrations of a general principle — an empty
  array is a declaration that declares nothing and is likelier a mistake than an
  intent, on §5.1's own reasoning about `core_library_desugaring = false`.

`minItems` is a schema property, so Phase 1 cannot avoid choosing.

### A8 — `exported_required = false` has no false-rejection rule, where two neighbours do

[§5.1](../../SPEC.md#51-build-floors) rejects `core_library_desugaring = false`
explicitly and gives the reason: "version 1 has no way to require that a build
setting be *off*, and a declaration that requires nothing is far likelier to be
a mistake than an intent." [§7.6](../../SPEC.md#76-objective-c-categories)
carries the identical rule for `objc_categories` and cites §5.1 for it.

[§6.6](../../SPEC.md#66-manifest-components) says only "A producer **MAY**
declare `exported_required = true` with a `reason`". Nothing addresses
`exported_required = false`. (`conditional = false` is different — §5.2 and §5.3
name it as the default, so writing it explicitly is plainly fine.)

- **Reading 1:** `exported_required = false` is valid and identical to omitting
  the key, since components are unexported by default anyway.
- **Reading 2:** it takes §5.1's rule for the same reason — it requests nothing
  — and is rejected; the two sections that state that rule both explain it as
  general.

Related and separable: **is `reason` valid on a component that does not declare
`exported_required`?** §6.6 makes `reason` REQUIRED "when present", saying
nothing about a `reason` standing alone.

### A9 — `from_dependency` on an `[[…r8.keep]]` entry is never marked required

[§6.7](../../SPEC.md#67-shrinker-keep-patterns) describes the two forms as
"distinguished by whose classes are kept" and says of the second
"`from_dependency` **MUST** match a dependency the same sidecar declares".
Appendix B lists the entry as "`pattern`, `from_dependency`" without marking
either required.

- **Reading 1:** `from_dependency` is what makes the entry the second form, so
  it is required; an entry without one is invalid.
- **Reading 2:** it is optional, and an entry without one is a `keep_classes`
  equivalent subject to §6.1 rule 3's owned-namespace test.

Reading 2 creates a second spelling for the same declaration, which §6.7's
comparison treats as two exclusive forms — but the document never closes it.

### A10 — a `reason` on a Swift package with no `credentials_required`

Appendix B: "**Required when `credentials_required` is set**, and **unused
otherwise**". [§7.2](../../SPEC.md#72-swift-packages) states only the required
half.

- **Reading 1:** "unused" means accepted and ignored — a producer may write a
  `reason` on any package.
- **Reading 2:** a key with no defined effect in the shape it is written in is
  an unrecognized declaration in that position, and §4.4 fails closed on it.

`gradle_repositories` is the contrast: there `reason` is unconditionally
REQUIRED, so the question does not arise.

### A11 — no TOML types are stated for any action field

[§5.3](../../SPEC.md#53-actions)'s field table has **Field / Required /
Description** and no type column. `acceptance` is "Statements of the end state";
`uses` is "Value `id`s in this sidecar"; `instructions` is "Prose telling a
reader how to do it". Types are recoverable from §5.3's example and from §5.6's
"Each item in `acceptance` is checked independently", and from nowhere
normative.

Contrast [§5.2](../../SPEC.md#52-values), which states "The supplied value is a
**non-empty string**", and [§7.4](../../SPEC.md#74-infoplist), which fixes an
entire TOML-to-plist type table because "'Set verbatim' is not enough for two
implementations to agree."

- **Reading 1:** the example is normative enough — `acceptance` is an array of
  strings, `uses` an array of strings, the rest strings.
- **Reading 2:** a single-string `acceptance` is not forbidden by any sentence
  in the document, and §5.6's "each item" reads naturally over a one-item list.

### A12 — what makes a sidecar "contribute Swift source", or "contribute Java or Kotlin source"

Three rules turn on this phrase and none defines it:

- [§7.1](../../SPEC.md#71-symbol-prefixes): reject `symbol_prefixes` "in a
  sidecar that contributes no Swift source".
- [§7.3](../../SPEC.md#73-swift-source): reject `accessed_api_types` otherwise.
- [§6.1](../../SPEC.md#61-ownership): `java_namespaces` is REQUIRED "when the
  distribution contributes Java or Kotlin source".

- **Reading 1:** the test is declarative — `[ios.contributes.src]` declares a
  `swift` key. `swift = []` then still "contributes Swift source".
- **Reading 2:** the test is material — at least one `.swift` file is actually
  staged from a declared root. §6.2 and §7.3 both describe staging "exactly the
  files with the matching extension", so a root containing none stages nothing.

The two differ for `swift = []`, for a root with no matching files, and for a
sidecar declaring `kotlin = ["kotlin"]` where the directory holds only `.java`.
Reading 1 is checkable from the sidecar alone; Reading 2 needs the wheel's files.

### A13 — a third of §8's numbered requirements have no disposition

[§8.2](../../SPEC.md#82-dispositions-and-what-recording-is-not) offers exactly
two: **blocking** — "every numbered requirement below that says *fail*" — and
**advisory**, the §8.5 SHOULD list. It then names one case that is neither (an
unsatisfied conditional requirement) and calls that a recording matter rather
than a third disposition.

Requirements 1, 3, 6, 10, 11, 15, 16, 18, 19, 20, 21, 24, 39, 42, 43, 45 and 46
state MUSTs that name no failure. Requirement 45 — the bootstrap's activity must
be a `ComponentActivity` — is the clearest: a consumer either has that property
or does not, and no build fails over it.

- **Reading 1:** §8.2 classifies *findings*, not requirements. A requirement
  with no finding is a conformance property, tested against the consumer rather
  than against a sidecar, and §8.2 is not silent about it so much as not
  addressed to it.
- **Reading 2:** §8.2 says a finding "has one of two dispositions" and §8.1
  makes conformance a claim over all 46; a requirement that produces neither
  disposition has no stated way to be observed at all.

This is the reading Phase 2 depends on: `case.toml` is specified to carry
`accept` / `blocking` / `advisory`, and seventeen requirements fit none of the
three.

### A14 — advisory obligations carry no profile

[§8.1](../../SPEC.md#81-conformance-is-per-platform)'s profile table partitions
requirements **1–46** and says "Every requirement appears in exactly one row."
§8.5's S1–S15 are absent from it, though S5–S9 and S11–S13 are plainly Android
and S10, S14, S15 plainly iOS.

- **Reading 1:** advisories are never blocking, so profile membership is
  meaningless for them — an iOS-only consumer simply never meets an Android
  advisory.
- **Reading 2:** §8.5 says the identifiers exist "so a conformance claim can
  name the ones it meets", and a claim of the form "a v1 iOS consumer meeting
  S1–S4, S10, S14, S15" needs to know which are in range.

Phase 2's corpus is organised `core/ android/ ios/`, so an advisory fixture has
to land in one of them.

### A15 — is `slot` compared within a platform or across the sidecar?

[§5.7](../../SPEC.md#57-slots): "When **two actions in the effective set** share
a slot, a consumer **MUST** report them together." The effective set is defined
in §1 over the whole closure and says nothing about platform. §5.7's own note
says `slot` "is a field of the action table, which is one table with one field
set on both platforms", and every identifier it lists is Apple's.

- **Reading 1:** comparison is per-platform, because [§9.2](../../SPEC.md#92-the-report)
  fixes a report to one platform's build and §4.4 lets a consumer skip the other
  platform's table entirely.
- **Reading 2:** the rule says "in the effective set" without qualification, so
  an Android action and an iOS action sharing a string are reported together.

Reading 2 is unreachable for a single-platform consumer, which would make one
sidecar produce different findings from two conforming tools.

### A16 — an unpaired resource reference in `meta_data`

[§6.8](../../SPEC.md#68-manifest-meta-data): "A producer **MUST NOT** reference
one unless the same sidecar declares an action asking the application to supply
it." The Caution beneath says "Nothing links these two entries structurally… **A
consumer cannot check this pairing**, because an action is prose." Requirement
32 does not mention resource references at all.

- **Reading 1:** unenforceable by design; a producer obligation with no consumer
  check, and the AAPT error is the backstop the Caution names.
- **Reading 2:** a consumer can check the weak form — a `value` beginning `@` or
  `?` in a sidecar declaring **no action at all** violates the rule
  observably — and "cannot check this pairing" refers to matching a *particular*
  action, not to the existence of any.

Phase 2 needs this decided to know whether a fixture exists.

### A17 — two unenforceable MUSTs, and what a corpus does with them

Distinct from A16 because no reading makes them checkable:

- [§5.2](../../SPEC.md#52-values): "A producer **MUST NOT** declare a value for
  something an SDK accepts at runtime." Nothing in a sidecar distinguishes a
  build-time key from a runtime one.
- [§6.4](../../SPEC.md#64-maven-repositories): "A producer **MUST NOT** put a
  credential in a sidecar, in any field, under any spelling", where the
  consumer's obligation is narrower — reject where "syntactically identifiable —
  at minimum, URL user-info" and **SHOULD** warn elsewhere.

- **Reading 1:** these bind the producer and are outside a consumer's
  conformance surface, so no fixture exists.
- **Reading 2:** a corpus that omits them records a specification obligation
  nothing tests, which is the drift §8's own Caution warns about.

---

## What the gate is deciding

**A1**, **A4**, **A5**, **A7**, **A9**, **A10** and **A11** determine cells in
`contract/v1.toml` or in the generated JSON Schema directly, so Phase 1 cannot
begin without them. **A13** and **A14** determine the shape of Phase 2's
`case.toml` before any fixture is authored, and **A2**, **A3**, **A12**, **A15**
and **A16** each decide whether a particular fixture exists at all.

**A2** is the one worth reading first regardless of phase: under one reading a
producer can write an iOS purpose string through `append`, which is a thing the
specification otherwise forbids in three separate places.

Two further items above are not ambiguities and are recorded for the same
review: **D7**, which puts a Phase 1 acceptance criterion in conflict with the
file it names, and §8.3's thematic index, which files requirement 18
(attribution) and requirement 20 (scaffolding) under "Composition between
distributions" while the themes those belong to are listed as 38–44 and 10–11.
