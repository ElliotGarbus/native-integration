# The native-integration specification

**Version:** `1` (draft)
**Entry-point group:** `native_integration.v1`

A Python distribution uses this convention to declare what an Android or iOS
application build must provide on its behalf. A build tool discovers those
declarations, stages what it can, and tells the application author what is left
to do.

> **Status: draft, in progress.** This document replaces an earlier attempt,
> kept at [`development/first-attempt.md`](development/first-attempt.md) for its
> reasoning and its evidence. Neither was ever released, so this takes version 1
> rather than renumbering around a version nobody had to support. Sections
> marked *to be ported* are not yet written.

---

## Goals

This convention automates the parts of native integration that are portable and
repeatable, and states the rest as explicit tasks for the application author.

A declaration is automated when all three of these hold:

1. The producer knows exactly what is required.
2. The consumer can do it deterministically.
3. Little or no application-specific policy is involved.

Maven and SwiftPM dependencies, glue source, permissions, manifest components,
fixed manifest and `Info.plist` entries, and SDK floors all qualify. Those are
the things an application author would otherwise transcribe out of a README.

Everything else is stated as a requirement on the application. **Manual is a
first-class outcome, not a gap in this document.** By **manual** this document
means the consumer states the requirement — as an action, a value, or a
placeholder ([§1](#1-terminology)) — and the application author satisfies it.
A requirement that this convention cannot automate is still worth stating: the
consumer reports it, and — where the shape is a value — scaffolds it as a
placeholder in the application's own `pyproject.toml`, a TODO the author
resolves where they already work
([§2.3](#23-what-the-consumer-generates)). That makes the requirement
attributed and reviewed, rather than a gap discovered at runtime.

## Non-goals

This convention does not:

- execute anything a producer ships, at build time or any other time;
- describe edits to make to a build file, manifest, or Xcode project;
- model every platform construct Apple and Google ship.

The third is deliberate. Platform vocabulary that this document must track is
platform vocabulary that dates it.

---

## 1. Terminology

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY**
are to be interpreted as described in
[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

| Term | Meaning |
| --- | --- |
| **Distribution** | An installed Python distribution, as seen by `importlib.metadata`. |
| **Producer** | A distribution that declares a native integration. Where this document addresses the person who writes one, it says **package author**. |
| **Consumer** | A tool that reads declarations and generates a native app project. Consumers are build tools, not installers. |
| **Application** | The app being built. Its own configuration is outside this document. |
| **Dependency closure** | The application's direct dependencies and their transitive requirements, as resolved for the target platform. |
| **Sidecar** | The declaration file a producer ships. |
| **Contribution** | Native material the consumer stages on the producer's behalf. |
| **Value** | A string the application supplies and the consumer writes to a platform key. |
| **Action** | An outcome the application must achieve, which the consumer states and does not perform. |
| **Placeholder** | Text a consumer scaffolds in place of a value it does not have. The build does not proceed while a placeholder stands. |
| **Fail closed** | On anything unrecognized, invalid, or unverifiable, reject and stop the build — never proceed as though it were absent. The opposite, **fail open**, is never conforming behavior under this document. |

---

## 2. Overview

A producer ships a TOML file inside its wheel and registers an entry point
identifying its location. A consumer enumerates the application's dependency
closure, reads each sidecar, validates it, stages the declared material into the
native project it generates, and reports what the application still owes.

Nothing here requires a change to any packaging standard, a custom build
backend, or a new artifact type.

### 2.1 Design principles

**Declarations are data.** A sidecar contains no commands, scripts, plugins,
hooks, or build-system arguments. A producer describes; it never instructs. A
consumer **MUST NOT** execute any content of a sidecar.

**All native integration material falls into one of three categories.** They are
the sidecar's top-level shape, and each carries a different part of the security
model.

| Category | Meaning | Enforcement |
| --- | --- | --- |
| **`owns`** | An exclusive claim, held across every distribution in the closure | collision-checked; a second claimant fails |
| **`requires`** | A condition the application or its build must satisfy | reported and never auto-satisfied; the consumer invents nothing |
| **`contributes`** | Material the consumer stages into the generated project on the producer's behalf | staged, attributed, and disclosed in the record |

A Java namespace is owned. An SDK floor, a value the application supplies, and
an action it performs are required — [§5](#5-requirements-on-the-application)
covers those three shapes. Source files, dependency coordinates, permissions and
manifest components are contributed — [§6](#6-android-contributions) and
[§7](#7-ios-contributions) cover those per platform.

**Automate what is deterministic; state the rest.** The three-part test under
[Goals](#goals) is what decides between the last two categories: material that
passes all three is a contribution, and material that fails any of them is a
requirement. When it fails, state it as an action rather than forcing it into a
shape the consumer cannot honor. A partial automation that looks complete is
worse than a clear task.

**Never originate what belongs to the application.** Where the application owns
the artifact — an entitlement, its `Info.plist`, its bundle, a build target — a
producer states a requirement and stops. A consumer **MAY** place a value the
application supplied. It **MUST NOT** invent one.

**Unrecognized declarations fail closed.** A consumer **MUST NOT** skip a
declaration it does not understand. Skipping one ships an application that
breaks at runtime, far from the cause.

**Contributions stay per-distribution.** A consumer **MUST** name the
contributing distribution in every diagnostic it emits about declared material.

**Native dependency resolution is reproducible.** Every contributed dependency
**MUST** resolve identically from the same integration record.

### 2.2 How the application answers

The application answers every requirement through the **consumer's own
configuration**. This document mandates the capability a consumer offers, never
its spelling. Two conforming consumers can ask for the same thing in different
words.

A consumer **MUST** provide a way for the application to:

| Answer | Joined by |
| --- | --- |
| Supply a value | `(distribution, id)` |
| Acknowledge an action | `(distribution, id)` |
| Suppress a contributed permission | permission `name` |
| Approve an exported component | component `name` |
| Supply credentials for an authenticated repository | repository `url` |

The consumer chooses the path; the producer fixes the leaf. If a producer
declares `id = "sentry_dsn"`, the application answers under that exact string,
wherever the consumer nests it.

**Identity is scoped by distribution and platform.** Two distributions may each
declare `id = "client_id"` without collision. One distribution may use the same
`id` on Android and iOS and mean two different values — which is common, because
account identifiers frequently differ per platform.

**Credentials are supplied by indirection.** For a build-time credential, a
consumer **MUST** accept a reference — an environment variable, a secret store,
a file outside the project — and **MUST NOT** require the value to be written
into a file the consumer tells the application to commit.

> **Note:** Ordinary values are different. An analytics DSN or an ad-network
> application ID is embedded in the shipped application and readable by anyone
> who unzips it, so committing one is not a leak. A build-time credential is
> the opposite: it is used only to fetch dependencies during the build and
> never ships inside the application, which makes the repository the only
> place it can leak from — and why it is the one thing here that must not come
> to rest there.

### 2.3 What the consumer generates

A consumer **MUST** report every unmet requirement, naming the distribution
that declared it, the `reason`, and — for an action — the `summary`,
`instructions`, and `acceptance`. Omitting the latter two would report that
something is owed without carrying what a person or agent needs to do the work
and confirm it.

A consumer **SHOULD** scaffold declared placeholders into the application's own
configuration, so that what remains is visible where the author already works:

```toml
# Added by examplebuild. Required by pysentry.
[tool.examplebuild.native.pysentry.android.values]
sentry_dsn = "<TODO: your Sentry DSN, from Settings → Projects → Client Keys>"
```

An action has no placeholder — nothing satisfies it but the application
author's own acknowledgement — so a consumer **SHOULD** instead scaffold it
**commented out**, carrying `summary`, `reason`, `instructions`, and
`acceptance` as commentary the author uncomments once done. `instructions` and
`acceptance` are what let a coding agent act on this directly rather than stop
and wait for a human to translate a one-line summary
([§5.6](#56-instructions-and-acceptance-criteria)):

```toml
# Added by examplebuild. Required by mywechatpkg.
# Add a WXEntryActivity under your own application ID.
# WeChat resolves this class by name under your application ID; without it,
# login and share callbacks never reach the SDK.
#
# Create WXEntryActivity in the package <applicationId>.wxapi. It must extend
# Activity, implement IWXAPIEventHandler, and forward both callbacks to
# IWXAPI.handleIntent. Declare it in your manifest as exported, with
# android:launchMode="singleTask".
#
# Acceptance:
#   - WXEntryActivity exists in the package <applicationId>.wxapi
#   - The activity implements IWXAPIEventHandler
#   - The activity is declared in the manifest, exported, with launchMode singleTask
#   - Both callbacks are forwarded to IWXAPI.handleIntent
#
# Uncomment once done:
# [tool.examplebuild.native.mywechatpkg.android]
# acknowledged_actions = ["wechat_entry"]
```

Three rules govern scaffolding:

- A consumer **MUST NOT** modify a file the application owns unless the
  application asked it to. Scaffolding is a command the author runs, not a side
  effect of a build.
- A consumer **MUST NOT** treat a placeholder as a supplied value. See
  [§5.4](#54-how-a-requirement-is-satisfied).
- A consumer **MUST NOT** scaffold an action's acknowledgement anywhere but
  commented out. An acknowledgement the consumer wrote itself is
  indistinguishable from one the application author wrote after doing the
  work, and only the author can make that claim true.

### 2.4 Obligations on the consumer's bootstrap

Before it reads any sidecar, a consumer's bootstrap must provide two properties
that declared material depends on and no producer can check.

**Android.** The bootstrap **MUST** make the Android activity it generates an
`androidx.activity.ComponentActivity`, or a subclass of one.

> **Note:** Current Android SDKs return their results through the
> activity-result contract, `registerForActivityResult`, which is declared on
> `ComponentActivity` and not on the platform's own `Activity`. The
> `onActivityResult` path it replaced is deprecated. An SDK that opens a screen
> of its own — a payment sheet, an identity check — then has nowhere to hand its
> result back to. The application sees a compile error inside generated glue, or
> a cast failure at first use, with nothing tying either to the distribution
> that declared the dependency.
>
> Naming a class dates this obligation. That is accepted deliberately: every
> other spelling describes the same type in more words, and a minor revision
> revisits it when Android's mainstream moves.

**iOS.** The bootstrap **MUST NOT** consume a URL callback delivered to
`application(_:open:options:)` without providing a documented way for
application code to observe it.

> **Note:** [§5.3](#53-actions) lets a producer ask the application to register
> a URL scheme and forward the resulting callback to an SDK's handler. In this
> ecosystem the application author writes Python and the app delegate belongs to
> the bootstrap, so a bootstrap that swallows the callback leaves a requirement
> nobody can satisfy. An application that acknowledged forwarding it would then
> be wrong through no fault of its own.

Neither clause gives a producer a way to run code at startup or to join a
lifecycle callback. Both are properties of a bootstrap the consumer already
writes, not a seam for producer code to enter.

> **Note:** Some SDKs need this and already solve it themselves. Where a
> vendor's own SDK provides a declarative load hook — a manifest entry naming a
> class its own bundled loader reads before any component runs, as Android's
> Airship `Autopilot` and Sentry's `ContentProvider` trick do — a producer
> states that entirely through an ordinary value ([§5.2](#52-values)) and a
> contributed class ([§6](#6-android-contributions)), and no manual step
> remains. Where no such hook exists — iOS has none today — the requirement
> stays an action ([§5.3](#53-actions)): the application author calls the SDK
> from their own code at startup. This document grants no other path for
> producer code to run early, on either platform.

---

## 3. Discovery

### 3.1 The entry point

A producer **MUST** declare exactly one entry point in the group
`native_integration.v1`, in the producer's own `pyproject.toml`:

```toml
# the producer's own pyproject.toml
[project.entry-points."native_integration.v1"]
native = "mypkg._native"
```

- The entry-point name **SHOULD** be `native`. It carries no meaning, and
  consumers ignore it — see [§3.3](#33-iterate-do-not-look-up-by-name).
- The value **MUST** be an importable module reference: a dotted path of valid
  Python identifiers, with no `:attr` suffix, naming the directory that contains
  the sidecar.

Nothing is ever imported. The value is spelled as a module reference so the
metadata stays truthful to the entry-points specification, which defines a value
as pointing to an importable object. This convention reads the named directory's
*files* instead.

> **Caution:** There are two ways to misspell the group, and both are silent.
> The underscore is required —
> [entry-point group names](https://packaging.python.org/en/latest/specifications/entry-points/)
> cannot contain hyphens, so `native-integration.v1` is not this group despite
> matching the project name. The quotes are required TOML syntax: in an unquoted
> header a dot nests, so `[project.entry-points.native_integration.v1]` declares
> a group named `native_integration` containing a table `v1`. Either mistake
> produces a wheel that installs cleanly and a build that never finds the
> sidecar.

### 3.2 Resolution

A consumer **MUST** resolve declarations as follows:

1. Determine the candidate set: the resolved **dependency closure** of the
   application for the target platform. A consumer operating in an isolated
   environment that contains exactly that closure **MAY** treat all installed
   distributions as candidates.
2. For each candidate, read entry points in the group `native_integration.v1`
   through `importlib.metadata`.
3. Interpret the value's dotted path as a directory within the distribution —
   `mypkg._native` becomes `mypkg/_native/` — and read `native.toml` inside it.

A consumer **MUST NOT** accept contributions from distributions outside the
closure, whatever else is installed alongside it.

> **Note:** `importlib.metadata` has no concept of "the application's
> dependencies"; it enumerates entry points across whatever is installed.
> Resolving the closure into a clean environment is what makes step 1's shortcut
> sound — only there does *installed* coincide with *in the closure*. Outside
> such an environment the two sets diverge, and the consumer must compute the
> closure and filter against it rather than trust what it finds.

A consumer **MUST** access the sidecar and every resource it references through
the distribution's metadata and file-resource interface —
`importlib.metadata.Distribution.locate_file()`, `Distribution.files`, or
equivalent. A consumer **MUST NOT** assume a distribution is represented by a
conventional `site-packages` directory. When a distribution's resources cannot
be materialized or read, the consumer **MUST** fail, naming the distribution,
rather than skipping it.

**Nothing is imported, ever.** A consumer **MUST NOT** import the producing
package or any module of it, at any point, including the module the entry point
names. Metadata reads and file reads only.

> **Note:** A consumer runs on a desktop build host. A distribution targeting
> Android or iOS may raise on import on that host, or may not be importable on
> it at all.

**Provenance.** For each producer, a consumer **MUST** be able to state how it
entered the dependency closure. Where several dependency paths exist, the
consumer **MUST** report at least the producer's immediate dependents, and any
path it reports **MUST** be deterministic across runs.

### 3.3 Iterate; do not look up by name

One distribution contributes at most one entry ([§3.4](#34-one-entry-per-distribution)),
but the closure holds one candidate per distribution, so the group can hold
many — one from each distribution that ships a sidecar. A consumer **MUST**
iterate every entry in the group `native_integration.v1` across the closure and
ignore each entry's own name. A consumer **MUST NOT** look an entry up by name.

> **Note:** The name carries no information — the platform lives inside the
> file — so a name-keyed lookup silently skips any distribution that labelled it
> differently. The package installs, the build succeeds, and the declaration
> never lands.

### 3.4 One entry per distribution

A distribution that declares more than one entry in the group is invalid. A
consumer **MUST** fail, naming the distribution. It **MUST NOT** select one or
merge them.

### 3.5 The distribution is the only carrier of the sidecar

A sidecar reaches a consumer only by riding on an installed Python
distribution in the application's dependency closure. There is no other channel:
no path, no registry, and no configuration key by which a consumer can be
pointed at a sidecar the closure does not contain.

A project whose material is entirely native — a Swift package, a Maven
artifact — **MUST** therefore publish a Python distribution to participate,
however thin. A distribution carrying nothing but a sidecar and the package data
it references is a legitimate and expected shape.

> **Note:** This is a real obligation, not a formality. It asks projects with no
> other reason to build a wheel to build one. It is worth the cost because the
> dependency closure is what bounds the set of things allowed to configure the
> application: a declaration that could arrive from outside the closure would be
> a declaration nobody chose to depend on.

The closure is resolved for a target platform **and a Python version**. A
sidecar **MUST NOT** restate an interpreter requirement. `Requires-Python`
already carries it enforceably, and a closure correctly resolved for one
interpreter cannot contain a distribution built for another.

## 4. The sidecar file

### 4.1 Location and name

The sidecar **MUST** be named `native.toml`, **MUST** reside in the directory
the entry-point value identifies, and **MUST** ship as ordinary package data.

```
mypkg/
  __init__.py
  _native/
    __init__.py          ← required: keeps the entry-point value importable
    native.toml          ← fixed name; the entry point does not spell it
    java/…               ← optional, per §6
    swift/…              ← optional, per §7
```

The sidecar directory **MUST** contain an `__init__.py`, typically empty.

> **Note:** Without it the directory is only a namespace package
> ([PEP 420](https://peps.python.org/pep-0420/)), and implicit
> namespace-package resolution is not guaranteed to behave identically across
> import systems — so the entry point's dotted path would not be reliably
> portable. A regular package makes it one unambiguous thing.

**Referenced resources.** Every path a sidecar declares is interpreted relative
to `native.toml` and **MUST NOT** escape its directory, checked *after* path
normalization and symlink resolution. Symlinked resources are not permitted in
version 1; a consumer **MUST** reject one, naming the distribution. Contributed
source files **MUST** be UTF-8 encoded.

**The sidecar directory is build input, not application payload.** A consumer
**MUST** exclude it — `native.toml` and every resource under it — from any
Python payload it assembles for the device.

> **Note:** Its contents have already been consumed at build time, and
> contributed source is compiled by the application's own toolchain. A second
> copy inside the application is at best dead weight. At worst it is a
> regression: source that compilation had turned into something less directly
> readable ships again as plain text, undoing whatever protection the build step
> gave a producer's glue code.

### 4.2 One file for all platforms

A distribution **MUST** ship exactly one sidecar covering every platform it
supports. Platforms are tables within it, not separate files.

> **Note:** The contract version is then declared once and validated in a single
> read, before anything is trusted. Per-platform files would let those versions
> disagree.

### 4.3 Contract version

The sidecar **MUST** declare a top-level `contract` key: a string holding the
major version of this specification, optionally with a minor.

```toml
contract = "1"        # equivalent to "1.0"
```

```toml
contract = "1.1"      # uses a capability added in revision 1.1
```

Declare the smallest contract whose capabilities you use.

A consumer implementing contract *X.Y* **MUST** reject a sidecar that declares a
different major, or a minor greater than *Y*, with a message naming the
distribution and the contract the sidecar needs. It **MUST NOT** parse such a
sidecar partially.

A consumer **MUST** also reject a sidecar that **under-declares**: one using a
key or table introduced in a revision later than the contract it names, even
when the consumer implements both.

> **Note:** Without the under-declaration rule the gate protects only older
> consumers. A producer that mis-declares its contract is then caught by nobody
> until an older consumer meets it — at which point the diagnostic blames the
> consumer's age rather than the producer's declaration.

The declaration reference in Appendix D is the registry that makes the
under-declaration rule checkable. Every key it lists is contract 1.0 unless it
carries a *Since* note, and a minor revision that adds a key **MUST** record the
minor there. Without one normative source for *which revision introduced this
key*, two conforming consumers would reach different verdicts on the same
sidecar.

A consumer **MUST** be able to state the contract it implements, and **SHOULD**
report it where a person can see it — a version string, a doctor check. That is
what lets a package author decide whether adopting a minor strands their users.

### 4.4 Unknown declarations fail closed

Within a platform table the consumer is **building for**, an unrecognized key
**MUST** be rejected, naming the distribution and the key. A consumer **MUST
NOT** ignore a declaration it does not understand in order to proceed.

**Values fail closed on the same terms.** Some contribution keys take a value
from a vocabulary the *platform* owns and this document does not enumerate — an
Android `<data>` attribute, a foreground service type. Where a key is defined
that way, a consumer **MUST** reject a value it does not implement, naming the
distribution and the value, and **MUST NOT** substitute a default it does
understand. A consumer **SHOULD** say which values it does implement, so a
producer can tell an unsupported declaration from a misspelled one.

An unrecognized **top-level key that is not a table MUST be rejected**, naming
the distribution and the key.

A consumer **MAY** ignore a platform table for a platform it is not building —
an `[ios]` table during an Android build is outside its concern. A consumer
**SHOULD** warn about a top-level *table* it does not recognize at all, since it
cannot distinguish a future platform from a misspelled one.

> **Caution:** That tolerance is for tables only. A future platform arrives as a
> table, so nothing legitimate has the other shape, and the key likeliest to be
> misspelled is `platforms`. A `platfroms = ["ios"]` that only warned would
> discard the one claim [§4.5](#45-platform-support) exists to carry — silently,
> which is the failure that section was added to prevent.

> **Note:** Silently ignoring an unknown *contribution* is the dangerous case. A
> 1.0 consumer skipping a 1.1 table builds an application that breaks at
> runtime, far from the cause. Failing closed also catches typos: a misspelled
> `permisions` key is an error, not a no-op. Additive evolution is preserved by
> [§4.3](#43-contract-version)'s minor, which turns *silently ignored* into
> *visibly rejected, with the version that would work*.

### 4.5 Platform support

```toml
platforms = ["ios"]
```

Optional. Names the platforms on which the distribution **functions at all**. A
consumer building for a platform not listed **MUST** fail, naming the
distribution and how it entered the dependency closure.

- Values **MUST** be platform names this document defines: `android`, `ios`. An
  empty list is invalid.
- Declaring a platform table for a platform the key omits is a contradiction. A
  consumer **MUST** reject it, naming the distribution.
- Omitting the key makes no claim, and is the default.

**A missing platform table and a missing platform name are different claims.**
No `[ios]` table means *I contribute no native material on iOS*; the package may
still work there and simply need nothing. Omitting `android` from
`platforms = ["ios"]` means something stronger: *I do not function on Android at
all*.

> **Note:** A platform-specific framework's Python wrapper installs fine on the
> wrong platform, because its own content is pure Python and nothing in the
> wheel objects. The build succeeds. The failure appears later, at `import`, or
> never: a facade whose unimplemented branch is `pass` runs and does nothing.
> [§4.4](#44-unknown-declarations-fail-closed) cannot catch this — there is no
> key to reject, only a distribution that does not work here.
>
> `platforms` makes a claim about the **distribution**, not about native
> material. That reaches beyond this document's usual scope, and no other
> mechanism carries the claim today.

## 5. Requirements on the application

A producer states a requirement in one of three shapes.

| Shape | Use it when | Section |
| --- | --- | --- |
| **Floor** | The application's build configuration must meet a minimum | [§5.1](#51-build-floors) |
| **Value** | The application has a string, and the consumer knows where to write it | [§5.2](#52-values) |
| **Action** | The application must achieve an outcome the consumer cannot produce | [§5.3](#53-actions) |

**The boundary between a value and an action is what the consumer can place
deterministically.** If the consumer can take a string and write it to a known
key, it is a value. If the application must create something, configure
something, or make a claim the consumer cannot inspect, it is an action.

Classify by what the requirement is, not by which shape would be easier to
satisfy. A notification icon is a drawable image someone must draw: there is
no string for the consumer to write, so it is an action — however convenient
declaring it as a value would be.

### 5.1 Build floors

Floors are minimums the application's build must meet.

```toml
[android.requires]
min_sdk = 24
compile_sdk = 35
target_sdk = 33                 # optional
core_library_desugaring = true  # optional

[ios.requires]
deployment_target = "15.0"
```

A consumer **MUST** fail, naming the distribution, when the application's
configured value is lower, or when a declared boolean floor is not enabled. A
consumer **MUST NOT** raise the application's configuration to satisfy a floor.

> **Caution:** `target_sdk` changes behavior across the whole application, in
> code that has nothing to do with the producer's package. Declare it only when
> a specific behavior depends on it, and say which one.

### 5.2 Values

A producer declares a value when the application has a string that the build
must embed, and the producer knows the platform key it goes to.

```toml
[[android.requires.application_value]]
id = "sentry_dsn"
kind = "manifest_meta_data"
key = "io.sentry.dsn"
reason = "Your Sentry project DSN, from Settings → Projects → Client Keys"
placeholder = "<TODO: your Sentry DSN>"
```

| Field | Required | Description |
| --- | --- | --- |
| `id` | **yes** | A logical name, unique within the sidecar. Identity is `(distribution, id)`, scoped by platform. |
| `kind` | **yes** | Where the consumer writes the value. A closed set — see [§5.5](#55-value-kinds). |
| `key` | depends on `kind` | The platform key the value is written to. |
| `reason` | **yes** | What the value is and where to obtain it. |
| `placeholder` | **SHOULD** | Text the consumer scaffolds until the application supplies the value. |
| `conditional` | no | Defaults to `false`. See [§5.4](#54-how-a-requirement-is-satisfied). |

Rules:

- The supplied value is a **non-empty string**. Version 1 defines no other type.
- A value **MUST** declare a `kind`. If there is nowhere for the consumer to
  write the string, the requirement is an action, not a value.
- Two values targeting the same `(kind, key)` **coalesce** when the supplied
  content is equal, preserving both provenance records. When it differs, the
  consumer **MUST** fail, naming both distributions.
- A key the **application** sets itself is the application's. The consumer keeps
  the application's value and reports the override.
- A producer **MUST NOT** declare a value for something an SDK accepts at
  runtime. Pass that from the producer's own Python code instead.

Three pieces make up the whole exchange: the sidecar above declares the
requirement, the consumer scaffolds it, and the application author fills it
in.

The consumer reads `id`, `reason`, and `placeholder` from the sidecar and
writes this into the application's own `pyproject.toml`
([§2.3](#23-what-the-consumer-generates)) — the application has supplied
nothing yet:

```toml
# Added by examplebuild. Required by pysentry. Fill in the value below.
[tool.examplebuild.native.pysentry.android.application_values]
sentry_dsn = "<TODO: your Sentry DSN, from Settings → Projects → Client Keys>"
```

The application author replaces the placeholder with the real string, under
the same `(distribution, id)` — scoped to the same platform, `android` here —
the consumer scaffolded:

```toml
[tool.examplebuild.native.pysentry.android.application_values]
sentry_dsn = "https://examplePublicKey@o0.ingest.sentry.io/0"
```

Only once that placeholder is gone does the consumer write the string to
`io.sentry.dsn`, because `key` said so — the application never spells the
platform key, and the producer never sees the DSN.

> **Why values are scalar:** every delivery site in [§5.5](#55-value-kinds)
> takes one string. Array-valued platform keys are either producer-known, in
> which case they are contributions with merge rules of their own, or
> application-owned capabilities, in which case they are actions and the
> application does the merging. No composition mechanism is needed, and needing
> one would mean the boundary had slipped.

### 5.3 Actions

A producer declares an action when the application must achieve an outcome the
producer cannot hand the consumer as a string.

```toml
[[android.requires.application_action]]
id = "wechat_entry"
summary = "Add a WXEntryActivity under your own application ID"
reason = """\
WeChat resolves this class by name under your application ID. Without it, \
login and share callbacks never reach the SDK."""
instructions = """\
Create `WXEntryActivity` in the package `<applicationId>.wxapi`. It must
extend `Activity`, implement `IWXAPIEventHandler`, and forward both callbacks
to `IWXAPI.handleIntent`. Declare it in your manifest as exported, with
`android:launchMode="singleTask"`.
"""
acceptance = [
  "WXEntryActivity exists in the package <applicationId>.wxapi",
  "The activity implements IWXAPIEventHandler",
  "The activity is declared in the manifest, exported, with launchMode singleTask",
  "Both callbacks are forwarded to IWXAPI.handleIntent",
]
```

| Field | Required | Description |
| --- | --- | --- |
| `id` | **yes** | A logical name, unique within the sidecar. Identity is `(distribution, id)`, scoped by platform. |
| `summary` | **yes** | One line, in the imperative. This is what a report shows. |
| `reason` | **yes** | Why it is needed, and what breaks without it. |
| `instructions` | no | Prose telling a reader how to do it. |
| `acceptance` | **SHOULD** | Statements of the end state. See [§5.6](#56-instructions-and-acceptance-criteria). |
| `uses` | no | Value `id`s in this sidecar that this action consumes. |
| `slot` | no | An opaque key identifying a contended application-owned surface. See [§5.7](#57-slots). |
| `conditional` | no | Defaults to `false`. |

Rules:

- A producer **SHOULD NOT** declare an action for something a contribution or a
  value already expresses. An action is the cheapest thing to write and the most
  expensive thing for every application to act on.
- Every `id` in `uses` **MUST** resolve to a value declared in the same sidecar
  for the same platform. A consumer **MUST** reject one that does not, naming
  the distribution and the unresolved `id`.
- There is no verification mechanism in version 1. A consumer reports an action
  and the application acknowledges it.

An action has no placeholder, so the consumer scaffolds it commented out,
carrying every field above as commentary
([§2.3](#23-what-the-consumer-generates)), built entirely from the sidecar
above:

```toml
# Added by examplebuild. Required by mywechatpkg.
# Add a WXEntryActivity under your own application ID.
# WeChat resolves this class by name under your application ID; without it,
# login and share callbacks never reach the SDK.
#
# Create WXEntryActivity in the package <applicationId>.wxapi. It must extend
# Activity, implement IWXAPIEventHandler, and forward both callbacks to
# IWXAPI.handleIntent. Declare it in your manifest as exported, with
# android:launchMode="singleTask".
#
# Acceptance:
#   - WXEntryActivity exists in the package <applicationId>.wxapi
#   - The activity implements IWXAPIEventHandler
#   - The activity is declared in the manifest, exported, with launchMode singleTask
#   - Both callbacks are forwarded to IWXAPI.handleIntent
#
# Uncomment once done:
# [tool.examplebuild.native.mywechatpkg.android]
# acknowledged_actions = ["wechat_entry"]
```

The third piece is the application author doing that work, then uncommenting
the acknowledgement themselves — the consumer never uncomments it on their
behalf, because only the author can make that claim true:

```toml
[tool.examplebuild.native.mywechatpkg.android]
acknowledged_actions = ["wechat_entry"]
```

Acknowledging is a claim, not a proof: nothing here checks that
`WXEntryActivity` exists. The application author is asserting that
`instructions` was followed, and a consumer **MUST** take that assertion as
satisfying the requirement — see [§5.4](#54-how-a-requirement-is-satisfied).

> **Note:** `uses` links an action to a value it depends on, when a
> requirement has both halves. An app group identifier is a string the
> application supplies — a value ([§5.2](#52-values)) — but enabling App
> Groups on two targets and getting the entitlement into a provisioning
> profile is work only the application author can do — an action. Declare
> both, and put the value's `id` in the action's `uses`:
>
> ```toml
> [[ios.requires.application_value]]
> id = "app_group_id"
> kind = "info_plist"
> key = "com.example.app-group"
> reason = "The App Group identifier this SDK shares data through"
>
> [[ios.requires.application_action]]
> id = "app_group_entitlement"
> summary = "Enable App Groups and add the identifier above to the entitlement"
> uses = ["app_group_id"]
> ```
>
> Without `uses`, these would read as two unrelated line items, and nothing
> would stop an application author from acknowledging the action while the
> value it depends on is still an unfilled placeholder. `uses` makes that
> dependency checkable ([§5.3](#53-actions) rejects a `uses` that does not
> resolve) and lets a report show the action beside the value it needs,
> instead of asking the reader to notice the connection on their own. It does
> not collapse the two into one requirement — the value is still something a
> consumer can place automatically, and the action is still something only
> the application author can complete.

### 5.4 How a requirement is satisfied

| Shape | Satisfied when the application… |
| --- | --- |
| Floor | is configured at or above the declared value |
| Value | has supplied a non-empty string that is not the placeholder |
| Action | has acknowledged it by `(distribution, id)` |

A consumer **MUST**:

- fail the build when an **unconditional** (`conditional == false`)
  requirement is unsatisfied, naming the distribution and the `reason`;
- record an unsatisfied **conditional** (`conditional == true`) requirement in
  the integration record and **MUST NOT** fail the build for it.

Declare `conditional = true` when you cannot tell whether the requirement
applies and the application can. State the triggering condition in `reason`.

> **Caution:** Do not mark an unconditional requirement conditional to avoid a
> build failure. It converts a failure that names the problem into a line in a
> report.

**A consumer MAY report what it already knows.** Nothing here forbids a consumer
from noticing that a file it is packaging is present, or that a key it manages
is set, and saying so alongside an action. What it **MUST NOT** do is treat its
own observation as satisfaction: an observation covers the part the consumer can
see, and an action exists because part of it is out of view.

> **Why version 1 defines no checks:** a check that cannot satisfy an action
> only improves an error message, and a check that can satisfy one reports
> *done* for a requirement that is only half met. Presence of an entitlement key
> says nothing about the provisioning profile that must carry it. Version 1
> takes acknowledgement, which never tells an author they are finished when they
> are not, and revisits this when support evidence says otherwise.

### 5.5 Value kinds

`kind` tells the consumer where to write the value. The set is **closed**: a
consumer is being asked to modify the build, so it **MUST** reject a `kind` it
does not implement, naming the distribution and the value.

| `kind` | Platform | `key` is | The consumer writes |
| --- | --- | --- | --- |
| `manifest_meta_data` | Android | a `<meta-data>` name | `<meta-data android:name="<key>" android:value="<value>"/>` in `<application>` |
| `manifest_placeholder` | Android | an AGP placeholder name | the value as a manifest placeholder, for a dependency's own manifest to consume |
| `info_plist` | iOS | an `Info.plist` key | the value under that key |
| `usage_description` | iOS | a `*UsageDescription` key | the value under that key, verbatim |
| `inline` | both | *(omitted)* | nothing directly; a contribution references the `id` and the consumer substitutes it |

`info_plist` **MUST NOT** name a `*UsageDescription` key; use
`usage_description`, which exists so that a report can tell an author they are
being asked for user-facing text that App Store review reads.

**Nothing in this section has an open vocabulary.** Some contribution keys
elsewhere in this document stay open deliberately, because the *platform* owns
the names — an Android `<data>` attribute, a foreground service type. A
requirement never does. An action ([§5.3](#53-actions)) carries no vocabulary
at all: `summary`, `reason`, `instructions` and `acceptance` are prose, `slot`
is opaque and compared only for equality, and `uses` names values in the same
sidecar. `kind`, above, is a **closed**, enumerated set for the same reason
every other closed set is: a consumer is being asked to write something. There
is nothing left in [§5](#5-requirements-on-the-application) that a platform's
own vocabulary could extend.

### 5.6 Instructions and acceptance criteria

`instructions` and `acceptance` are addressed to a person or to a coding agent
working on that person's behalf. They are not addressed to the consumer.

**Write for a reader with no other context.** A coding agent acting on a
scaffolded action ([§2.3](#23-what-the-consumer-generates)) has this text and
nothing else — not the producer's README, not its issue tracker, not a human
across a desk to ask a follow-up of. Name the exact class, package, method,
and manifest attribute; an instruction that leans on context a human would
infer ("wire it up the usual way") gives an agent nothing to act on and
produces a plausible-looking implementation that satisfies none of the
`acceptance` items below.

**Acceptance criteria state an end state, never an operation.**

| Write this | Not this |
| --- | --- |
| "The activity is declared in the manifest" | "Insert an `<activity>` element into AndroidManifest.xml" |
| "The extension target shares an app group with the application" | "Add the app group key to Extension.entitlements" |

Criteria written as end states stay true when a toolchain lays its project out
differently, and can be evaluated by whoever did the work — including an agent
checking its own output against a list before declaring the action done, the
same way it would check any other task's exit criteria. Criteria written as
operations are a build-mutation language, which this convention does not have
and does not want.

**Each item in `acceptance` is checked independently.** A producer **SHOULD**
split it into several short statements — one end state per item — rather than
folding everything into a single long entry, so a reader, human or agent, can
work through the list item by item instead of re-deriving what "done" means
from a wall of prose.

**Security boundary.** A producer's `instructions` and `acceptance` are
**untrusted content**, and this document distinguishes three parties:

| Party | May act on instructions? |
| --- | --- |
| The consumer | **No.** It renders, records and hashes them, and never executes, applies, or fetches. |
| A human or agent working for the application author | **Yes**, with that author's authority — treating the content as third-party input, not as direction from the author. |
| The producer | Supplies them, and is the untrusted party. |

Because a human or an agent may act on this text, a consumer **MUST** include
`instructions` and `acceptance` in the hashed inputs of the integration record.
A change between versions then appears as a reviewable delta, which is what
bounds the channel.

### 5.7 Slots

**The problem `slot` solves:** iOS allows exactly one notification service
extension per application. A push SDK that needs to decrypt or rewrite a
notification before it displays asks the application to create one and call
into its handler — an ordinary action. A second, unrelated push SDK, added
later, asks for the same thing. Nothing about either action alone reveals the
conflict: each reads as a reasonable, self-contained request, and an
application author acting on them one at a time creates two extension
targets — which iOS does not run side by side — or overwrites one vendor's
handler with the other's, and finds out only when that vendor's feature
silently stops working.

Nothing about this is specific to notifications. An iOS broadcast upload
extension (screen recording), a file provider extension, and a watch
extension are each capped at one per application the same way, and a `slot`
covers all of them identically — it is the shape, "the platform allows
exactly one," not the particular surface, that makes something worth naming
this way.

A `slot` names the contended surface so a consumer can catch this before the
application author starts, by recognizing that two actions claim the same
one-only surface:

```toml
slot = "com.apple.usernotifications.service"
```

- A `slot` is an **opaque string**. A consumer compares slots for equality and
  **MUST NOT** interpret them.
- A producer **SHOULD** use the platform's own identifier for the surface: an
  Apple extension point identifier, an entitlement key, a manifest attribute.
  This document enumerates none of them.
- When two actions in the effective set share a slot, a consumer **MUST** report
  them together, naming both distributions.

Reporting a contention is disclosure, not a failure. The application resolves
it — by merging two vendors' code into the one target the platform allows, which
is work no consumer can do and no producer can anticipate.

---

## 6. Android contributions

Material the consumer stages into the generated Gradle project on the
producer's behalf.

| § | Key | Contributes | How conflicts resolve |
| --- | --- | --- | --- |
| [6.1](#61-ownership) | `android.owns.java_namespaces` | A claim on a Java/Kotlin namespace | Overlapping claims **fail** the build |
| [6.2](#62-source) | `android.contributes.src` | Java/Kotlin source under an owned namespace | N/A — one producer owns the namespace |
| [6.3](#63-gradle-dependencies) | `android.contributes.gradle_dependencies` | A Gradle dependency coordinate | Versions resolve to a **floor** ([§5.1](#51-build-floors)); conflicting configurations fail |
| [6.4](#64-maven-repositories) | `android.contributes.gradle_repositories` | A Maven repository URL | Union; a consumer **MAY** refuse an untrusted host |
| [6.5](#65-permissions-and-features) | `android.contributes.permissions`, `.features` | A `<uses-permission>` or `<uses-feature>` entry | Union; the application **MAY** suppress one |
| [6.6](#66-manifest-components) | `android.contributes.components` | An `<activity>`, `<service>`, `<receiver>`, or `<activity-alias>` entry | Two producers naming the same class **fail** the build |
| [6.7](#67-shrinker-keep-patterns) | `android.contributes.r8.keep` | An R8 keep pattern | Union |
| [6.8](#68-manifest-meta-data) | `android.contributes.meta_data` | An application-scoped `<meta-data>` entry | Equal values coalesce, differing values **fail**, the application's own value always wins |
| [6.9](#69-package-visibility) | `android.contributes.queries` | A `<queries>` entry (`package` or `provider_authority`) | Union |

### 6.1 Ownership

Claim the Java namespaces your distribution writes into, so no other
distribution can collide with them or replace a toolchain's entry point through
a transitive dependency.

```toml
[android.owns]
java_namespaces = ["org.example.mypkg"]
```

`java_namespaces` is **REQUIRED** when the distribution contributes Java or
Kotlin source, producer-sourced manifest components, or shrinker keep patterns
under its own namespace.

A consumer **MUST** enforce every rule below and fail the build when one is
violated, naming the distribution or distributions responsible:

| # | Rule |
| --- | --- |
| 1 | Every contributed source file's path **and** its declared `package` falls under an owned namespace. |
| 2 | Every producer-sourced component name ([§6.6](#66-manifest-components)) falls under an owned namespace. A component attributed to a declared dependency is exempt; the class is not the producer's. |
| 3 | Every `keep_classes` pattern falls within an owned namespace. Dependency keeps are checked differently ([§6.7](#67-shrinker-keep-patterns)). |
| 4 | An owned namespace under a reserved prefix is rejected. |
| 5 | Two distributions claiming overlapping namespaces fail, naming both. |

Reserved prefixes are the bootstrap namespaces of the known Python-mobile
toolchains — `org.kivy.android`, `org.libsdl.app`, `org.jnius`,
`org.renpy.android`, `com.chaquo.python`, `org.beeware.android` — plus any
namespace the consumer's own bootstrap occupies.

> **Note:** Rule 4 stops a distribution shipping
> `org/kivy/android/PythonActivity.java` from silently replacing the
> application's entry point. The list is consumer-independent so that one
> toolchain's runtime cannot be clobbered because a different toolchain built
> the application.

**Containment is computed on dot-separated segments, never on raw strings**, in
rule 4 as in rule 5. A namespace *A* contains *B* when *B* equals *A*, or when
*B* begins with *A* followed by a `.`. So `org.kivy.android` contains
`org.kivy.android.helpers` and does not contain `org.kivy.androidx`, and `PyGMA`
does not contain `PyGMAKit`.

An owned namespace **SHOULD** be reverse-DNS. A consumer **SHOULD** warn on a
single-label one: it is ownable and collision-checked like any other, but it
claims a top-level name for one distribution, which makes accidental overlap
with a sibling project far likelier.


### 6.2 Source

Source code for "glue classes" your binding needs on the device, compiled by the application's own
toolchain.

```toml
[android.contributes.src]
java = ["java"]
kotlin = []
```

From each listed directory the consumer stages, recursively, exactly the files
with the matching extension — `.java` for `java` roots, `.kt` for `kotlin`
roots — and ignores other files. Contents **MUST** be source text.

A consumer **MUST**:

- compile them with the application's own toolchain;
- exclude the source files from any Python payload it assembles;
- compile `.java` sources with UTF-8 forced, never the platform default.

Path rules are [§4.1](#41-location-and-name)'s. Subject to
[§6.1](#61-ownership) rule 1.

> **Note:** `kotlinc` and the Swift compiler always read source as UTF-8;
> `javac` does not, and falls back to the platform default charset unless told
> otherwise. Without forcing it, §4.1's UTF-8 requirement on the producer's side
> guarantees nothing.

### 6.3 Gradle dependencies

A vendor SDK, declared as a Maven coordinate and resolved by Gradle, rather than
transcribed into the application's build file by hand.

```toml
[[android.contributes.gradle_dependencies]]
coordinate = "com.google.android.gms:play-services-ads:25.2.0"
configuration = "implementation"    # optional
```

A dependency **MUST** be spelled in exactly one of two forms. The exact form
above is **RECOMMENDED**. The second is a bounded range:

```toml
[[android.contributes.gradle_dependencies]]
module = "com.onesignal:OneSignal"
version = { at_least = "5.6.1", below = "6.0.0" }
```

| Field | Rule |
| --- | --- |
| `coordinate` | `group:artifact:version`. The version **MUST** be exact. |
| `module` | `group:artifact`. `version` is **REQUIRED**, and **both** `at_least` (inclusive) and `below` (exclusive) are **REQUIRED** within it. A range open at either end is invalid. |
| `configuration` | Optional. `implementation` (default), `api`, `compileOnly`, `runtimeOnly`. A **closed** set. |

A consumer **MUST** reject an entry declaring both `coordinate` and `module`, or
neither. Changing versions (`-SNAPSHOT`), unbounded dynamic versions (`+`,
`latest.release`), and ranges spelled inside `coordinate` are invalid in either
form.

**The configuration set is closed, and deliberately not the platform's own.**
Adding a coordinate to `annotationProcessor`, `kapt` or `ksp` makes the build
*run code from that artifact*. A producer **MUST NOT** declare a processor
configuration, and a consumer **MUST** reject one, naming the distribution. The
four names above add a dependency and execute nothing.

**A declared version is a minimum, not a pin.** Gradle may select a higher
version when something else in the graph requires it. A consumer **MUST NOT**
silently convert a declaration into a `strictly` constraint — that would make
two producers naming different versions of one library unresolvable, and
composing independently-authored packages is the point. Where the selected
version differs from the declared one, the record and report **MUST** show both:

```
  + dependency  com.example:widget   requested 1.2.3 → resolved 1.4.0
```

**Resolution is locked, not merely versioned.** A consumer **MUST**:

- record the fully resolved dependency graph — every artifact and version,
  transitives included — in the integration record;
- resolve from that record on subsequent builds until a new resolution is
  accepted;
- record a checksum per resolved artifact, verify each one on subsequent builds,
  and fail on a mismatch, naming the artifact and the distribution that declared
  it.

> **Note:** A version is a coordinate, not a content hash. A repository can
> serve different bytes under one version, and a moved tag resolves elsewhere.
> The checksum is what makes reproducibility literally true, and it is cheap,
> because the consumer has already downloaded every artifact it is hashing.

**Cross-artifact alignment is not expressible.** Every rule here governs one
dependency at a time. A vendor BOM — Gradle's `platform(…)` — is a constraint
over a set, and neither form can state it. A family split across several
distributions pins its artifacts independently, and nothing makes those choices
agree. Producers publishing such a family **SHOULD** pin compatible versions
deliberately and release together.

### 6.4 Maven repositories

For an SDK its vendor does not publish to Maven Central.

> **Caution:** This is the most powerful thing a sidecar can contribute. An
> unconstrained repository can reach the application through any transitive
> dependency, which is a dependency-confusion vector, so the rules here are the
> strictest in this document.

```toml
[[android.contributes.gradle_repositories]]
url = "https://maven.pkg.github.com/example/repo"
reason = "Hosts org.example:shim, which is not on Maven Central"
groups = ["org.example"]
```

`reason` is **REQUIRED**. At least one of `groups` (Maven group IDs) or
`modules` (`group:artifact` pairs) is **REQUIRED**.

**The normative requirement is bounded participation.** The contributed
repository **MUST NOT** participate in resolution for anything outside the
declared groups or modules. A consumer implements that with its build system's
native mechanism; Gradle's repository content filtering expresses exactly this.

**Overlapping scopes are rejected.** Two contributed repositories whose scopes
intersect **MUST** fail, naming both distributions and the contested
coordinates — unless they declare the same `url`, which is not a conflict.

> **Caution:** Do not substitute Gradle's `exclusiveContent` for content
> filtering. It is a different and stronger policy: it additionally makes the
> declared modules resolvable *only* from that repository, which can change
> first-time resolution results. A consumer **MUST NOT** substitute it, because
> the same sidecar would then resolve differently depending on which mechanism
> the consumer picked.

A consumer **MUST** report repository contributions with distinct prominence in
the record and report, never folded into a generic list, and **SHOULD** surface
them in any standing diagnostic. A consumer **MAY**, as its own policy, require
explicit application approval before adding one to resolution.

**Authenticated repositories.** Set `credentials_required = true` to declare
that the repository is authenticated.

```toml
[[android.contributes.gradle_repositories]]
url = "https://api.mapbox.com/downloads/v2/releases/maven"
reason = """Mapbox does not publish to Maven Central. Access needs a Mapbox token scoped DOWNLOADS:READ, used as the password with username "mapbox"."""
groups = ["com.mapbox"]
credentials_required = true
```

- A producer **MUST NOT** put a credential in a sidecar, in any field, under any
  spelling. A sidecar is package data inside a wheel, readable by everyone who
  installs the distribution.
- A consumer **MUST** reject a credential where one is syntactically
  identifiable — at minimum, URL user-info (`https://user:pass@host/…`) in
  `url` — and **SHOULD** warn on obvious embedded-secret forms elsewhere.
- The application supplies credentials through the consumer's configuration,
  which **MUST** accept them by indirection ([§2.2](#22-how-the-application-answers)).
  `reason` **MUST** say what credential is needed and where to obtain it.
- A consumer **MUST** report an authenticated repository as a requirement and
  **MUST** fail when no credentials are configured, naming the distribution,
  rather than attempting resolution and surfacing a bare `401`.
- A consumer **MUST NOT** write supplied credentials into the generated project
  in any persisted form, into the integration record, or into any diagnostic.

### 6.5 Permissions and features

The permissions and hardware features your code needs at runtime — visible to
the application instead of arriving silently through a dependency's AAR, and
refusable, because the application is accountable for what the installed app can
do.

```toml
[[android.contributes.permissions]]
name = "android.permission.INTERNET"
reason = "Ad delivery"

[[android.contributes.features]]
name = "android.hardware.bluetooth_le"
```

| Field | Applies to | Description |
| --- | --- | --- |
| `name` | both | The canonical manifest string — `android.permission.INTERNET`, never a shorthand. No prefix expansion is defined, which accommodates custom and vendor permissions with no extra rule. |
| `reason` | permission | **RECOMMENDED**. Consumers **SHOULD** carry it into the record and report. |
| `max_sdk_version` | permission | Optional integer. Becomes `android:maxSdkVersion`. |
| `never_for_location` | permission | Optional boolean. Becomes `android:usesPermissionFlags="neverForLocation"`. |

> **Note:** `never_for_location` is unscoped for the same reason `name` takes
> no prefix expansion: a consumer passes it through without interpreting
> which permissions it is meaningful on. Android recognizes it only on
> `BLUETOOTH_SCAN` today, but hard-coding that here would model Android's own
> vocabulary rather than this document's — exactly what the
> [Non-goals](#non-goals) rule out. A producer that sets it elsewhere is
> caught by AGP or Play policy, not by this document.

**Attributes merge least-restrictively, and the merge is reported.** A consumer
**MUST** register a permission with the widest need any distribution stated: an
entry with no `max_sdk_version` defeats one that has it, a lower
`max_sdk_version` gives way to a higher, and `never_for_location` holds only
when **every** declaration of that permission asserts it. The result **MUST**
appear in the record and report with the distributions that produced it.

**Features are never required.** A producer **MUST NOT** set `required` on a
feature. A consumer **MUST** treat every producer-declared feature as
`required = false` and **MUST NOT** promote one on a producer's declaration
alone.

> **Note:** Whether an application *requires* Bluetooth or merely uses it when
> present is a property of the application. A producer promoting a feature to
> required would silently remove the application from devices lacking that
> hardware.

**Application-side suppression.** A consumer **MUST** provide a way for the
application to suppress any contributed permission. A suppressed permission
**MUST** be absent from the **effective merged manifest**, together with any
feature it alone implied, and the suppression **MUST** appear in the record and
report.

The application triggers this in its own `pyproject.toml`
([§2.2](#22-how-the-application-answers)), joined by the permission's `name` —
not `(distribution, id)`, because a suppression addresses the merged manifest,
and two distributions can contribute the same permission name:

```toml
[tool.examplebuild.android]
suppressed_permissions = ["android.permission.INTERNET"]
```

The record and report entry that follows is the *disclosure* of that choice,
not the mechanism for making it — a consumer **MUST** show the suppression
happened; it does not originate one on its own.

> **Note:** Permissions and features are **opt-out**, not opt-in — staged the
> moment a producer declares them, with the report as the default channel and
> `pyproject.toml` touched only to override that default. An exported
> component ([§6.6](#66-manifest-components)) is the opposite: staged **only**
> with explicit approval in `pyproject.toml`, and the build fails without it.
> The asymmetry tracks risk, not category. Lacking a declared permission
> breaks a feature at runtime; an unwanted exported component is a standing
> attack surface reachable by any other app on the device. Requiring an
> accept step for every ordinary permission would make each dependency's
> routine manifest needs manual toil for the application author, which is
> exactly what [Goals](#goals)' automation test exists to avoid.

Omitting a suppressed permission from the generated manifest is not sufficient.
A resolved `.aar` carries its own manifest, which AGP merges, so a permission
the consumer never wrote can still arrive from a dependency — and the permission
a producer declares here is very often the same one its AAR declares. A consumer
**MUST** emit an explicit manifest-merger removal (`tools:node="remove"`) so the
permission is absent from the merged result, and **MUST** report it as
suppressed rather than silently losing the suppression.

Suppression is at the application's own risk: the producer's code may fail or
degrade when a permission it declared is withheld. A consumer **SHOULD** make an
active suppression visible in its standing diagnostics, so the failure stays
traceable to the application's choice.

### 6.6 Manifest components

A producer registers a service, receiver, or activity — its own class, or one
belonging to a declared dependency.

```toml
[[android.contributes.components]]
kind = "service"        # service | activity | receiver
name = "org.example.mypkg.PushService"

[[android.contributes.components]]
kind = "receiver"
name = "com.vendor.sdk.InstallReferrerReceiver"
from_dependency = "com.vendor:sdk"
```

> **Note:** `provider` is deliberately absent. A `<provider>` is invalid without
> `android:authorities`, and an authority must be unique across every
> application on the device, so it is conventionally derived from the
> application ID — which a producer does not know. A producer that needs one
> declares an action ([§5.3](#53-actions)) instead: the application author
> writes the class and its manifest entry directly, where
> `${applicationId}` is available to them the same way it is in any
> hand-written manifest.

**Provenance.** A component's class comes from one of two places, and the entry
states which:

- **Producer source** (no `from_dependency`): `name` **MUST** refer to a class
  the distribution contributes and **MUST** fall under an owned namespace.
- **A declared dependency** (`from_dependency = "group:artifact"`): the value
  **MUST** match the group and artifact of a dependency the same sidecar
  declares, in either form. The owned-namespace rule does not apply. A consumer
  **SHOULD** verify the class exists in the resolved artifact.

Two distributions registering the same component class **MUST** fail, naming
both.

**Foreground services.** Since Android 14 a foreground service must declare what
it is for, and one that starts without a type is refused by the platform.

```toml
[[android.contributes.components]]
kind = "service"
name = "org.example.mypkg.ScreenCaptureService"
foreground_service_type = "mediaProjection"
```

`foreground_service_type` is valid **only** on `kind = "service"`; a consumer
**MUST** reject it elsewhere, naming the distribution. The value is Android's
own, written exactly as the platform defines it, and the vocabulary is open per
[§4.4](#44-unknown-declarations-fail-closed). Android also requires the matching
`FOREGROUND_SERVICE_*` permission, which is an ordinary
[§6.5](#65-permissions-and-features) contribution.

**Export.** Components are registered `android:exported="false"` by default. A
producer **MUST NOT** declare `exported = true` directly. A producer **MAY**
declare `exported_required = true` with a `reason` (**REQUIRED** when present).

A consumer **MUST** treat that as an application requirement: it **MUST NOT**
register the component as exported without explicit application approval, and
**MUST** report the pending requirement, naming the distribution and the
`reason`.

Where approval is absent the consumer **MUST** fail. It **MUST NOT** fall back
to registering the component unexported: the producer has said the component is
useless unless reachable, so a non-exported registration builds an application
that does not work.

**Link targets.** An activity reachable from a browser or another app — an OAuth
redirect receiver, a deep-link target — needs an intent filter. Version 1 models
one stereotyped filter, not the intent-filter grammar.

```toml
  [[android.contributes.components.view_links]]
  scheme = { application_value = "oauth_redirect_scheme" }
  host = "oauth2redirect"
  path_prefix = "/callback"
```

- Valid only on `kind = "activity"` entries that declare
  `exported_required = true`. A consumer **MUST** reject the inconsistent
  combination — a link target that is not exported is unreachable.
- The fields are Android's own `<data>` attribute names in snake case, and the
  set is **open** per [§4.4](#44-unknown-declarations-fail-closed): `port`,
  `mime_type`, `path`, `path_pattern` and `path_suffix` are as declarable as the
  three shown. Only `scheme` is **REQUIRED**.
- Every attribute may take a literal or an inline application value
  ([§5.5](#55-value-kinds)).
- The consumer **generates** the filter: `android.intent.action.VIEW`, the
  `DEFAULT` and `BROWSABLE` categories, and one `<data>` element. Actions and
  categories are not spellable; they are implied by the type.
- The record and report **MUST** show the link data alongside the export.

Verified App Links are **not contributable**. `android:autoVerify` requires an
`assetlinks.json` file on the application's own domain, which is application
infrastructure. State the need as an action ([§5.3](#53-actions)).

**Vendor actions.** Some components receive a vendor-defined event — not a link
a browser opens, but an intent the SDK's own backend or the system delivers
under an action string the vendor defines.

```toml
[[android.contributes.components]]
kind = "service"
name = "org.example.mypkg.MessagingService"

  [[android.contributes.components.intent_filters]]
  action = "com.google.firebase.MESSAGING_EVENT"
```

- Exactly one `action` per filter. No categories and no data element; those
  belong to `view_links`, which models the browser-reachable case.
- Valid **only** on a component that is not exported. A consumer **MUST** reject
  `intent_filters` on an entry that declares `exported_required`, or that also
  declares `view_links`.
- The record and report **MUST** show the action alongside the component.

### 6.7 Shrinker keep patterns

Keep classes R8 — Android's default shrinker, and the ProGuard-compatible
successor to the ProGuard tool it replaced — would otherwise strip or rename:
a producer's own reflectively-reached classes, or a declared dependency's,
without letting any distribution disable shrinking for the application as a
whole.

```toml
[android.contributes.r8]
keep_classes = ["org.example.mypkg.**"]

[[android.contributes.r8.keep]]
pattern = "okhttp3.**"
from_dependency = "com.squareup.okhttp3:okhttp"
```

These are class patterns, **not** raw ProGuard or R8 directives; the consumer
generates the corresponding `-keep class <pattern> { *; }` rules itself. Two
forms, distinguished by whose classes are kept:

- **`keep_classes`** — patterns that **MUST** fall within an owned namespace
  ([§6.1](#61-ownership) rule 3). Containment is computed on dot-separated
  segments.
- **`[[…r8.keep]]`** — a pattern belonging to a declared dependency.
  `from_dependency` **MUST** match a dependency the same sidecar declares. A
  consumer **MUST** evaluate the pattern against the **effective compilation
  classpath** and reject the entry when any class it matches originates outside
  that dependency's resolved artifacts — a listing of archive contents, not a
  parser — naming the distribution, the pattern, and the artifact the stray
  class came from.

A consumer **MUST** apply these only when the application has enabled shrinking.

> **Note:** A pattern's namespace need not match its dependency's Maven group:
> `com.squareup.okhttp3:okhttp` ships classes under `okhttp3.*`. Checking the
> group would reject that legitimate pattern, so the consumer checks the
> resolved artifact instead. The check covers the whole classpath because the
> generated rule applies everywhere in the program, not only inside the named
> dependency.

### 6.8 Manifest meta-data

A `<meta-data>` entry whose value the producer already knows — a vendor flag,
a model list, a class name the SDK loads reflectively.

> **Why this exists:** `<meta-data>` is the one channel Android gives a
> library to read a build-time constant with no application code at all —
> the manifest is already merged from every dependency, so a vendor gets a
> working config channel for the cost of one line, instead of inventing and
> documenting a loader of its own. Firebase Messaging's notification
> defaults, ML Kit's model list, Branch's test-mode flag, and Google Mobile
> Ads' initialization flags are each a fixed constant the producer already
> knows, with zero application-specific judgment involved.

```toml
[[android.contributes.meta_data]]
key = "com.google.mlkit.vision.DEPENDENCIES"
value = "barcode,face"
reason = "Bundles the barcode and face models rather than downloading them on first use"
```

- `key` is the manifest entry's name, written exactly as the vendor code reads
  it. It is **not** scoped by the declaring distribution.
- `reason` is **REQUIRED**. The key is global, its effect is invisible in
  Python, and the report is where an application sees what a transitive
  dependency turned on.
- `value` is a string, integer or boolean, mapped to `android:value` as the
  text verbatim, the digits, or `true`/`false`.
- `<meta-data>` can be nested under `<application>`, where it is global, or
  under a specific component (`<activity>`, `<service>`, `<receiver>`,
  `<provider>`), where the platform hands it only to that component. This
  section writes only the first form. A producer needing the second declares
  an action ([§5.3](#53-actions)) instead, naming the exact `<meta-data>` entry
  and the component it belongs on.

**This shares one key space with [§5.2](#52-values)'s `manifest_meta_data`
delivery.** A key set here and a value delivered there are the same manifest
entry, so both merge together: equal values coalesce with every provenance
record kept, differing values **MUST** fail naming both distributions, and a key
the **application** sets itself is the application's — the consumer keeps that
value and reports the override.

> **Note:** Because an application-scoped `key` is not scoped by distribution
> either, `pyfoo` could name a key belonging to an SDK it doesn't even depend
> on. That isn't a hole: the application's own value for that key always
> wins, no matter who else declares it.

**Resource references.** A `value` **MAY** be a resource reference — anything
beginning `@` or `?`. A producer **MUST NOT** reference one unless the same
sidecar declares an action ([§5.3](#53-actions)) asking the application to
supply it:

```toml
[[android.contributes.meta_data]]
key = "android.accessibilityservice"
value = "@xml/accessibility_config"
reason = "Declares the service's capabilities to the platform"

[[android.requires.application_action]]
id = "accessibility_config_resource"
summary = "Add res/xml/accessibility_config.xml"
instructions = "Create res/xml/accessibility_config.xml with the capabilities MySDK declares..."
acceptance = ["res/xml/accessibility_config.xml exists with the described content"]
```

> **Caution:** Nothing links these two entries structurally. `meta_data` has
> no `id`, and the action's `uses` ([§5.3](#53-actions)) resolves only against
> declared values, not against a contribution like this one — so there is no
> field for either entry to name the other. A consumer cannot check this
> pairing, because an action is prose. This is a producer obligation, and the
> failure when it is broken is an AAPT error naming a missing resource. What
> makes that tolerable is that the `<meta-data>` entry appears in the record
> attributed to the distribution, so the error has a trail back to the
> package that caused it.

### 6.9 Package visibility

Since Android 11, an app cannot see whether another app is installed unless
it declares that need in advance: without a `<queries>` entry naming the
target, `PackageManager` answers "not installed" for it — silently, not as an
error — even when it is actually present. If a producer's bundled code checks
for another app, it declares that check here, so the consumer can add the
`<queries>` entry the check depends on.

A `<queries>` element grants this visibility three ways: by exact package
name, by content-provider authority, or by intent-filter pattern. This
section models the first two, as one contribution:

```toml
[[android.contributes.queries]]
package = "com.google.android.apps.healthdata"
reason = "Health Connect availability check; the client reports it absent without this"
```

- Exactly one of `package` (an application ID) or `provider_authority` (a
  content provider authority) is **REQUIRED**. A consumer **MUST** reject an
  entry declaring both or neither.
- `reason` is **REQUIRED**. This is a producer asking what else is installed on
  the user's device, and the report is where an application sees that a
  transitive dependency does so.
- Entries merge as a **union**. Two distributions naming one package are asking
  for the same visibility.

The third form, `<intent>`, grants visibility by matching an action and data
pattern rather than a name. A producer that needs it declares an action
([§5.3](#53-actions)) instead: the application author adds the
`<queries><intent>...</intent></queries>` block to the manifest directly,
with the same action/data pattern a hand-written `<queries>` entry would use.

> **Note:** There is no veto here, where [§6.5](#65-permissions-and-features)
> has one. A permission is user-visible, policy-relevant, and refusing it leaves
> the application working with less. A `<queries>` entry is none of those:
> removing it does not reduce what the application may do, it makes the
> producer's code quietly get a wrong answer.

## 7. iOS contributions

Material the consumer stages into the generated Xcode project.

| § | Key | Contributes | How conflicts resolve |
| --- | --- | --- | --- |
| [7.1](#71-symbol-prefixes) | `ios.swift_symbol_prefixes` | A declared prefix for contributed Swift type names | N/A — a diagnostic aid, not an enforced claim |
| [7.2](#72-swift-packages) | `ios.contributes.swift_packages` | A SwiftPM package dependency | Locked to the resolved graph; a branch or path dependency **fails** |
| [7.3](#73-source) | `ios.contributes.src` | Raw Swift source, compiled into the application target | N/A — no ownership or collision check |
| [7.3](#73-source) | `ios.contributes.accessed_api_types` | A required-reason API disclosure for contributed source | Union; `reasons` de-duplicated per `type` |
| [7.4](#74-infoplist) | `ios.contributes.info_plist.values` | A scalar `Info.plist` key | Equal values coalesce, differing values **fail**, the application's own value always wins |
| [7.4](#74-infoplist) | `ios.contributes.info_plist.append`, `.skadnetwork_identifiers` | An array-valued `Info.plist` key, or an `SKAdNetworkItems` entry | Union |
| [7.5](#75-python-modules) | `ios.contributes.python_modules` | A Python-extension-module registration (name and init symbol) | Two producers naming the same `name` **fail** |
| [7.6](#76-objective-c-categories) | `ios.contributes.objc_categories` | A request to load Objective-C categories from static libraries | Union; one producer asking is enough |

### 7.1 Symbol prefixes

Contributed Swift compiles straight into the application's single target. iOS
lacks Android's per-package namespace to keep declarations apart.

```toml
[ios]
swift_symbol_prefixes = ["MyPkg"]
```

A producer that contributes Swift source ([§7.3](#73-source)) **SHOULD** do two
things: name every class, struct, enum, and protocol it declares — its
*types*, and in particular their `@objc` runtime names — with a consistent
prefix, and declare that same prefix here.

Xcode's compiler error for this case names the type but not the distribution
that declared it — `error: invalid redeclaration of 'MyPkgFooBar'`. A consumer
**SHOULD** match the named type against each sidecar's declared prefix and
attribute the error to the distribution whose prefix matches, in the build
output and the report, rather than leaving the application author to search
every dependency's source for the name.

**What this does not reach.** Prefixing covers type names and `@objc` runtime
names only — not file-scope functions, global constants, or extension members. A
contributed file declaring `let ui_scale`, `func invertedHeight(_:)`, or
`extension Double { var retinaScaled }` puts all three into the application
target's scope under exactly the names it wrote, and a consumer has no way to
check for it.

> **Note:** This guidance deliberately does not live in an `owns` table. One
> shared module and globally-scoped `@objc` names leave a consumer nothing to
> enforce, where [§6.1](#61-ownership) has a namespace it can hold exclusively.
> A producer that ships its Swift as a package ([§7.2](#72-swift-packages))
> avoids the problem entirely: a package compiles as its own module, so its
> symbols are already isolated. `@objc` names are the exception either way —
> they register in the Objective-C runtime's single flat namespace whatever
> module declared them.

### 7.2 Swift packages

A Swift package — a vendor's, or one the producer authored itself: resolved by
SwiftPM, locked by the integration record, and compiled as its own module
rather than into the application's.

```toml
[[ios.contributes.swift_packages]]
name = "Shim"
url = "https://github.com/example/shim"
requirement = { exact = "1.2.3" }
products = ["Shim"]
```

`name` is a local handle, **unique within the sidecar**. [§7.5](#75-python-modules)
refers to packages by it, so two entries sharing a `name` are invalid even when
their URLs differ; a consumer **MUST** reject that, naming the distribution.

`requirement` **MUST** be exactly one of:

| Form | Meaning |
| --- | --- |
| `{ exact = "1.2.3" }` | That version only |
| `{ from = "1.2.0" }` | SwiftPM's up-to-next-major range |
| `{ revision = "<commit>" }` | A specific commit |

A `branch` requirement **MUST NOT** appear in a distribution published to a
package index; a consumer **MUST** reject it, naming the distribution.

**The whole graph is locked, not only what the sidecar names.** A consumer
**MUST** record the fully resolved Swift package graph, transitives included, in
the integration record, and **MUST** resolve from that record on subsequent
builds until a new resolution is accepted.

**Record the resolved revision, not only the resolved version.** A version is a
tag, and a tag can be moved; the commit identifies the source that was built.
`Package.resolved` records both, and the integration record **MUST** preserve
both for every package in the graph — for `exact` and `revision` requirements as
much as for `from`.

> **Note:** This is why [§7.2](#72-swift-packages) needs no per-artifact
> checksum where [§6.3](#63-gradle-dependencies) does. A recorded revision *is*
> content identity: a commit names the tree it contains. A Maven version names
> no content, which is why the Android side must add a hash to get the same
> guarantee. The asymmetry is in the ecosystems.

**Binary targets are where that reasoning stops.** A Swift package may vend a
prebuilt binary target, whose bytes are fetched from a URL the package names and
which the package's own revision does not cover. SwiftPM models this already: a
remote `binaryTarget` carries a `checksum`. A consumer **MUST** record that
checksum for every binary target in the resolved graph, **MUST** verify it on
subsequent builds, and **MUST** fail on a mismatch, naming the package and the
declaring distribution. A consumer **SHOULD** warn when a remote binary target
carries no checksum, since the record then pins nothing.

**The rules above bind what the sidecar declares; the resolved graph is where
they are enforced.** The sidecar entry constrains only the package the
producer names directly — its `exact`, `from`, or `revision`. That package's
own `Package.swift` can declare its transitive dependencies however it wants,
and the sidecar entry says nothing about those; resolving the graph is the
only point where they become visible.

A **path** dependency is the case this actually catches: it points at a
location on one machine's filesystem, which will not exist on anyone else's,
and SwiftPM has no rule against declaring one. A consumer **MUST** reject a
resolved graph containing a path dependency anywhere in it, naming the
distribution that declared the top-level package and the offending transitive
package.

A **branch** dependency, by contrast, is close to unreachable in practice:
SwiftPM itself refuses to resolve a version-pinned package (which is what
`exact` or `from` produces) against a transitively branch-pinned one, so a
producer would have to encounter a vendor package that violates SwiftPM's own
rules to hit this. This document still names it explicitly, both because
that guarantee is SwiftPM's to keep, not this specification's, and because it
gives the record and the report the same vocabulary either way.

**You may declare your own repository here.** A distribution whose native half
lives in a Swift package it also publishes is an expected shape. Two
consequences:

- The declared package **MUST** be resolvable in the form declared. A repository
  with no tags cannot use `exact` or `from`, leaving `revision` as the only
  valid option.
- Your distribution's version does **not** pin the native half, and the record's
  per-file hashing does not reach it. A consumer's record **MUST** make that
  distinction visible rather than implying the distribution's version covers
  both.

Swift Package Manager is the **RECOMMENDED** channel for anything larger than a
few glue files.

### 7.3 Source

Contributed Swift lands in the application's own compilation scope under exactly
the names it was written with, which is why this is for shims and
[§7.2](#72-swift-packages) is for everything else.

```toml
[ios.contributes.src]
swift = ["swift"]
```

The consumer stages `.swift` files recursively and ignores other files. Path
rules are [§4.1](#41-location-and-name)'s. This is intended for small `@objc`
shims whose value is versioning atomically with the Python half; it **SHOULD
NOT** be used for a library.

**The scope restriction is narrow and load-bearing.** Every declaration a
contributed file makes at file scope is exposed to the application's own code —
free functions, global constants, protocols, and extension members on types the
producer does not own — and [§7.1](#71-symbol-prefixes)'s guidance reaches none
of them. A producer whose Swift declares anything at file scope beyond prefixed
types **SHOULD** ship a Swift package instead, where those declarations are
confined to its own module.

**Required-reason APIs.** Contributed Swift compiles into the application's
target, so by Apple's rule it *is* application code: an SDK's own privacy
manifest reports the SDK's usage, and nothing reports code that has no target of
its own. A Swift package ([§7.2](#72-swift-packages)) carries its own
`PrivacyInfo.xcprivacy` in its resources, which Apple's tooling reads
automatically; raw source staged here has no such carrier, so this table is
the sidecar's substitute for the manifest a package would otherwise bring. A
producer declares what its contributed source touches, and the consumer — the
only thing that ever writes the real file — merges the declaration into the
application's `PrivacyInfo.xcprivacy`.

```toml
[[ios.contributes.accessed_api_types]]
type = "NSPrivacyAccessedAPICategoryUserDefaults"
reasons = ["CA92.1"]
reason = "Caches the last selected region so the shim can restore it"
```

- This table is valid **only** where the same sidecar contributes Swift under
  `[ios.contributes.src]`. A consumer **MUST** reject it otherwise, naming the
  distribution and directing the producer to [§7.2](#72-swift-packages) — a
  Swift package carries its own `PrivacyInfo.xcprivacy` in its resources, which
  is both the better answer and the one Apple documents.
- `type` and `reasons` are **Apple's canonical strings**, written exactly as
  Apple defines them. No expansion or shorthand is defined.
- `reason` is **RECOMMENDED** prose. Apple's codes are opaque by design, and the
  record is where an application reads what its dependencies claim.
- Entries merge as a **union**: the application's own entries first, then each
  distribution's in normalized distribution-name order, with the `reasons` for
  one `type` unioned and de-duplicated.

> **Caution:** A consumer cannot verify this declaration. Nothing checks that
> the declared categories match what the contributed Swift actually calls, and
> nothing could without implementing Apple's static analysis. An omission is
> invisible at build time and surfaces as an App Store rejection of the
> application, weeks later, naming an API rather than a package. Recording the
> claim is what makes the omission attributable after the fact.

### 7.4 Info.plist

Most `Info.plist` keys an SDK asks for are ordinary configuration — a feature
flag, a URL scheme to recognize, a value it reads at runtime — and this
section covers those. Two kinds are excluded on purpose, and covered later in
this section instead: a key like `UIBackgroundModes` that would grant the
application a new capability, and a key like `UIRequiredDeviceCapabilities`
that would restrict which devices may install it at all. Both change what the
application *is*, not just how an SDK behaves within it, so a producer states
those as an action ([§5.3](#53-actions)) instead of setting the key directly.

```toml
[ios.contributes.info_plist.values]
CADisableMinimumFrameDurationOnPhone = true

[ios.contributes.info_plist.append]
LSApplicationQueriesSchemes = ["examplescheme"]
```

Two contribution modes, by shape:

- **`values`** — scalar keys, set verbatim. A consumer **MUST** fail on a key
  that collides with one it manages itself — the identity and version keys it
  derives from the application's own project settings, such as
  `CFBundleIdentifier`, `CFBundleShortVersionString`, `CFBundleVersion`, and
  `MinimumOSVersion` — and on two distributions setting the same key to
  different values, naming the distributions. Two distributions
  setting the same key to the **same** value coalesce, preserving both
  provenance records. A key the **application** also sets is the application's:
  the consumer **MUST** keep the application's value and report the override.
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

A consumer **MUST** reject any other TOML type — offset and local date-times,
and inline or nested tables — naming the distribution and the key. An array
**MUST** be homogeneous: a mixed-type array has no unambiguous plist form.

**Usage descriptions are not contributable.** A consumer **MUST** reject any
`values` key whose name ends in `UsageDescription`, or which is otherwise a
purpose string, naming the distribution and directing the producer to
[§5.2](#52-values)'s `usage_description` kind. That text is user-facing,
localized, and read by App Store review; it is a claim about what *the
application* does with the data, and a `values` entry is the one place a
producer could write it by accident.

**Capability keys are not contributable either.** A consumer **MUST** reject
these keys in `values` and in `append` alike, naming the distribution and
directing the producer to state an action ([§5.3](#53-actions)):

| Key | What a producer's entry would do |
| --- | --- |
| `UIBackgroundModes` | grant the application background execution |
| `UIRequiredDeviceCapabilities` | **restrict installation** — silently remove the application from devices lacking that hardware |

The list is closed, and a minor revision may extend it. What puts a key on it is
that a producer's entry **changes what the application may do, or who may
install it** — not that the key is array-valued. `LSApplicationQueriesSchemes`
grants nothing and stays an ordinary contribution.

**A key delivered as a value is consumer-managed.** A producer contributing the
same `Info.plist` key through `values` that another declares through
[§5.2](#52-values)'s `info_plist` kind **MUST** fail, on the collision rule
above.

**Dictionary-valued keys are excluded by design.** The structured
cases examined are better served by a narrower primitive: `NSExtension` is
generated from a declared extension target, and `NSAppTransportSecurity` depends
on what the application loads and is not the producer's to declare at all. A
general form would hand producers the ability to write arbitrary structured
application configuration.

**`skadnetwork_identifiers` is the one narrower primitive that case needed.**
`SKAdNetworkItems` is an array of single-entry dictionaries, one per ad network,
which every advertising and mediation SDK requires and which runs to around a
hundred entries for a mediated integration.

```toml
[ios.contributes.info_plist]
skadnetwork_identifiers = ["su67r6k2v3.skadnetwork", "4fzdc2evr5.skadnetwork"]
```

- Each entry is an ad network identifier: lowercase, and ending in
  `.skadnetwork`, which is the form Apple defines. A consumer **MUST** reject an
  entry that is not, naming the distribution and the entry.
- The consumer renders `SKAdNetworkItems`, one `SKAdNetworkIdentifier`
  dictionary per identifier. A producer never writes the dictionary itself.
- Merging follows `append` exactly.
- A consumer **MUST** reject `SKAdNetworkItems` offered through `values` or
  `append`, naming the distribution and directing the producer here.

> **Note:** A mistyped identifier does not fail. It sits in the plist, matches
> no network, and silently loses attribution for that network's installs — a
> quiet wrong answer of exactly the kind this convention exists to turn into a
> build-time diagnostic. That is what the two validation conditions buy.

### 7.5 Python modules

Registers a Swift package that **implements** a Python extension module — it
exposes a `PyInit_*` entry point meant to be reached with `import name` —
rather than one that is merely Swift code the application happens to use. The
package is built as its own module ([§7.2](#72-swift-packages)) and linked
into the application binary, not into a `.so` the ordinary import machinery
would find on disk, so this registration is what lets `import name` succeed
at all: without it, the build still succeeds but the `import` fails.

> **Note:** "Swift package" here means a SwiftPM package — a `Package.swift`
> manifest and a resolved product — not Swift source specifically. SwiftPM
> targets may be plain C or Objective-C, so a producer whose extension module
> is generated by Cython, or hand-written in C, can register it the same way
> by wrapping the generated C in a minimal `Package.swift`. The requirement is
> "resolved through §7.2," not "written in Swift."

```toml
[[ios.contributes.python_modules]]
name = "web_views"
swift_package = "PyWebViews"
init = "PyInit_WebViews"      # optional; defaults to PyInit_<name>
```

The package is linked into the application binary rather than loaded from a
shared object, so the ordinary import machinery never sees it. This table
registers it with the interpreter — a name and a symbol, nothing executed at
build time.

- `swift_package` **MUST** name a package the same sidecar declares. A module
  cannot be registered without the code that implements it.
- `name` is the name Python imports, and **MUST** be a single ASCII Python
  identifier: `[A-Za-z_][A-Za-z0-9_]*`. **Dotted names are not permitted.** A
  dotted name would require a parent package object with its own `__path__`
  for the submodule to resolve under, and this table has no mechanism to
  create one — it registers one flat name against one init function, nothing
  else. Submodule registration is an unsupported capability, not a
  deferred one.
- `init` names the module's initialization function and defaults to
  `PyInit_<name>`. When supplied it **MUST** be a valid C identifier. It exists
  because the three names need not agree: a package `PyWebViews` may implement a
  module whose Swift type is `WebViews` and whose Python name is `web_views`.
- Two distributions registering the same `name` **MUST** fail, naming both.
- A consumer **MUST** make the module importable from first use — in practice,
  registering it before interpreter initialization.

A consumer **MUST** exclude both `<name>.py` and `<name>.pyi` from the Python
payload it assembles for the device, for every module this table registers.

> **Note:** Producers ship stubs of the same name for type checking off device.
> A `.py` stub would otherwise sit on `sys.path` as a silent fallback: a
> registration that failed or was skipped would surface not as `ImportError` but
> as an application that imports successfully and does nothing. The `.pyi` is
> excluded with it because it is inert on device and its presence invites the
> `.py` back.

### 7.6 Objective-C categories

An Objective-C **category** adds methods to an existing class without
subclassing it — a common way for an SDK to extend a class like `NSString` or
`UIView`. A category's methods are not referenced by name anywhere the linker
can see, so when the SDK ships as a static library, the linker silently
drops them; the application builds and links, then crashes at runtime the
first time that method is actually called. The fix is a linker setting on the
*application's own build target* — a producer has no way to set it from
inside its own package, and the application author has no way to know it is
needed, since nothing in their own code points at the missing method.

```toml
[ios.contributes]
objc_categories = true
```

- A consumer **MUST** link the application target so that Objective-C categories
  in statically linked libraries are loaded. In Apple's toolchain that is the
  `-ObjC` flag; this key names the **effect**, not the flag, so a consumer whose
  toolchain spells it differently is still conforming.
- Entries merge as a **union**: one producer asking is enough.
- A consumer **MUST** report it in the record, naming the distributions that
  asked. It changes how the whole application links, and the application is
  entitled to see which dependency caused that.
- There is **no veto**, for [§6.9](#69-package-visibility)'s reason: withholding
  it does not reduce what the application may do, it makes the producer's code
  fail at runtime with a message pointing nowhere.

> **Note:** In practice this surfaces as `unrecognized selector sent to
> instance` — Apple's generic message for a missing method — with nothing in
> it naming the library, let alone the Python distribution that brought it in.
>
> SwiftPM independently rejects a package setting raw linker flags on itself
> when consumed by version, which is a second, mechanical reason a producer
> could not set this even if the setting belonged to its own package rather
> than the application's.
>
> The cost of granting it is that loading every category also loads the
> classes carrying them, so the binary grows by whatever the static libraries
> contain — which is why this is
> declared by the producers that need it rather than switched on for everyone.

## 8. Consuming tool requirements

Everything a **consumer** must do: the build tool that reads sidecars and
generates the native project, as distinct from the application it builds or the
distributions it reads.

This section restates §§2–7 and [§9](#9-recording-and-review) as a checklist. It
introduces no obligation those sections do not already carry. **Where the two
differ, the body governs**, and the discrepancy is a defect worth reporting.

Numbering is stable: a later revision appends rather than renumbering, so a
conformance claim can name the requirements it meets.

### 8.1 Three outcomes, and no others

What a consumer finds falls into exactly three kinds, named here so that two
implementations classify the same condition the same way.

| Outcome | Meaning | Produced by |
| --- | --- | --- |
| **blocking** | the build **MUST NOT** proceed | every numbered requirement below that says *fail* |
| **advisory** | reported; the build proceeds | the **SHOULD** list in [§8.4](#84-advisory-obligations) |
| **recorded** | written to the integration record, and not reported as a problem at all | an unsatisfied *conditional* requirement ([§5.4](#54-how-a-requirement-is-satisfied)), and the disclosure [§9](#9-recording-and-review) requires |

The third is the one an implementation is likely to lack. [§5.4](#54-how-a-requirement-is-satisfied)
and [§9](#9-recording-and-review) both require material that neither stops the
build nor warns about anything. A consumer with only two levels files it under
one of them and is wrong either way: as a warning it becomes noise to be
silenced, and as nothing it stops being the durable disclosure that was the
point.

### 8.2 Thematic index

| Theme | Requirements |
| --- | --- |
| Discovery and the sidecar | 1–9 |
| Answering, reporting, and scaffolding | 10, 11, 20, 21 |
| Never satisfy a requirement on the producer's authority | 12, 13, 14, 15, 16 |
| Composition between distributions | 17, 22, 26, 30, 33 |
| Generated project material | 23, 24, 25, 27, 28, 29, 31, 32, 34, 35 |
| Recording, disclosure, attribution | 36, 37, 38, 39, 40, 41, 42 |
| The bootstrap | 43, 44 |
| Everywhere | 18, 19, 45, 46 |

### 8.3 A conforming consumer MUST

**Discovery and the sidecar**

1. Restrict candidate producers to the application's resolved dependency
   closure, and never accept contributions from a distribution outside it,
   whatever else is installed ([§3.2](#32-resolution)).
2. Discover by iterating the entry-point group, ignoring entry-point names, and
   fail when one distribution declares more than one entry
   ([§3.3](#33-iterate-do-not-look-up-by-name), [§3.4](#34-one-entry-per-distribution)).
3. Never import the producing package or any module of it, and never execute any
   content of a sidecar ([§2.1](#21-design-principles), [§3.2](#32-resolution)).
4. Read the sidecar and every resource it references through the distribution's
   metadata and file-resource interface, and fail naming the distribution when
   a resource cannot be materialized or read ([§3.2](#32-resolution)).
5. Reject a resource that escapes the sidecar directory after normalization, and
   reject a symlinked resource ([§4.1](#41-location-and-name)).
6. Exclude the sidecar directory, and every resource under it, from any Python
   payload it assembles for the device ([§4.1](#41-location-and-name)).
7. Enforce the contract version gate including the minor, reject a sidecar that
   under-declares, and be able to state the contract it implements
   ([§4.3](#43-contract-version)).
8. Fail closed on an unrecognized key in a platform table it is building, and on
   a value from a closed vocabulary it does not implement, substituting no
   default ([§4.4](#44-unknown-declarations-fail-closed)).
9. Fail when building for a platform a sidecar's `platforms` key omits, naming
   the distribution and how it entered the closure
   ([§4.5](#45-platform-support)).

**Answering, reporting, and scaffolding**

10. Provide a way for the application to supply a value, acknowledge an action,
    suppress a contributed permission, approve an exported component, and supply
    repository credentials — each joined by the key
    [§2.2](#22-how-the-application-answers) names — and accept a build-time
    credential **by indirection** rather than only as a literal in a committed
    file ([§2.2](#22-how-the-application-answers)).
11. Report every unmet requirement, naming the distribution, the `reason`, and —
    for an action — the `summary`, `instructions` and `acceptance`
    ([§2.3](#23-what-the-consumer-generates)).

**Never satisfy a requirement on the producer's authority**

12. Fail when the application's configuration is below a declared floor, and
    never raise it to satisfy one ([§5.1](#51-build-floors)).
13. Fail when a declared value is unsupplied, and never treat a scaffolded
    placeholder as a supplied value
    ([§5.2](#52-values), [§5.4](#54-how-a-requirement-is-satisfied)).
14. Fail when an unconditional action is unacknowledged; record an unsatisfied
    conditional requirement without failing; and take an acknowledgement as
    satisfying the requirement
    ([§5.3](#53-actions), [§5.4](#54-how-a-requirement-is-satisfied)).
15. Never treat its own observation of the application's project as satisfaction
    of an action ([§5.4](#54-how-a-requirement-is-satisfied)).
16. Never write an entitlement, a capability, a bundle file, a build target, or
    any other application-owned artifact because a producer asked for it
    ([§2.1](#21-design-principles)).

**Composition between distributions**

17. Fail when two values target the same `(kind, key)` with different content,
    naming both distributions, and coalesce them when the content is equal
    ([§5.2](#52-values)).
18. Name the contributing distribution in **every** diagnostic it emits about
    declared material ([§2.1](#21-design-principles)).
19. Ignore entry-point groups for other major versions entirely, rather than
    attempting to read them ([§10](#10-versioning)).
20. Never modify a file the application owns unless the application asked it to,
    and never scaffold an action's acknowledgement other than commented out
    ([§2.3](#23-what-the-consumer-generates)).
21. Never execute, apply, or fetch anything named by `instructions` or
    `acceptance`, and include both in the record's hashed inputs
    ([§5.6](#56-instructions-and-acceptance-criteria), [§9.3](#93-hashed-inputs)).
22. Reject a `uses` entry naming no value the same sidecar declares, and report
    two actions sharing a `slot` together, naming both distributions, without
    interpreting the slot ([§5.3](#53-actions), [§5.7](#57-slots)).

**Generated project material**

23. Enforce every ownership rule, computing containment on dot-separated
    segments, and fail on a collision naming the distributions responsible
    ([§6.1](#61-ownership)).
24. Compile contributed source with the application's own toolchain, force UTF-8
    for `.java`, and exclude the source from any Python payload
    ([§6.2](#62-source)).
25. Reject a Gradle dependency declaring both or neither of `coordinate` and
    `module`, reject a changing or unbounded version, reject a processor
    configuration, never convert a declared version into a `strictly`
    constraint, and show requested against resolved where they differ
    ([§6.3](#63-gradle-dependencies)).
26. Lock the fully resolved native graphs — Gradle and SwiftPM alike,
    transitives included — resolve from the record thereafter, record a checksum
    per Maven artifact and per Swift binary target, verify both on subsequent
    builds, and fail on a mismatch naming the artifact and the distribution
    ([§6.3](#63-gradle-dependencies), [§7.2](#72-swift-packages)).
27. Restrict a contributed repository to its declared groups or modules, reject
    two whose scopes overlap at different URLs, never substitute an exclusivity
    mechanism for content filtering, report repositories with distinct
    prominence, reject a syntactically identifiable credential, fail when an
    authenticated repository has no credentials configured, and never persist a
    supplied credential anywhere ([§6.4](#64-maven-repositories)).
28. Merge permission attributes least-restrictively and report the merge;
    register every producer-declared feature `required = false`; and honor a
    suppression in the **effective merged manifest**, emitting a merger removal
    where a resolved dependency contributes the same permission
    ([§6.5](#65-permissions-and-features)).
29. Enforce component provenance and uniqueness, reject `foreground_service_type`
    on a non-service, fail when a component declaring `exported_required` has no
    application approval — never falling back to an unexported registration —
    and reject `view_links` or `intent_filters` in an invalid combination
    ([§6.6](#66-manifest-components)).
30. Validate `view_links` and generate their filters, including the action and
    the `DEFAULT` and `BROWSABLE` categories, and show the link data and each
    `intent_filters` action in the record
    ([§6.6](#66-manifest-components)).
31. Validate shrinker keep patterns against owned namespaces, reject a
    `from_dependency` keep whose pattern matches any class on the effective
    classpath originating outside that dependency's resolved artifacts, and
    apply keeps only when the application has enabled shrinking
    ([§6.7](#67-shrinker-keep-patterns)).
32. Merge contributed `meta_data` with [§5.2](#52-values)'s delivery as one key
    space, keeping and reporting the application's own entry where it sets the
    key, and reject a `queries` entry declaring both or neither of `package` and
    `provider_authority` ([§6.8](#68-manifest-meta-data), [§6.9](#69-package-visibility)).
33. Reject two Swift packages sharing a `name`, reject a `branch` requirement,
    reject a resolved graph containing a path dependency, and make visible in
    the record that a self-declared package is not pinned by the distribution's
    own version ([§7.2](#72-swift-packages)).
34. Reject `accessed_api_types` from a sidecar contributing no Swift source, and
    merge what it declares into the application's `PrivacyInfo.xcprivacy` in the
    order [§7.3](#73-source) fixes.
35. Enforce [§7.4](#74-infoplist)'s TOML-to-plist mapping, fail on a key it
    manages itself or on two distributions setting one key differently, keep and
    report the application's own value, reject usage-description and capability
    keys, validate SKAdNetwork identifiers, and render `SKAdNetworkItems` only
    from `skadnetwork_identifiers`.
36. Register declared Python modules against a Swift package the same sidecar
    declares, reject a dotted or non-identifier `name`, fail on a duplicate
    module name, make each module importable from first use, and exclude
    `<name>.py` and `<name>.pyi` from the Python payload
    ([§7.5](#75-python-modules)).
37. Link the application target so Objective-C categories in statically linked
    libraries are loaded when any distribution asks, and report it naming the
    distributions that asked ([§7.6](#76-objective-c-categories)).

**Recording, disclosure, attribution**

38. Compute the resolution, compare it against the last accepted record, report
    the delta, require explicit acceptance — including on the first build — and
    update the record only on acceptance ([§9.1](#91-the-lifecycle)).
39. Report the distribution, how it entered the closure, and the delta, keeping
    repository contributions, artifact-sourced material, unmet against
    conditional requirements, and **staged against remaining** distinct, for one
    platform's build ([§9.2](#92-the-report)).
40. Record a SHA-256 per input file, keyed by normalized relative path
    ([§9.3](#93-hashed-inputs)).
41. Record and report every permission, feature and component declared by
    resolved Android artifacts' own manifests, attributed to the artifact;
    override a resolved artifact's `required="true"` feature unless the
    application declares it; and report a resolved artifact's exported
    components with contribution-level prominence
    ([§9.4](#94-what-resolved-artifacts-bring-with-them)).
42. Never write an application-supplied credential or secret into the record, a
    report, or a diagnostic ([§9.5](#95-secrets-are-never-recorded)).
43. Make every row of [§9.6](#96-what-a-record-must-contain) recoverable from
    the record, including every value and action with its state.
44. Detect packaging collisions between the resolved artifacts of different
    distributions, resolve only packaging metadata on its own authority, fail on
    any other colliding file the application has not chosen between, and record
    every collision against the distributions responsible
    ([§9.7](#97-packaging-collisions)).

**The bootstrap**

45. Make the Android activity its bootstrap generates an
    `androidx.activity.ComponentActivity` or a subclass
    ([§2.4](#24-obligations-on-the-consumers-bootstrap)).
46. Provide a documented means for application code to observe a URL callback
    delivered to the bootstrap's `application(_:open:options:)`, rather than
    consuming it ([§2.4](#24-obligations-on-the-consumers-bootstrap)).

### 8.4 Advisory obligations

These carry stable identifiers of their own, referenced as 8.S1 and so on, so a
conformance claim can name the ones it meets. They are reported, never blocking.

A conforming consumer **SHOULD**:

| | Obligation | |
| --- | --- | --- |
| **S1** | Warn about a top-level *table* it does not recognize at all | [§4.4](#44-unknown-declarations-fail-closed) |
| **S2** | Say which values of a closed vocabulary it implements, so a producer can tell an unsupported declaration from a misspelled one | [§4.4](#44-unknown-declarations-fail-closed) |
| **S3** | Report the contract it implements where a person can see it | [§4.3](#43-contract-version) |
| **S4** | Scaffold declared placeholders into the application's own configuration | [§2.3](#23-what-the-consumer-generates) |
| **S5** | Warn on a single-label owned namespace | [§6.1](#61-ownership) |
| **S6** | Verify that a `from_dependency` component class exists in the resolved artifact | [§6.6](#66-manifest-components) |
| **S7** | Carry a permission's `reason` into the record and report | [§6.5](#65-permissions-and-features) |
| **S8** | Make an active permission suppression visible in standing diagnostics | [§6.5](#65-permissions-and-features) |
| **S9** | Surface contributed repositories in standing diagnostics | [§6.4](#64-maven-repositories) |
| **S10** | Attribute a duplicate-symbol error to the distribution whose declared prefix matches | [§7.1](#71-symbol-prefixes) |
| **S11** | Warn when a remote binary target carries no checksum | [§7.2](#72-swift-packages) |
| **S12** | Report the fully merged Android manifest's delta, beyond the per-artifact declarations requirement 41 requires | [§9.4](#94-what-resolved-artifacts-bring-with-them) |
| **S13** | Report consumer ProGuard rules embedded in a resolved `.aar` | [§9.4](#94-what-resolved-artifacts-bring-with-them) |

> **Note:** A consumer that stops at per-artifact declarations rather than
> implementing S12 **MUST** say so in its own documentation
> ([§9.4](#94-what-resolved-artifacts-bring-with-them)). An advisory obligation
> quietly skipped is how a conformance claim overstates itself.

## 9. Recording and review

The integration record serves two purposes: **review** of the native surface an
application is acquiring, and **integrity** of the inputs and resolved artifacts
that produced it. Per-file hashes, per-artifact checksums, and failing on drift
are what make the second more than a claim.

### 9.1 The lifecycle

1. **Compute** the integration resolution — the effective set from the
   application's dependency closure, including locked native dependency graphs.
2. **Compare** it against the last accepted integration record.
3. **Report the delta**, naming each distribution and how it entered the closure.
4. **Fail, or require explicit acceptance** — a re-lock, a flag, a committed
   record; the consumer's workflow decides the form.
5. **Update the record** only on acceptance.

**The first build is step 4, not an exemption.** When no accepted record exists,
every contribution is new, and a consumer **MUST** require the same explicit
acceptance it would require for a change — reporting the whole effective set
rather than silently writing a record and proceeding. A single bootstrap action
covering the initial set satisfies this; treating "no record yet" as implicit
approval does not, because the first build is the one where an application
acquires *all* of its inherited native surface at once.

### 9.2 The report

A report **MUST** carry three things: the distribution, **how it entered the
dependency closure**, and the delta. It covers **one platform's build**, since
that is what a consumer computes ([§2.2](#22-how-the-application-answers)).

```
android build — 12 contributions staged, 1 value and 2 actions outstanding

analytics-shim 2.1.0  (via some-ui-lib)
  + permission   android.permission.ACCESS_FINE_LOCATION  ("optional BLE discovery")
  + feature      android.hardware.location.gps  (required=false)

map-sdk 4.1.0  (direct dependency)
  ! REPOSITORY  https://maven.example.com/releases  → groups: com.example.maps
                authenticated — no credentials configured        ✗ BLOCKING
  + dependency  com.example.maps:android:4.1.0
  + from com.example.maps:android:4.1.0 (resolved artifact manifest):
      + permission  com.example.permission.MAPS_ID
  ! value       maps_api_key → meta-data com.example.maps.API_KEY
                placeholder not replaced                          ✗ BLOCKING
  ! action      maps_config   "Add maps-config.json to your assets"
                not acknowledged                                  ✗ BLOCKING
  ~ action      map_deep_links  "Register your link domain as a verified App Link"
                conditional, unresolved
```

The middle element matters most for the case that motivates the requirement: a
transitive dependency the application author has never heard of.

The shape of that second entry is normative in four respects:

| Requirement | Why |
| --- | --- |
| A repository contribution is set apart, never folded into a list | [§6.4](#64-maven-repositories) |
| Contributions arriving from a **resolved artifact's own manifest** are attributed to that artifact, not to the distribution that declared the coordinate | [§9.4](#94-what-resolved-artifacts-bring-with-them) |
| An unmet requirement is distinguished from an unresolved **conditional** one | [§5.4](#54-how-a-requirement-is-satisfied) — the first blocks the build, the second is guidance |
| **What was staged is distinguished from what remains** | the whole point of this convention: the application author needs to see the boundary between work that was done for them and work that is theirs |

No format is mandated. A report that collapses these distinctions has not
reported them.

A requirement belonging to the platform **not** being built belongs in neither
the report nor the record. An `[ios]` table is outside an Android build's
concern ([§4.4](#44-unknown-declarations-fail-closed)), and a consumer that
failed an Android build over an unmet iOS requirement would be failing it for
something that build never had to satisfy.

### 9.3 Hashed inputs

Inputs are hashed for **every** producer, not only path and editable installs.
The record **MUST** include a SHA-256 per file, keyed by normalized relative path
(forward slashes, relative to the sidecar directory), covering `native.toml` and
every resource it references.

The wheel's own hash pins the distribution, but the useful identity for this
protocol is the material the integration was computed from: per-file hashes let
a diagnostic say `java/Bridge.java changed`, not merely "the producer's hash
changed."

> **Note:** This is also what bounds the `instructions` and `acceptance` channel
> ([§5.6](#56-instructions-and-acceptance-criteria)). Both are inline in
> `native.toml`, so hashing that file covers them: text a human or an agent may
> act on cannot change between versions without appearing as a delta the
> application reviews.

### 9.4 What resolved artifacts bring with them

A resolved dependency carries native effects of its own. A Maven coordinate can
resolve to an `.aar` whose manifest AGP merges into the application's; a Swift
package can vend binary targets.

**For Android**, a consumer **MUST** include in the record and report every
`<uses-permission>`, `<uses-feature>`, and manifest component declared by the
**manifests of the resolved artifacts themselves**, beyond those declared by
sidecars and the application, attributed to the artifact that declares each one.
The resolved graph is already required by [§6.3](#63-gradle-dependencies), and
this obligation is bounded by it: read each resolved `.aar`'s own
`AndroidManifest.xml`.

A consumer **SHOULD** additionally report the fully merged manifest's delta.
That is a larger claim — it depends on merge semantics rather than on what each
artifact declares — and where a consumer stops at the artifact manifests, its
documentation **MUST** say that the record's coverage is per-artifact
declarations rather than the merged result.

**For iOS**, reporting the native effects of a Swift package's binary targets
remains a **SHOULD**: there is no equivalent merge step, and no comparable
manifest to read.

**Native dependencies are a trust boundary, and two rules cross it.** The
restrictions in §§5–7 constrain effects *authored by the sidecar*. An `.aar` may
carry a manifest, resources, JNI libraries and consumer ProGuard rules; a Swift
package may vend binary targets. Those artifacts remain subject to their own
ecosystem's authority model, and this convention provides **attribution and
review** for their native effects, not restriction. Policing arbitrary library
code is not attempted and would not succeed.

Two exceptions exist, because otherwise moving material out of the sidecar and
into an `.aar` would launder past a rule this document treats as
security-sensitive:

- A resolved artifact declaring `<uses-feature required="true">` **MUST NOT** be
  allowed to silently make hardware mandatory. The consumer **MUST** report it,
  and **MUST** override it to `required="false"` unless the **application
  itself** independently declares that feature required. Silently shrinking an
  application's device reach is the same harm whoever authors it.
- A resolved artifact declaring an **exported component** **MUST** be reported
  with the same prominence as a contributed one
  ([§6.6](#66-manifest-components)), so the application sees every externally
  reachable surface it is acquiring, whatever declared it.

Consumer ProGuard rules embedded in a resolved `.aar` **SHOULD** likewise be
reported: they are appended to the application's shrinker configuration without
passing through [§6.7](#67-shrinker-keep-patterns)'s scoping.

> **Note:** The Android half is a **MUST** because it is the case this section
> exists for — a permission arriving through a transitive Python dependency the
> author has never heard of, carrying obligations beyond the build.
> `com.google.android.gms.permission.AD_ID` comes from an ads AAR and pulls the
> application into a Play Console data-safety declaration. [§11](#11-out-of-scope)
> also rests on it: an `.aar` embedded in a wheel is excluded there because its
> manifest merges with no attribution, while one reached through a declared
> coordinate is permitted because this section surfaces it — a justification
> that cannot stand on an optional feature.

### 9.5 Secrets are never recorded

A consumer **MUST NOT** write an application-supplied credential — or any value
the application supplies as a secret — into the integration record, into a
report, or into a diagnostic. Where a record must refer to one, it refers to the
*requirement* (that a repository is authenticated,
[§6.4](#64-maven-repositories)) and never to the value.

> **Caution:** This is the one place where the rest of this section works
> against itself. The record is durable, diffable, hashes every input, and is
> normally committed — so the machinery that makes contributions auditable is
> exactly the machinery that would publish a credential to version control.

### 9.6 What a record must contain

Two concepts are worth distinguishing by name, though this document mandates
neither a file nor a format:

- **integration resolution** — computing the effective set (step 1);
- **integration record** — the durable, diffable artifact of the last accepted
  resolution (step 5).

A lockfile entry, a checksum file beside the generated project, or any other
durable artifact satisfies the record. The normative property is that a change
in what distributions contribute **MUST NOT** pass silently.

For every distribution in the effective set, a record **MUST** make these
recoverable:

| | |
| --- | --- |
| the distribution | its name and version, and the contract it declared |
| its provenance | how it entered the dependency closure ([§3.2](#32-resolution)) |
| its inputs | a SHA-256 per file, keyed by normalized relative path ([§9.3](#93-hashed-inputs)) |
| its contributions | each one, in a form two records can be compared by |
| its requirements | every value and every action, **with its state** — supplied, acknowledged, or unresolved-and-conditional |
| the native graph | every resolved artifact with its checksum ([§6.3](#63-gradle-dependencies)), and every resolved package with its version **and** revision, plus a checksum per binary target ([§7.2](#72-swift-packages)) |

A record that cannot answer one of those rows has not recorded the integration,
whatever else it contains.

> **Note:** The requirements row does more work here than its counterpart did in
> the first attempt, which recorded only unsatisfied conditional prerequisites.
> Version 1 has no verification mechanism ([§5.4](#54-how-a-requirement-is-satisfied)):
> an action is satisfied by the application's claim that it was done. Recording
> every action and its acknowledgement — with the version and the date the claim
> was made — is what makes that claim attributable afterwards. It is the
> mechanism that lets the model take a claim at face value without the claim
> vanishing.

**What acceptance does and does not guarantee.** The build *does* stop: an
unaccepted change fails. What acceptance cannot guarantee is that anyone read
what they accepted — a reviewer can approve a delta unexamined, and no mechanism
in a build tool prevents that. So this is a review gate whose *blocking* is
enforced and whose *scrutiny* is not, which is a deliberate trade: a blocking
prompt inside a build loop earns click-through quickly and then provides
nothing, whereas a recorded delta stays attributable before the fact in review
and after the fact in history.

### 9.7 Packaging collisions

Two independently-authored packages composing is what this convention is for,
and Android packaging is where that composition breaks first. The producers
cannot see the collision; the consumer is the only party that can.

Two resolved artifacts from **different distributions** may carry a file at the
same path — `lib/arm64-v8a/libc++_shared.so` from two SDKs that each bundle a
C++ runtime, or `META-INF/LICENSE` from almost any pair of libraries. A consumer
**MUST** detect such a collision across the artifacts of the effective set, and
**MUST** treat two cases differently:

| Case | Rule |
| --- | --- |
| **Packaging metadata** — files under `META-INF/` that are not code, such as licence texts and build fingerprints | A consumer **MAY** resolve these itself, by a rule that does not depend on resolution order, and **MUST** record what it did |
| **Anything else, and every native library** | A consumer **MUST NOT** choose silently. It **MUST** fail, naming the path and **both declaring distributions**, unless the application has chosen which artifact supplies the file; where the application has chosen, the consumer **MUST** record the choice |

A consumer **MUST** record every collision it detected and how it was resolved,
attributed to the distributions whose declarations pulled the artifacts in.

> **Note:** `pickFirst` is what an application writes by hand today, and for a
> licence file it is right. For two copies of a C++ runtime it is a coin toss
> between two ABIs, decided by declaration order, and the symptom is a crash in
> native code with no path back to either package.
>
> This is a consumer obligation rather than a declaration because a collision is
> not a property of any producer: it exists only in a combination, and no
> producer can know what it will be composed with. What the consumer adds that
> the build system cannot is which *Python distributions* asked for the
> colliding artifacts — Gradle already fails on a duplicate path, in a message
> naming two artifacts and nothing else.

## 10. Versioning

The entry-point group carries the major version (`native_integration.v1`). A
consumer implementing version *N* **MUST** ignore groups for other major
versions entirely, rather than attempting to read them.

Within a major, the `contract` minor ([§4.3](#43-contract-version)) negotiates
capabilities: minor revisions add optional keys and tables, producers declare
the smallest contract they use, and an older consumer rejects a newer
declaration visibly instead of mis-building it.

Any change that would alter the meaning of an existing key, or make a previously
valid sidecar invalid, requires a new major version and a new group name.

**That rule binds from the moment the draft marker at the top of this document
is removed, and not before.** While this document is a draft it is amended in
place. It is the second attempt at this convention; the first is kept at
[`development/first-attempt.md`](development/first-attempt.md), was never
released, and is not a version anyone has to support — which is why the
restructure took version 1 rather than renumbering around it.

**What a minor revision has to cover is smaller than it looks.** A minor is
required for a new key, a new table, or a new value in a **closed** vocabulary —
[§5.5](#55-value-kinds)'s value kinds, [§6.3](#63-gradle-dependencies)'s Gradle
configurations, [§7.4](#74-infoplist)'s capability-key list. It is **not**
required for:

| | Why not |
| --- | --- |
| A new kind of application requirement | An action is prose. A platform construct this document has never heard of is stated in `summary`, `reason` and `acceptance` without the document changing. |
| A new `slot` | Slots are opaque and compared only for equality ([§5.7](#57-slots)). |
| A new value in an **open** vocabulary | `foreground_service_type`, `<data>` attributes, and Apple's required-reason strings are the platform's to extend; a consumer rejects what it does not implement. |

That is the point of the split between contributions and actions. Contribution
vocabulary is closed and versioned because a consumer is being asked to modify
the build; requirement vocabulary barely exists, because a consumer is being
asked to report a sentence.

Anticipated minor-revision work, deliberately excluded from version 1: further
intent-filter forms beyond `view_links`; conditional contributions (a `when` key
with a **closed vocabulary** of conditions such as ABI or simulator/device — not
an expression language); further Gradle configurations; and further
namespace-scoped shrinker rule forms.

**Version 1 has no way to say "either A or B".** Where a vendor offers two paths
to the same outcome — a configuration file *or* an initialization class — the
producer picks one and declares it. That is a deliberate limitation rather than
a judgment that alternatives could never be useful: expressing them would mean
handing the application author two tasks for one fact, with nothing saying that
doing either is enough. Revisit if a vendor appears whose two paths are
genuinely equivalent and both common.

## 11. Out of scope

| Not covered | Reason |
| --- | --- |
| Prebuilt `.aar` **embedded in the wheel** | Carries an `AndroidManifest.xml` that merges into the application's, defeating [§6.5](#65-permissions-and-features) and [§6.6](#66-manifest-components) with no attribution |
| Prebuilt iOS binaries **carried by the wheel** | Forces a platform tag onto an otherwise pure-Python wheel, and is opaque to this convention's source-level inspection model |
| Native `.so`, extension modules | Solved by `android_<api>_<abi>`-tagged wheels ([PEP 738](https://peps.python.org/pep-0738/)) |
| iOS frameworks in wheels | Solved by `ios_*`-tagged wheels ([PEP 730](https://peps.python.org/pep-0730/)) |
| Android resources (`res/`) | Resource names are a flat global namespace per type, so no ownership rule can be built for them — [§6.1](#61-ownership) needs dots to compute containment. A producer shipping `values/strings.xml` with `app_name` renames the application. Resources reach an application through an `.aar` from a declared coordinate, where AGP merges them; a producer that needs one asks for it as an action |
| Scripts, hooks, build plugins | Excluded on principle ([§2.1](#21-design-principles)), not as a deferral |
| **Arbitrary manifest, `Info.plist` or build-file fragments** | The declarative form of the same capability, excluded on the same principle. A fragment cannot be collision-checked, refused per-permission, gated per-component, or diffed in a record. Permanent; see below |
| **Build-file, manifest and project mutation instructions** | A producer describes an outcome, never an edit. See below |
| **CocoaPods-only iOS SDKs** | [§7.2](#72-swift-packages) declares Swift packages, and this document defines no CocoaPods channel. A vendor that publishes only a podspec is out of reach; see below |
| **Native runtime lifecycle composition** | No way for a producer to run code at application start, or to participate in an app-delegate callback. Deliberate in version 1, and not on principle — see below |
| Xcode build settings, compiler and linker flags | Arbitrary build mutation. The exclusion stands for flags in general; [§7.6](#76-objective-c-categories)'s `objc_categories` is the one bounded exception, and it names a behavior rather than passing a flag |
| Application configuration — *writing* it | The application's own build settings are its own. **Declaring a requirement on it is in scope**, and is what [§5](#5-requirements-on-the-application) is for |

**What "in the wheel" excludes, and what it does not.** The qualifier on the
first four rows is deliberate. A declared Maven coordinate may resolve to an
`.aar`, a declared Swift package may vend binary targets, and a Swift package
may implement a Python extension module from source
([§7.5](#75-python-modules)). All three are in scope: they arrive through the
platform's own dependency channel, locked by [§6.3](#63-gradle-dependencies) and
[§7.2](#72-swift-packages) and surfaced by [§9](#9-recording-and-review). What
is excluded is native material smuggled inside the Python artifact, where no
resolver, lock, or manifest tooling ever sees it.

That distinction is only as good as the surfacing, which is why
[§9.4](#94-what-resolved-artifacts-bring-with-them) makes the Android half of
that reporting a **MUST**. An embedded `.aar` and a coordinate-resolved `.aar`
merge identical manifests into the application; what separates them is that one
is locked, attributable, and reported.

**Why arbitrary fragments stay excluded, and what it costs.** The obvious answer
to every gap in this section is to let a producer contribute a block of manifest
XML, a subtree of `Info.plist`, or a snippet of build script. It would make
almost everything expressible, and it would remove the reason to trust any of
it: authority here is carried by knowing, per key, whether a producer may set it
freely, only with the application's approval, or not at all. A fragment answers
that question nowhere. [§6.7](#67-shrinker-keep-patterns) already refuses raw
shrinker directives for this reason and takes structured class patterns instead;
this row is that argument generalized.

**Mutation instructions are excluded for the same reason, and it is worth
separating from fragments.** A producer does not describe an edit to make — a
file to open, an element to insert, a setting to change. It describes the
**outcome the application must reach**, and
[§5.6](#56-instructions-and-acceptance-criteria) requires acceptance criteria to
be end states rather than operations. An edit language would put this document
in the business of tracking Gradle, AGP and Xcode project formats forever, which
is the maintenance burden the whole design is arranged to avoid.

> **Note:** The cost of both exclusions is real and is paid deliberately: a
> mechanism this document has no vocabulary for is unreachable until a minor
> adds one. What makes that cost survivable now is [§5.3](#53-actions). A
> requirement the document cannot automate is still *stateable*, so the choice
> is no longer between modelling a construct and being silent about it.

**Build-time uploads are an excluded category, not one product.** Any SDK whose
value depends on uploading build artifacts — symbol files, mapping files, source
maps — requires build-time execution by construction. Firebase Crashlytics is
the canonical case: its Gradle plugin uploads the R8 mapping file, and a
run-script phase uploads dSYMs. Sentry, Bugsnag, Instabug and Datadog share the
shape. Such an SDK can be *linked* through [§6.3](#63-gradle-dependencies) or
[§7.2](#72-swift-packages) and the result will build; the build-time step must
be configured in the application's own build. **This is permanent, not a
deferral.**

**Uploading is not the only shape.** A second class of plugin **transforms the
code being built** — instrumenting bytecode, or running as a compiler plugin —
and for those the sentence above is false: linking the SDK produces a build that
succeeds and an SDK that does nothing, or code that does not compile at all.

Work out which of three cases your package is in:

| Case | Example | Ship a wrapper? |
| --- | --- | --- |
| **The SDK degrades.** The build-time step adds symbolication to something that already captures and delivers events | Sentry — its Gradle plugin is optional, and its configuration is declarations this document can express | Yes, with a known deficiency |
| **The SDK fails.** The build-time step is load-bearing for the SDK's core value | Crashlytics — without it every report is unsymbolicated | No |
| **The SDK cannot be integrated at all.** The build-time step *is* the integration | Embrace's `embrace-swazzler` and New Relic's Gradle plugin instrument bytecode to insert the hooks the SDK reads; Realm's Kotlin compiler plugin generates members its model classes are unusable without | No — and say so, rather than publishing a wrapper whose failure looks like a bug in this convention |

**A CocoaPods-only vendor is out of reach, and a producer has two options.**
Nothing here resolves podspecs, and adding a second dependency channel is a
larger commitment than any single vendor justifies. Where a vendor publishes
only to CocoaPods — Google's ML Kit for Apple platforms is the standing
example — a producer can wait for the vendor's own Swift package, or publish a
package of its own that vends the vendor's binaries and declare that under
[§7.2](#72-swift-packages), taking on the maintenance that implies.

**Lifecycle composition is a deferral, not a principle**, and is the most
consequential thing version 1 cannot automate. Firebase calls
`FirebaseApp.configure()` from `application(_:didFinishLaunchingWithOptions:)`,
OneSignal's Android integration is an `Application` subclass, and Stripe needs a
URL callback forwarded from the app delegate.

Two things argue for waiting. Some vendors reach the same result declaratively —
Sentry initializes before any application code through a `ContentProvider` in
its own library plus manifest meta-data, and Airship loads a class named in one
`<meta-data>` entry — so a hook is not the only shape the problem takes. And it
would be the largest runtime capability here: unlike a `service` or `receiver`,
which run when the platform routes an event to them, a startup hook runs
unconditionally and first, in every application that acquires the package
transitively.

If it is added, the shape is a closed vocabulary of events plus a
producer-owned typed handler, with the consumer generating a static dispatcher —
never a source snippet, which would breach [§2.1](#21-design-principles). The
singleton slots such a design needs — `<application android:name>`, the
generated entry point — are the consumer's, and a producer **MUST NOT** be able
to claim one meanwhile.

> **Note:** Unlike the other deferrals here, this one already has a form. *Call
> `pyfoo.init()` early in your application* is an action
> ([§5.3](#53-actions)): stated, reported, acknowledged, and attributed in the
> record. What version 1 lacks is the automation, not the ability to say the
> thing — which is the difference between a deferral and a silence.

## 12. Guidance for package authors

**Declare only what you unconditionally require.** A producer **SHOULD**
declare only what every application that imports the package needs. Anything
needed only when a particular feature is used does not belong in your sidecar.

**Do not reach for an action where a contribution or a value already expresses
the requirement.** A producer **SHOULD NOT** state as an action anything the
automated core can carry. An action is the cheapest thing for you to write and
the most expensive thing for every application that installs your package to act
on. Run the three-part test under [Goals](#goals) honestly before deciding that
something cannot be automated.

**Split feature-conditional surface into optional distributions.**
Feature-conditional native surface **SHOULD** ship as separate distributions
rather than in one package's sidecar. The union problem matters most for **facade packages** — libraries exposing many optional
platform features behind one API, the [Plyer](https://github.com/kivy/plyer)
shape. A facade declaring every permission any feature *might* use hands every
application its worst-case manifest, and no amount of disclosure repairs that:
per-permission suppression ([§6.5](#65-permissions-and-features)) becomes each
application's cleanup chore rather than a rare override.

Ship the conditional surface as optional distributions instead, each carrying
its own sidecar, with extras as the opt-in mechanism:

```toml
# the facade's pyproject.toml
[project.optional-dependencies]
gps = ["plyer-gps"]
camera = ["plyer-camera"]
```

`pip install plyer[gps]` then installs `plyer-gps`, whose sidecar contributes
exactly `android.permission.ACCESS_FINE_LOCATION` and nothing else. An extra
cannot vary the facade's *own* sidecar — extras select dependencies; they do not
change a distribution's contents — but it can select a distribution that carries
one, which is all that is needed.

This is why there is no conditional **contribution** syntax: **the dependency
graph is the conditionality mechanism.** Sidecars are per-distribution,
applications opt in by depending on the piece they use, and the record
attributes each contribution to the smallest meaningful unit.

**Requirements are the exception, and they do carry a `conditional` flag.** The
asymmetry is deliberate. A contribution *imposes* — an application that acquires
the distribution gets the permission whether or not it wanted it — so making one
conditional needs a mechanism that can actually withhold it, and the dependency
graph is that mechanism. A requirement imposes nothing; it asks. Marking one
conditional changes only whether an unmet ask blocks the build, so a flag
suffices where a contribution would need a whole opt-in channel.

The honest cost falls on you: splitting a facade into optional distributions is
real packaging work — separate releases, and an import layout that tolerates
missing pieces. The guidance is **SHOULD**, not MUST, for exactly that reason,
and [§6.5](#65-permissions-and-features)'s suppression exists in part as the
application's recourse when a producer declares more than its applications want.

### 12.1 Framework bindings, where this guidance does not apply

The advice above assumes a **facade**: independent features behind one
dispatcher, with a seam to split along. A **1:1 binding of a platform
framework** has no such seam. Its API surface is the platform vendor's, it is
typically one native module and one Python module, and its requirements vary per
method rather than per feature:

| A `CLLocationManager` binding | pulls in |
| --- | --- |
| `requestWhenInUseAuthorization` | `NSLocationWhenInUseUsageDescription` |
| `requestAlwaysAuthorization` | `NSLocationAlwaysAndWhenInUseUsageDescription` |
| `allowsBackgroundLocationUpdates` | `UIBackgroundModes = ["location"]` |
| `startMonitoringLocationPushes` | a location push extension and an Apple-approved entitlement |

Splitting that into optional distributions would mean splitting the class, which
is not packaging work but a worse API. So a binding cannot follow the guidance
above, and it faces the union problem that guidance exists to prevent: declare
everything and every application carries the worst case, or declare the minimum
and callers of everything else fail at runtime.

**Conditional requirements are the answer for this shape.** Declare your
unconditional needs normally, and mark the rest `conditional = true` with the
triggering condition in `reason`. Nothing is imposed on applications that do not
use the feature, and nothing is silent for applications that do.

> **Caution:** Producers **SHOULD NOT** reach for `conditional` to avoid
> stating an unconditional requirement. It converts a build failure that names
> the problem into a line in a report, and the application discovers the
> requirement at runtime instead.
