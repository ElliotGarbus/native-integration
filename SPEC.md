# The native-integration specification

**Version:** `1` (draft)
**Entry-point group:** `native_integration.v1`

A convention by which a Python distribution declares the native material an
Android or iOS application build must provide on its behalf, and by which a build
tool discovers, validates, and stages that material.

> **Status: draft.** No build tool implements this yet; a reference reader in
> this repository does, and tracks the text. Breaking changes are expected until
> this line is removed, and this revision makes some — the draft is amended in
> place rather than by contract minor.
>
> This revision incorporates the corrections found by expressing **ten packages**
> against the text as ten **integration cases** — four existing Python packages,
> and six clean-sheet sidecars
> for Firebase, Sentry, Stripe and Mapbox, whose vendors have never heard of this
> convention. See [`examples/`](examples/) for a worked integration with both
> halves, [`development/examples/`](development/examples/) for the nine that
> shaped the text, and [`development/PROPOSALS.md`](development/PROPOSALS.md)
> for the decisions they produced, including the ones deliberately not adopted.

---

## Contents

Writing a sidecar? [§5.1](#51-a-complete-sidecar) shows one whole, and
[Appendix D](#appendix-d-declaration-reference) lists every key it may contain.
Building a tool that reads them? [§8](#8-consuming-tool-requirements) is the
checklist, and §§3–7 are what it refers to.

> Indented blocks like this one are **rationale**: why a rule is the way it is,
> and what went wrong in the cases that produced it. They state no requirement,
> and a reader who skips every one of them has missed nothing binding.

<!-- toc -->

- [1. Terminology](#1-terminology)
- [2. Overview](#2-overview)
  - [2.1 Design principles](#21-design-principles)
  - [2.2 How the application answers, at build time](#22-how-the-application-answers-at-build-time)
    - [What a consumer must be able to ask](#what-a-consumer-must-be-able-to-ask)
    - [The join key is not the consumer's to choose](#the-join-key-is-not-the-consumers-to-choose)
    - [Three answers, end to end](#three-answers-end-to-end)
  - [2.3 The host the consumer generates](#23-the-host-the-consumer-generates)
- [3. Discovery](#3-discovery)
  - [3.1 The entry point](#31-the-entry-point)
  - [3.2 Resolution](#32-resolution)
  - [3.3 Iteration, not lookup](#33-iteration-not-lookup)
  - [3.4 Multiple entries](#34-multiple-entries)
  - [3.5 The distribution is the carrier](#35-the-distribution-is-the-carrier)
- [4. The sidecar file](#4-the-sidecar-file)
  - [4.1 Location and name](#41-location-and-name)
  - [4.2 One file, all platforms](#42-one-file-all-platforms)
  - [4.3 Contract version](#43-contract-version)
  - [4.4 Unknown keys fail closed](#44-unknown-keys-fail-closed)
  - [4.5 Platform support](#45-platform-support-platforms)
- [5. Structure](#5-structure)
  - [5.1 A complete sidecar](#51-a-complete-sidecar)
  - [5.2 Every table at a glance](#52-every-table-at-a-glance)
- [6. Android](#6-android)
  - [6.1 Ownership](#61-ownership-androidowns)
  - [6.2 Build requirements](#62-build-requirements-androidrequires)
  - [6.3 Application-supplied values](#63-application-supplied-values-androidrequiresapplicationvalues)
  - [6.4 Source](#64-source-androidcontributessrc)
  - [6.5 Gradle dependencies](#65-gradle-dependencies-androidcontributesgradledependencies)
  - [6.6 Maven repositories](#66-maven-repositories-androidcontributesgradlerepositories)
  - [6.7 Permissions and features](#67-permissions-and-features-androidcontributespermissions-androidcontributesfeatures)
  - [6.8 Manifest components](#68-manifest-components-androidcontributescomponents)
  - [6.9 Shrinker keep patterns](#69-shrinker-keep-patterns-androidcontributesr8)
- [7. iOS](#7-ios)
  - [7.1 Symbol prefixes](#71-symbol-prefixes-ios)
  - [7.2 Build requirements](#72-build-requirements-iosrequires)
  - [7.3 Application prerequisites](#73-application-prerequisites-iosrequires)
    - [Common rules](#common-rules)
    - [What counts as satisfied](#what-counts-as-satisfied)
    - [Conditional prerequisites](#conditional-prerequisites)
    - [The six tables](#the-six-tables)
  - [7.4 Swift packages](#74-swift-packages-ioscontributesswiftpackages)
  - [7.5 Source](#75-source-ioscontributessrc)
  - [7.6 Info.plist](#76-infoplist-ioscontributesinfoplist)
  - [7.7 Python modules](#77-python-modules-ioscontributespythonmodules)
- [8. Consuming tool requirements](#8-consuming-tool-requirements)
- [9. Recording and review](#9-recording-and-review)
  - [The lifecycle](#the-lifecycle)
  - [The report](#the-report)
  - [Hashing the integration inputs](#hashing-the-integration-inputs)
  - [What resolved artifacts bring with them](#what-resolved-artifacts-bring-with-them)
  - [Secrets are never recorded](#secrets-are-never-recorded)
  - [What a record is, and what it must contain](#what-a-record-is-and-what-it-must-contain)
- [10. Versioning](#10-versioning)
- [11. Out of scope](#11-out-of-scope)
- [12. Guidance for package authors](#12-guidance-for-package-authors)
  - [12.1 Framework bindings, where the guidance does not apply](#121-framework-bindings-where-the-guidance-does-not-apply)
- [Appendix A: why contributions stay per-distribution](#appendix-a-why-contributions-stay-per-distribution)
- [Appendix B: why not a build backend](#appendix-b-why-not-a-build-backend)
- [Appendix C: prior art](#appendix-c-prior-art)
- [Appendix D: declaration reference](#appendix-d-declaration-reference)
- [Appendix E: a record that satisfies §9](#appendix-e-a-record-that-satisfies-9)

<!-- /toc -->

---

## 1. Terminology

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are
to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

- **Distribution** — an installed Python distribution, as seen by
  `importlib.metadata`.
- **Producer** — a distribution that declares a native integration. Where
  something is addressed to the person who writes and publishes one, this
  specification says **package author**.
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


### 2.1 Design principles

**Declarations are data, not executable build logic.** A producer describes
artifacts, requirements, and application contributions. A sidecar **MUST NOT**
provide commands, scripts, plugins, hooks, or arbitrary build-system arguments
for a consumer to execute, and a consumer **MUST NOT** execute any content of a
sidecar. This is the property that keeps declarations inspectable without
trusting producer code, and it is deliberate that this specification resembles
`pkg-config` — *describe what consuming me requires* — rather than a build
script.

**All native integration material a producer declares falls into one of three
categories:**

| Category | Meaning | Examples |
| --- | --- | --- |
| **`owns`** | An exclusive claim, enforced across all distributions | a Java namespace |
| **`requires`** | A condition the application or build environment must satisfy; the consumer verifies and reports it, and never invents a value to meet it | an SDK floor, an entitlement, a purpose string, an application-supplied value, a config file, a repository credential |
| **`contributes`** | Material the consumer stages into the generated project on the producer's behalf | source files, dependency coordinates, permissions, manifest components |

The categories carry the security model: ownership claims are exclusive and
collision-checked; requirements are reported and verified, never auto-satisfied;
contributions are staged, attributed, and disclosed per §9.

**Never originate what belongs to the application.** Where the application owns
the artifact — an entitlement, its `Info.plist`, its bundle, an extra build
target, a URL registration — a producer **MUST** declare a requirement and stop,
not attempt a contribution (§7.3). The same rule binds the consumer at build
time: it may *place* a value it was given — an application-supplied value into
the manifest (§6.3), a credential into repository configuration (§6.6) — but it
must never invent one. A producer that needs a Mapbox download token (§6.6), for
instance, declares the requirement and stops; the token comes from the
application, and the consumer's only job is to write that supplied value into
the generated repository configuration, never to source or default it.

**Unrecognized declarations fail closed.** A consumer **MUST NOT** silently
skip a contribution it does not understand (§4.4) — doing so ships an
application that is broken at runtime, far from the cause.

**Contributions stay per-distribution.** A consumer **MUST** name the
contributing distribution in **every** diagnostic it emits about declared
material — not only the ones this specification spells out individually
(Appendix A explains why). Skip that, and a transitive contribution stops being
reviewable: the diagnostic points the reader at the wrong repository.

**Native dependency resolution MUST resolve identically from the same
integration record**, every time, for every dependency a producer contributes
(§6.5, §7.4).

### 2.2 How the application answers, at build time

The **application** answers every `requires` in this specification, through
the **consumer's own configuration**. This specification mandates the
capability a consumer must offer, never its spelling: two conforming
consumers can ask for the same value in different words, and that is expected.

#### What a consumer must be able to ask

A consumer **MUST** provide a means for the application to:

| Answer | For |
| --- | --- |
| supply a declared application value, keyed by its `id` | §6.3 |
| satisfy each prerequisite kind | §7.3 |
| approve an exported component | §6.8 |
| suppress a contributed permission | §6.7 |
| supply credentials for an authenticated repository | §6.6 |

**Credentials MUST be supplyable by indirection.** For a build-time credential
(§6.6), a consumer **MUST** support supplying it as a *reference* — an
environment variable, an external secret store, a file outside the project — and
**MUST NOT** require the value to be written into a file the consumer directs the
application to commit.

> Rationale. §9 already forbids a consumer from writing a credential into the
> integration record, which protects the machine-written path. This protects the
> human-written one, and that is the likelier leak: directing an application
> author to paste a token into `pyproject.toml` and then carefully keeping it out
> of the lock beside it would be theatre. Vendors already assume indirection —
> Mapbox's own instructions put its download token in `~/.gradle/gradle.properties`,
> outside the project, for exactly this reason.
>
> Note the asymmetry with ordinary application values, which is deliberate: a
> value like an analytics DSN or an ad-network application ID is **embedded in
> the shipped application** and readable by anyone who unzips it. Committing
> those is not a leak, and treating them as secrets buys nothing. A build-time
> credential never reaches the device, and is the only thing here that must not
> come to rest in the repository.

#### The join key is not the consumer's to choose

A consumer's spelling is its own, but the *key*
an application answers under is not: it comes from the declaration, so that an
answer can be matched to the requirement that asked for it. For example, a
producer that declares `id = "sentry_dsn"` (§6.3) fixes that string as the join
key. A consumer can nest the answer under any config path it likes — say,
`[tool.examplebuild.native.pysentry.android.application_values]` — but to
satisfy the requirement the application must answer with that same key inside
it: `sentry_dsn = "https://…"`. The path around it is the consumer's spelling;
`sentry_dsn` is the producer's, and the application supplies it verbatim.

**A producer-local identifier is scoped by its distribution.** Where the join key
is an `id` the producer invents rather than a name the platform defines, the
identity is the pair **(declaring distribution, `id`)**, and a consumer **MUST**
key the answer on both. Two distributions may each declare `id = "client_id"`
without collision, and an application answering only `client_id` would not say
which it meant.

| The producer declares | Joined by | The application answers with |
| --- | --- | --- |
| `[[android.requires.application_values]]` | distribution + `id` | the value |
| a contributed permission (§6.7) | permission `name` | a suppression |
| a component with `exported_required` (§6.8) | component `name` | approval |
| a repository with `credentials_required` (§6.6) | repository `url` | credentials, by indirection |
| `[[ios.requires.entitlements]]` | `key` | the entitlement, configured |
| `[[ios.requires.usage_descriptions]]` | `key` | a non-empty string |
| `[[ios.requires.application_files]]` | `name` | the file, in the bundle |
| `[[ios.requires.app_extensions]]` | distribution + `id` | acknowledgement, plus an extension target of that `kind` |
| `[[ios.requires.url_schemes]]` | distribution + `id` | acknowledgement |
| `[[ios.requires.plist_capabilities]]` | `key` + `value` | the capability, in its own `Info.plist` |

The platform supplies a natural key for some of these — an entitlement key, a
plist key, a file name — and for the rest the producer supplies an `id`. Both
are joined under the declaring distribution; only the source of the local part
differs.

#### Three answers, end to end

**Illustrative only** — no consumer is required to use these spellings. Each
pair shows the sidecar the producer ships, then the application's own
`pyproject.toml`, which no sidecar ever contains.

An application value (§6.3) — joined by `id`:

```toml
# producer's native.toml
[[android.requires.application_values]]
id = "sentry_dsn"
reason = "Your Sentry project DSN, from Settings → Projects → Client Keys"
manifest_meta_data = "io.sentry.dsn"
```

```toml
# the application's pyproject.toml — answered under (distribution, `id`)
[tool.examplebuild.native.pysentry.android.application_values]
sentry_dsn = "https://examplePublicKey@o0.ingest.sentry.io/0"
```

The consumer then emits `<meta-data android:name="io.sentry.dsn" …/>` into the
generated manifest: the application never spells the vendor's key.

A repository credential (§6.6) — joined by `url`. The reference is committed;
the value never is:

```toml
# producer's native.toml
[[android.contributes.gradle_repositories]]
url = "https://api.mapbox.com/downloads/v2/releases/maven"
reason = "Needs a Mapbox token scoped DOWNLOADS:READ, as password with username \"mapbox\""
groups = ["com.mapbox"]
credentials_required = true
```

```toml
# the application's pyproject.toml
[tool.examplebuild.android.repository_credentials."https://api.mapbox.com/downloads/v2/releases/maven"]
username = "mapbox"
password = { env = "MAPBOX_DOWNLOADS_TOKEN" }
```

```bash
export MAPBOX_DOWNLOADS_TOKEN=sk.ey...        # developer shell, or a CI secret store
```

A usage description (§7.3) — joined by `key`, and the producer never writes the
sentence:

```toml
# producer's native.toml
[[ios.requires.usage_descriptions]]
key = "NSLocationWhenInUseUsageDescription"
reason = "requestWhenInUseAuthorization() traps if this key is absent"
```

```toml
# the application's pyproject.toml — the app supplies the user-facing text
[tool.examplebuild.ios.usage_descriptions]
NSLocationWhenInUseUsageDescription = "Shows trails near you."
```

A consumer **MAY** accept a literal in place of a reference — a developer
experimenting should not be blocked — but **MUST NOT** make the literal the only
option.

**A note for tool authors.** `[tool.*]` is the namespace `pyproject.toml`
reserves for exactly this — arbitrary, tool-specific configuration (PEP 518).
Anchoring under your own `tool.<name>` prefix, as every example above does, is
the natural choice; everything beneath it — nesting, naming, whether you key
by distribution first or by `id` first — is yours to design. What is fixed is
only the leaf: the literal join key from the declaration, scoped by the
declaring distribution wherever the table above requires it.

### 2.3 The host the consumer generates

*For the two properties of the generated native entry point — an Android
activity, an iOS app delegate — that material declared under this convention
depends on, and that no producer can check. §2.2 covers what the application
answers; this covers what the consumer provides before any sidecar is read.*

Both obligations are **scoped to a consumer that generates the host**. A
consumer whose application author writes their own activity or app delegate has
nothing here to make conform, and neither clause applies to it.

**Android.** A consumer that generates the application's Android activity
**MUST** make it an `androidx.activity.ComponentActivity`, or a subclass of one.

> Rationale. Current Android SDKs return their results through the
> activity-result contract — `registerForActivityResult` — which is declared on
> `ComponentActivity` and not on the platform's own `Activity`; the older
> `onActivityResult` path it replaced is deprecated. An SDK reached through §6.5
> that opens a screen of its own, such as a payment sheet or an identity check,
> then has nowhere to hand its result back to. What the application sees is a
> compile error inside generated glue, or a cast failure at first use, with
> nothing tying either to the distribution that declared the dependency.
>
> This names a class, which dates the obligation, and that is accepted
> deliberately: the alternative spellings all describe the same type in more
> words. A minor revision revisits it when Android's mainstream moves.

**iOS.** A consumer that generates the application's app delegate **MUST NOT**
consume a URL callback delivered to `application(_:open:options:)` without
providing a documented means for application code to observe it.

> Rationale. §7.3's `url_schemes` asks the application for two things: register
> a scheme, and forward the resulting callback to the SDK's handler. In this
> ecosystem the application author writes Python and the app delegate belongs to
> the consumer, so a generated delegate that swallows the callback — dispatching
> it as something else, or dropping it — leaves a prerequisite nobody can
> satisfy. An application acknowledging that it forwarded the callback would
> then be wrong through no fault of its own, which turns §7.3's disclosure into
> the opposite of disclosure.

Neither clause gives a producer a way to run code at startup or to participate
in a lifecycle callback. §11's exclusion of runtime lifecycle composition is
untouched: what is required here is a property of a host the consumer already
writes, not a seam for producer code to enter.

## 3. Discovery

### 3.1 The entry point

A producer **MUST** declare exactly one entry point in the group
`native_integration.v1`:

```toml
[project.entry-points."native_integration.v1"]
native = "mypkg._native"
```

- The entry-point name **SHOULD** be `native`. It carries no meaning and
  consumers ignore it (§3.3).
- The value **MUST** be an importable module reference — a dotted path of valid
  Python identifiers, no `:attr` suffix — naming the directory that contains the
  sidecar (§4.1).

**Nothing is ever imported** (§3.2). The value is spelled as a module reference
so the metadata stays truthful to the entry-points specification, which defines a
value as pointing to an importable object; this convention reads the named
directory's *files* instead.

**There are two ways to misspell the group, and both are silent.** The
underscore is required —
[entry-point group names](https://packaging.python.org/en/latest/specifications/entry-points/)
cannot contain hyphens, so `native-integration.v1` is not this group despite
matching the project name. And the quotes are required TOML syntax: in an
unquoted header a dot nests, so `[project.entry-points.native_integration.v1]`
declares a group `native_integration` containing a table `v1`. Either mistake
yields a wheel that installs cleanly and a build that never finds the sidecar.

### 3.2 Resolution

A consumer **MUST** resolve declarations as follows:

1. Determine the candidate set: the **resolved dependency closure** (§1) **of
   the application** for the target platform. A consumer operating in an isolated
   environment containing exactly that closure **MAY** treat all installed
   distributions as candidates.
2. For each candidate, read entry points in the group `native_integration.v1`
   via `importlib.metadata`.
3. Interpret the value's dotted path as a directory within the distribution —
   e.g. `mypkg._native` → `mypkg/_native/` — and read `native.toml` inside it.

A consumer **MUST NOT** accept contributions from distributions outside the
closure, regardless of what else is installed alongside it.

> Rationale: `importlib.metadata` has no concept of "the application's
> dependencies" — it enumerates entry points across whatever is installed.
> Resolving the closure into a clean environment that contains nothing else is
> what makes step 1's shortcut sound: only there does "installed" coincide with
> "in the closure," so the consumer can skip writing its own filter. Outside
> such an environment the two sets diverge, and the consumer must compute the
> closure itself and filter against it rather than trust what it finds
> installed.

A consumer **MUST** access the sidecar and every resource it references through
the distribution's metadata/file-resource interface
(`importlib.metadata.Distribution.locate_file()`, `Distribution.files`, or
equivalent). A consumer **MUST NOT** assume a distribution is represented by a
conventional `site-packages` directory. When a distribution's resources cannot
be materialized or read, the consumer **MUST** fail, naming the distribution —
not silently skip it.

**Nothing is imported, ever.** A consumer **MUST NOT** import the producing
package or any module of it, at any point — including the module the entry point
names. Metadata reads and file reads only.

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

### 3.5 The distribution is the carrier

A declaration reaches a consumer **only** by riding on an installed Python
distribution in the application's dependency closure. There is no other channel:
no path, no registry, no configuration key by which a consumer can be pointed at
a sidecar belonging to something the closure does not contain.

A project whose material is entirely native — a Swift package, a Maven artifact
— therefore **MUST** publish a Python distribution to participate, however thin.
A distribution carrying nothing but a sidecar and the package data it references
is a legitimate and expected shape.

> This is a real obligation, not a formality. It asks projects that have no
> other reason to build a wheel to build one, and the reason it is worth the
> cost is §3.2: the dependency closure is what bounds the set of things allowed
> to configure the application. A declaration that could arrive from outside the
> closure would be a declaration nobody chose to depend on.

Note also that the closure is resolved for a target platform **and a Python
version**. A sidecar **MUST NOT** restate an interpreter requirement:
`Requires-Python` already carries it enforceably, and a closure correctly
resolved for one interpreter cannot contain a distribution built for another.

Platform support is **not** symmetric with this, which is why §4.5 exists. No
enforceable standard metadata carries "this distribution does not function on
Android" for a distribution whose own content is pure Python: wheel platform
tags require platform-specific content, and `Classifier: Operating System ::
Android` is only informational.

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

The sidecar directory **MUST** contain an `__init__.py` (typically empty).

> Rationale: without it, the directory is only a namespace package (PEP 420),
> and implicit namespace-package resolution is not guaranteed to behave
> identically across import systems — so the entry point's dotted-path
> reference would not be reliably portable. A regular package makes it one
> unambiguous thing.

**Referenced resources.** Every path a sidecar declares is interpreted relative
to `native.toml` and **MUST NOT** escape its directory, checked **after** path
normalization and symlink resolution. Symlinked resources are not permitted in
version 1; a consumer **MUST** reject one, naming the distribution. Contributed
source files **MUST** be UTF-8 encoded.

**The sidecar directory is build input, not application payload.** A consumer
**MUST** exclude it — `native.toml` and every resource under it — from any
Python payload it assembles for the device.

> Rationale: its contents have already been consumed at build time —
> contributed source is compiled by the application's own toolchain (§6.4,
> §7.5) — so a second copy inside the application is at best dead weight. At
> worst it is a regression: source that compilation had already turned into
> something less directly readable now ships a second time as plain,
> human-readable text, undoing whatever protection the build step gave a
> producer's proprietary glue code.

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

A consumer **MUST** also reject a sidecar that **under-declares**: one using a
key or table introduced in a revision later than the contract it names, even
when the consumer implements both. Without this the gate protects only older
consumers, and a producer that mis-declares its contract is caught by nobody
until an older consumer meets it — at which point the diagnostic blames the
consumer's age rather than the producer's declaration.

> The minor is capability negotiation: a producer adopting a 1.1 feature is
> rejected by a 1.0 consumer with an actionable message ("requires contract
> 1.1"), instead of the consumer ignoring the feature and building a silently
> broken application.

**[Appendix D](#appendix-d-declaration-reference) is the registry that makes the
under-declaration rule checkable.** Every key it lists is contract 1.0 unless it
carries a *Since* note, and a minor revision that adds a key **MUST** record the
minor there. Without a single normative source for "which revision introduced
this key", two conforming consumers would reach different verdicts on the same
sidecar — the rule above would be stated and unimplementable.

**A consumer MUST be able to state the contract it implements**, and **SHOULD**
report it where a person can see it — a version string, a doctor check. The
rejection messages above already name the contract a sidecar needs; this is the
other half, and it is what lets a package author decide whether adopting a minor
strands their users.

### 4.4 Unknown keys fail closed

Within a platform table the consumer is **building for**, an unrecognized key
**MUST** be rejected, naming the distribution and the key. A consumer **MUST
NOT** ignore a declaration it does not understand in order to proceed.

**Values fail closed on the same terms.** Several keys take a value from a
vocabulary the *platform* owns and this specification does not enumerate — a
Gradle configuration name, an Apple extension point identifier, an Android
`<data>` attribute. Where a key is defined that way, a consumer **MUST** reject
a value it does not implement, naming the distribution and the value, and
**MUST NOT** substitute a default it does understand. A consumer **SHOULD** say
which values it does implement, so a producer can tell an unsupported
declaration from a misspelled one.

> Rationale: an open vocabulary keeps a producer's pace tied to the platform's
> releases rather than to this document's, which is the point of not
> enumerating. It is safe only where the value names something the *application*
> or the platform provides. Where a value instead selects behaviour the
> **consumer performs**, the set stays enumerated here and the enumeration is
> doing security work — §6.5's configurations are the worked case.

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

### 4.5 Platform support: `platforms`

```toml
platforms = ["ios"]
```

Optional. Names the platforms on which the distribution **functions at all**. A
consumer building for a platform not listed **MUST** fail, naming the
distribution and how it entered the dependency closure (§9).

- Values **MUST** be platform names this specification defines (`android`,
  `ios`). An empty list is invalid.
- Declaring a platform table for a platform the key omits is a contradiction; a
  consumer **MUST** reject it, naming the distribution.
- **Omitting the key makes no claim**, and is the default.

**A missing platform table and a missing platform name are different claims.**
No `[ios]` table means *"I contribute no native material on iOS."* The package
may still work there; it just needs nothing. Omitting `android` from
`platforms = ["ios"]` means something stronger: *"I do not function on Android
at all."*

> Rationale: a platform-specific framework's Python wrapper installs fine on
> the wrong platform — its own content is pure Python, so nothing in the wheel
> objects. The build succeeds. The failure shows up later, at `import`, or not
> at all: a facade with an unimplemented branch that is just `pass` runs and
> does nothing, silently. §4.4 cannot catch this — there is no key to reject,
> only a distribution that does not work here.
>
> This key makes a claim about the **distribution**, not about native
> material. That reaches beyond this specification's usual scope, but no other
> mechanism carries the claim today (§3.5).

## 5. Structure

A sidecar whole, and then every table it may contain. §§6–7 take the same
material apart key by key.

### 5.1 A complete sidecar

Nothing here is special. This is an ordinary `native.toml` for a wrapper around
a hypothetical cross-platform analytics SDK — the shape the problem statement
opens with, where an application author would otherwise transcribe a screenful
of build configuration out of a README.

In the example below, two tables are worth reading closely. They require
information only the application has: `[[android.requires.application_values]]`
asks for the analytics key, and `[[ios.requires.usage_descriptions]]` asks for a
sentence only the application can honestly write. 

```toml
# examplytics/_native/native.toml
contract = "1"
platforms = ["android", "ios"]

# ---------------------------------------------------------------- Android ---

# Reserves this Java namespace; no other distribution may write into it.
[android.owns]
java_namespaces = ["org.example.analytics"]

# SDK floors the application must build against.
[android.requires]
min_sdk = 24
compile_sdk = 35

# The application supplies this value at build time, keyed by this
# distribution's id.
[[android.requires.application_values]]
id = "analytics_key"
reason = "Your project key, from the vendor console under Settings → Client Keys"
manifest_meta_data = "com.example.analytics.API_KEY"

# Java sources the consumer compiles into the application.
[android.contributes.src]
java = ["java"]

# The SDK itself, pulled in via Gradle.
[[android.contributes.gradle_dependencies]]
coordinate = "com.example.analytics:android-sdk:4.2.0"

# Needed to deliver events over the network.
[[android.contributes.permissions]]
name = "android.permission.INTERNET"
reason = "Event delivery"

# A service the SDK dispatches delivery events to.
[[android.contributes.components]]
kind = "service"
name = "org.example.analytics.DeliveryService"

  [[android.contributes.components.intent_filters]]
  action = "com.example.analytics.DELIVER"

# Keeps the SDK's classes through shrinking/obfuscation.
[android.contributes.r8]
keep_classes = ["org.example.analytics.**"]

# -------------------------------------------------------------------- iOS ---

# Namespaces the Swift symbols this sidecar generates (§7.5).
[ios]
swift_symbol_prefixes = ["ExampleAnalytics"]

# SDK floor the application must build against.
[ios.requires]
deployment_target = "15.0"

# A purpose string only the application can write, and only if attribution
# is enabled (§7.6).
[[ios.requires.usage_descriptions]]
key = "NSUserTrackingUsageDescription"
conditional = true
reason = """\
Required only if you enable attribution. The sentence is yours to write: it is \
shown to the user and read by App Store review."""

# The SDK itself, pulled in via Swift Package Manager.
[[ios.contributes.swift_packages]]
name = "ExampleAnalytics"
url = "https://github.com/example/analytics-swift"
requirement = { from = "4.2.0" }
products = ["ExampleAnalytics"]

# Registers the URL scheme the SDK needs to detect other apps.
[ios.contributes.info_plist.append]
LSApplicationQueriesSchemes = ["exampleanalytics"]
```

Read it as the three categories of §2.1. It **owns** a Java namespace, so no
other distribution may write into it. It **requires** two SDK floors, a value
only the application has, and — on iOS, and only if a feature is used — a
purpose string the application must provide. Everything else it **contributes**:
source, a Maven coordinate, a permission, a service the SDK dispatches to, a
shrinker rule, a Swift package, one `Info.plist` array entry.

[`examples/pystripe/`](examples/pystripe/) carries both halves of one
integration, sidecar and application reply side by side.

### 5.2 Every table at a glance

```toml
contract = "1"                   # §4.3 — required
platforms = ["android", "ios"]   # §4.5 — optional; where the distribution works

[android.owns]                              # §6.1  java_namespaces
[android.requires]                          # §6.2  compile_sdk, min_sdk,
                                            #       core_library_desugaring
  [[android.requires.application_values]]   # §6.3
[android.contributes]
  [android.contributes.src]                 # §6.4  java, kotlin
  [[android.contributes.gradle_dependencies]]   # §6.5
  [[android.contributes.gradle_repositories]]   # §6.6
  [[android.contributes.permissions]]           # §6.7
  [[android.contributes.features]]              # §6.7
  [[android.contributes.components]]            # §6.8  + view_links, intent_filters
  [android.contributes.r8]                      # §6.9  keep_classes
  [[android.contributes.r8.keep]]               # §6.9  + from_dependency

[ios]                                       # §7.1  swift_symbol_prefixes
[ios.requires]                              # §7.2  deployment_target
  [[ios.requires.entitlements]]             # §7.3 ─┐
  [[ios.requires.usage_descriptions]]       # §7.3  │ prerequisites the
  [[ios.requires.app_extensions]]           # §7.3  │ application supplies;
  [[ios.requires.application_files]]        # §7.3  │ never satisfied by
  [[ios.requires.url_schemes]]              # §7.3  │ the consumer
  [[ios.requires.plist_capabilities]]       # §7.3 ─┘
[ios.contributes]
  [[ios.contributes.swift_packages]]        # §7.4
  [ios.contributes.src]                     # §7.5  swift
  [ios.contributes.info_plist]              # §7.6  values, append,
                                            #       skadnetwork_identifiers
  [[ios.contributes.python_modules]]        # §7.7
```

A sidecar declaring no platform table is valid and contributes nothing — which
is a statement about contributions, not about where the distribution works
(§4.5). Within a platform table, each category is optional.

Every key above is listed with a one-line description in
[Appendix D](#appendix-d-declaration-reference).

## 6. Android

### 6.1 Ownership: `[android.owns]`

*For claiming a Java namespace as a distribution's own, so no other
distribution can collide with it or replace a toolchain's entry point through
a transitive dependency.*

```toml
[android.owns]
java_namespaces = ["org.example.mypkg"]
```

`java_namespaces` is **REQUIRED** when the distribution contributes Java or
Kotlin source (§6.4), producer-sourced manifest components (§6.8), or shrinker
keep patterns under its own namespace (§6.9).

A consumer **MUST** enforce every rule below, and **MUST** fail the build when
any is violated, naming the distribution or distributions responsible:

1. Every contributed source file's path **and** its declared `package` **MUST**
   fall under an owned namespace.
2. Every producer-sourced manifest component name (§6.8) **MUST** fall under an
   owned namespace. A component attributed to a declared dependency is exempt;
   the class is not the producer's.
3. Every `keep_classes` pattern **MUST** fall within an owned namespace.
   Dependency keeps are checked differently (§6.9).
4. An owned namespace under a reserved prefix **MUST** be rejected: the
   bootstrap namespaces of the known Python-mobile toolchains —
   `org.kivy.android`, `org.libsdl.app`, `org.jnius`, `org.renpy.android`
   (Kivy / python-for-android), `com.chaquo.python` (Chaquopy),
   `org.beeware.android` (Briefcase) — plus any namespace the consumer's own
   generated bootstrap occupies.
5. Two distributions claiming overlapping namespaces **MUST** fail, naming both.

**Containment is computed on dot-separated segments, never on raw strings**, in
rule 4 as in rule 5. A namespace *A* contains a namespace *B* when *B* equals
*A*, or when *B* begins with *A* followed by a `.`: `org.kivy.android` contains
`org.kivy.android.helpers` and does **not** contain `org.kivy.androidx`;
`PyGMA` does not contain `PyGMAKit`.

An owned namespace **SHOULD** be reverse-DNS. A consumer **SHOULD** warn on a
single-label one (`PyGMA`): ownable and collision-checked like any other, but it
claims a top-level name for a single distribution, which makes accidental
overlap with a sibling project far likelier.

> Rationale. Rule 4 is what stops a distribution shipping
> `org/kivy/android/PythonActivity.java` from silently replacing the
> application's entry point, and its shared list is consumer-independent so that
> one toolchain's runtime cannot be clobbered because a different toolchain
> built the application. Rule 5's exclusivity parallels Cargo's `links` key,
> which permits only one crate to claim a native library.
>
> A raw string-prefix test would wrongly count `PyGMAKit` as falling inside
> `PyGMA` — a false collision here, a false accept in §6.9's `keep_classes`
> check. Segmenting on `.` is what rules that out.

### 6.2 Build requirements: `[android.requires]`

*For specifying the minimum SDK levels a build must meet — `compile_sdk`,
`min_sdk`, `target_sdk` — checked as floors.*

```toml
[android.requires]
compile_sdk = 34
min_sdk = 24
```

These are **floors**, not settings. A consumer **MUST** fail, naming the
distribution, when the application's configured value is lower. A consumer
**MUST NOT** raise the application's configuration to satisfy them.

**`core_library_desugaring`** is a boolean requirement on the same terms,
declared when the producer's code — or a dependency it declares — calls a Java
API the platform provides only above the application's `min_sdk`:

```toml
[android.requires]
# Media3 uses java.time below API 26, which desugaring backfills.
core_library_desugaring = true
```

A consumer **MUST** fail, naming the distribution, when the application has not
enabled core library desugaring, and **MUST NOT** enable it on the producer's
behalf — it changes how the application's own code compiles, and it adds a
dependency to the build. Declaring `false` is the same as declaring nothing.

> Rationale: this is a floor whose axis happens to be boolean rather than
> numeric. It earns a key of its own because the failure is otherwise a
> `NoClassDefFoundError` on a device below the floor, long after the build, from
> a library the application never named — and because it cannot be expressed as
> an SDK floor: raising `min_sdk` to avoid desugaring drops devices, which is
> the application's decision and a far larger one than a build flag.

`target_sdk` is a floor on the same terms:

```toml
[android.requires]
# POST_NOTIFICATIONS is requested at runtime only when targetSdk >= 33.
target_sdk = 33
```

`target_sdk` is the most invasive of the three: raising it changes behaviour
app-wide, in code that has nothing to do with the producer. Declare it only
when a specific behaviour depends on it, and say which one in a comment — a
bare version number tells the reader nothing (§12).

> Why this needs to be a floor. Below SDK 33, `POST_NOTIFICATIONS` is granted
> at install time instead of requested at runtime, so a push package's runtime
> request for it silently does nothing. Declaring the floor forces
> `target_sdk` to be at least 33, turning that mismatch into a build failure
> instead of an application that ships with notifications silently broken.

### 6.3 Application-supplied values: `[[android.requires.application_values]]`

*For a value only the application has — an account identifier, a redirect
scheme — that the **build** must embed because no runtime call can reach it.
Sentry's DSN is read before any Python runs.*

```toml
[[android.requires.application_values]]
id = "sentry_dsn"
reason = "Your Sentry project DSN, from Settings → Projects → Client Keys"
manifest_meta_data = "io.sentry.dsn"
```

- **`id`** is a **logical identifier**, unique within the sidecar. It is how
  contributions refer to the value (below) and how the consumer's own
  configuration asks the application for it. It is not a platform key, and its
  identity is scoped by the declaring distribution (§2.2) — two distributions
  may each declare `client_id` without collision.
- **`reason`** is **REQUIRED**.
- The supplied value is a **non-empty string**. Version 1 defines no other type:
  a manifest attribute and an intent-filter field are both text, and admitting
  TOML integers or booleans would leave each consumer to invent its own
  serialisation.
- **`manifest_meta_data`** is **OPTIONAL** and names the `<meta-data>` key the
  SDK itself reads. Unlike `id`, this key is **not** scoped by distribution —
  it is a real, platform-global manifest key, so two distributions naming the
  same one are necessarily talking about the same manifest entry. When the
  supplied values are equal the consumer coalesces them, preserving both
  provenance records; when they differ it **MUST** fail, naming both. A key the
  **application** also sets is the application's — the consumer keeps its value
  and reports the override. When present, the consumer emits
  `<meta-data android:name="<that key>" android:value="<the supplied value>"/>`
  into the generated manifest, where "the supplied value" is what the
  application gave for this `id` — never anything the producer or consumer
  originates. When absent, the consumer emits no manifest entry for this
  value.

**`manifest_placeholder`** is **OPTIONAL** and names an AGP manifest
placeholder the consumer supplies the value as. It exists for a value a
**declared dependency's own manifest** reads, which `manifest_meta_data` cannot
reach: Auth0's and AppAuth's Android libraries ship the intent filter
pre-written with `${auth0Domain}` and `${auth0Scheme}` holes in it, and the
application fills them through `manifestPlaceholders` in its build file. Like
`manifest_meta_data`, the name is **not** scoped by distribution — it is a
build-global name that vendor code already reads — so the coalescing rule above
governs it identically: equal supplied values coalesce with both provenance
records kept, different values **MUST** fail naming both, and a placeholder the
application sets itself is the application's, kept and reported as an override.
An entry **MAY** declare both delivery fields; the same supplied value then
reaches the manifest twice, once as `<meta-data>` and once as a substitution.

> Rationale: §6.8 already cites this mechanism approvingly — AppAuth "ships the
> intent filter pre-written, with a placeholder for the one value the
> application supplies via `manifestPlaceholders`" — and version 1 gave a
> producer no way to use it. Without this field the application is back to
> transcribing a value into its own build file, which is the problem this
> specification exists to remove, and the dependency's filter cannot be reached
> any other way.

The  manifest key, when there is one, is fixed by whatever vendor code reads it —
it is not this specification's to name or scope. The `id` is this
specification's own handle for the application's answer, and stays usable
even for a value with no manifest key of its own, as above.

**A value belongs here only when the *build* must embed it** — a manifest entry,
intent-filter data, anything baked into generated XML that no runtime call can
reach. A value an SDK accepts at runtime is the application's to pass in its own
Python code, and a producer **SHOULD NOT** route one through build configuration
merely because it can.

The contrast that shows where the line falls is Google Mobile Ads. The *legacy*
SDK reads its application ID from a manifest `<meta-data>` entry and fails at
startup without it, so the build must embed it. The Next-Gen SDK takes the same
value programmatically, through `InitializationConfig.Builder(appId)` — a
wrapper for that SDK declares nothing here and passes the ID from Python
instead. The application ID is identical either way; only the legacy SDK's
build-time reading makes it this table's business — the Next-Gen SDK's
wrapper declares nothing here.

**Satisfying an `application_values` entry.** It is satisfied when the
application has supplied a non-empty value for its `id` through the consumer's
own configuration — never by hand-editing a manifest. The consumer then
delivers it: into `manifest_meta_data` if one is declared, and by substitution
wherever a contribution references the `id`. If the application has not
supplied a value, the consumer emits nothing and fails the build, naming the
distribution and the `reason`. A *requires* is checked, never auto-satisfied
(§2.1).

> **Why this table is Android-only, and why it stays that way.** No iOS case has
> needed a build-embedded value: the iOS SDKs examined either take their
> configuration through a runtime call or read a whole file (§7.3's
> `application_files`). Sentry needs its DSN on both platforms but reaches it on
> iOS through `SentrySDK.start`, which is a runtime call and not this table's
> business.
>
> When one does appear, the shape is a **parallel `[[ios.requires.application_values]]`
> table** with its own delivery field — not this table promoted to the top level
> with one delivery field per platform. That promotion looks tidier and cannot
> work, because **the value itself is frequently per-platform**. An AdMob
> application ID differs between Android and iOS, since the console registers a
> separate app for each. Firebase encodes the platform *inside* the identifier —
> `1:1234:android:…` against `1:1234:ios:…` — which is why `google-services.json`
> and `GoogleService-Info.plist` carry different values rather than one value in
> two formats.
>
> A single entry answered once cannot express that. Producers would be forced to
> invent `admob_app_id_android` and `admob_app_id_ios`, pushing the platform into
> the `id` — precisely what an identifier separated from its delivery key exists
> to avoid. With parallel tables, a value that genuinely is the same on both
> platforms is declared twice under one `id` and answered once per platform,
> which is mild duplication in the easy case and the only correct shape in the
> hard one.

**Inline references.** Some contributed fields need an application value
spliced directly into them — an OAuth redirect scheme inside an intent
filter's `scheme` (§6.8's `view_links`), for instance — not merely written to
a fixed manifest key. For that case, a contribution **MAY** reference an
application value **inline** instead: `{ application_value = "<id>" }`. The
consumer substitutes the supplied value wherever the reference appears. (This
mirrors AGP manifest placeholders, the mechanism established Android
libraries such as AppAuth already use for application-specific values like a
redirect scheme.)

**An inline reference MUST resolve to an `id` declared in this table.** A
consumer **MUST** reject a reference that does not, naming the distribution and
the unresolved `id`. Inline use does not implicitly declare anything: an
implicit declaration would have no `reason`, which is the one field a
prerequisite report cannot do without — leaving the application told that
something is missing and not what it is or where to get it.

Satisfaction above governs both forms: an inline reference is a prerequisite on
exactly the same terms as a declared value.

### 6.4 Source: `[android.contributes.src]`

*For the glue classes a binding needs on the device, compiled by the
application's own toolchain rather than shipped as a binary.*

```toml
[android.contributes.src]
java = ["java"]
kotlin = []
```

Path rules per §4.1. From each listed directory the consumer stages, recursively,
exactly the files with the matching extension — `.java` for `java` roots, `.kt`
for `kotlin` roots — and ignores other files. Contents **MUST** be source text;
a consumer **MUST** compile them with the application's own toolchain, and
**MUST** exclude the source files from any Python payload it assembles. A
consumer **MUST** compile `.java` sources with UTF-8 forced, never the platform
default. Subject to §6.1 rule 1.

> Rationale: `kotlinc` and the Swift compiler (§7.5) always read source as
> UTF-8; `javac` does not — it falls back to the platform default charset
> unless told otherwise. Without forcing it here, §4.1's UTF-8 requirement on
> the producer's side guarantees nothing: a validly UTF-8-encoded `.java` file
> can still be misread on a consumer whose environment defaults elsewhere,
> corrupting non-ASCII content or failing to compile, through no fault of the
> producer's.

### 6.5 Gradle dependencies: `[[android.contributes.gradle_dependencies]]`

*For a vendor SDK — declared as a Maven coordinate, resolved by
Gradle, locked and attributed in the integration record described by §9,
rather than transcribed into the application's build file by hand.*

```toml
[[android.contributes.gradle_dependencies]]
coordinate = "com.google.android.gms:play-services-ads:25.2.0"
configuration = "implementation"    # optional; default and only v1 value
```

A dependency **MUST** be spelled in exactly one of two forms. The exact form
above is **RECOMMENDED**. The second is a **bounded** range:

```toml
[[android.contributes.gradle_dependencies]]
module = "com.onesignal:OneSignal"
version = { at_least = "5.6.1", below = "6.0.0" }
```

- `coordinate` is `group:artifact:version` and **MUST** be exactly versioned.
- `module` is `group:artifact` and **MUST** be accompanied by `version`, in
  which **both** `at_least` (inclusive) and `below` (exclusive) are
  **REQUIRED**. A range open at either end is invalid.
- `coordinate` and `module` are mutually exclusive; a consumer **MUST** reject
  an entry declaring both or neither.
- **Changing versions (`-SNAPSHOT`) are invalid in either form**, as are
  unbounded dynamic versions (`+`, `latest.release`) and any range spelled
  inside `coordinate`. A version whose content can change under a fixed spelling
  defeats the record of §9, and no lock can repair it.
- `configuration` defaults to `implementation`. Version 1 additionally defines
  `api`, `compileOnly` and `runtimeOnly`. Per §4.4 a consumer **MUST** reject a
  value it does not implement, naming the distribution — the set above is what
  a producer may *declare*, not what every consumer must support.

**This set is closed, and deliberately not the platform's own.** Gradle's
configuration names are otherwise exactly the kind of open vocabulary §4.4
describes, and this one stays enumerated because some of its members select
behaviour the **consumer performs**: adding a coordinate to
`annotationProcessor`, `kapt` or `ksp` makes the build *run code from that
artifact*. A producer **MUST NOT** declare a processor configuration, and a
consumer **MUST** reject one, naming the distribution — this is §2.1's
exclusion of build-time execution, reached through a field rather than through a
script. The four names above add a dependency to the build and execute nothing.

> Rationale: `api` differs from `implementation` only in exposing the dependency
> on the application's own compile classpath, `compileOnly` keeps it out of the
> package, and `runtimeOnly` keeps it off the compile classpath. None is a
> capability. A processor is, and it arrives under a field that looks like a
> spelling choice.

**A declared version is a requirement, not a pin.** Gradle treats the version in
a dependency declaration as the version that module *requires*, and its conflict
resolution may select a **higher** one when something else in the graph requires
it. This specification keeps that behaviour: a consumer **MUST NOT** silently
convert a declaration into a `strictly` constraint, because doing so would make
two producers that name different versions of one library unresolvable, and
composing independently-authored packages is the point.

The consequence is that **`coordinate = "g:a:1.2.3"` does not promise 1.2.3 will
be used.** Where the selected version differs from the declared one, the record
and report of §9 **MUST** show both:

```
  + dependency  com.example:widget   requested 1.2.3 → resolved 1.4.0
```

**Resolution is locked, not merely versioned.** An exact coordinate does not by
itself make resolution reproducible: transitive versions can float, and — per the
paragraph above — so can direct ones. A consumer **MUST** record the fully
resolved dependency graph — every artifact and version, including transitives —
in the integration record (§9), and **MUST** resolve from that record on
subsequent builds until a new resolution is accepted. A consumer **MUST**
record a checksum per resolved artifact, and on subsequent builds **MUST**
verify each resolved artifact against the recorded checksum and fail on a
mismatch, naming the artifact and the distribution that declared it.

> **"Reproducible" here means artifact identity, not graph identity.** §2.1 says
> every contributed dependency must resolve identically from the same record. A
> locked graph alone delivers only the weaker promise — the same modules at the
> same versions — and a version is a coordinate, not a content hash: a
> repository can serve different bytes under one version, and a moved tag
> resolves elsewhere. The checksum is what makes §2.1's sentence literally true,
> and it is cheap, because the consumer has already downloaded every artifact it
> is hashing.

**Choosing between the two forms.** Both are equally reproducible, because the
lock is what delivers that and it applies to both — §7.4 permits an
up-to-next-major range on the same reasoning. The exact form is **RECOMMENDED**
for something the lock does not cover: it tells a reviewer the floor this
producer requires, straight from the sidecar, without consulting the record —
even though, per the rule above, the resolved version may end up higher. A
range trades that legibility for not having to cut a release on every upstream
patch, which several SDK vendors' documented coordinates make a real cost.
Make that trade knowingly.

**Cross-artifact alignment is not expressible**, and producers of SDK families
should know it. Every rule here governs **one dependency at a time**. A vendor
BOM — Gradle's `platform(...)`, as Firebase publishes — is a constraint over a
*set*, asserting that a group of versions was tested together, and neither form
above can state that. A family split across several distributions (§12) pins its
artifacts independently, and nothing makes those choices agree.

The failure is at least honest: Gradle resolves one version per artifact, the
result is locked, and requirement 8.16 requires a resolution conflict to name the
distributions that declared the conflicting versions. Producers publishing such
a family **SHOULD** pin compatible versions deliberately and release together.

This is the **RECOMMENDED** channel for anything larger than a few glue
classes. Note that a coordinate may resolve to an Android library (`.aar`)
whose own manifest AGP merges into the application's; see §9 and §11.

### 6.6 Maven repositories: `[[android.contributes.gradle_repositories]]`

*For an SDK its vendor does not publish to Maven Central. This is the most
powerful thing a sidecar can contribute — an unconstrained repository can
reach the application through any transitive dependency, a dependency-confusion
vector — so the rules here are the strictest in this specification.*

```toml
[[android.contributes.gradle_repositories]]
url = "https://maven.pkg.github.com/example/repo"
reason = "Hosts org.example:shim, which is not on Maven Central"
groups = ["org.example"]
```

`reason` is **REQUIRED**. At least one of `groups` (Maven group IDs) or
`modules` (`group:artifact` pairs) is **REQUIRED**.

**The normative requirement is bounded participation**: the contributed
repository **MUST NOT** participate in resolution for anything outside the
declared groups/modules. A consumer implements that with its build system's
native mechanism — Gradle's repository content filtering expresses exactly this.
That constraint is what reduces a contributed repository from "may shadow
anything" to "may serve exactly what it named."

**Overlapping scopes are rejected.** Two contributed repositories whose
`groups`/`modules` intersect **MUST** fail, naming both distributions and the
contested coordinates — unless they declare the same `url`, which is not a
conflict. Gradle searches repositories in declaration order and takes a module's
artifacts from the first repository that has its metadata, so an overlap makes
the source of an artifact depend on declaration order rather than on anything
either sidecar said.

```
native integration conflict: com.example may resolve from two repositories
  package-a  →  https://repo-a.example/maven
  package-b  →  https://repo-b.example/maven
```

The rule is deliberately blunt for version 1. It is simple to implement, the
diagnostic writes itself, and it can be relaxed if a real package demonstrates a
need that ordering rules would serve better.

**A note on implementation choice: do not reach for Gradle's `exclusiveContent`
instead of content filtering.** It is a **different and stronger** policy —
it additionally makes the declared modules resolvable *only* from that
repository, which can change first-time resolution results. Nothing here
requires it, and a consumer **MUST NOT** substitute it for content filtering,
because the same sidecar would then resolve differently depending on which
mechanism the consumer picked. Should a vendor genuinely require exclusivity,
that is a future explicit field for the producer to declare, not an
implementation detail for the consumer to decide on its own.

A consumer **MUST** additionally report repository contributions with distinct
prominence in the record and report of §9 — never folded into a generic list —
and **SHOULD** surface them in any standing diagnostic (e.g. a doctor check). A
consumer **MAY**, as its own policy, require explicit application approval
before adding a contributed repository to resolution.

**Authenticated repositories: `credentials_required`.** Many private
repositories need credentials, and the commonest reason a vendor hosts its own
is precisely that access is gated:

```toml
[[android.contributes.gradle_repositories]]
url = "https://api.mapbox.com/downloads/v2/releases/maven"
reason = """\
Mapbox does not publish to Maven Central. Access needs a Mapbox token scoped \
DOWNLOADS:READ, used as the password with username "mapbox"."""
groups = ["com.mapbox"]
credentials_required = true
```

- **A producer MUST NOT put a credential in a sidecar, in any field, under any
  spelling.** A sidecar is package data inside a wheel: it is readable by
  everyone who installs the distribution and by anyone browsing the archive.
- A consumer **MUST** reject a credential in the places where one is
  *syntactically identifiable* — at minimum, URL user-info
  (`https://user:pass@host/…`) in `url` — and **SHOULD** warn on obvious
  embedded-secret forms elsewhere.

- `credentials_required = true` declares only that the repository is
  authenticated. The application supplies the credentials through the
  consumer's own configuration (§2.2), which **MUST** accept them by
  indirection so the value need never be committed; `reason` **MUST** say what
  credential is needed and where to obtain it.
- A consumer **MUST** report an authenticated repository as a prerequisite and
  **MUST** fail when no credentials are configured for it, naming the
  distribution — rather than attempting resolution and surfacing a bare `401`.
- A consumer **MUST NOT** write supplied credentials into the generated
  project in any persisted form, into the integration record (§9), or into any
  diagnostic.

### 6.7 Permissions and features: `[[android.contributes.permissions]]`, `[[android.contributes.features]]`

*For the permissions and hardware features a producer's code needs at
runtime — visible to the application instead of arriving silently through a
dependency's AAR, and refusable, because the application is the one
accountable for what the installed app can do.*

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
- **`max_sdk_version`** is **OPTIONAL**, an integer, and becomes
  `android:maxSdkVersion`. It says the permission is needed only up to that API
  level — `WRITE_EXTERNAL_STORAGE` through 28, the legacy Bluetooth permissions
  through 30 — so a device above it is never asked.
- **`never_for_location`** is **OPTIONAL**, a boolean, and becomes
  `android:usesPermissionFlags="neverForLocation"`. It asserts that the
  producer's scanning will not be used to derive the device's location, which is
  the difference between asking for Bluetooth and asking for the user's
  whereabouts. A consumer passes it through without interpreting which
  permissions it is meaningful on, for the same reason `name` takes no prefix
  expansion.

**Attributes are merged least-restrictively, and the merge is reported.** Two
distributions may declare one permission with different attributes. A consumer
**MUST** register the permission with the **widest** need any of them stated:
an entry with no `max_sdk_version` defeats one that has it, a lower
`max_sdk_version` gives way to a higher, and `never_for_location` holds only
when **every** declaration of that permission asserts it. The result **MUST**
appear in the record and report of §9 with the distributions that produced it.

> Rationale: a permission is a single fact about the built application — it is
> requested or it is not — so the merged form has to satisfy every producer that
> asked. The `never_for_location` direction is the one worth stating explicitly:
> if any producer might derive location from a scan, the application cannot
> truthfully assert that none will, and the flag is a claim made to the platform
> and to Play policy rather than a preference.
>
> Both attributes exist for **minimization**, which is what §6.7 is for. Without
> them a producer over-asks on every modern device, and the application carries
> a permission prompt neither party wanted.
- Declared permissions **are staged into the generated manifest**, not held
  back for a standalone prompt. What actually gates them is §9's acceptance
  step: a new or changed permission must appear in the report and be
  explicitly accepted (i.e. running a re-lock) before the build proceeds.
  This is deliberately the same capability an Android AAR dependency already
  has via manifest merging, with the disclosure an AAR does not provide.
- A producer **MUST NOT** set `required` on a feature. A consumer **MUST** treat
  every producer-declared feature as `required = false`, and **MUST NOT**
  promote one on a producer's declaration alone.

> Rationale: whether an application *requires* Bluetooth or merely uses it when
> present is a property of the application. A producer promoting a feature to
> required would silently remove the application from devices lacking that
> hardware.

**Application-side suppression.** A consumer **MUST** provide a means for the
application to suppress any contributed permission. A suppressed permission
**MUST** be absent from the **effective merged manifest**, together with any
feature it alone implied, and the suppression **MUST** appear in the record and
report of §9 (e.g. `− android.permission.ACCESS_FINE_LOCATION (suppressed by
application)`). Suppression is global per permission — the merged manifest
either carries the permission or it does not — and this specification does not
define the application-side syntax, only the capability; the application's
configuration format is the consumer's concern.

**Omitting a suppressed permission from the generated manifest is not
sufficient.** A resolved `.aar` carries its own `AndroidManifest.xml`, 
which AGP merges into the application's,
so a permission the consumer never wrote can still arrive from a dependency —
and the permission a producer declares here is very often the same one its AAR
declares. Where that happens the consumer **MUST** emit an explicit
manifest-merger removal (`tools:node="remove"`) so the permission is absent from
the merged result, and **MUST** report it as suppressed rather than silently
losing the suppression.

> Without this the authority model is aspirational rather than real: the
> application's refusal would be honoured in the one file the consumer writes
> and quietly overridden by the merger. `tools:node="remove"` is the mechanism
> the platform provides for exactly this case, which is why §6.7's rationale
> below cites it.

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

*For registering the manifest components a producer needs — services,
receivers, activities — whether the producer's own class or one from a declared
dependency; unexported by default, and exported only when the application
explicitly approves the producer's request to open it.*

```toml
[[android.contributes.components]]
kind = "service"        # service | activity | receiver
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
```

**`provider` is deliberately absent from the vocabulary.** A `<provider>` is
invalid without `android:authorities`, and a provider authority must be unique
**across every application on the device** — two applications installed with the
same authority conflict, so the value is conventionally derived from the
application ID, which a producer does not know. A `kind` this specification
could not register validly is worse than one it does not offer, because a
consumer would have to invent the authority to make the manifest parse, and
inventing is exactly what §2.1 forbids.

The two provider shapes seen in practice do not need this table anyway: a
provider belonging to a declared dependency is registered by that dependency's
own merged manifest, and a **shared** provider such as AndroidX Startup's
`InitializationProvider` is a contended singleton that must be merged rather
than registered a second time. A future minor **MAY** introduce providers with
a producer-declared authority *suffix* the consumer prefixes with the
application ID — the form §4.3's rationale already imagines as a 1.1
`content_providers` table — once a producer needs one.

**Provenance.** A component's class comes from one of two places, and the entry
states which:

- **Producer source** (no `from_dependency`): `name` **MUST** refer to a class
  the distribution contributes (§6.4) and **MUST** fall under an owned namespace
  (§6.1 rule 2).
- **A declared dependency** (`from_dependency = "group:artifact"`): the value
  **MUST** match the group and artifact of a dependency the same sidecar
  declares (§6.5), in either the `coordinate` or the `module` form. 
  The owned-namespace rule does not apply — the class is the
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

Where approval is absent the consumer **MUST fail**. It **MUST NOT** fall back
to registering the component unexported: the producer has said the component is
useless unless reachable, so a non-exported registration builds an application
that does not work. Withholding approval means the integration cannot proceed,
not that it proceeds broken.

> Rationale: an exported component is an IPC entry point reachable by any other
> application on the device. Some integrations legitimately need one — OAuth
> callbacks, deep links — but opening it is the application's decision. The
> producer states the need; the application grants it.

**A minimal example.** Before approval, a report (§9) surfaces the pending
prerequisite and the build fails rather than proceeding unexported:

```
oauth-sdk 2.0.0  (direct dependency)
  ! export required   org.example.mypkg.RedirectActivity
                       "Receives the OAuth redirect from the browser"   ✗ BLOCKING
```

The application answers by naming that exact component in its own
configuration — the join key is the component `name` (§2.2):

```toml
[tool.examplebuild.android.exported_components]
"org.example.mypkg.RedirectActivity" = true
```

The next build finds that answer, registers the component
`android:exported="true"`, and reports the change instead of failing:

```
oauth-sdk 2.0.0  (direct dependency)
  + activity   org.example.mypkg.RedirectActivity  (exported, approved)
```

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

**The fields are Android's own `<data>` attribute names**, in this
specification's snake-case spelling, and the set is **open** per §4.4: `port`,
`mime_type`, `path`, `path_pattern` and `path_suffix` are as declarable as the
three shown, and a consumer rejects an attribute it does not implement rather
than dropping it. Only `scheme` is **REQUIRED**. Every attribute may take a
literal or an inline application value (§6.3), as `scheme` does.

> Rationale: nothing is gained by curating this list. The attributes are the
> platform's, their meaning is Android's to define, and each one only narrows
> or widens matching *within* a filter the application has already approved as
> exported. What the stereotype is actually for — generating the action and the
> `DEFAULT`/`BROWSABLE` categories, so nobody omits one by hand — is untouched
> by which `<data>` attributes it carries.

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
- **Not expressible in v1**: verified App Links. `android:autoVerify` is an
  attribute of the filter rather than of `<data>`, and it requires
  `assetlinks.json` on the application's own domain — application
  infrastructure, so a producer may state the need but not contribute it (§7.3
  is the shape that fits, and §10 anticipates it).

**Putting the pieces together.** The component, the `application_values`
entry `scheme` refers to, and `view_links` itself are three declarations in
one sidecar, satisfied by one application:

```toml
# the producer's sidecar
[[android.contributes.components]]
kind = "activity"
name = "org.example.mypkg.RedirectActivity"
exported_required = true
reason = "Receives the OAuth redirect from the browser"

  [[android.contributes.components.view_links]]
  scheme = { application_value = "oauth_redirect_scheme" }
  host = "oauth2redirect"
  path_prefix = "/callback"

[[android.requires.application_values]]
id = "oauth_redirect_scheme"
reason = "The redirect URI scheme registered with your OAuth provider"
```

```toml
# the application's build configuration — two separate answers
[tool.examplebuild.android.exported_components]
"org.example.mypkg.RedirectActivity" = true

[tool.examplebuild.native.some-oauth-sdk.android.application_values]
oauth_redirect_scheme = "myapp-oauth"
```

The consumer combines both answers into the generated manifest — the export
approval and the spliced-in scheme:

```xml
<activity android:name="org.example.mypkg.RedirectActivity" android:exported="true">
  <intent-filter>
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data android:scheme="myapp-oauth"
          android:host="oauth2redirect"
          android:pathPrefix="/callback" />
  </intent-filter>
</activity>
```

Neither a plain Gradle project nor a sidecar-based project requires anyone to
hand-write this XML. Gradle solves it the same way: AppAuth-Android
ships the intent filter pre-written, with a placeholder for the one value the
application supplies via `manifestPlaceholders` in `build.gradle`.
`view_links` reproduces that same split — the producer supplies the filter's
shape, the application supplies one value, and the consumer does the
substitution.

**Vendor actions: `intent_filters`.** Some components need to receive a
**vendor-defined event** — not a link a browser or another app opens, but an
intent the SDK's own backend or the Android system delivers under an action
string the vendor defines. Firebase Cloud Messaging is the archetype: its
`FirebaseMessagingService` is invoked via the action
`com.google.firebase.MESSAGING_EVENT`, and most Android push,
work-scheduling, and install-referrer SDKs register a component the same
way:

```toml
[[android.contributes.components]]
kind = "service"
name = "org.example.mypkg.MessagingService"

  [[android.contributes.components.intent_filters]]
  action = "com.google.firebase.MESSAGING_EVENT"
```

- Exactly one `action` per filter. **No categories and no data element**: those
  belong to `view_links`, which models the browser-reachable case.
- Valid **only on a component that is not exported**. A consumer **MUST** reject
  `intent_filters` on an entry that declares `exported_required`, or that also
  declares `view_links`.
- The record and report of §9 **MUST** show the action alongside the component.

> Rationale: there is nothing subtle to get wrong here. The action is fixed
> by the vendor, the component stays unexported, and no other application can
> reach it — so there is no externally reachable surface to open, and no
> filter grammar worth modelling beyond the one field.

### 6.9 Shrinker keep patterns: `[android.contributes.r8]`

*For keeping classes R8's shrinker would otherwise strip or rename — a
producer's own reflectively-reached classes, or a declared dependency's —
without letting any distribution disable shrinking for the application as a
whole.*

```toml
[android.contributes.r8]
keep_classes = ["org.example.mypkg.**"]

[[android.contributes.r8.keep]]
pattern = "okhttp3.**"
from_dependency = "com.squareup.okhttp3:okhttp"
```

These are class patterns, **not** raw ProGuard/R8 directives; the consumer
generates the corresponding `-keep class <pattern> { *; }` rules itself. Two
forms, distinguished by **whose classes are being kept**:

- **`keep_classes`** — a list of patterns, each of which **MUST** fall within an
  **owned namespace** (§6.1 rule 3), protecting the distribution's own
  reflectively-reached classes. Containment is computed on dot-separated
  segments per §6.1.
- **`[[…r8.keep]]`** — a pattern belonging to a **declared dependency**.
  `from_dependency` **MUST** match the group and artifact of a dependency the
  same sidecar declares (§6.5). A consumer **MUST** evaluate the pattern against
  the **effective compilation classpath** and reject the entry when any class it
  matches originates outside that dependency's **resolved artifacts** — a
  listing of archive contents, not a parser — naming the distribution, the
  pattern, and the artifact the stray class came from.

> **Why dependency keeps are checked against the archive, not the Maven
> group.** A pattern's namespace does not have to match its dependency's
> Maven group: `com.squareup.okhttp3:okhttp` ships classes under `okhttp3.*`,
> not `com.squareup.okhttp3.*`. Checking the group would reject that
> legitimate pattern outright, so the consumer checks the resolved artifact
> instead.
>
> **Why the check covers the whole classpath, not just the named artifact.**
> The generated rule (`-keep class <pattern> { *; }`) applies everywhere in
> the program, not only inside the named dependency. If some other artifact
> also ships a class matching the pattern — `okhttp3.extra.Bar`, say — that
> class gets kept too, unrelated to the dependency declared. Checking the
> whole classpath is what makes `from_dependency` bound what the rule
> reaches, rather than just where it came from.

This scope permits *keeping*, not contributing, and is not exclusive.

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

*For reducing collisions between two producers' Swift type names: contributed
Swift compiles straight into the application's own single target, with no
per-package namespace like Android's to keep them apart. Declaring a prefix
is guidance toward avoiding that collision — not, unlike §6.1's ownership
rule, something a consumer can enforce.*

```toml
[ios]
swift_symbol_prefixes = ["MyPkg"]
```

**A producer that contributes Swift source (§7.5) SHOULD** do two things:
name its contributed types — and in particular its `@objc` runtime names —
with a consistent prefix in the code it writes, and declare that same prefix
in `swift_symbol_prefixes`.

> Rationale: this guidance deliberately does not live in an `owns` table. One
> shared module and globally-scoped `@objc` names leave a consumer nothing to
> enforce, where §6.1 has a namespace it can hold exclusively.

A consumer **SHOULD** use declared prefixes to attribute a redeclaration or
duplicate-name error to the contributing distribution.

**What this guidance does not reach.** Prefixing covers type names and `@objc`
runtime names only — not file-scope functions, global constants, or extension
members. A contributed file declaring `let ui_scale`,
`func invertedHeight(_:)`, or `extension Double { var retinaScaled }` puts all
three into the application target's scope under exactly the names it wrote,
with the extension member visible to the application's own code, and a
consumer has no way to check for it.

That limit is the real argument for keeping raw contributed Swift source
narrowly scoped (§7.5) rather than adding more prefix guidance here. **A
producer that instead ships its Swift as its own Swift package (§7.4)
avoids the problem entirely**: a package compiles as its own module, so its
symbols are already isolated from the application's. The module separation
once anticipated as future work therefore already exists today, for any
producer willing to package that way. Packaging as a Swift package isolates
ordinary Swift symbols, but not `@objc` names: those register in the
Objective-C runtime's single, flat, global namespace regardless of which
Swift module declared them, so they stay unpoliced whether the Swift is
packaged (§7.4) or contributed as raw source (§7.5).

### 7.2 Build requirements: `[ios.requires]`

```toml
[ios.requires]
deployment_target = "15.0"
```

A floor, with the same semantics as §6.2.

### 7.3 Application prerequisites: `[ios.requires]`

*For everything on iOS a producer needs and must not write: entitlements,
purpose strings, bundle files, extension targets, URL registrations, capability
keys. The producer states the need and the application answers, because each of
these fails far from its cause — a codesign error, a trap on first API call.*

```toml
[[ios.requires.entitlements]]
key = "aps-environment"
reason = "Push notification delivery"

[[ios.requires.usage_descriptions]]
key = "NSLocationWhenInUseUsageDescription"
reason = "requestWhenInUseAuthorization() traps if this key is absent"

[[ios.requires.app_extensions]]
id = "onesignal_nse"
kind = "notification_service"
reason = """\
Without it, confirmed delivery, badge counts and image attachments are \
unavailable. The extension must share an app group with the application."""
```

#### Common rules

Binding on every table in this section — `entitlements`, `usage_descriptions`,
`app_extensions`, `application_files`, `url_schemes` and `plist_capabilities`
alike:

1. `reason` is **REQUIRED**.
2. An entry **MAY** declare `conditional = true` (default `false`), whose
   meaning and constraints are below.
3. A consumer **MUST** report every entry as a prerequisite, naming the
   distribution.
4. An **unconditional** prerequisite (`conditional = false`, the default)
   that is unsatisfied **MUST** fail the build, naming the distribution and
   the `reason`.
5. A **conditional** prerequisite (`conditional = true`) that is unsatisfied
   **MUST** be recorded in the integration record (§9) and **MUST NOT** fail
   the build.
6. **A producer declaration MUST NOT cause a consumer to originate or enable
   application-owned configuration.** No entry here is satisfied by the consumer
   writing an entitlement, an `Info.plist` key, a bundle file, a URL
   registration, or a build target on the producer's authority.

> Rationale for rule 4: reporting alone is not enough. An entitlement the
> application has not enabled produces a `codesign` failure far from its
> cause, and a missing usage description terminates the application the
> first time the API is touched. The consumer fails early, where the
> diagnostic can still name the distribution that needed it.

**Rule 6 is the §2.1 distinction, not a broader prohibition.** A consumer that
also generates the application's project — as most will — may still
materialize application-owned configuration the **application itself**
supplied: if the application declares its own
`NSLocationWhenInUseUsageDescription`, the consumer writes it into
`Info.plist` as a matter of course. What it must never do is originate that
text, or enable a capability, because a *producer* asked for it.

#### What counts as satisfied

Per table, stated because two conforming readers would otherwise diverge:

| Table | Satisfied when the application… |
| --- | --- |
| `entitlements` | …configures the entitlement **key**. v1 verifies key presence, not the semantic correctness of any value it carries |
| `usage_descriptions` | …supplies a **non-empty** value for the key |
| `application_files` | …configures the named file for inclusion in the application bundle |
| `app_extensions` | …declares an extension target of the requested `kind` **and** acknowledges this entry by `(distribution, id)` |
| `url_schemes` | …**explicitly acknowledges** this entry by `(distribution, id)` |
| `plist_capabilities` | …configures the declared `value` under the declared `key` in its own `Info.plist` |

**Why `app_extensions` and `url_schemes` use an `id` instead of a platform
key.** Neither has a single string iOS defines the way an entitlement or an
`Info.plist` key does, so there is nothing else to join on. And unlike the
other four tables, satisfying either one is an **acknowledgement**, not
something the consumer can verify on its own — the next two paragraphs
explain why, for each.

**Why `url_schemes` only asks for acknowledgement.** It asks the application
for two separate things: **register** a custom URL scheme in its own
`CFBundleURLTypes`, and **forward** the resulting callback, in code, to the
SDK's handler (e.g. `StripeAPI.handleURLCallback(with:)`). Only the first is
something a consumer can inspect — read `CFBundleURLTypes` and see whether a
scheme exists; there is no way to inspect application code and confirm the
second actually happens. A consumer **MUST NOT** treat that inspectable half
as sufficient on its own, since it would only prove half of what was asked
for; the table above requires the application's explicit acknowledgement
that both were done instead. In practice that means offering the application
a way to answer, keyed by `(distribution, id)` (§2.2); treating that answer,
once given, as satisfaction with no further check; and recording it in the
integration record (§9) — disclosure standing in for the verification the
consumer cannot do, per §9's report already covering this mode.

**Why `app_extensions` also asks for acknowledgement, not just a target.**
Start with the underlying constraint: iOS allows an application only **one**
active extension target per `kind` — one `notification_service` extension,
full stop, no matter how many producers ask for one. Take the example above:
OneSignal declares `id = "onesignal_nse"`, `kind = "notification_service"`.
If a second, unrelated push SDK also declared a `notification_service`
requirement, the application cannot build a second target to satisfy it
separately — there is nowhere else on the device for that code to go.
Resolving that conflict is the application developer's job: merging both
producers' extension logic into the single target iOS permits, by hand,
since neither vendor's own instructions account for the other's code sharing
it.

That merge is exactly what a consumer cannot verify. It can check that a
target of the declared `kind` exists at all, but it has no way to open that
target and confirm whose code — OneSignal's, the other SDK's, both, or
neither — actually made it in. So satisfying this table takes two separate
actions: the application builds a real target of the requested `kind`
(checkable), and separately, per producer, acknowledges by `(distribution,
id)` that this specific producer's need is one the target actually meets
(not checkable, so it must be stated).

#### Conditional prerequisites

Per common rule 2, any entry in this section
**MAY** declare `conditional = true`, meaning *the producer cannot determine
whether this applies; the application can*:

```toml
[[ios.requires.usage_descriptions]]
key = "NSLocationAlwaysAndWhenInUseUsageDescription"
conditional = true
reason = "Required only if your application calls requestAlwaysAuthorization()"
```

Common rules 3 and 5 govern the handling; the one additional constraint is that
the `reason` **MUST** state the condition that makes the prerequisite apply.
Recording it in the integration record rather than a build-log line is the point
— a log line scrolls past, and the whole value of a conditional prerequisite is
that it survives to be read later.

> Rationale. Elsewhere, this specification's answer to feature-conditional
> native surface is to split it into optional distributions the application
> opts into (§12) — but that needs a seam to split along, and a **framework
> binding** (one class wrapping one platform API, not a facade with
> independent features behind a dispatcher) has none (§12.1). It cannot be
> split. Without a `conditional` flag it would have to choose between
> declaring the union — forcing every application to write an "Always"
> location purpose string that App Store review scrutinizes, whether or not
> it ever requests Always — and declaring the minimum, which leaves the
> caller of anything else to discover the requirement as a runtime trap.
> Neither is acceptable, and the second is the silent failure this
> specification exists to prevent.
>
> This is disclosure rather than enforcement, which §9 already treats as a
> legitimate mode. It is also the one mechanism here a producer can misuse:
> marking a genuinely unconditional requirement as conditional turns a build
> failure that names the problem into a line in a report instead — exactly
> the misuse §12.1 warns against.

#### The six tables

The common rules above govern every table below. What follows covers only
what differs per table.

##### `entitlements`

An entitlement is bound to the App ID and provisioning profile.
`codesign` requires the application's entitlements to be a subset of the
profile's. Writing one the app developer has not enabled produces a signing
failure with no trace back to the distribution that caused it, and some cannot
be granted locally at all: `com.apple.developer.location.push` requires approval
from Apple, so the gap between "declared" and "grantable" can be weeks.

**The application supplies the actual value an entitlement's `key` requires,
through the consumer's own configuration; the consumer checks only that the
key exists, never whether the value it carries is correct.**

> Rationale for leaving the value unmodelled. Several entitlements carry
> one — `com.apple.security.application-groups` takes a group identifier,
> `com.apple.developer.in-app-payments` takes merchant identifiers, and some
> must agree across targets — and a structured field would describe
> something the consumer can neither write nor check on the producer's
> behalf. All of that belongs in `reason` instead: "must be
> `group.<your-bundle-id>.onesignal`, the same on both targets" tells a
> reader more than a type tag ever could.

##### `usage_descriptions`

A purpose string is **user-facing, localized, and
read by App Store review**, and it is a claim about what *the application* does
with the data. A library cannot know it, and a binding that wrote one would give
every application the same unhelpful sentence: useless to users, and a rejection
risk the application answers for. A producer cannot contribute one through
`[ios.contributes.info_plist]` either — §7.6 rejects that outright, for the
same reason.

```toml
# the producer's sidecar — names the key it needs; asking for the text
[[ios.requires.usage_descriptions]]
key = "NSLocationWhenInUseUsageDescription"
reason = "requestWhenInUseAuthorization() traps if this key is absent"
```

```toml
# the application's own configuration — supplies the actual sentence
[tool.examplebuild.ios.usage_descriptions]
NSLocationWhenInUseUsageDescription = "Shows trails near you."
```

The consumer writes that sentence into `Info.plist` under the requested key,
verbatim and unmodified; it never sees or generates the text itself (§2.2).

##### `application_files`

Some SDKs read a configuration file from the built bundle:

```toml
[[ios.requires.application_files]]
name = "GoogleService-Info.plist"
reason = "Download from the Firebase console; Analytics reads it from the bundle and has no programmatic alternative"
```

`name` is the file's name in the bundle. **Obtaining the file is the
application developer's job, done by hand outside the build** — downloading it
from a vendor console, typically — **and placing it where the consumer's
project expects such files; the consumer's build then includes it under that
name, and checks only that a file of that name is wired into the bundle.** A
consumer **MUST NOT** create, fetch, or synthesize the file's contents itself —
these are account-specific, sometimes credential-adjacent, and always the
application's to provide.

A producer **SHOULD NOT** declare a file here when the SDK offers a programmatic
path.

> Rationale. Most application configuration reaches a producer through the
> application's Python code; this table is for the residual case where the
> vendor leaves no choice. Firebase is the motivating example — most of its
> services accept `FirebaseOptions` programmatically, and Analytics on Apple
> platforms does not.

##### `app_extensions`

`id` names the requirement. `kind` names the **extension point**, and the
vocabulary is **open** per §4.4: any of Apple's extension point identifiers may
be declared, in this specification's snake-case spelling —
`notification_service` and `location_push`, and equally
`notification_content`, `broadcast_upload`, `share` or `widget`. A consumer
**MUST** reject a `kind` it does not implement, naming the distribution. The
application creates the target, writes its source, and configures its bundle
identifier, entitlements and `Info.plist`.

> Rationale for an open set here, where §6.5's is closed. This table is a
> *requires*: the value lets a producer state what it needs and gives it nothing
> — the application decides whether to build the target at all, and no consumer
> acts on the value except to check and report. Opening it also improves the
> check rather than weakening it, because Apple's extension point identifiers
> are what a built target carries in its own `Info.plist`, where a consumer can
> match them exactly. A spec-invented label had nothing to compare against.
>
> The one-per-kind constraint below is Apple's and holds for every identifier,
> so nothing in the acknowledgement rule depends on the set being short.

> Rationale for the `requires` form. An app extension is a separate signed
> executable with its own bundle identifier and entitlements, launched by the
> operating system when the application may not be running — a larger thing for
> a transitive dependency to introduce than anything else here, and no package
> examined ships one. A contribution form is a reasonable future addition, since
> identical boilerplate written once per application is exactly what a package
> should own; it needs a producer that wants to own it. Meanwhile this converts
> a silent capability loss into a reported prerequisite.

##### `url_schemes`

An SDK whose flow leaves the application and returns through a browser needs a
custom URL scheme:

```toml
[[ios.requires.url_schemes]]
id = "stripe_3ds_callback"
conditional = true
reason = """\
Required only if the 3D Secure webview fallback is reached. Register a custom \
URL scheme and forward it from application(_:open:options:) to \
StripeAPI.handleURLCallback(with:)."""
```

The application chooses the scheme, registers it in its own `CFBundleURLTypes`,
and forwards the callback; a consumer **MUST NOT** register one on the
producer's behalf. `id` names the requirement rather than the scheme, so a
package needing several — an OAuth callback and a payment return, say — declares
one entry each and the application answers them separately.

> Rationale, and why this is not the iOS half of §6.8's `view_links`. On Android
> an intent filter is attached to the producer's own component, which is what
> makes `view_links` a contribution. `CFBundleURLTypes` is bundle-level, bound to
> no class, and routing happens at runtime in the application's delegate — an
> asymmetry belonging to the platform, not to this specification. A consumer that
> wrote the plist entry would still leave the application to forward the
> callback, because nothing says which producer symbol should receive it; naming
> one is the startup-hook shape, deliberately absent (§11). Registering half a
> requirement is worse than reporting both, because it looks done.

##### `plist_capabilities`

A few `Info.plist` keys do not describe the application, they **grant it a
capability or restrict who may install it**:

```toml
[[ios.requires.plist_capabilities]]
key = "UIBackgroundModes"
value = "remote-notification"
reason = """\
Delivery of silent pushes while the application is backgrounded. You must also \
implement the background handler; App Store review asks what the application \
does with it."""
```

`key` and `value` are the plist key and the single array entry the producer
needs, and the pair is the join key — a natural platform key, so an application
that already declares `remote-notification` for its own reasons satisfies every
producer that asked for it.

The keys this applies to are a **closed list**, given in §7.6, which rejects them
as contributions. Version 1 names two:

| Key | Why it is not contributable |
| --- | --- |
| `UIBackgroundModes` | Grants background execution. It is a claim about what the application does when the user is not looking, it costs battery, and App Store review scrutinizes it |
| `UIRequiredDeviceCapabilities` | **Restricts installation.** A producer adding an entry silently removes the application from devices lacking that hardware — precisely the harm §6.7 forbids by refusing to let a producer promote a feature to `required` |

> Rationale. This is §2.1's rule applied to a boundary a type constraint cannot
> draw: *when the application owns the artifact, state the need rather than
> contributing.* A background mode written by a producer is half a requirement —
> the handler, the battery cost and the review answer all remain the
> application's — and §2.1 says plainly that half a requirement is worse than a
> prerequisite naming both, because it looks finished.
>
> The list is closed and short on purpose. Most array-valued plist keys are
> ordinary contributions and stay that way: `LSApplicationQueriesSchemes` lets an
> SDK ask whether a wallet application is installed, which grants the application
> nothing and is exactly what §7.6's `append` is for. What earns a key a place
> here is that a producer's entry changes what the application may do, or who may
> install it.

### 7.4 Swift packages: `[[ios.contributes.swift_packages]]`

*For a vendor's Swift package, or a producer's own: resolved by SwiftPM, locked
by §9, and compiled as its own module rather than into the application's.*

```toml
[[ios.contributes.swift_packages]]
name = "Shim"
url = "https://github.com/example/shim"
requirement = { exact = "1.2.3" }
products = ["Shim"]
```

`name` is a local handle, **unique within the sidecar** — §7.7 and the app
extensions of §7.3 refer to packages by it, so two entries sharing a `name` are
invalid even when their URLs differ; a consumer **MUST** reject that, naming the
distribution.

`requirement` **MUST** be exactly one of:

| Form | Meaning |
| --- | --- |
| `{ exact = "1.2.3" }` | That version only |
| `{ from = "1.2.0" }` | SwiftPM's up-to-next-major range |
| `{ revision = "<commit>" }` | A specific commit |

A `branch` requirement **MUST NOT** appear in a distribution published to a
package index; a consumer **MUST** reject it, naming the distribution.

Reproducibility (§2.1) applies across platforms, and — as on the Android side —
**the whole graph is locked, not only what the sidecar names.** A consumer
**MUST** record the fully resolved Swift package graph, every package
**including transitives**, in the integration record (§9), and **MUST** resolve
from that record on subsequent builds until a new resolution is accepted.

**Record the resolved revision, not only the resolved version.** A version is a
tag, and a tag can be moved; the commit is what identifies the source that was
built. `Package.resolved` records both, and the integration record **MUST**
preserve both for every package in the graph — for `exact` and `revision`
requirements as much as for `from`, since a locked graph that only remembers
version strings does not pin what a later build will fetch.

**Choosing between the requirement forms.** Neither is inherently safer.
`exact` looks stricter and is the right choice when a vendor's components must
move together, but it also makes two packages that pin different versions of one
dependency unresolvable. `from` composes better and is pinned just as firmly
once the resolution is recorded. Choose on whether the dependency's versions are
independent, not on which spelling sounds stricter.

**Why this section needs no per-package checksum, and §6.5 does.** A recorded
revision *is* content identity: a commit names the tree it contains, so
re-resolving one either yields the same source or fails to produce it at all. A
Maven version names no content — a repository may serve different bytes under
one coordinate indefinitely — which is why §6.5 must add a hash to get the same
guarantee. The asymmetry is in the ecosystems, not in what this specification
asks of them.

**Binary targets are where that reasoning stops.** A Swift package may vend a
prebuilt binary target (§11), whose bytes are fetched from a URL the package
names and which the package's own revision does not cover. SwiftPM models this
already: a remote `binaryTarget` carries a `checksum`. A consumer **MUST**
record that checksum for every binary target in the resolved graph, and on
subsequent builds **MUST** verify it and fail on a mismatch, naming the package
and the declaring distribution — the obligation §6.5 places on a resolved Maven
artifact, for the reason that applies identically here. A consumer **SHOULD**
warn when a remote binary target carries no checksum, since the record then pins
nothing.

**The declaration rules above bind the sidecar; the resolved graph is where they
are enforced.** A declared package's own `Package.swift` may name anything — a
branch, a local filesystem path, an arbitrary URL — and nothing in the
declaration reveals it. A consumer **MUST** therefore reject a resolved graph
containing a **branch** requirement or a **path** dependency, naming the
declaring distribution and the offending package. A branch dependency pins a
revision after first resolution but that revision has no stable meaning; a path
dependency does not resolve on another machine at all.

**A producer MAY declare its own repository here.** A distribution whose native
half lives in a Swift package it also publishes is an expected shape, and
nothing above forbids it. Two consequences a producer **MUST** understand:

- The declared package **MUST** be resolvable in the form declared — a
  repository with no tags cannot use `exact` or `from`, leaving `revision` as
  the only valid option.
- The distribution's own version does **not** pin the native half, and §9's
  per-file hashing does not reach it. The record identifies what the wheel
  carries; a self-declared package arrives from the index its URL names, and
  only the recorded resolution pins it. A consumer's record **MUST** make that
  distinction visible rather than implying the distribution's version covers
  both.

> This specification does not require the two version lines to agree, and
> deliberately so: a Swift package's version may encode something other than the
> distribution's release history — an ABI generation, for instance — in which
> case no correspondence exists to require.

Swift Package Manager is the **RECOMMENDED** channel for anything larger than a
few glue files. Note that a Swift package may vend prebuilt binary targets; see
§11.

### 7.5 Source: `[ios.contributes.src]`

*Contributed Swift lands in the application's own compilation scope under
exactly the names it was written with — which is why this is for shims, and
§7.4 is for everything else.*

```toml
[ios.contributes.src]
swift = ["swift"]
```

Path rules per §4.1; the consumer stages `.swift` files recursively and ignores
other files. Intended for small `@objc` shims whose value is versioning
atomically with the Python half; it **SHOULD NOT** be used for a library.

**The scope restriction is narrow and load-bearing.** Every declaration a
contributed file makes at file scope is exposed to the application's own code —
free functions, global constants, protocols, and extension members on types the
producer does not own — and §7.1's prefix guidance reaches none of them. A file
declaring `let ui_scale` and `func invertedHeight(_:)` is a collision waiting
for a second producer or for the application itself, and
`extension Double { … }` is visible to everything the target compiles.

A producer whose Swift declares anything at file scope beyond prefixed types
**SHOULD** ship a Swift package (§7.4) instead, where those declarations are
confined to its own module. In practice this is nearly every producer with more
than a shim, which is what the SHOULD NOT above intends.

### 7.6 Info.plist: `[ios.contributes.info_plist]`

*For the `Info.plist` keys an SDK genuinely needs set — and deliberately not
the ones that grant the application a capability or restrict who may install
it, which are §7.3's.*

```toml
[ios.contributes.info_plist.values]
CADisableMinimumFrameDurationOnPhone = true

[ios.contributes.info_plist.append]
LSApplicationQueriesSchemes = ["examplescheme"]
```

Two contribution modes, by shape:

- **`values`** — scalar keys, set verbatim. A consumer **MUST** fail on a key
  that collides with one it manages itself, and on two distributions setting the
  same key to different values, naming the distributions. Two distributions
  setting the same key to the **same** value coalesce, preserving both
  provenance records. A key the **application** also sets is the
  application's: the consumer **MUST** keep the application's value and report
  the override — the rule §6.3 states for a manifest `<meta-data>` key, which
  applies here for the same reason.
- **`append`** — array-valued keys. Contributions from all distributions and the
  application are concatenated and de-duplicated in a deterministic order: the
  application's entries first, then each distribution's in normalized
  distribution-name order.

**TOML-to-plist mapping.** "Set verbatim" is not enough for two implementations
to agree, so the correspondence is fixed:

| TOML type | plist type |
| --- | --- |
| string | `<string>` |
| integer | `<integer>` |
| float | `<real>` |
| boolean | `<true/>` / `<false/>` |
| array of the above, homogeneous | `<array>` |

A consumer **MUST** reject any other TOML type — offset/local date-times, and
inline or nested tables — naming the distribution and the key. Dictionary values
are excluded by design (below), and dates have no motivating case; admitting
either by inference is how two readers start producing different `Info.plist`
files from one sidecar. An array **MUST** be homogeneous: a mixed-type array has
no unambiguous plist form.

**Usage descriptions are not contributable.** A consumer **MUST** reject any
`values` key whose name ends in `UsageDescription`, or which is otherwise a
purpose string, naming the distribution and directing the producer to §7.3.
These are application-authored text, and a `values` entry is the one place a
producer could write it by accident.

**Capability keys are not contributable either.** A consumer **MUST** reject
these keys in `values` and in `append` alike, naming the distribution and
directing the producer to §7.3's `plist_capabilities`:

| Key | What a producer's entry would do |
| --- | --- |
| `UIBackgroundModes` | grant the application background execution |
| `UIRequiredDeviceCapabilities` | remove the application from devices lacking the hardware |

The list is closed, and a minor revision may extend it. What puts a key on it is
that a producer's entry **changes what the application may do, or who may install
it** — not that the key is array-valued. `LSApplicationQueriesSchemes`, the
example above, grants nothing and stays an ordinary contribution.

> Rationale. Without this, §7.6 quietly undoes §7.3. Every other capability an
> iOS application acquires — an entitlement, an app extension, a URL
> registration — is a prerequisite the application answers, and a background mode
> arriving through `append` from a transitive dependency would be the one that
> did not. The evidence that the boundary was missing is in this repository: two
> worked examples contribute `UIBackgroundModes` and a third refuses to, writing
> down why. Both readings were conforming, which is the defect.

**Dictionary-valued keys are excluded by design, not deferred.** The structured
cases this specification has examined are better served by a narrower primitive
than by general dictionary support: `NSExtension` is generated from a declared
extension type, `NSLocationTemporaryUsageDescriptionDictionary` is a §7.3
prerequisite the application supplies, and `NSAppTransportSecurity` depends on
what the application loads and is not the producer's to declare at all. A
general form would hand producers the ability to write arbitrary structured
application configuration for cases that keep turning out to be something else.

**`skadnetwork_identifiers` is the one narrower primitive that case needed.**
`SKAdNetworkItems` is an array of single-entry dictionaries, one per ad network,
which every advertising and mediation SDK requires and which runs to around a
hundred entries for a mediated integration. It is producer-known, it grants the
application nothing, and it merges by de-duplicating on the identifier — the
shape `append` exists for, reachable only because the type restriction above
would otherwise block it:

```toml
[ios.contributes.info_plist]
skadnetwork_identifiers = ["su67r6k2v3.skadnetwork", "4fzdc2evr5.skadnetwork"]
```

- Each entry is an **ad network identifier**: lowercase, and ending in
  `.skadnetwork`, which is the form Apple defines. A consumer **MUST** reject an
  entry that is not, naming the distribution and the entry.
- The consumer renders `SKAdNetworkItems`, one `SKAdNetworkIdentifier`
  dictionary per identifier. A producer never writes the dictionary itself.
- Merging follows `append` exactly: the application's own identifiers first,
  then each distribution's in normalized distribution-name order,
  de-duplicated.
- A consumer **MUST** reject `SKAdNetworkItems` offered through `values` or
  `append`, naming the distribution and directing the producer here — the same
  redirection §7.6 already performs for usage descriptions and capability keys,
  and for the same reason: one destination, one merge rule, one place to look.

> Rationale, and why this is not the dictionary support refused above. The
> paragraph above says a structured case is better served by a narrower
> primitive; this is that primitive rather than an exception to the rule. What
> makes it narrow is that the producer declares a **flat list of identifiers**
> and the dictionary shape is the consumer's to render, so nothing here lets a
> producer write arbitrary structure into the application's `Info.plist`.
>
> Validating the form is worth the two conditions it costs. A mistyped
> identifier does not fail: it sits in the plist, matches no network, and
> silently loses attribution for that network's installs — a quiet wrong answer
> of exactly the kind this specification exists to convert into a build-time
> diagnostic.

### 7.7 Python modules: `[[ios.contributes.python_modules]]`

*When a Swift package **is** the Python extension module, compiled into the
application target. Without this registration the build succeeds and the
`import` fails.*

```toml
[[ios.contributes.python_modules]]
name = "web_views"
swift_package = "PyWebViews"
init = "PyInit_WebViews"      # optional; defaults to PyInit_<name>
```

The package (§7.4) is compiled into the application target rather than loaded
from a shared object, so the ordinary import machinery never sees it. This table
registers it with the interpreter — a name and a symbol, nothing executed at
build time.

- `swift_package` **MUST** name a package the same sidecar declares (§7.4). A
  module cannot be registered without the code that implements it.
- `name` is the name Python imports, and **MUST** be a single ASCII Python
  identifier: `[A-Za-z_][A-Za-z0-9_]*`. **Dotted names are not permitted** —
  registering a submodule means creating the parent package too, which is
  package semantics this table does not model.
- `init` names the module's initialization function and defaults to
  `PyInit_<name>`. When supplied it **MUST** be a valid C identifier. It exists
  because the three names need not agree: a package `PyWebViews` may implement a
  module whose Swift type is `WebViews` and whose Python name is `web_views`.
- Two distributions registering the same `name` **MUST** fail, naming both.
- A consumer **MUST** make the module importable from first use — in practice,
  registering it before interpreter initialization.

**A consumer MUST exclude, from the Python payload it assembles for the device,
both `<name>.py` and `<name>.pyi` for every module this table registers.**
Producers ship stubs of the same name for type checking off device, and a `.py`
stub would otherwise sit on `sys.path` as a silent fallback: a registration that
failed or was skipped would surface not as `ImportError` but as an application
that imports successfully and does nothing. The `.pyi` is excluded with it
because it is inert on device and its presence invites the `.py` back. This is
the same reasoning as requirement 8.14.

> Rationale, and why this is not the case §11 excludes. §11 excludes extension
> modules **carried as binaries in wheels**, which are solved by platform-tagged
> wheels ([PEP 730](https://peps.python.org/pep-0730/),
> [PEP 738](https://peps.python.org/pep-0738/)) and are loaded by the ordinary
> import machinery. This is a different shape: no binary is in the wheel, the
> code arrives as source through a declared Swift package, and it is compiled
> into the application target against the application's own interpreter. That is
> precisely why `dlopen` is not involved and why registration is needed at all.
>
> The table is iOS-only because that is where the shape occurs. On Android the
> §11 answer holds.

## 8. Consuming tool requirements

Everything a **consumer** (§1) must do — the build tool that reads sidecars and
generates the native project, as distinct from the application it builds or the
distributions it reads.

This section restates §§3–7 as a checklist; it introduces no obligation those
sections do not already carry. Where the two differ, **the body governs** and
the discrepancy is a defect worth reporting.

The list below is numbered in the order the requirements were added, and stable
numbering matters more than tidy grouping once implementations exist. This index
gives the thematic reading:

| Theme | Requirements |
| --- | --- |
| Discovery and the sidecar | 1, 2, 3, 4, 14 |
| Exclusive claims and namespaces | 5, 17 |
| **Never satisfy a prerequisite** | 6, 8, 21, 22, 23, 25 |
| The application's authority | 7 |
| Native dependency resolution | 10, 12, 16 |
| Generated manifest and project material | 11, 13, 20, 24, 27 |
| Recording, disclosure, attribution | 9, 15, 19, 25 |
| Platform applicability | 18 |
| The application's side of the contract | 7, 26 |
| The host the consumer generates | 28, 29 |

**Three outcomes, and no others.** What a consumer finds falls into exactly
three kinds, named here so that two implementations classify the same condition
the same way:

| Outcome | Meaning | Produced by |
| --- | --- | --- |
| **blocking** | the build **MUST NOT** proceed | every numbered requirement below that says *fail* |
| **advisory** | reported; the build proceeds | the **SHOULD** list below |
| **recorded** | written to the integration record (§9), and not reported as a problem at all | an unsatisfied *conditional* prerequisite (§7.3 rule 5), and the disclosure §9 requires |

The third is the one an implementation is likely to lack. §7.3 rule 5 and §9
both require material that neither stops the build nor warns about anything, and
a consumer with only two levels files it under one of them and is wrong either
way: as a warning it becomes noise to be silenced, and as nothing it stops being
the durable disclosure that was the point.

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
   required entitlement or usage description (§7.3) — including rejecting a
   usage description offered as an `info_plist` value (§7.6).
7. Provide application-side permission suppression, ensure a suppressed
   permission is absent from the **effective merged** manifest — emitting a
   merger removal rule when a resolved dependency contributes it — and report
   it (§6.7).
8. Fail when a producer's `requires` exceeds the application's configuration
   (§6.2, §7.2), when a declared application value is unsupplied or an inline
   reference names no declared `id` (§6.3), when an unconditional §7.3
   prerequisite is unsatisfied — judged by that section's satisfaction table —
   or when a component declaring `exported_required` has no application
   approval (§6.8).
9. Record each distribution's resolved contribution durably and in reviewable
   form, per the lifecycle of §9, and fail the build when the effective set
   drifts from the last accepted record.
10. Restrict contributed repositories to their declared groups/modules, reject
    two whose scopes overlap at different URLs, report them with distinct
    prominence, and reject a credential in a syntactically identifiable location
    such as URL user-info (§6.6).
11. Validate `keep_classes` against owned namespaces, and reject a
    `from_dependency` keep whose pattern matches any class on the effective
    classpath originating outside that dependency's resolved artifacts (§6.9).
12. Enforce reproducible native dependency resolution: reject unbounded and
    changing versions, and lock the **fully resolved graph, transitives
    included** — Gradle and SwiftPM alike, recording the resolved *revision* for
    Swift packages — in the record, resolving from it thereafter (§6.5, §7.4).
    Never convert a declared Gradle version into a `strictly` constraint, and
    show requested-versus-resolved where they differ. **Verify each resolved
    artifact against its recorded checksum on every subsequent build, failing on
    a mismatch** (§6.5). Reject a resolved Swift graph containing a branch or
    path dependency, and record and verify the checksum of every **binary
    target** in it, which the package's revision does not pin (§7.4).
13. Validate `view_links` (activity-only, export-gated) and generate their
    filters (§6.8).
14. Exclude sidecar directories from any Python payload it assembles.
15. Name the contributing distribution in every diagnostic.
16. When native dependency resolution **fails**, report every declared
    coordinate, module, and Swift package **with the distribution that declared
    it** (§6.5, §7.4).
17. Compute every namespace and reserved-prefix containment test on
    dot-separated segments (§6.1).
18. Fail when building for a platform a sidecar's `platforms` key omits, naming
    the distribution (§4.5).
19. Record and report the permissions, features, and components declared by
    resolved Android artifacts' own manifests, attributed to the artifact; never
    let a resolved artifact silently promote a feature to `required`, and report
    its exported components with contribution-level prominence (§9).
20. Register declared Python modules against a Swift package the same sidecar
    declares, reject a non-identifier or dotted `name`, fail on a duplicate
    module name, and exclude `<name>.py` and `<name>.pyi` from the Python
    payload (§7.7).
21. Report required app extensions as prerequisites, and never create a build
    target to satisfy one (§7.3).
22. Record an unsatisfied conditional prerequisite in the integration record,
    attributed to its distribution, without failing the build (§7.3).
23. Report required application files and URL schemes as prerequisites, and
    never create, fetch, or register one (§7.3).
24. Generate `intent_filters` only on components that are neither exported nor
    declaring `view_links`, and show each action in the record (§6.8).
25. Fail when a repository declaring `credentials_required` has no credentials
    configured, and never write a supplied credential into the generated
    project, the record, or a diagnostic (§6.6, §9).
26. Provide a means for the application to answer every `requires`, joined to
    the declaration by the key §2.2 names, and accept a build-time credential
    **by indirection** rather than only as a literal in a committed file (§2.2).
    Reject a sidecar declaring two `app_extensions` or `url_schemes` entries
    under one `id`, which the application could not answer separately (§7.3).
27. Compile contributed `.java` sources with UTF-8 forced, never the platform
    default (§6.4).
28. When it generates the application's Android activity, make it an
    `androidx.activity.ComponentActivity` or a subclass (§2.3).
29. When it generates the application's iOS app delegate, provide a documented
    means for application code to observe a URL callback delivered to
    `application(_:open:options:)`, rather than consuming it (§2.3).

> Rationale for 16. Every other rule here assumes native resolution *succeeds*.
> It need not: two distributions in one closure can declare native dependencies
> that cannot coexist — incompatible majors of a shared transitive package, two
> versions of one SDK. That failure is correct, but it surfaces as a Gradle or
> SwiftPM resolver error naming an artifact neither application author has heard
> of, with nothing connecting it back to the Python distributions that asked for
> it. The mapping from native coordinate to declaring distribution is the one
> thing the consumer knows and the underlying resolver does not, which is what
> makes requirement 8.15 meetable in the case that needs it most.

The advisory obligations carry stable identifiers of their own — referenced as
requirement 8.S1 and so on — so that a conformance claim can name the ones it
meets rather than gesturing at the list.

A conforming consumer **SHOULD**:

- **S1.** Warn on unrecognized top-level tables (§4.4).
- **S2.** Verify `from_dependency` component classes against the resolved
  artifact (§6.8).
- **S3.** Report the delta of the **fully merged** Android manifest, beyond the
  per-artifact declarations required by requirement 8.19, and the native effects of Swift
  packages' binary targets (§9, §11).

## 9. Recording and review

The integration record serves two purposes: **review** of the native surface an
application is acquiring, and **integrity** of the inputs and resolved artifacts
that produced it. Per-file hashes, per-artifact checksums and failing on drift
are what make the second more than a claim.

#### The lifecycle

1. **Compute** the integration resolution — the effective set from the
   application's dependency closure, including locked native dependency graphs
   (§6.5, §7.4).
2. **Compare** it against the last accepted integration record.
3. **Report the delta**, naming each distribution and how it entered the
   dependency closure.
4. **Fail, or require explicit acceptance** (a re-lock, a flag, a committed
   record — the consumer's workflow decides the form).
5. **Update the record** only on acceptance.

**The first build is step 4, not an exemption.** When no accepted record exists,
every contribution is new, and a consumer **MUST** require the same explicit
acceptance it would require for a change — reporting the whole effective set
rather than silently writing a record and proceeding. A single bootstrap action
covering the initial set satisfies this; treating "no record yet" as implicit
approval does not, because the first build is the one where an application
acquires *all* of its inherited native surface at once.

#### The report

A report **MUST** carry three things — the distribution, **how it entered the
dependency closure**, and the delta:

```
analytics-shim 2.1.0  (via some-ui-lib)
  + permission   android.permission.ACCESS_FINE_LOCATION  ("optional BLE device discovery")
  + feature      android.hardware.location.gps  (required=false)

map-sdk 4.1.0  (direct dependency)
  ! REPOSITORY  https://maven.example.com/releases  → groups: com.example.maps
                authenticated — no credentials configured   ✗ BLOCKING
  + dependency  com.example.maps:android:4.1.0
  + from com.example.maps:android:4.1.0 (resolved artifact manifest):
      + permission  com.example.permission.MAPS_ID
  ! requires    NSLocationWhenInUseUsageDescription  ✗ not supplied by application
  ~ requires    NSLocationAlwaysAndWhenInUseUsageDescription  (conditional, unresolved)
```

The middle element matters most for the case that motivates the requirement — a
transitive dependency the application author has never heard of.

The shape of that second entry is normative in three respects, each required
elsewhere in this specification: a repository contribution is set apart rather
than folded into a list (§6.6); contributions arriving from a **resolved
artifact's own manifest** are attributed to that artifact rather than to the
distribution that declared the coordinate (below); and an unmet prerequisite is
distinguished from an unresolved **conditional** one (§7.3), because the first
blocks the build and the second is guidance. No format is mandated — only that a
report which collapses these distinctions has not reported them.

#### Hashing the integration inputs

Inputs are hashed for **every** producer, not only path and editable
installs. The record **MUST** include a SHA-256 per file, keyed by
normalized relative path (forward slashes, relative to the sidecar directory),
covering `native.toml` and every resource it references. The wheel's own hash
pins the distribution, but the useful identity for *this* protocol is precisely
the material the integration was computed from: per-file hashes let a
diagnostic say `java/Bridge.java changed`, not merely "the producer's hash
changed."

#### What resolved artifacts bring with them

A resolved dependency carries native effects of its own. A Maven coordinate can
resolve to an `.aar` whose manifest AGP merges into the application's; a Swift
package can vend binary targets.

For Android, a consumer **MUST** include in the record and report every
`<uses-permission>`, `<uses-feature>`, and manifest component declared by the
**manifests of the resolved artifacts themselves**, beyond those declared by
sidecars and the application, attributed to the artifact that declares each one.
The resolved graph is already required by §6.5, and this obligation is bounded
by it: read each resolved `.aar`'s own `AndroidManifest.xml`.

A consumer **SHOULD** additionally report the fully merged manifest's delta.
That is a larger claim — it depends on merge semantics (`tools:node` overrides,
placeholder substitution, library ordering) rather than on what each artifact
declares — and where a consumer stops at the artifact manifests, its
documentation **MUST** say that the record's coverage is per-artifact
declarations rather than the merged result.

For iOS, reporting the native effects of a Swift package's binary targets
remains a **SHOULD**: there is no equivalent merge step, and no comparable
manifest to read.

**Native dependencies are a trust boundary, and two rules cross it.** The
restrictions in §§6–7 constrain effects *authored by the sidecar*. An `.aar` is
an Android library and may carry a manifest, resources, JNI libraries and
consumer ProGuard rules that AGP appends to the application's shrinker
configuration; a Swift package may vend binary targets. Those artifacts remain
subject to their own ecosystem's authority model, and this specification
provides **attribution and review** for their native effects, not restriction.
Policing arbitrary library code is not attempted and would not succeed.

Two exceptions exist because otherwise moving material out of the sidecar and
into an `.aar` would launder past a rule this specification treats as
security-sensitive — and because the consumer is already reading these manifests
to satisfy the paragraph above:

- A resolved artifact declaring `<uses-feature required="true">` **MUST NOT** be
  allowed to silently make hardware mandatory. The consumer **MUST** report it,
  and **MUST** override it to `required="false"` unless the **application itself**
  independently declares that feature required. Silently shrinking an
  application's device reach is the same harm whoever authors it.

  This deliberately adds no approval channel to §2.2: required hardware is
  already the application's to declare, so its own configuration is the source
  of truth and a resolved artifact cannot enlarge it.
- A resolved artifact declaring an **exported component** **MUST** be reported
  with the same prominence as a contributed one (§6.8), so the application sees
  every externally reachable surface it is acquiring, whatever declared it.

Consumer ProGuard rules embedded in a resolved `.aar` **SHOULD** likewise be
reported: they are appended to the application's shrinker configuration without
passing through §6.9's scoping.

> Why the Android half is a MUST. It is the case this section says matters
> most — a permission arriving through a transitive Python dependency the
> author has never heard of, carrying obligations beyond the build:
> `com.google.android.gms.permission.AD_ID` comes from an ads AAR and pulls the
> application into a Play Console data-safety declaration.
>
> §11 also rests on it. An `.aar` embedded in a wheel is excluded there because
> its manifest merges with no attribution, while one reached through a declared
> coordinate is permitted because §9 surfaces it — a justification that cannot
> stand on an optional feature. The cost is small: reading `AndroidManifest.xml`
> out of each resolved `.aar` is unzip-and-parse over a graph the consumer
> already records, needing no manifest merger.

#### Secrets are never recorded

A consumer **MUST NOT** write an
application-supplied credential — or any value the application supplies as a
secret — into the integration record, into a report, or into a diagnostic. Where
a record must refer to one, it refers to the *requirement* (that a repository is
authenticated, §6.6) and never to the value.

> This is the one place where the rest of this section works against itself. The
> record is required to be durable, diffable, and to hash every input, and it is
> normally committed — so the machinery that exists to make contributions
> auditable is exactly the machinery that would publish a credential to version
> control. The rule is stated here rather than left to implementers' judgement
> because nothing else in this specification would prompt the thought.

#### What a record is, and what it must contain

Two concepts are worth distinguishing by name, though this specification
mandates neither a file nor a format:

- **integration resolution** — computing the effective set (step 1);
- **integration record** — the durable, diffable artifact of the last accepted
  resolution (step 5).

A lockfile entry, a checksum file beside the generated project, or any other
durable artifact satisfies the record. The normative property is that a change
in what distributions contribute **MUST NOT** pass silently.

**What a record must make recoverable.** No format is mandated, and that is
deliberate — a consumer's records belong beside its own lock files, and Gradle,
SwiftPM and Python packaging each spell that differently. What is not optional is
the content. For every distribution in the effective set, a record **MUST** make
these recoverable:

| | |
| --- | --- |
| the distribution | its name and version, and the contract it declared |
| its provenance | how it entered the dependency closure (§3.2) |
| its inputs | a SHA-256 per file, keyed by normalized relative path (above) |
| its contributions | each one, in a form two records can be compared by |
| its unmet asks | every unsatisfied **conditional** prerequisite (§7.3 rule 5) |
| the native graph | every resolved artifact with its checksum (§6.5), and every resolved package with its version **and** revision, plus a checksum per binary target (§7.4) |

A record that cannot answer one of those rows has not recorded the integration,
whatever else it contains. [Appendix E](#appendix-e-a-record-that-satisfies-9)
shows one shape that does; it is illustrative and not required, and exists so
that a second implementer is not obliged to rediscover the same decisions.

> **What this does and does not guarantee.** The build *does* stop: an
> unaccepted change fails, and that is requirement 8.9. What acceptance cannot
> guarantee is that anyone read what they accepted — a reviewer can approve a
> delta unexamined, and no mechanism in a build tool prevents that. So this is a
> review gate whose *blocking* is enforced and whose *scrutiny* is not, which is
> a deliberate trade: a blocking prompt inside a build loop earns click-through
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

**That rule binds from the moment the draft marker at the top of this document is
removed, and not before.** While the specification is a draft it is amended in
place, and this one has done what the paragraph above forbids more than once:
§7.6 now rejects usage-description keys and capability keys it once accepted,
and §6.5's dependency forms changed shape. Each was a correction found by
expressing real packages against the text, or by implementing it. No contract
minor was allocated for the capabilities added alongside them, because there is
no released version to negotiate against yet.

Anticipated minor-revision work, deliberately excluded from version 1: verified
App Links (`autoVerify`) and further filter forms beyond `view_links`;
conditional contributions (a `when` key with a **closed vocabulary** of
conditions such as ABI or simulator/device — not an expression language);
further Gradle configurations; and further namespace-scoped shrinker rule forms.

## 11. Out of scope

| Not covered | Reason |
| --- | --- |
| Prebuilt `.aar` **embedded in the wheel** | Carries an `AndroidManifest.xml` that merges into the application's, defeating §6.7 and §6.8 with no attribution |
| Prebuilt iOS binaries **carried by the wheel** | Forces a platform tag onto an otherwise pure-Python wheel, and is opaque to this convention's source-level inspection model |
| Native `.so`, extension modules | Solved by `android_<api>_<abi>`-tagged wheels ([PEP 738](https://peps.python.org/pep-0738/)) |
| iOS frameworks in wheels | Solved by `ios_*`-tagged wheels ([PEP 730](https://peps.python.org/pep-0730/)) |
| Android resources (`res/`) | Resource names are a flat global namespace per type, so no ownership rule can be built for them (§6.1 needs dots to compute containment). A producer shipping `values/strings.xml` with `app_name` renames the application. Resources reach an application through an `.aar` from a declared coordinate, where AGP merges them |
| Scripts, hooks, build plugins | Excluded on principle (§2.1), not as a deferral |
| **Arbitrary manifest, `Info.plist` or build-file fragments** | The declarative form of the same capability, and excluded on the same principle. A fragment cannot be collision-checked, cannot be refused per-permission (§6.7), cannot be gated per-component (§6.8), and cannot be diffed in a record (§9) — a producer's material stops being reviewable the moment its meaning is a merge nobody computes. Permanent, not a deferral; see below |
| **CocoaPods-only iOS SDKs** | §7.4 declares Swift packages, and this specification defines no CocoaPods channel. A vendor that publishes only a podspec is out of reach; see below |
| **Native runtime lifecycle composition** | No way for a producer to run code at application start, or to participate in an app-delegate callback. Deliberate in version 1, and not on principle — see below |
| Xcode build settings, compiler/linker flags | Arbitrary build mutation; revisit only with a concrete, bounded need |
| Application configuration — *writing* it | The application's own build settings are the consumer's concern. **Declaring a requirement on it is in scope** and is most of §7.3; see below |

**What "in the wheel" excludes — and what it does not.** The qualifier on the
first four rows is deliberate. A **declared Maven coordinate** may resolve to an
`.aar`, a **declared Swift package** may vend binary targets, and a Swift package
may implement a Python extension module from source, compiled into the
application target against the application's own interpreter (§7.7). All three
are in scope: they arrive through the platform's own dependency channel, locked
by §6.5/§7.4 and surfaced by §9. What is excluded is native material smuggled
inside the Python artifact, where no resolver, lock, or manifest tooling ever
sees it.

That distinction is only as good as the surfacing, which is why §9 makes the
Android half of that reporting a **MUST**. An embedded `.aar` and a
coordinate-resolved `.aar` merge identical manifests into the application; what
separates them is that one is locked, attributable, and reported. Were the
reporting optional, the two would differ only by whether the consumer bothered.

**The application-configuration row is a boundary, not a silence.** A producer
cannot write the application's entitlements, `Info.plist`, bundle contents,
build targets or URL registrations — but it can and should *declare that it
needs them*, and a consumer must report those requirements and fail when they
are unmet. That is what §7.3 is: six kinds of prerequisite, plus §6.6's
repository credentials. The excluded thing is the producer reaching into the
application's configuration, not the producer having a say in it.

**Build-time uploads are an excluded category, not one product.** Any SDK whose
value depends on uploading build artifacts — symbol files, mapping files, source
maps — requires build-time execution by construction. Firebase Crashlytics is
the canonical case: its Gradle plugin uploads the R8 mapping file, and a
run-script phase uploads dSYMs. Sentry, Bugsnag, Instabug and Datadog share the
shape. Such an SDK can be *linked* through §6.5 or §7.4 and the result will
build; the build-time step must be configured in the application's own build,
outside this convention. **This is permanent, not a deferral.**

**Uploading is not the only shape.** A second class of plugin **transforms the
code being built** — instrumenting bytecode, or running as a compiler plugin —
and for those the sentence above is false: linking the SDK produces a build that
succeeds and an SDK that does nothing, or code that does not compile at all.

The consequence is not uniform, and a producer should work out which of three
cases it is in:

- **The SDK degrades.** The build-time step adds symbolication to something that
  already captures and delivers events. Sentry is the example — its Gradle plugin
  is optional and its configuration is declarations this specification can
  express. A wrapper is worth shipping, with a known deficiency.
- **The SDK fails.** The build-time step is load-bearing for the SDK's core
  value. Crashlytics is the example: without it every report is unsymbolicated,
  which is the part nobody wants. A wrapper is not worth shipping.
- **The SDK cannot be integrated at all.** The build-time step *is* the
  integration: Embrace's `embrace-swazzler` and New Relic's Gradle plugin
  instrument bytecode to insert the hooks the SDK reads, and Realm's Kotlin
  compiler plugin generates members its model classes are unusable without.
  There is nothing here to ship, and a producer should say so rather than
  publish a wrapper whose failure looks like a bug in this convention.

**Why arbitrary fragments stay excluded, and what it costs.** The obvious answer
to every gap in this section is to let a producer contribute a block of manifest
XML, a subtree of `Info.plist`, or a snippet of build script. It would make
almost everything expressible, and it would remove the reason to trust any of
it: authority in this specification is carried by knowing, per key, whether a
producer may set it freely, only with the application's approval, or not at all
(§6.7, §6.8, §7.3, §7.6). A fragment answers that question nowhere. §6.9 already
refuses raw shrinker directives for exactly this reason and takes structured
class patterns instead — *"raw rules are also a capability"* — and this row is
that argument generalized. The cost is real and is paid deliberately: a
mechanism this specification has no vocabulary for is unreachable until a minor
adds one, which is the trade §4.4's fail-closed rule already makes.

**A CocoaPods-only vendor is out of reach, and a producer has two options.**
§7.4 resolves Swift packages; nothing here resolves podspecs, and adding a
second dependency channel is a larger commitment than any single vendor
justifies. Where a vendor publishes only to CocoaPods — Google's ML Kit for
Apple platforms is the standing example — a producer can wait for the vendor's
own Swift package, or publish a package of its own that vends the vendor's
binaries and declare that under §7.4, taking on the maintenance that implies.
Neither is free, and pretending otherwise by leaving the case unmentioned served
nobody.

**Lifecycle composition is a deferral, not a principle**, and is the most
consequential thing version 1 cannot express. Firebase calls
`FirebaseApp.configure()` from `application(_:didFinishLaunchingWithOptions:)`,
OneSignal's Android integration is an `Application` subclass, and Stripe needs a
URL callback forwarded from the app delegate. Each is currently the
application's work to wire up, and a producer can only say it is needed.

Two things argue for waiting. Some vendors reach the same result declaratively —
Sentry initializes before any application code through a `ContentProvider` in its
own library plus manifest meta-data (§6.3) — so a hook is not the only shape the
problem takes. And it would be the largest runtime capability here: unlike a
`service` or `receiver`, which run when the platform routes an event to them, a
startup hook runs unconditionally and first, in every application that acquires
the package transitively. If it is added, the shape is a closed vocabulary of
events plus a producer-owned typed handler, with the consumer generating a
static dispatcher — never a source snippet, which would breach §2.1. The
singleton slots such a design needs (`<application android:name>`, the generated
entry point) are the consumer's, and a producer **MUST NOT** be able to claim one
meanwhile.

## 12. Guidance for package authors

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

This is why the specification defines no conditional **contribution** syntax
(§10): **the dependency graph is the conditionality mechanism.** Sidecars are
per-distribution, applications opt in by depending on the piece they use, and
the record of §9 attributes each contribution to the smallest meaningful unit.

**Prerequisites are the exception, and §7.3 does carry a `conditional` flag.**
The asymmetry is deliberate. A contribution *imposes* — an application that
acquires the distribution gets the permission whether or not it wanted it — so
making one conditional needs a mechanism that can actually withhold it, and the
dependency graph is that mechanism. A prerequisite imposes nothing; it asks.
Marking one conditional changes only whether an unmet ask blocks the build, so a
flag is sufficient where a contribution would need a whole opt-in channel.

The honest cost falls on the producer: splitting a facade into optional
distributions is real packaging work (separate releases, an import layout that
tolerates missing pieces). The guidance is **SHOULD**, not MUST, for exactly
that reason — and §6.7's suppression exists in part as the application's
recourse when a producer declares more than its applications want.

### 12.1 Framework bindings, where the guidance does not apply

The advice above assumes a **facade**: features that are independent
implementations behind one dispatcher, with a seam to split along. A **1:1
binding of a platform framework** has no such seam. Its API surface is the
platform vendor's, it is typically one native module and one Python module, and
its requirements vary per method rather than per feature:

| A `CLLocationManager` binding | pulls in |
| --- | --- |
| `requestWhenInUseAuthorization` | `NSLocationWhenInUseUsageDescription` |
| `requestAlwaysAuthorization` | `NSLocationAlwaysAndWhenInUseUsageDescription` |
| `allowsBackgroundLocationUpdates` | `UIBackgroundModes = ["location"]` |
| `startMonitoringLocationPushes` | a location push extension and an Apple-approved entitlement |

Splitting that into optional distributions would mean splitting the class, which
is not packaging work but a worse API. So a binding cannot follow the guidance
above, and it faces the union problem it exists to prevent: declare everything
and every application carries the worst case, or declare the minimum and callers
of everything else fail at runtime.

**Conditional prerequisites are the answer for this shape** — see §7.3. A
binding declares its unconditional needs normally, and marks the rest
`conditional = true` with the triggering condition in the `reason`. Nothing is
imposed on applications that do not use the feature, and nothing is silent for
applications that do.

Producers **SHOULD NOT** reach for that mechanism to avoid stating an
unconditional requirement. A requirement wrongly marked conditional converts a
build failure that names the problem into a line in a report.

## Appendix A: why contributions stay per-distribution

The tempting implementation is to let every distribution write its material into
one shared location under `site-packages` and let the installer merge them. It is
less code, and it forecloses most of this specification.

A merged tree **destroys provenance at install time**. Once files are overlaid,
nothing can determine which distribution contributed which file — so collision
detection, per-distribution attribution, the review record of §9, and every
diagnostic required by requirement 8.15 all become impossible.

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
- **Expo config plugins** — the executable form of this problem: JavaScript
  functions a package ships to mutate the generated native project. Widely used,
  and precisely the capability §2.1 excludes.
- **Cordova / Capacitor `plugin.xml`** — the *declarative* form, and the more
  instructive comparison, because it concedes §2.1's principle and keeps the
  capability anyway: `<config-file target="AndroidManifest.xml" parent="/manifest">`
  admits arbitrary XML at a chosen location. Fifteen years of practice, with the
  failure Appendix A predicts for merged material — plugin-contributed manifest
  entries that no tool can attribute, refuse, or arbitrate between plugins. §11's
  exclusion of arbitrary fragments is a decision against this, not an oversight.

## Appendix D: declaration reference

Every key a sidecar may contain, with the section that defines it. Descriptions
are summaries; where this table and the body differ, the body governs.

**This table is also the contract-minor registry** (§4.3). Every entry below is
contract **1.0**; a key added by a later minor **MUST** be marked *Since 1.n*
here, and a consumer checks under-declaration against these marks. An unmarked
key is 1.0, which is why nothing below carries a mark yet.

| Entry | Description |
| --- | --- |
| **Top level** | |
| `contract` | **Required.** Major of this specification, optionally with a minor — `"1"` or `"1.1"`. §4.3 |
| `platforms` | Optional. Where the distribution *functions*, not merely where it contributes; a build for an omitted platform fails. §4.5 |
| **`[android.owns]`** §6.1 | |
| `java_namespaces` | Java package namespaces this distribution claims exclusively; two distributions claiming overlapping ones fail the build. Required when contributing Java/Kotlin, producer-sourced components, or keep patterns |
| **`[android.requires]`** §6.2 | |
| `compile_sdk`, `min_sdk`, `target_sdk` | Floors. The build fails when the application is lower; the consumer never raises the application to match. `target_sdk` is the most invasive — it changes behaviour app-wide — so declare it only when a behaviour depends on it |
| `core_library_desugaring` | Optional boolean. A floor on a boolean axis: the build fails when the application has not enabled desugaring, and the consumer never enables it |
| **`[[android.requires.application_values]]`** §6.3 | |
| `id` | A logical name for the value, unique within the sidecar; full identity is (distribution, `id`). The application supplies the value under it, and contributions reference it as `{ application_value = "…" }`. Values are non-empty strings |
| `reason` | **Required.** What the value is and where to obtain it |
| `manifest_meta_data` | Optional. The `<meta-data>` key the SDK reads; the consumer writes the supplied value there |
| `manifest_placeholder` | Optional. An AGP manifest placeholder the consumer supplies the value as, for a value a **declared dependency's own manifest** reads (Auth0, AppAuth). Merged like `manifest_meta_data`, and the two may both appear |
| **`[android.contributes.src]`** §6.4 | |
| `java`, `kotlin` | Directories whose `.java` / `.kt` files the application's own toolchain compiles |
| **`[[android.contributes.gradle_dependencies]]`** §6.5 | |
| `coordinate` | `group:artifact:version` with an exact version. **Recommended**, because the version is visible here — with the range form below, finding what was actually used means opening the integration record (§9) |
| `module` + `version` | `group:artifact` with a bounded `{ at_least, below }` range. Open-ended and changing versions are invalid |
| `configuration` | Optional; `implementation` (default), `api`, `compileOnly`, `runtimeOnly`. A **closed** set: processor configurations are excluded because they execute code at build time (§2.1) |
| **`[[android.contributes.gradle_repositories]]`** §6.6 | |
| `url` | A Maven repository to add to the application's resolution. The most powerful thing a sidecar can contribute, which is why the next two rows are mandatory |
| `reason` | **Required.** Why the artifacts are not available from the default repositories, and — when authenticated — which credential is needed and where to get it |
| `groups`, `modules` | **At least one required.** Bounds what the repository may serve |
| `credentials_required` | Optional. Declares the repository authenticated. A sidecar **MUST NOT** contain the credential itself |
| **`[[android.contributes.permissions]]`** §6.7 | |
| `name` | The canonical manifest string — `android.permission.INTERNET`, never a shorthand |
| `reason` | Recommended; carried into the report of §9 |
| `max_sdk_version`, `never_for_location` | Optional. `android:maxSdkVersion` and `android:usesPermissionFlags="neverForLocation"`. Both are minimization; where two distributions differ, the **widest** need wins and the merge is reported |
| **`[[android.contributes.features]]`** §6.7 | |
| `name` | Always registered `required="false"`; only the application may promote a feature |
| **`[[android.contributes.components]]`** §6.8 | |
| `kind` | `service`, `activity` or `receiver`. `provider` is deliberately absent: an authority is mandatory and must be unique device-wide, so only the application ID can supply it |
| `name` | The class. Under an owned namespace unless `from_dependency` says otherwise |
| `from_dependency` | `group:artifact` of a declared dependency that owns the class |
| `exported_required` + `reason` | Requests export. The build fails without explicit application approval — it never falls back to unexported |
| `[[…view_links]]` — `scheme`, `host`, `path_prefix`, and Android's other `<data>` attributes (`port`, `mime_type`, `path`, `path_pattern`, `path_suffix`) | Generates the browser-return filter. Valid only on an exported activity; `scheme` is required, the attribute set is open (§4.4), and each may take an inline application value |
| `[[…intent_filters]]` — `action` | One vendor-defined action, on a component that is neither exported nor carrying `view_links` |
| **`[android.contributes.r8]`** §6.9 | |
| `keep_classes` | Class patterns the shrinker must keep; the consumer generates the `-keep` rules itself. Each must fall within an owned namespace |
| `[[…r8.keep]]` — `pattern`, `from_dependency` | Keeps a *dependency's* classes instead. Checked against what the resolved artifact actually contains, since a Maven group ID need not match the Java packages inside it |
| **`[ios]`** §7.1 | |
| `swift_symbol_prefixes` | Prefixes the producer puts on its Swift type names. Guidance only — nothing enforces it, and it does not cover file-scope functions or extension members |
| **`[ios.requires]`** §7.2 | |
| `deployment_target` | Minimum iOS version the producer needs. A floor: the build fails if the application targets lower, and the consumer never raises it |
| **`[ios.requires.*]` — prerequisites** §7.3 | Every entry takes `reason` (**required**) and `conditional` (optional). Unconditional and unsatisfied fails the build; conditional and unsatisfied is recorded |
| `[[…entitlements]]` — `key` | Satisfied by the key's presence; v1 does not model its value |
| `[[…usage_descriptions]]` — `key` | The application writes the sentence; §7.6 rejects one offered as a contribution |
| `[[…app_extensions]]` — `id`, `kind` | `kind` is an Apple extension point identifier, snake-cased; the set is open (§4.4). The application builds the target and acknowledges this `id`, since one target cannot be assumed to serve two producers |
| `[[…application_files]]` — `name` | A file the SDK reads from the bundle. Declare only when no programmatic path exists |
| `[[…url_schemes]]` — `id` | Says the application must register a URL scheme and forward the callback. `id` names the requirement, not the scheme — the application chooses that — so a package may declare several |
| `[[…plist_capabilities]]` — `key`, `value` | An `Info.plist` key that grants a capability or restricts installation. A closed list, given in §7.6, which rejects the same keys as contributions |
| **`[[ios.contributes.swift_packages]]`** §7.4 | |
| `name` | Local handle, unique within the sidecar; §7.7 and §7.3 refer to packages by it |
| `url`, `products` | The repository, and which of its products to link |
| `requirement` | Exactly one of `{ exact }`, `{ from }`, `{ revision }`. `branch` is invalid |
| **`[ios.contributes.src]`** §7.5 | |
| `swift` | Directories of `.swift` staged into the application target. For small shims only |
| **`[ios.contributes.info_plist]`** §7.6 | |
| `values` | Scalar keys set verbatim. Collisions fail; `*UsageDescription` keys are rejected |
| `append` | Array keys merged with the application's and other producers', de-duplicated |
| `skadnetwork_identifiers` | Ad network identifiers, lowercase and ending `.skadnetwork`. The consumer renders `SKAdNetworkItems` from them; offering that key through `values` or `append` is rejected |
| **`[[ios.contributes.python_modules]]`** §7.7 | |
| `name` | The name Python imports. A single ASCII identifier, no dots |
| `swift_package` | A package the same sidecar declares, which implements the module |
| `init` | Optional initialization symbol; defaults to `PyInit_<name>` |

## Appendix E: a record that satisfies §9

**Non-normative.** §9 mandates the content of an integration record and
deliberately not its format. This is the shape the reference reader writes,
included so that a second implementation has a worked example to disagree with
rather than a blank page. Nothing here is required, and a consumer whose records
live inside its own lock file is conforming without resembling this at all.

```json
{
  "record": 1,
  "platform": "android",
  "contract": "1",
  "distributions": [
    {
      "name": "pystripe",
      "version": "2.1.0",
      "origin": "via some-ui-lib",
      "contract": "1",
      "inputs": {
        "java/org/pystripe/PaymentReturnActivity.java": "sha256:9f2c…",
        "native.toml": "sha256:cde8…"
      },
      "entries": [
        "permission android.permission.INTERNET  (\"Stripe API calls\")",
        "component activity org.pystripe.PaymentReturnActivity (exported)",
        "  view_link org.pystripe.PaymentReturnActivity: scheme trailmap-pay, host stripe-redirect",
        "dependency com.stripe:stripe-android  requested [21.0.0, 22.0.0) → resolved 21.6.0",
        "requires url_schemes stripe_3ds_callback (conditional, unresolved)"
      ],
      "artifacts": { "com.stripe:stripe-android:21.6.0": "sha256:4b1a…" },
      "swift": {},
      "swift_binaries": {}
    }
  ]
}
```

Three properties are worth naming, because they are what make the file useful
rather than merely present:

- **One line per contributed thing.** A set difference over `entries` *is* the
  delta a reviewer reads, so the report of §9 needs no separate computation and
  a `git diff` is already legible.
- **Sorted keys, UTF-8, one contribution per line.** The record is normally
  committed; anything that reorders between runs turns review into noise.
- **No credential, ever.** An authenticated repository appears as
  `REPOSITORY … authenticated — credentials configured`. That the repository
  needs a credential is a fact about the integration; the credential is not
  (§6.6, and the secrets rule above).
