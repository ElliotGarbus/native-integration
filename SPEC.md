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
pointing at it. A consumer enumerates installed distributions, reads each
sidecar, validates it against this specification, and stages the declared
material into the native project it generates.

Nothing in this specification requires a change to any packaging standard, a
custom build backend, or a new artifact type.

```
producer's pyproject.toml          →  wheel  →  site-packages  →  consumer
  [project.entry-points.…]            .dist-info/entry_points.txt
  package data                        pkg/_native/native.toml
```

## 3. Discovery

### 3.1 The entry point

A producer **MUST** declare exactly one entry point in the group
`native-integration.v1`:

```toml
[project.entry-points."native-integration.v1"]
native = "mypkg._native"
```

- The entry-point **name MUST** be the literal string `native`.
- The entry-point **value MUST** be a module reference — a dotted module path,
  with no `:attr` suffix. It **MUST NOT** be a filesystem path.

> The quotes around the group name are required TOML syntax: a dot in an unquoted
> table header is a nesting separator, so `[project.entry-points.native-integration.v1]`
> declares a group named `native-integration` containing a table `v1`, which no
> consumer will find.

### 3.2 Resolution

A consumer **MUST** resolve the declaration as follows:

1. Enumerate installed distributions via `importlib.metadata`.
2. For each, read entry points in the group `native-integration.v1`.
3. Map the value's dotted module path to a directory path, and read `native.toml`
   inside it — e.g. `mypkg._native` → `mypkg/_native/native.toml` — using
   `Distribution.locate_file()` or equivalent.

A consumer **MUST NOT** import the producing package, or any module of it, at any
point. Metadata reads and file reads only. A module *reference* is not a module
*import*.

> Rationale: a consumer runs on a desktop build host. A distribution targeting
> Android or iOS may raise on import there, or may not be importable at all.

### 3.3 Iteration, not lookup

A consumer **MUST** iterate every entry in the group and ignore the entry-point
name. A consumer **MUST NOT** look the entry up by the name `native`.

> Rationale: the name carries no information — the platform lives inside the file
> — so a name-keyed lookup silently skips any distribution that labelled it
> differently. The package installs, the build succeeds, and the declaration never
> lands. Producers are pinned to one spelling and consumers accept any.

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
    __init__.py          ← so the directory is a module the entry point can name
    native.toml          ← fixed name; the entry point does not spell it
    java/…               ← optional, per §6.3
    swift/…              ← optional, per §7.3
```

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

## 5. Common structure

```toml
contract = "1"

[android]     # optional; see §6
[ios]         # optional; see §7
```

A sidecar declaring no platform table is valid and contributes nothing.

## 6. Android

### 6.1 Namespace ownership

```toml
[android]
java_namespace = "org.example.mypkg"
```

`java_namespace` is **REQUIRED** when the distribution contributes Java or Kotlin
source (§6.3), manifest components (§6.6), or ProGuard rules (§6.7).

A consumer **MUST** enforce all of the following, and **MUST** fail rather than
resolve any conflict by file or copy order:

1. Every contributed source file's path **and** its declared `package` **MUST**
   fall under `java_namespace`.
2. Every manifest component name (§6.6) **MUST** fall under `java_namespace`.
3. Every class-matching pattern in a ProGuard rule (§6.7) **MUST** resolve within
   `java_namespace`.
4. A `java_namespace` under a reserved prefix **MUST** be rejected. Reserved
   prefixes are `org.kivy.android`, `org.libsdl.app`, `org.jnius`,
   `org.renpy.android`, and any namespace the consumer's own generated bootstrap
   occupies.
5. Two distributions declaring overlapping namespaces **MUST** fail, naming both.

> Rationale: without rule 4, a distribution shipping
> `org/kivy/android/PythonActivity.java` replaces the application's own entry
> point — unauthenticated, reachable through any transitive dependency. Rule 3
> exists because a keep rule is a capability rather than data: a single
> `-keep class ** { *; }` disables shrinking for the entire application.

### 6.2 Build requirements

```toml
[android.requires]
compile_sdk = 34
min_sdk = 24
```

These are **floors**, not settings. A consumer **MUST** fail, naming the
distribution, when the application's configured value is lower. A consumer
**MUST NOT** raise the application's configuration to satisfy them.

### 6.3 Source

```toml
[android.src]
java = ["java"]
kotlin = []
```

Paths are relative to `native.toml` and **MUST NOT** escape its directory.
Contents **MUST** be source text. A consumer **MUST** compile them with the
application's own toolchain, and **MUST** exclude them from any Python payload it
assembles.

### 6.4 Gradle dependencies

```toml
[android.gradle]
dependencies = ["com.google.android.gms:play-services-ads:25.2.0"]
repositories = ["https://maven.pkg.github.com/example/repo"]
```

Coordinates **MUST** be fully versioned; dynamic versions are invalid. This is
the **RECOMMENDED** channel for anything larger than a few glue classes.

### 6.5 Permissions and features

```toml
[android.permissions]
uses = ["INTERNET", "ACCESS_NETWORK_STATE"]
features = [{ name = "android.hardware.bluetooth_le" }]
```

A producer **MUST NOT** set `required` on a feature. A consumer **MUST** treat
every producer-declared feature as `required = false`, and **MUST NOT** promote
one on a producer's declaration alone.

> Rationale: whether an application *requires* Bluetooth or merely uses it when
> present is a property of the application. A producer promoting a feature to
> required would silently remove the application from devices lacking that
> hardware.

### 6.6 Manifest components

```toml
[[android.components]]
kind = "service"        # service | activity | receiver | provider
name = "org.example.mypkg.PushService"
exported = false
```

`name` **MUST** refer to a class the distribution contributes (§6.3) or that its
declared Gradle dependencies supply.

A producer **MUST NOT** set `exported = true`. A consumer **MUST** reject a
component declaring it, naming the distribution.

> Rationale: an exported component is an IPC entry point reachable by any other
> application on the device. Opening one is the application's decision.

### 6.7 ProGuard rules

```toml
[android.proguard]
keep = ["-keep class org.example.mypkg.** { *; }"]
```

Subject to §6.1 rule 3. A consumer **MUST** apply these only when the application
has enabled shrinking.

### 6.8 Required application-supplied values

```toml
[[android.manifest.meta_data_required]]
name = "com.google.android.gms.ads.APPLICATION_ID"
reason = "Your AdMob application ID, from the AdMob console"
```

Values a producer needs but cannot supply. A consumer **MUST** report these as
prerequisites and **MUST** fail when the application has not provided one,
naming the distribution and the `reason`. A consumer **MUST NOT** invent a value.

## 7. iOS

### 7.1 Symbol prefix

```toml
[ios]
swift_symbol_prefix = "MyPkg"
```

**REQUIRED** when the distribution contributes Swift source (§7.3).

> Swift source compiled into the application target shares one module namespace,
> so this guarantee is weaker than §6.1: a consumer **SHOULD** attribute a
> redeclaration error to the contributing distribution, but is not expected to
> prevent it.

### 7.2 Build requirements

```toml
[ios.requires]
deployment_target = "15.0"
```

A floor, with the same semantics as §6.2.

### 7.3 Swift packages and source

```toml
[ios.native.swift_packages]
Shim = { url = "https://github.com/example/shim", requirement = { from = "1.2.0" }, products = ["Shim"] }

[ios.src]
swift = ["swift"]
```

Swift Package Manager is the **RECOMMENDED** channel. `[ios.src].swift` is for
small `@objc` shims whose value is versioning atomically with the Python half;
it **SHOULD NOT** be used for a library.

### 7.4 Info.plist keys

```toml
[ios.info_plist]
NSBluetoothAlwaysUsageDescription = "Connects to your fitness tracker."
```

Merged into the generated `Info.plist`. A consumer **MUST** fail on a key that
collides with one it manages itself, naming the distribution.

### 7.5 Required entitlements

```toml
[[ios.entitlements_required]]
key = "aps-environment"
reason = "Push notification delivery"
```

A consumer **MUST** report these as prerequisites and **MUST NOT** write them
into the application's entitlements.

> Rationale: entitlements are bound to the App ID and provisioning profile.
> `codesign` requires the application's entitlements to be a subset of the
> profile's, so writing one the developer has not enabled produces a signing
> failure with no trace back to the distribution that caused it. This is the one
> declaration a consumer cannot satisfy on its own.

## 8. Consumer requirements

A conforming consumer **MUST**:

1. Reject a `contract` major version it does not implement (§4.3).
2. Discover by iterating the group, ignoring the entry-point name (§3.3).
3. Fail when a distribution declares multiple entries (§3.4).
4. Enforce namespace ownership and fail on collision, never resolving by order
   (§6.1).
5. Never grant a permission, promote a feature to `required`, or accept
   `exported = true` on a producer's declaration alone (§6.5, §6.6).
6. Fail when a producer's `requires` exceeds the application's configuration
   (§6.2, §7.2).
7. Record each distribution's resolved contribution durably and in reviewable
   form; **report the delta** wherever that record changes, naming the
   distribution and how it entered the dependency tree; and fail the build when
   the effective set drifts from the record (§9).
8. Report `entitlements_required` and `meta_data_required` as prerequisites
   rather than supplying them (§6.8, §7.5).
9. Exclude sidecar directories from any Python payload it assembles.
10. Read declarations without importing the producing package (§3.2).
11. Name the contributing distribution in every diagnostic.

A conforming consumer **SHOULD** warn on unrecognized keys within a supported
major version (§4.4).

## 9. Recording and review

Requirement 8.7 is about **disclosure**, not integrity.

Integrity needs no new mechanism: a sidecar ships inside its wheel, and any
consumer that pins wheels by hash already pins the declaration transitively. What
a hash cannot convey is *what the declaration says* — a version bump reads
identically whether it fixed a typo or began requesting a location permission.

A consumer **MUST** therefore record the **resolved contribution** in a form a
human can diff: which distribution, and what it contributes. A report **MUST**
carry three things:

```
analytics-shim 2.1.0  (via some-ui-lib)
  + permission  ACCESS_FINE_LOCATION
  + feature     android.hardware.location.gps  (required=false)
```

the distribution, **how it entered the dependency tree**, and the delta. The
middle element matters most for the case that motivates the requirement — a
transitive dependency the application author has never heard of.

Distributions installed from a path or in editable mode have no wheel hash. For
those a consumer **MUST** record a content hash over the sidecar and every file
it references.

This specification does not mandate a storage format. A lockfile entry, a
checksum file beside the generated project, or any other durable artifact
satisfies it. The normative property is that a change in what distributions
contribute **MUST NOT** pass silently.

> Disclosure is not enforcement. If nobody reads the diff, it ships. This is a
> deliberate trade: a blocking prompt inside a build loop earns click-through
> quickly and then provides nothing, whereas a recorded delta stays attributable
> before the fact in review and after the fact in history.

## 10. Versioning

The entry-point group carries the major version (`native-integration.v1`). A
consumer implementing version *N* **MUST** ignore groups for other major
versions entirely, rather than attempting to read them.

Additive changes — new optional keys, new platform tables — do not change the
major version. Any change that would alter the meaning of an existing key, or
make a previously valid sidecar invalid, requires a new major version and a new
group name.

## 11. Out of scope

| Not covered | Reason |
| --- | --- |
| Prebuilt `.aar` | Carries an `AndroidManifest.xml` that merges into the application's, defeating §6.5 and §6.6 |
| Prebuilt iOS binaries | Forces a platform tag onto an otherwise pure-Python wheel; unauditable |
| Native `.so`, extension modules | Solved by `android_<api>_<abi>`-tagged wheels ([PEP 738](https://peps.python.org/pep-0738/)) |
| iOS frameworks in wheels | Solved by `ios_*`-tagged wheels ([PEP 730](https://peps.python.org/pep-0730/)) |
| Application configuration | The application's own build settings are the consumer's concern |

## Appendix A: why contributions stay per-distribution

The tempting implementation is to let every distribution write its material into
one shared location under `site-packages` and let the installer merge them. It is
less code, and it forecloses most of this specification.

A merged tree **destroys provenance at install time**. Once files are overlaid,
nothing can determine which distribution contributed which file — so collision
detection, per-distribution attribution, the review record of §9, and every
diagnostic required by 8.11 all become impossible.

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
