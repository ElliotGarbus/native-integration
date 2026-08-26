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
> [[ios.requires.application_values]]
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

*To be ported from the first attempt (§6): ownership, source, Gradle
dependencies and repositories, permissions and features, manifest components,
shrinker keep patterns, manifest meta-data, package visibility.*

## 7. iOS contributions

*To be ported from the first attempt (§7): symbol prefixes, Swift packages,
source and required-reason APIs, `Info.plist`, Python modules, Objective-C
categories.*

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
