# The native-integration specification

**Version:** `1` (draft)
**Entry-point group:** `native_integration.v1`

A convention by which a Python distribution declares the native material an
Android or iOS application build must provide on its behalf, and by which a build
tool discovers, validates, and stages that material.

> **Status: draft.** Not implemented. Breaking changes are expected until this
> line is removed.

---

## 1. Terminology

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are
to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

- **Distribution** — an installed Python distribution, as seen by
  `importlib.metadata`.
- **Producer** — a distribution that declares a native integration.
- **Consumer** — a tool that reads declarations and generates a native app
  project. Consumers are build tools, not installers.
- **Application** — the app being built. Its own configuration is outside this
  specification.
- **Dependency closure** — the application's direct dependencies and their
  transitive requirements, as resolved for the target platform.
- **Sidecar** — the declaration file a producer ships.

## 2. Overview

A producer ships a TOML file inside its own wheel and registers an entry point
identifying its location. A consumer enumerates the application's dependency
closure, reads each sidecar, validates it against this specification, and stages
the declared material into the native project it generates.

Nothing in this specification requires a change to any packaging standard, a
custom build backend, or a new artifact type.

```
producer's pyproject.toml          →  wheel  →  site-packages  →  consumer
  [project.entry-points.…]            .dist-info/entry_points.txt
  package data                        pkg/_native/native.toml
```

### 2.1 Design principles

**Declarations are data, not executable build logic.** A producer describes
artifacts, requirements, and application contributions. A sidecar **MUST NOT**
provide commands, scripts, plugins, hooks, or arbitrary build-system arguments
for a consumer to execute, and a consumer **MUST NOT** execute any content of a
sidecar. This is the property that keeps declarations inspectable without
trusting producer code, and it is deliberate that this specification resembles
`pkg-config` — *describe what consuming me requires* — rather than a build
script.

**Everything a producer declares falls into one of three categories:**

| Category | Meaning | Examples |
| --- | --- | --- |
| **`owns`** | An exclusive claim, enforced across all distributions | a Java namespace |
| **`requires`** | A condition the application or build environment must satisfy; the consumer checks it but never satisfies it | an SDK floor, an entitlement, an application-supplied value |
| **`contributes`** | Material the consumer stages into the generated project on the producer's behalf | source files, dependency coordinates, permissions, manifest components |

The categories carry the security model: ownership claims are exclusive and
collision-checked; requirements are reported and verified, never auto-satisfied;
contributions are staged, attributed, and disclosed per §9.

**Unrecognized declarations fail closed.** A consumer never silently ignores a
contribution it does not understand (§4.4) — a build that omits declared native
material produces a broken application that fails far from the cause.

**Contributions stay per-distribution.** Provenance survives from declaration to
diagnostic; see Appendix A.

**Native dependency resolution MUST be reproducible.** Every dependency a
producer contributes must resolve identically from the same integration record;
see §6.5 and §7.4.

## 3. Discovery

### 3.1 The entry point

A producer **MUST** declare exactly one entry point in the group
`native_integration.v1`:

```toml
[project.entry-points."native_integration.v1"]
native = "mypkg._native"
```

- The group name uses an **underscore**: the
  [entry-points specification](https://packaging.python.org/en/latest/specifications/entry-points/)
  requires group names to match `^\w+(\.\w+)*$` — letters, numbers, and
  underscores separated by dots; a hyphen is not permitted. The spelling also
  follows the specification's recommendation that a new group begin with a PyPI
  project name: `native_integration` is the normalized form of the
  `native-integration` project that hosts this specification and its reference
  reader.
- The entry-point name **SHOULD** be `native`. The name has no semantic meaning
  and consumers ignore it (§3.3).
- The entry-point value **MUST** be an importable module reference — a dotted
  path whose parts are valid Python identifiers, with no `:attr` suffix — naming
  the package directory that contains the sidecar (§4.1).

**The entry point is used solely as distribution metadata identifying the
location of a resource.** A consumer **MUST NOT** load the entry point or import
the module it names; the reference exists so the metadata stays truthful to the
entry-points specification, which defines a value as pointing to an importable
object, while this convention reads the named directory's *files* instead.

> The quotes around the group name are required TOML syntax: a dot in an unquoted
> table header is a nesting separator, so `[project.entry-points.native_integration.v1]`
> declares a group named `native_integration` containing a table `v1`, which no
> consumer will find.

### 3.2 Resolution

A consumer **MUST** resolve declarations as follows:

1. Determine the candidate set: the **resolved dependency closure of the
   application** for the target platform. A consumer operating in an isolated
   environment containing exactly that closure **MAY** treat all installed
   distributions as candidates. A consumer **MUST NOT** accept contributions
   from distributions outside the closure — a debugging tool that happens to be
   installed beside the application, and happens to ship a sidecar, must not
   configure the application.
2. For each candidate, read entry points in the group `native_integration.v1`
   via `importlib.metadata`.
3. Interpret the value's dotted path as a directory within the distribution —
   e.g. `mypkg._native` → `mypkg/_native/` — and read `native.toml` inside it.

A consumer **MUST** access the sidecar and every resource it references through
the distribution's metadata/file-resource interface
(`importlib.metadata.Distribution.locate_file()`, `Distribution.files`, or
equivalent). A consumer **MUST NOT** assume a distribution is represented by a
conventional `site-packages` directory. When a distribution's resources cannot
be materialized or read, the consumer **MUST** fail, naming the distribution —
not silently skip it.

A consumer **MUST NOT** import the producing package, or any module of it, at
any point. Metadata reads and file reads only.

> Rationale: a consumer runs on a desktop build host. A distribution targeting
> Android or iOS may raise on import there, or may not be importable at all.

**Provenance.** For each producer, the consumer **MUST** be able to state how it
entered the dependency closure (§9). When multiple dependency paths exist, the
consumer **MUST** report at least the producer's immediate dependents, and any
path it reports **MUST** be deterministic across runs.

### 3.3 Iteration, not lookup

A consumer **MUST** iterate every entry in the group and ignore the entry-point
name. A consumer **MUST NOT** look the entry up by name.

> Rationale: the name carries no information — the platform lives inside the file
> — so a name-keyed lookup silently skips any distribution that labelled it
> differently. The package installs, the build succeeds, and the declaration never
> lands.

### 3.4 Multiple entries

A distribution declaring more than one entry in the group is invalid. A consumer
**MUST** fail, naming the distribution. It **MUST NOT** select one or merge them.

## 4. The sidecar file

### 4.1 Location and name

The sidecar **MUST** be named `native.toml` and **MUST** reside in the directory
identified by the entry-point value. It **MUST** be shipped as ordinary package
data.

```
mypkg/
  __init__.py
  _native/
    __init__.py          ← required: keeps the entry-point value importable
    native.toml          ← fixed name; the entry point does not spell it
    java/…               ← optional, per §6.4
    swift/…              ← optional, per §7.5
```

The sidecar directory **MUST** contain an `__init__.py` (typically empty). It
exists solely to make the entry-point value a truthful importable module
reference — a subdirectory of a regular package is not importable without one —
and **nothing ever imports it** (§3.1, §3.2). The requirement serves the
packaging metadata, not this convention's own mechanics.

Nothing is placed at the `site-packages` root.

**Referenced resources.** Every path a sidecar declares is interpreted relative
to `native.toml` and **MUST NOT** escape its directory, checked **after** path
normalization and symlink resolution. Symlinked resources are not permitted in
version 1; a consumer **MUST** reject one, naming the distribution. Contributed
source files **MUST** be UTF-8 encoded.

### 4.2 One file, all platforms

A distribution **MUST** ship exactly one sidecar covering every platform it
supports. Platforms are tables within it, not separate files.

> Rationale: the contract version is declared once and validated in a single read
> before anything is trusted. Per-platform files would allow those versions to
> disagree.

### 4.3 Contract version

The sidecar **MUST** declare a top-level `contract` key: a string holding the
major version of this specification, optionally with a minor —

```toml
contract = "1"        # equivalent to "1.0"
```

```toml
contract = "1.1"      # uses a capability added in revision 1.1
```

A producer **MUST** declare the smallest contract whose capabilities it uses. A
consumer implementing contract *X.Y* **MUST** reject a sidecar declaring a
different major, or a minor greater than *Y*, with a message naming the
distribution and the required contract — never by parsing it partially.

> The minor is capability negotiation: a producer adopting a 1.1 feature is
> rejected by a 1.0 consumer with an actionable message ("requires contract
> 1.1"), instead of the consumer ignoring the feature and building a silently
> broken application.

### 4.4 Unknown keys fail closed

Within a platform table the consumer is **building for**, an unrecognized key
**MUST** be rejected, naming the distribution and the key. A consumer **MUST
NOT** ignore a declaration it does not understand in order to proceed.

Platform tables for platforms the consumer is **not** building — an `[ios]`
table during an Android build — are legitimately outside its concern and **MAY**
be ignored. A consumer **SHOULD** warn about a top-level table it does not
recognize at all, since it cannot distinguish a future platform from a
misspelled one.

> Rationale: silently ignoring an unknown *contribution* is the dangerous case —
> a 1.0 consumer skipping a 1.1 `content_providers` table builds an application
> that is broken at runtime, far from the cause. Failing closed also catches
> typos: a misspelled `permisions` key is an error, not a silent no-op. Additive
> evolution is preserved by §4.3's contract minor, which converts "silently
> ignored" into "visibly rejected with the version that would work."

## 5. Structure

```toml
contract = "1"

[android.owns]         # §6.1 — exclusive claims
[android.requires]     # §6.2–6.3 — conditions the application must satisfy
[android.contributes]  # §6.4–6.9 — material staged into the project

[ios]                  # §7.1 — symbol-prefix guidance (no ownership claims in v1)
[ios.requires]         # §7.2–7.3
[ios.contributes]      # §7.4–7.6
```

A sidecar declaring no platform table is valid and contributes nothing. Within a
platform table, each category is optional.

## 6. Android

### 6.1 Ownership: `[android.owns]`

```toml
[android.owns]
java_namespaces = ["org.example.mypkg"]
```

`java_namespaces` is **REQUIRED** when the distribution contributes Java or
Kotlin source (§6.4), producer-sourced manifest components (§6.8), or shrinker
keep patterns under its own namespace (§6.9).

A consumer **MUST** enforce all of the following, and **MUST** fail rather than
resolve any conflict by file or copy order:

1. Every contributed source file's path **and** its declared `package` **MUST**
   fall under an owned namespace.
2. Every producer-sourced manifest component name (§6.8) **MUST** fall under an
   owned namespace. (A component attributed to a declared dependency via
   `from_dependency` is exempt — its class is the dependency's, not the
   producer's.)
3. Every shrinker keep pattern (§6.9) **MUST** fall within one of its permitted
   scopes.
4. An owned namespace under a reserved prefix **MUST** be rejected. Reserved
   prefixes are the bootstrap/runtime namespaces of the known Python-mobile
   toolchains — `org.kivy.android`, `org.libsdl.app`, `org.jnius`,
   `org.renpy.android` (Kivy / python-for-android), `com.chaquo.python`
   (Chaquopy), `org.beeware.android` (Briefcase) — plus any namespace the
   consumer's own generated bootstrap occupies. The shared portion of the list
   is deliberately consumer-independent: a distribution must not be able to
   clobber one toolchain's runtime just because a different toolchain built the
   application.
5. Two distributions claiming overlapping namespaces **MUST** fail, naming both.

> Rationale: without rule 4, a distribution shipping
> `org/kivy/android/PythonActivity.java` replaces the application's own entry
> point — unauthenticated, reachable through any transitive dependency. The
> exclusivity model parallels Cargo's `links` key, which permits only one crate
> to claim a native library.

### 6.2 Build requirements: `[android.requires]`

```toml
[android.requires]
compile_sdk = 34
min_sdk = 24
```

These are **floors**, not settings. A consumer **MUST** fail, naming the
distribution, when the application's configured value is lower. A consumer
**MUST NOT** raise the application's configuration to satisfy them.

### 6.3 Application-supplied values: `[[android.requires.application_values]]`

```toml
[[android.requires.application_values]]
name = "com.google.android.gms.ads.APPLICATION_ID"
reason = "Your AdMob application ID, from the AdMob console"
```

Values a producer needs but cannot supply. `reason` is **REQUIRED**.

A declared application value is satisfied when the application's own
configuration supplies a manifest `<meta-data>` entry with that `name`; the
consumer emits nothing on the producer's behalf (a *requires* is checked, never
auto-satisfied — §2.1).

A contribution **MAY** also reference an application value **inline** —
`{ application_value = "<name>" }`, as in §6.8's `view_links` — which implicitly
declares the same requirement: the application must supply the named value
through the consumer's configuration, and the consumer substitutes it where
referenced. (This mirrors AGP manifest placeholders, the mechanism established
Android libraries such as AppAuth already use for application-specific values
like a redirect scheme.)

In both forms a consumer **MUST** report unsatisfied values as prerequisites and
**MUST** fail when one is absent, naming the distribution and the `reason`. A
consumer **MUST NOT** invent a value.

### 6.4 Source: `[android.contributes.src]`

```toml
[android.contributes.src]
java = ["java"]
kotlin = []
```

Path rules per §4.1. From each listed directory the consumer stages, recursively,
exactly the files with the matching extension — `.java` for `java` roots, `.kt`
for `kotlin` roots — and ignores other files. Contents **MUST** be source text;
a consumer **MUST** compile them with the application's own toolchain, and
**MUST** exclude them from any Python payload it assembles. Subject to §6.1
rule 1.

### 6.5 Gradle dependencies: `[[android.contributes.gradle_dependencies]]`

```toml
[[android.contributes.gradle_dependencies]]
coordinate = "com.google.android.gms:play-services-ads:25.2.0"
configuration = "implementation"    # optional; default and only v1 value
```

- `coordinate` **MUST** be exactly versioned. Dynamic versions (`+`, ranges) and
  **changing versions** (`-SNAPSHOT`) are invalid — a coordinate whose content
  can change under a fixed spelling defeats the record of §9.
- `configuration` defaults to `implementation`, the only value defined in
  version 1. Other Gradle configurations (`api`, `compileOnly`, `runtimeOnly`,
  annotation processors) may be added in a minor revision; per §4.4 a consumer
  **MUST** reject a value it does not implement, naming the distribution.

**Resolution is locked, not merely versioned.** An exact coordinate does not by
itself make resolution reproducible: transitive versions can float. A consumer
**MUST** record the fully resolved dependency graph — every artifact and
version, including transitives — in the integration record (§9), and **MUST**
resolve from that record on subsequent builds until a new resolution is
accepted. A consumer **SHOULD** record a checksum per resolved artifact.

This is the **RECOMMENDED** channel for anything larger than a few glue
classes. Note that a coordinate may resolve to an Android library (`.aar`)
whose own manifest AGP merges into the application's; see §9 and §11.

### 6.6 Maven repositories: `[[android.contributes.gradle_repositories]]`

```toml
[[android.contributes.gradle_repositories]]
url = "https://maven.pkg.github.com/example/repo"
reason = "Hosts org.example:shim, which is not on Maven Central"
groups = ["org.example"]
```

`reason` is **REQUIRED**. At least one of `groups` (Maven group IDs) or
`modules` (`group:artifact` pairs) is **REQUIRED**, and a consumer **MUST**
restrict the repository's participation in resolution to the declared
groups/modules — using its build system's native mechanism where one exists
(Gradle repository content filtering / `exclusiveContent`).

A repository contribution changes where artifacts in the application's build can
resolve from, which makes it a supply-chain concern of a different order than
any other contribution — an unconstrained repository added by a transitive
dependency is a dependency-confusion vector. The content constraint reduces
that surface from "may shadow anything" to "may serve exactly what it named."

A consumer **MUST** additionally report repository contributions with distinct
prominence in the record and report of §9 — never folded into a generic list —
and **SHOULD** surface them in any standing diagnostic (e.g. a doctor check). A
consumer **MAY**, as its own policy, require explicit application approval
before adding a contributed repository to resolution.

### 6.7 Permissions and features: `[[android.contributes.permissions]]`, `[[android.contributes.features]]`

```toml
[[android.contributes.permissions]]
name = "android.permission.INTERNET"
reason = "Ad delivery"

[[android.contributes.features]]
name = "android.hardware.bluetooth_le"
```

- `name` is the **canonical manifest string** — `android.permission.INTERNET`,
  not a shorthand. No prefix expansion is defined; this accommodates custom and
  vendor permissions with no additional rule.
- `reason` on a permission is **RECOMMENDED**; consumers **SHOULD** carry it
  into the record and report of §9.
- Declared permissions **are staged into the generated manifest.** The gate is
  §9 — the contribution is recorded, attributed, and reported, not silently
  merged and not withheld pending a prompt. This is deliberately the same
  capability an Android AAR dependency has via manifest merging, with the
  disclosure an AAR does not provide.
- A producer **MUST NOT** set `required` on a feature. A consumer **MUST** treat
  every producer-declared feature as `required = false`, and **MUST NOT**
  promote one on a producer's declaration alone.

> Rationale: whether an application *requires* Bluetooth or merely uses it when
> present is a property of the application. A producer promoting a feature to
> required would silently remove the application from devices lacking that
> hardware.

**Application-side suppression.** A consumer **MUST** provide a means for the
application to suppress any contributed permission. A suppressed permission
**MUST** be omitted from the generated manifest, together with any feature it
alone implied, and the suppression **MUST** appear in the record and report of
§9 (e.g. `− android.permission.ACCESS_FINE_LOCATION (suppressed by
application)`). Suppression is global per permission — the merged manifest
either carries the permission or it does not — and this specification does not
define the application-side syntax, only the capability; the application's
configuration format is the consumer's concern.

Suppression is **at the application's own risk**: the producer's code may fail
at runtime, or degrade silently, when a permission it declared is withheld. A
consumer **SHOULD** make an active suppression visible in its standing
diagnostics so the failure remains traceable to the application's choice rather
than being reported against the producer.

> Rationale: this completes the authority model — a producer requests, the
> application grants or refuses — and it is the recourse the platform itself
> provides for the equivalent case: Android's manifest merger removes an
> AAR-merged permission via `tools:node="remove"`. Without it, a contributed
> permission that violates a store policy (e.g.
> `android.permission.QUERY_ALL_PACKAGES`) would leave the application no
> remedy short of forking the producer.

### 6.8 Manifest components: `[[android.contributes.components]]`

```toml
[[android.contributes.components]]
kind = "service"        # service | activity | receiver | provider
name = "org.example.mypkg.PushService"

[[android.contributes.components]]
kind = "receiver"
name = "com.vendor.sdk.InstallReferrerReceiver"
from_dependency = "com.vendor:sdk"

[[android.contributes.components]]
kind = "activity"
name = "org.example.mypkg.RedirectActivity"
exported_required = true
reason = "Receives the OAuth redirect from the browser"

  [[android.contributes.components.view_links]]
  scheme = { application_value = "oauth_redirect_scheme" }
```

**Provenance.** A component's class comes from one of two places, and the entry
states which:

- **Producer source** (no `from_dependency`): `name` **MUST** refer to a class
  the distribution contributes (§6.4) and **MUST** fall under an owned namespace
  (§6.1 rule 2).
- **A declared dependency** (`from_dependency = "group:artifact"`): the value
  **MUST** match the group and artifact of a coordinate the same sidecar
  declares (§6.5). The owned-namespace rule does not apply — the class is the
  dependency's. A consumer **SHOULD** verify the class exists in the resolved
  artifact. Two distributions registering the same component class **MUST**
  fail, naming both.

**Export.** Components are registered `android:exported="false"` by default. A
producer **MUST NOT** declare `exported = true` directly. A producer **MAY**
declare `exported_required = true` with a `reason` (**REQUIRED** when present);
a consumer **MUST** treat that as an application prerequisite: it **MUST NOT**
register the component as exported without explicit application approval, and
**MUST** report the pending requirement, naming the distribution and the
`reason`.

> Rationale: an exported component is an IPC entry point reachable by any other
> application on the device. Some integrations legitimately need one — OAuth
> callbacks, deep links — but opening it is the application's decision. The
> producer states the need; the application grants it.

**Link targets: `view_links`.** An activity that must be reachable from a
browser or another app — an OAuth redirect receiver, a deep-link target — needs
an intent filter. Version 1 deliberately models **one stereotyped filter**, not
the intent-filter grammar:

```toml
  [[android.contributes.components.view_links]]
  scheme = { application_value = "oauth_redirect_scheme" }  # or a literal string
  host = "oauth2redirect"                                   # optional
  path_prefix = "/callback"                                 # optional
```

- Valid only on `kind = "activity"` entries that declare
  `exported_required = true` — a link target that is not exported is
  unreachable, and a consumer **MUST** reject the inconsistent combination.
- The consumer **generates** the filter: `android.intent.action.VIEW`, the
  `DEFAULT` and `BROWSABLE` categories, and one `<data>` element from the
  declared fields. Actions and categories are not spellable; they are implied by
  the type. (Omitting `DEFAULT` by hand is the classic silent-failure bug this
  removes.)
- `scheme` is **REQUIRED**, as a literal or an inline application-value
  reference (§6.3) — a producer cannot know the application's redirect scheme,
  which is registered per-application with the identity provider.
- The record and report of §9 **MUST** show the link data alongside the export
  (`exported activity, matching scheme ${oauth_redirect_scheme}`).
- **Not expressible in v1**: verified App Links (`android:autoVerify` — requires
  `assetlinks.json` on the application's domain, which is application
  infrastructure), mimeTypes, path patterns, and filters on non-activity
  components. Anticipated as minor revisions (§10); per §4.3 a producer needing
  them declares the contract that provides them.

### 6.9 Shrinker keep patterns: `[android.contributes.r8]`

```toml
[android.contributes.r8]
keep_classes = ["org.example.mypkg.**", "com.google.android.gms.ads.**"]
```

`keep_classes` is a list of class patterns, **not** raw ProGuard/R8 directives.
The consumer generates the corresponding `-keep class <pattern> { *; }` rules
itself. Each pattern **MUST** fall within one of two scopes (§6.1 rule 3); a
consumer **MUST** reject a pattern matching neither, naming the distribution
and the pattern:

1. an **owned namespace** — protecting the distribution's own
   reflectively-reached classes; or
2. the **group** of a Gradle coordinate **the same sidecar declares** (§6.5) —
   reflective access to a declared dependency's classes is the dominant
   JNI-bridge pattern, and those classes are otherwise invisible to the
   shrinker. This scope permits *keeping*, not contributing, and is not
   exclusive.

The group-prefix check is a declaration-time gate, and Maven group IDs only
conventionally match Java package names. A consumer **SHOULD** therefore verify
at build time that every class a pattern matches on the compilation classpath
belongs to an owned namespace or to the resolved artifacts of the sidecar's
declared coordinates — a listing of the resolved `.jar`/`.aar` contents, not a
parser — and reject patterns that reach beyond them.

A consumer **MUST** apply these only when the application has enabled
shrinking.

> Rationale for the structured form: R8's rule grammar is large (`-dontwarn`,
> `-keepattributes`, `-if`, …) and validating raw directives against a
> namespace would require implementing a substantial parser. Restricting
> version 1 to class-keep patterns makes validation a string-prefix check plus
> an archive listing. Raw rules are also a capability: a single
> `-keep class ** { *; }` from a transitive dependency disables shrinking for
> the entire application. The bounded worst case here is a producer exempting a
> library it itself declared — a size cost, not an application-wide
> shrink-disable.

## 7. iOS

### 7.1 Symbol prefixes: `[ios]`

```toml
[ios]
swift_symbol_prefixes = ["MyPkg"]
```

**RECOMMENDED** when the distribution contributes Swift source (§7.5): prefix
contributed type names, and in particular `@objc` runtime names, with a declared
prefix.

This is **producer guidance, not an ownership claim**, and it deliberately does
not live in an `owns` table: Swift source compiled into the application target
shares one module, and `@objc` runtime names are global across modules, so a
consumer cannot enforce exclusivity the way §6.1 does for Java. A consumer
**SHOULD** use declared prefixes to attribute a redeclaration or duplicate-name
error to the contributing distribution. Compiling each producer's Swift into a
separate module would give Swift-level symbols real ownership and is anticipated
hardening (§10) — but it would still not police `@objc` runtime names, which are
the namespace this tier actually exercises.

### 7.2 Build requirements: `[ios.requires]`

```toml
[ios.requires]
deployment_target = "15.0"
```

A floor, with the same semantics as §6.2.

### 7.3 Required entitlements: `[[ios.requires.entitlements]]`

```toml
[[ios.requires.entitlements]]
key = "aps-environment"
reason = "Push notification delivery"
```

`reason` is **REQUIRED**. A consumer **MUST** report these as prerequisites and
**MUST NOT** write them into the application's entitlements.

> Rationale: entitlements are bound to the App ID and provisioning profile.
> `codesign` requires the application's entitlements to be a subset of the
> profile's, so writing one the developer has not enabled produces a signing
> failure with no trace back to the distribution that caused it. This is a
> declaration a consumer cannot satisfy on its own.

### 7.4 Swift packages: `[[ios.contributes.swift_packages]]`

```toml
[[ios.contributes.swift_packages]]
name = "Shim"
url = "https://github.com/example/shim"
requirement = { exact = "1.2.3" }
products = ["Shim"]
```

`requirement` **MUST** be exactly one of:

| Form | Meaning |
| --- | --- |
| `{ exact = "1.2.3" }` | That version only |
| `{ from = "1.2.0" }` | SwiftPM's up-to-next-major range |
| `{ revision = "<commit>" }` | A specific commit |

A `branch` requirement **MUST NOT** appear in a distribution published to a
package index; a consumer **MUST** reject it, naming the distribution.

Reproducibility (§2.1) applies across platforms. When a Swift package uses
`from`, the consumer **MUST** record the version actually resolved in the
integration record (§9) **and resolve from that record on subsequent builds**
until a new resolution is accepted — the semantics SwiftPM itself implements
with `Package.resolved`.

Swift Package Manager is the **RECOMMENDED** channel for anything larger than a
few glue files. Note that a Swift package may vend prebuilt binary targets; see
§11.

### 7.5 Source: `[ios.contributes.src]`

```toml
[ios.contributes.src]
swift = ["swift"]
```

Path rules per §4.1; the consumer stages `.swift` files recursively and ignores
other files. Intended for small `@objc` shims whose value is versioning
atomically with the Python half; it **SHOULD NOT** be used for a library.

### 7.6 Info.plist: `[ios.contributes.info_plist]`

```toml
[ios.contributes.info_plist.values]
NSBluetoothAlwaysUsageDescription = "Connects to your fitness tracker."

[ios.contributes.info_plist.append]
LSApplicationQueriesSchemes = ["examplescheme"]
```

Two contribution modes, by shape:

- **`values`** — scalar keys, set verbatim. A consumer **MUST** fail on a key
  that collides with one it manages itself, and on two distributions setting the
  same key to different values, naming the distributions.
- **`append`** — array-valued keys. Contributions from all distributions and the
  application are concatenated and de-duplicated in a deterministic order: the
  application's entries first, then each distribution's in normalized
  distribution-name order.

Dictionary-valued keys (e.g. `NSAppTransportSecurity`) are not expressible in
version 1; typed contributions for specific structures may be added in a minor
revision.

## 8. Consumer requirements

A conforming consumer **MUST**:

1. Enforce the contract version gate, including the minor (§4.3), and fail
   closed on unrecognized keys in platform tables it builds (§4.4).
2. Restrict candidate producers to the application's dependency closure (§3.2).
3. Discover by iterating the group, ignoring the entry-point name (§3.3), and
   never import the producing package or execute declared content (§2.1, §3.2).
4. Fail when a distribution declares multiple entries (§3.4), when a declared
   resource cannot be read (§3.2), or when a resource violates the containment
   and symlink rules (§4.1).
5. Enforce ownership and fail on collision, never resolving by order (§6.1).
6. Never promote a feature to `required` (§6.7), never register a component as
   exported without explicit application approval (§6.8), and never write a
   required entitlement (§7.3).
7. Provide application-side permission suppression, honor it in the generated
   manifest, and report it (§6.7).
8. Fail when a producer's `requires` exceeds the application's configuration
   (§6.2, §7.2), or when a required application value — declared or referenced
   inline — is absent (§6.3).
9. Record each distribution's resolved contribution durably and in reviewable
   form, per the lifecycle of §9, and fail the build when the effective set
   drifts from the last accepted record.
10. Restrict contributed repositories to their declared groups/modules and
    report them with distinct prominence (§6.6).
11. Validate shrinker keep patterns against their permitted scopes (§6.9).
12. Enforce reproducible native dependency resolution: reject dynamic and
    changing versions, lock the resolved Gradle graph, and pin resolved Swift
    package versions in the record (§6.5, §7.4).
13. Validate `view_links` (activity-only, export-gated) and generate their
    filters (§6.8).
14. Exclude sidecar directories from any Python payload it assembles.
15. Name the contributing distribution in every diagnostic.

A conforming consumer **SHOULD**:

- Warn on unrecognized top-level tables (§4.4).
- Verify keep patterns against resolved artifact contents (§6.9), and
  `from_dependency` classes against the resolved artifact (§6.8).
- Record per-artifact checksums for the resolved Gradle graph (§6.5).
- Report the **effective native delta** introduced by resolved dependencies —
  permissions and components arriving via library manifests that no sidecar and
  not the application declared — attributed to the resolved artifact where
  determinable (§9, §11).

## 9. Recording and review

Requirement 8.9 is about **disclosure**, not integrity.

The lifecycle is:

1. **Compute** the integration resolution — the effective set from the
   application's dependency closure, including locked native dependency graphs
   (§6.5, §7.4).
2. **Compare** it against the last accepted integration record.
3. **Report the delta**, naming each distribution and how it entered the
   dependency closure.
4. **Fail, or require explicit acceptance** (a re-lock, a flag, a committed
   record — the consumer's workflow decides the form).
5. **Update the record** only on acceptance.

A report **MUST** carry three things — the distribution, **how it entered the
dependency closure**, and the delta:

```
analytics-shim 2.1.0  (via some-ui-lib)
  + permission  android.permission.ACCESS_FINE_LOCATION  ("optional BLE device discovery")
  + feature     android.hardware.location.gps  (required=false)
```

The middle element matters most for the case that motivates the requirement — a
transitive dependency the application author has never heard of.

**Integration inputs are hashed for every producer** — not only path and
editable installs. The record **MUST** include a SHA-256 per file, keyed by
normalized relative path (forward slashes, relative to the sidecar directory),
covering `native.toml` and every resource it references. The wheel's own hash
pins the distribution, but the useful identity for *this* protocol is precisely
the material the integration was computed from: per-file hashes let a
diagnostic say `java/Bridge.java changed`, not merely "the producer's hash
changed."

**Resolved dependencies can carry native effects of their own.** A Maven
coordinate can resolve to an `.aar` whose manifest AGP merges into the
application's; a Swift package can vend binary targets. A consumer **SHOULD**
include in the record and report the permissions and components the effective
merged manifest contains beyond those declared by sidecars and the application,
attributed to the resolved artifact where determinable. Where a consumer does
not, the record's coverage is the declarations, not the full effective manifest
— and its documentation **MUST** say so.

Two concepts are worth distinguishing by name, though this specification
mandates neither a file nor a format:

- **integration resolution** — computing the effective set (step 1);
- **integration record** — the durable, diffable artifact of the last accepted
  resolution (step 5).

A lockfile entry, a checksum file beside the generated project, or any other
durable artifact satisfies the record. The normative property is that a change
in what distributions contribute **MUST NOT** pass silently.

> Disclosure is not enforcement. If nobody reads the diff, it ships. This is a
> deliberate trade: a blocking prompt inside a build loop earns click-through
> quickly and then provides nothing, whereas a recorded delta stays attributable
> before the fact in review and after the fact in history. The places this
> specification goes beyond disclosure — exported components (§6.8),
> entitlements (§7.3), and repository content constraints (§6.6) — are the ones
> where a contribution opens an externally reachable surface, cannot be
> satisfied by the consumer at all, or reshapes artifact resolution itself.

## 10. Versioning

The entry-point group carries the major version (`native_integration.v1`). A
consumer implementing version *N* **MUST** ignore groups for other major
versions entirely, rather than attempting to read them. Within a major, the
`contract` minor (§4.3) negotiates capabilities: minor revisions add optional
keys and tables, producers declare the smallest contract they use, and an older
consumer rejects a newer declaration visibly instead of mis-building it.

Any change that would alter the meaning of an existing key, or make a previously
valid sidecar invalid, requires a new major version and a new group name.

Anticipated minor-revision work, deliberately excluded from version 1: verified
App Links (`autoVerify`) and further filter forms beyond `view_links`;
conditional contributions (a `when` key with a **closed vocabulary** of
conditions such as ABI or simulator/device — not an expression language);
further Gradle configurations; further namespace-scoped shrinker rule forms;
typed Info.plist structures; and per-producer Swift modules (§7.1).

## 11. Out of scope

| Not covered | Reason |
| --- | --- |
| Prebuilt `.aar` **embedded in the wheel** | Carries an `AndroidManifest.xml` that merges into the application's, defeating §6.7 and §6.8 with no attribution |
| Prebuilt iOS binaries **carried by the wheel** | Forces a platform tag onto an otherwise pure-Python wheel; unauditable |
| Native `.so`, extension modules | Solved by `android_<api>_<abi>`-tagged wheels ([PEP 738](https://peps.python.org/pep-0738/)) |
| iOS frameworks in wheels | Solved by `ios_*`-tagged wheels ([PEP 730](https://peps.python.org/pep-0730/)) |
| Scripts, hooks, build plugins | Excluded on principle (§2.1), not as a deferral |
| Xcode build settings, compiler/linker flags | Arbitrary build mutation; revisit only with a concrete, bounded need |
| Application configuration | The application's own build settings are the consumer's concern |

The wheel-embedded qualifier is deliberate: a **declared Maven coordinate** may
resolve to an `.aar`, and a **declared Swift package** may vend binary targets —
those arrive through the platform's own dependency channel, locked by §6.5/§7.4
and surfaced by §9's effective-delta reporting, rather than hidden inside a
Python artifact. What this specification excludes is native binaries smuggled in
the wheel itself, where no resolver, lock, or manifest tooling ever sees them.

## 12. Producer guidance

A producer **SHOULD** declare only what it **unconditionally** requires. A
declaration is unconditional when every application that imports the package
needs it; anything needed only when a particular feature is used does not belong
in the package's own sidecar.

The corollary matters most for **facade packages** — libraries exposing many
optional platform features behind one API (the [Plyer](https://github.com/kivy/plyer)
shape). A facade declaring the union of every permission any feature *might*
use hands every application its worst-case manifest, and no amount of
disclosure repairs that; per-permission suppression (§6.7) becomes each
application's cleanup chore rather than a rare override.

Feature-conditional native surface **SHOULD** instead ship as **optional
distributions**, each carrying its own sidecar, with extras as the opt-in
mechanism:

```toml
# the facade's pyproject.toml
[project.optional-dependencies]
gps = ["plyer-gps"]
camera = ["plyer-camera"]
```

`pip install plyer[gps]` then installs `plyer-gps`, whose sidecar contributes
exactly `android.permission.ACCESS_FINE_LOCATION` — nothing else. An extra
cannot vary the facade's *own* sidecar (extras select dependencies; they do not
change a distribution's contents), but it can select a distribution that
carries one, which is all that is needed.

This is why the specification defines no conditional-contribution syntax (§10):
**the dependency graph is the conditionality mechanism.** Sidecars are
per-distribution, applications opt in by depending on the piece they use, and
the record of §9 attributes each contribution to the smallest meaningful unit.

The honest cost falls on the producer: splitting a facade into optional
distributions is real packaging work (separate releases, an import layout that
tolerates missing pieces). The guidance is **SHOULD**, not MUST, for exactly
that reason — and §6.7's suppression exists in part as the application's
recourse when a producer declares more than its applications want.

## Appendix A: why contributions stay per-distribution

The tempting implementation is to let every distribution write its material into
one shared location under `site-packages` and let the installer merge them. It is
less code, and it forecloses most of this specification.

A merged tree **destroys provenance at install time**. Once files are overlaid,
nothing can determine which distribution contributed which file — so collision
detection, per-distribution attribution, the review record of §9, and every
diagnostic required by 8.15 all become impossible.

It also makes a shared source tree last-writer-wins by construction, which is the
substitution path §6.1 exists to close.

Keeping contributions inside each distribution costs an explicit merge step in
the consumer. That step is where validation, attribution, and collision detection
live.

## Appendix B: why not a build backend

An alternative is a PEP 517 backend that transforms configuration in the
producer's `pyproject.toml` into wheel payload. It reads well and it has been
built.

It requires one backend wrapper per existing backend, forever, and excludes every
backend nobody wrote one for. The entry-point metadata and package data this
convention relies on are standard wheel features every major backend can produce
— though the *file-inclusion configuration* is backend-specific (setuptools
`package-data`, with Hatchling, Flit, pdm, and maturin each having their own) —
and none of them need to know this specification exists.

The declaration cannot live in `pyproject.toml` directly: arbitrary `[tool.*]`
tables do not survive into the wheel or into `site-packages`, so a consumer
reading installed distributions never sees them. That constraint is what forces
either a custom backend or static package data, and this specification chooses
the latter.

## Appendix C: prior art

- **Cargo** — the `links` key gives a crate an exclusive claim on a native
  library, enforced across the graph; §6.1's ownership model is the same idea.
  Cargo's build scripts, by contrast, are exactly the capability §2.1 excludes:
  powerful, and executable.
- **pkg-config / SwiftPM system libraries** — the abstraction this specification
  borrows: a dependency describes what consuming it requires; the consumer's
  build system decides how to satisfy it. Declarative data, no executable hooks.
- **Gradle dependency locking / SwiftPM `Package.resolved`** — the locked-graph
  semantics §6.5 and §7.4 require: exact coordinates are not reproducibility;
  recorded resolutions are.
- **AGP manifest placeholders (e.g. AppAuth's redirect scheme)** — the
  established mechanism behind §6.3's inline application values: the library
  declares the filter shape, the application supplies the value.
- **PEP 561** — the standardization shape: a marker shipped as package data, a
  consumer that is not an installer, and normative obligations on that consumer,
  written down after the practice existed.
