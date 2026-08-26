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

**Automate what is deterministic; state the rest.** Use the three-part test
under [Goals](#goals). When a requirement fails the test, it is stated as an
action rather than forced into a shape the consumer cannot honor. A partial
automation that looks complete is worse than a clear task.

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

Material the consumer stages into the generated Gradle project on your behalf.

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

**Containment is computed on dot-separated segments, never on raw strings**, in
rule 4 as in rule 5. A namespace *A* contains *B* when *B* equals *A*, or when
*B* begins with *A* followed by a `.`. So `org.kivy.android` contains
`org.kivy.android.helpers` and does not contain `org.kivy.androidx`, and `PyGMA`
does not contain `PyGMAKit`.

An owned namespace **SHOULD** be reverse-DNS. A consumer **SHOULD** warn on a
single-label one: it is ownable and collision-checked like any other, but it
claims a top-level name for one distribution, which makes accidental overlap
with a sibling project far likelier.

> **Note:** Rule 4 stops a distribution shipping
> `org/kivy/android/PythonActivity.java` from silently replacing the
> application's entry point. The list is consumer-independent so that one
> toolchain's runtime cannot be clobbered because a different toolchain built
> the application.

### 6.2 Source

Glue classes your binding needs on the device, compiled by the application's own
toolchain rather than shipped as a binary.

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

**A declared version is a requirement, not a pin.** Gradle may select a higher
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

Register the services, receivers and activities your integration needs, whether
the class is yours or a declared dependency's. Components are unexported by
default and exported only when the application explicitly approves.

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
> application ID — which a producer does not know. A `kind` this document could
> not register validly would be worse than one it does not offer, because a
> consumer would have to invent the authority to make the manifest parse.

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

Keep classes R8 would otherwise strip or rename — your own reflectively-reached
classes, or a declared dependency's — without letting any distribution disable
shrinking for the application as a whole.

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

A `<meta-data>` entry whose value **you** know — a vendor flag, a model list, a
class name the SDK loads reflectively.

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
- Entries are written into the `<application>` element. Version 1 does not model
  `<meta-data>` on a component.

**This shares one key space with [§5.2](#52-values)'s `manifest_meta_data`
delivery.** A key set here and a value delivered there are the same manifest
entry, so both merge together: equal values coalesce with every provenance
record kept, differing values **MUST** fail naming both distributions, and a key
the **application** sets itself is the application's — the consumer keeps that
value and reports the override.

> **Note:** A `<meta-data>` key is global, and nothing stops a producer writing
> one that belongs to another vendor's SDK — turning analytics collection on,
> say, in an application that turned it off. The application's own entry
> winning, plus every entry appearing in the report against the distribution
> that asked for it, is the answer: the producer states a need, the application
> sees it, and setting the key itself is how the application refuses.

**Resource references.** A `value` **MAY** be a resource reference — anything
beginning `@` or `?` — only when the same sidecar declares an action
([§5.3](#53-actions)) asking the application to supply that resource. A producer
that references a resource it has not asked for **MUST NOT** do so.

> **Caution:** A consumer cannot check this pairing, because an action is prose.
> This is a producer obligation, and the failure when it is broken is an AAPT
> error naming a missing resource. What makes that tolerable is that the
> `<meta-data>` entry appears in the record attributed to the distribution, so
> the error has a trail back to the package that caused it.

### 6.9 Package visibility

The `<queries>` entries your own code needs in order to see that another
application exists at all. Android 11 made package visibility opt-in, and
without a declaration `PackageManager` answers "not installed" — silently — for
everything your code looks for.

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

The `<intent>` form, which matches by action and data rather than by name, is
not expressible in version 1. It is an intent-filter grammar, and the reasons
for modelling stereotypes instead apply unchanged.

> **Note:** There is no veto here, where [§6.5](#65-permissions-and-features)
> has one. A permission is user-visible, policy-relevant, and refusing it leaves
> the application working with less. A `<queries>` entry is none of those:
> removing it does not reduce what the application may do, it makes the
> producer's code quietly get a wrong answer.

## 7. iOS contributions

Material the consumer stages into the generated Xcode project on your behalf.

### 7.1 Symbol prefixes

Contributed Swift compiles straight into the application's single target, with
no per-package namespace like Android's to keep declarations apart.

```toml
[ios]
swift_symbol_prefixes = ["MyPkg"]
```

A producer that contributes Swift source ([§7.3](#73-source)) **SHOULD** do two
things: name its contributed types — and in particular its `@objc` runtime
names — with a consistent prefix, and declare that same prefix here.

A consumer **SHOULD** use declared prefixes to attribute a redeclaration or
duplicate-name error to the contributing distribution.

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

A vendor's Swift package, or your own: resolved by SwiftPM, locked by the
integration record, and compiled as its own module rather than into the
application's.

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

**The declaration rules bind the sidecar; the resolved graph is where they are
enforced.** A declared package's own `Package.swift` may name anything — a
branch, a local filesystem path, an arbitrary URL — and nothing in the
declaration reveals it. A consumer **MUST** therefore reject a resolved graph
containing a **branch** requirement or a **path** dependency, naming the
declaring distribution and the offending package.

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
its own. Declare what your contributed source touches, and the consumer merges
it into the application's `PrivacyInfo.xcprivacy`.

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

The `Info.plist` keys an SDK genuinely needs set — and deliberately not the ones
that grant the application a capability or restrict who may install it.

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

**Dictionary-valued keys are excluded by design, not deferred.** The structured
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

When a Swift package **is** the Python extension module, compiled into the
application target. Without this registration the build succeeds and the
`import` fails.

```toml
[[ios.contributes.python_modules]]
name = "web_views"
swift_package = "PyWebViews"
init = "PyInit_WebViews"      # optional; defaults to PyInit_<name>
```

The package is compiled into the application target rather than loaded from a
shared object, so the ordinary import machinery never sees it. This table
registers it with the interpreter — a name and a symbol, nothing executed at
build time.

- `swift_package` **MUST** name a package the same sidecar declares. A module
  cannot be registered without the code that implements it.
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

A consumer **MUST** exclude both `<name>.py` and `<name>.pyi` from the Python
payload it assembles for the device, for every module this table registers.

> **Note:** Producers ship stubs of the same name for type checking off device.
> A `.py` stub would otherwise sit on `sys.path` as a silent fallback: a
> registration that failed or was skipped would surface not as `ImportError` but
> as an application that imports successfully and does nothing. The `.pyi` is
> excluded with it because it is inert on device and its presence invites the
> `.py` back.

### 7.6 Objective-C categories

The one link-time setting a producer cannot work around and the application
cannot guess: a static library whose Objective-C **categories** are dropped by
the linker unless the application target asks for them.

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

> **Note:** Categories in a static library are not referenced by any symbol the
> linker can see, so it discards them. The application builds, links, ships, and
> then dies on `unrecognized selector sent to instance` the first time the SDK
> calls its own method, with nothing in the message naming the library — let
> alone the Python distribution that brought it in.
>
> A producer cannot solve this in its own package. SwiftPM rejects raw linker
> flags in a package consumed by version, so a vendor's own package cannot set
> it, and the setting belongs to the application target regardless. The cost is
> that loading every category also loads the classes carrying them, so the
> binary grows by whatever the static libraries contain — which is why this is
> declared by the producers that need it rather than switched on for everyone.

## 8. Consuming tool requirements

*To be written once §§4–7 are ported.*

## 9. Recording and review

*To be ported from the first attempt (§9): the lifecycle, the report, hashed
inputs, what resolved artifacts bring with them, the secrets rule, what a record
must contain, and packaging collisions.*

## 10. Versioning

*To be ported from the first attempt (§10).*

## 11. Out of scope

*To be ported from the first attempt (§11).*

## 12. Guidance for package authors

*To be ported from the first attempt (§12), plus one rule: do not reach for an
action where a contribution or a value already expresses the requirement.*
