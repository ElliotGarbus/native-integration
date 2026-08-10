# The native-integration specification

**Version:** `1` (draft)
**Entry-point group:** `native-integration.v1`

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
- **Sidecar** — the declaration file a producer ships.

## 2. Overview

A producer ships a TOML file inside its own wheel and registers an entry point
identifying its location. A consumer enumerates installed distributions, reads
each sidecar, validates it against this specification, and stages the declared
material into the native project it generates.

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
| **`owns`** | An exclusive claim, enforced across all distributions | a Java namespace, a Swift symbol prefix |
| **`requires`** | A condition the application or build environment must satisfy; the consumer checks it but never satisfies it | an SDK floor, an entitlement, an application-supplied value |
| **`contributes`** | Material the consumer stages into the generated project on the producer's behalf | source files, dependency coordinates, permissions, manifest components |

The categories carry the security model: ownership claims are exclusive and
collision-checked; requirements are reported and verified, never auto-satisfied;
contributions are staged, attributed, and disclosed per §9.

**Contributions stay per-distribution.** Provenance survives from declaration to
diagnostic; see Appendix A.

**Native dependency resolution MUST be reproducible.** Every dependency a
producer contributes must resolve identically on every build; see §6.5 and §7.4.

## 3. Discovery

### 3.1 The entry point

A producer **MUST** declare exactly one entry point in the group
`native-integration.v1`:

```toml
[project.entry-points."native-integration.v1"]
native = "mypkg._native"
```

- The entry-point name **SHOULD** be `native`. The name has no semantic meaning
  and consumers ignore it (§3.3).
- The entry-point value **MUST** be a dotted path locating the sidecar's
  directory within the distribution (§3.2). It **MUST NOT** be a filesystem
  path, and **MUST NOT** carry an `:attr` suffix.

**The entry point is used solely as distribution metadata identifying the
location of a resource.** Its value uses dotted-path syntax for compatibility
with entry-point metadata; it is a *resource anchor*, not an import target. A
consumer **MUST NOT** load the entry point or import anything it names.

> The quotes around the group name are required TOML syntax: a dot in an unquoted
> table header is a nesting separator, so `[project.entry-points.native-integration.v1]`
> declares a group named `native-integration` containing a table `v1`, which no
> consumer will find.

### 3.2 Resolution

A consumer **MUST** resolve the declaration as follows:

1. Enumerate installed distributions via `importlib.metadata`.
2. For each, read entry points in the group `native-integration.v1`.
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
    native.toml          ← fixed name; the entry point does not spell it
    java/…               ← optional, per §6.4
    swift/…              ← optional, per §7.5
```

An `__init__.py` in the sidecar directory is **OPTIONAL**. The dotted entry-point
value is a resource anchor (§3.1); whether the directory is importable as a
Python package is irrelevant, because nothing ever imports it.

Nothing is placed at the `site-packages` root.

### 4.2 One file, all platforms

A distribution **MUST** ship exactly one sidecar covering every platform it
supports. Platforms are tables within it, not separate files.

> Rationale: the contract version is declared once and validated in a single read
> before anything is trusted. Per-platform files would allow those versions to
> disagree.

### 4.3 Contract version

The sidecar **MUST** declare a top-level `contract` key whose value is a string
holding the major version of this specification:

```toml
contract = "1"
```

A consumer **MUST** reject a sidecar whose `contract` major version it does not
implement, naming the distribution. It **MUST NOT** parse it partially or ignore
unrecognized fields in order to proceed.

### 4.4 Unknown keys

Within a supported major version, a consumer **SHOULD** ignore unrecognized keys
and **SHOULD** report them as a warning naming the distribution. This permits
additive minor revisions.

## 5. Structure

```toml
contract = "1"

[android.owns]         # §6.1 — exclusive claims
[android.requires]     # §6.2–6.3 — conditions the application must satisfy
[android.contributes]  # §6.4–6.9 — material staged into the project

[ios.owns]             # §7.1
[ios.requires]         # §7.2–7.3
[ios.contributes]      # §7.4–7.6
```

A sidecar declaring no platform table is valid and contributes nothing. Within a
platform table, each of `owns`, `requires`, and `contributes` is optional.

## 6. Android

### 6.1 Ownership: `[android.owns]`

```toml
[android.owns]
java_namespaces = ["org.example.mypkg"]
```

`java_namespaces` is **REQUIRED** when the distribution contributes Java or
Kotlin source (§6.4), manifest components (§6.8), or shrinker keep patterns
(§6.9).

A consumer **MUST** enforce all of the following, and **MUST** fail rather than
resolve any conflict by file or copy order:

1. Every contributed source file's path **and** its declared `package` **MUST**
   fall under an owned namespace.
2. Every manifest component name (§6.8) **MUST** fall under an owned namespace.
3. Every shrinker keep pattern (§6.9) **MUST** fall within one of its
   permitted scopes: an owned namespace, or the group of a Gradle coordinate
   the same sidecar declares.
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

The requirement is satisfied when the application's own configuration supplies a
manifest `<meta-data>` entry with that `name`; the consumer emits nothing on the
producer's behalf (a *requires* is checked, never auto-satisfied — §2.1). A
consumer **MUST** report these as prerequisites and **MUST** fail when the
application has not provided one, naming the distribution and the `reason`. A
consumer **MUST NOT** invent a value.

### 6.4 Source: `[android.contributes.src]`

```toml
[android.contributes.src]
java = ["java"]
kotlin = []
```

Paths are relative to `native.toml` and **MUST NOT** escape its directory.
Contents **MUST** be source text. A consumer **MUST** compile them with the
application's own toolchain, and **MUST** exclude them from any Python payload
it assembles. Subject to §6.1 rule 1.

### 6.5 Gradle dependencies: `[[android.contributes.gradle_dependencies]]`

```toml
[[android.contributes.gradle_dependencies]]
coordinate = "com.google.android.gms:play-services-ads:25.2.0"
configuration = "implementation"    # optional; default and only v1 value
```

- `coordinate` **MUST** be fully versioned. Dynamic versions (`+`, ranges) are
  invalid.
- `configuration` defaults to `implementation`, the only value defined in
  version 1. Other Gradle configurations (`api`, `compileOnly`, `runtimeOnly`,
  annotation processors) may be added in a minor revision; a v1 consumer
  **MUST** reject a value it does not implement, naming the distribution.

This is the **RECOMMENDED** channel for anything larger than a few glue
classes.

### 6.6 Maven repositories: `[[android.contributes.gradle_repositories]]`

```toml
[[android.contributes.gradle_repositories]]
url = "https://maven.pkg.github.com/example/repo"
reason = "Hosts org.example:shim, which is not on Maven Central"
```

`reason` is **REQUIRED**.

A repository contribution changes where *every* artifact in the application's
build can resolve from, which makes it a supply-chain concern of a different
order than any other contribution — a hostile or compromised repository added by
a transitive dependency is a dependency-confusion vector.

A consumer **MUST** report repository contributions with distinct prominence in
the record and report of §9 — never folded into a generic list — and **SHOULD**
surface them in any standing diagnostic (e.g. a doctor check). A consumer
**MAY**, as its own policy, require explicit application approval before adding
a contributed repository to resolution.

> Version 1 deliberately specifies prominent disclosure rather than mandatory
> approval, for consistency with §9's model. Consumers with stricter
> supply-chain postures are expected to use the policy latitude above.

### 6.7 Permissions and features: `[[android.contributes.permissions]]`, `[[android.contributes.features]]`

```toml
[[android.contributes.permissions]]
name = "INTERNET"
reason = "Ad delivery"

[[android.contributes.features]]
name = "android.hardware.bluetooth_le"
```

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
§9 (e.g. `− ACCESS_FINE_LOCATION (suppressed by application)`). Suppression is
global per permission — the merged manifest either carries the permission or it
does not — and this specification does not define the application-side syntax,
only the capability; the application's configuration format is the consumer's
concern.

Suppression is **at the application's own risk**: the producer's code may fail
at runtime, or degrade silently, when a permission it declared is withheld. A
consumer **SHOULD** make an active suppression visible in its standing
diagnostics so the failure remains traceable to the application's choice rather
than being reported against the producer.

> Rationale: this completes the authority model — a producer requests, the
> application grants or refuses — and it is the recourse the platform itself
> provides for the equivalent case: Android's manifest merger removes an
> AAR-merged permission via `tools:node="remove"`. Without it, a contributed
> permission that violates a store policy (e.g. `QUERY_ALL_PACKAGES`) would
> leave the application no remedy short of forking the producer.

### 6.8 Manifest components: `[[android.contributes.components]]`

```toml
[[android.contributes.components]]
kind = "service"        # service | activity | receiver | provider
name = "org.example.mypkg.PushService"

[[android.contributes.components]]
kind = "activity"
name = "org.example.mypkg.OAuthCallbackActivity"
exported_required = true
reason = "Receives the OAuth redirect URI from the browser"
```

`name` **MUST** refer to a class the distribution contributes (§6.4) and
**MUST** fall under an owned namespace (§6.1 rule 2). To register a class
supplied by a Gradle dependency, subclass it in an owned namespace — the
standard Android idiom — so ownership and attribution stay intact.

Components are registered `android:exported="false"` by default. A producer
**MUST NOT** declare `exported = true` directly. A producer **MAY** declare
`exported_required = true` with a `reason` (**REQUIRED** when present); a
consumer **MUST** treat that as an application prerequisite: it **MUST NOT**
register the component as exported without explicit application approval, and
**MUST** report the pending requirement, naming the distribution and the
`reason`.

> Rationale: an exported component is an IPC entry point reachable by any other
> application on the device. Some integrations legitimately need one — OAuth
> callbacks, deep links — but opening it is the application's decision. The
> producer states the need; the application grants it.

### 6.9 Shrinker keep patterns: `[android.contributes.r8]`

```toml
[android.contributes.r8]
keep_classes = ["org.example.mypkg.**"]
```

`keep_classes` is a list of class patterns, **not** raw ProGuard/R8 directives.
The consumer generates the corresponding `-keep class <pattern> { *; }` rules
itself. Each pattern **MUST** fall within one of two scopes (§6.1 rule 3); a
consumer **MUST** reject a pattern matching neither, naming the distribution
and the pattern:

1. an **owned namespace** — protecting the distribution's own
   reflectively-reached classes; or
2. the **group** of a Gradle coordinate **the same sidecar declares** (§6.5) —
   e.g. declaring `com.google.android.gms:play-services-ads:…` permits patterns
   under `com.google.android.gms.**`. Reflective access to a declared
   dependency's classes is the dominant JNI-bridge pattern, and those classes
   are otherwise invisible to the shrinker. This scope permits *keeping*, not
   contributing, and is not exclusive: any distribution declaring the
   coordinate may keep under its group. The bounded worst case is a producer
   exempting its own dependency from shrinking — a size cost confined to a
   library it added, not an application-wide shrink-disable.

A consumer **MUST** apply these only when the application has enabled
shrinking.

> Rationale for the structured form: R8's rule grammar is large (`-dontwarn`,
> `-keepattributes`, `-if`, …) and validating raw directives against a
> namespace would require implementing a substantial parser. Restricting
> version 1 to class-keep patterns makes validation a string-prefix check while
> covering the dominant need — protecting a package's own reflectively-reached
> classes. Raw rules are also a capability: a single `-keep class ** { *; }`
> from a transitive dependency disables shrinking for the entire application.
> Further rule forms, namespace-scoped, may be added in a minor revision.

## 7. iOS

### 7.1 Ownership: `[ios.owns]`

```toml
[ios.owns]
swift_symbol_prefixes = ["MyPkg"]
```

**REQUIRED** when the distribution contributes Swift source (§7.5).

> Swift source compiled into the application target shares one module namespace,
> so this guarantee is weaker than §6.1: a consumer **SHOULD** attribute a
> redeclaration error to the contributing distribution, but is not expected to
> prevent it.

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

Reproducibility (§2.1) applies across platforms: Gradle coordinates are fully
versioned by construction (§6.5); when a Swift package uses `from`, the
consumer's record (§9) **MUST** pin the version actually resolved, so two
builds from the same record resolve identically.

Swift Package Manager is the **RECOMMENDED** channel for anything larger than a
few glue files.

### 7.5 Source: `[ios.contributes.src]`

```toml
[ios.contributes.src]
swift = ["swift"]
```

Same path rules as §6.4. Intended for small `@objc` shims whose value is
versioning atomically with the Python half; it **SHOULD NOT** be used for a
library.

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

1. Reject a `contract` major version it does not implement (§4.3).
2. Discover by iterating the group, ignoring the entry-point name (§3.3).
3. Fail when a distribution declares multiple entries (§3.4), or when a
   declared resource cannot be read (§3.2).
4. Enforce ownership and fail on collision, never resolving by order (§6.1).
5. Never promote a feature to `required` (§6.7), never register a component as
   exported without explicit application approval (§6.8), and never write a
   required entitlement (§7.3).
6. Provide application-side permission suppression, honor it in the generated
   manifest, and report it (§6.7).
7. Fail when a producer's `requires` exceeds the application's configuration
   (§6.2, §7.2), or when a required application value is absent (§6.3).
8. Record each distribution's resolved contribution durably and in reviewable
   form; **report the delta** wherever that record changes, naming the
   distribution and how it entered the dependency tree; and fail the build when
   the effective set drifts from the record (§9).
9. Report repository contributions with distinct prominence (§6.6).
10. Validate shrinker keep patterns against their permitted scopes (§6.9).
11. Enforce reproducible native dependency resolution (§6.5, §7.4).
12. Exclude sidecar directories from any Python payload it assembles.
13. Read declarations without importing the producing package, and without
    executing any declared content (§2.1, §3.2).
14. Name the contributing distribution in every diagnostic.

A conforming consumer **SHOULD** warn on unrecognized keys within a supported
major version (§4.4).

## 9. Recording and review

Requirement 8.8 is about **disclosure**, not integrity.

Integrity needs no new mechanism: a sidecar ships inside its wheel, and any
consumer that pins wheels by hash already pins the declaration transitively. What
a hash cannot convey is *what the declaration says* — a version bump reads
identically whether it fixed a typo or began requesting a location permission.

A consumer **MUST** therefore record the **resolved integration** in a form a
human can diff: which distribution, and what it contributes. A report **MUST**
carry three things:

```
analytics-shim 2.1.0  (via some-ui-lib)
  + permission  ACCESS_FINE_LOCATION  ("optional BLE device discovery")
  + feature     android.hardware.location.gps  (required=false)
```

the distribution, **how it entered the dependency tree**, and the delta. The
middle element matters most for the case that motivates the requirement — a
transitive dependency the application author has never heard of.

Distributions installed from a path or in editable mode have no wheel hash. For
those a consumer **MUST** record a content hash over the sidecar and every file
it references.

Two concepts are worth distinguishing by name, though this specification
mandates neither a file nor a format:

- **integration resolution** — computing the effective set from installed
  distributions;
- **integration record** — the durable, diffable artifact of the last accepted
  resolution.

A lockfile entry, a checksum file beside the generated project, or any other
durable artifact satisfies the record. The normative property is that a change
in what distributions contribute **MUST NOT** pass silently.

> Disclosure is not enforcement. If nobody reads the diff, it ships. This is a
> deliberate trade: a blocking prompt inside a build loop earns click-through
> quickly and then provides nothing, whereas a recorded delta stays attributable
> before the fact in review and after the fact in history. The two places this
> specification goes beyond disclosure — exported components (§6.8) and
> entitlements (§7.3) — are the ones where the contribution opens an externally
> reachable surface or cannot be satisfied by the consumer at all.

## 10. Versioning

The entry-point group carries the major version (`native-integration.v1`). A
consumer implementing version *N* **MUST** ignore groups for other major
versions entirely, rather than attempting to read them.

Additive changes — new optional keys, new platform tables, new `configuration`
values, new requirement forms — do not change the major version. Any change that
would alter the meaning of an existing key, or make a previously valid sidecar
invalid, requires a new major version and a new group name.

Anticipated additive work, deliberately excluded from version 1: conditional
contributions (a `when` key with a **closed vocabulary** of conditions such as
ABI or simulator/device — not an expression language), further Gradle
configurations, further namespace-scoped shrinker rule forms, and typed
Info.plist structures.

## 11. Out of scope

| Not covered | Reason |
| --- | --- |
| Prebuilt `.aar` | Carries an `AndroidManifest.xml` that merges into the application's, defeating §6.7 and §6.8 |
| Prebuilt iOS binaries | Forces a platform tag onto an otherwise pure-Python wheel; unauditable |
| Native `.so`, extension modules | Solved by `android_<api>_<abi>`-tagged wheels ([PEP 738](https://peps.python.org/pep-0738/)) |
| iOS frameworks in wheels | Solved by `ios_*`-tagged wheels ([PEP 730](https://peps.python.org/pep-0730/)) |
| Scripts, hooks, build plugins | Excluded on principle (§2.1), not as a deferral |
| Xcode build settings, compiler/linker flags | Arbitrary build mutation; revisit only with a concrete, bounded need |
| Application configuration | The application's own build settings are the consumer's concern |

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
exactly `ACCESS_FINE_LOCATION` — nothing else. An extra cannot vary the
facade's *own* sidecar (extras select dependencies; they do not change a
distribution's contents), but it can select a distribution that carries one,
which is all that is needed.

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
diagnostic required by 8.14 all become impossible.

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
backend nobody wrote one for. Entry points and package data work with setuptools,
hatchling, flit, pdm, and maturin without any of them knowing this specification
exists.

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
- **PEP 561** — the standardization shape: a marker shipped as package data, a
  consumer that is not an installer, and normative obligations on that consumer,
  written down after the practice existed.
