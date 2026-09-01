# The native-integration specification

**Version:** `1` (draft)
**Entry-point group:** `native_integration.v1`

A Python distribution uses this convention to declare what an Android or iOS
application build must provide on its behalf. A build tool discovers those
declarations, stages what it can, and tells the application author what is left
to do.

> **Status: draft, complete and under review.** This document replaces an
> earlier attempt, kept at
> [`development/first-attempt.md`](development/first-attempt.md) for its
> reasoning and its evidence. Neither was ever released, so this takes version 1
> rather than renumbering around a version nobody had to support.

---

## Contents

**Writing a sidecar for a package with both platforms, or unsure where to
start?** [Appendix A](#appendix-a-a-complete-sidecar) shows one whole, and
[Appendix B](#appendix-b-declaration-reference) lists every key it may contain.
[§1](#1-terminology) and [§2](#2-overview) explain the model those keys
declare into; [§12](#12-guidance-for-package-authors) has guidance specific to
producers.

**Writing Android contributions only?** [§6](#6-android-declarations) is the
normative reference for every key under `[android.contributes]`, and
[§12](#12-guidance-for-package-authors) again for guidance once §6's mechanics
are clear. [§7](#7-ios-declarations) does not apply.

**Writing iOS contributions only?** [§7](#7-ios-declarations) is the
equivalent normative reference for `[ios.contributes]`. [§6](#6-android-declarations)
does not apply.

**Building a consuming tool** — one that reads sidecars and generates a native
project? [§8](#8-consuming-tool-requirements) is the checklist, and §§2–7 and
[§9](#9-recording-and-review) are what it refers to.

**Building or maintaining an application that depends on packages using this
convention?** [§2.2](#22-how-the-application-answers) is how a value or action
is answered from `pyproject.toml`, and [§9](#9-recording-and-review) is what
the consumer's report — the thing naming what still needs a decision — looks
like.

**Reviewing a build's output, an audit, or a compliance sign-off?**
[§9](#9-recording-and-review) is the record a consumer must produce, and
[Appendix C](#appendix-c-a-record-that-satisfies-9) shows one that satisfies
it.

> Callouts like this one are **rationale**: why a rule is the way it is, and
> what goes wrong without it. They state no requirement, and a reader who skips
> every one of them has missed nothing binding.

<!-- toc -->

- [Goals](#goals)
- [Non-goals](#non-goals)
- [1. Terminology](#1-terminology)
- [2. Overview](#2-overview)
  - [2.1 Design principles](#21-design-principles)
  - [2.2 How the application answers](#22-how-the-application-answers)
  - [2.3 What the consumer generates](#23-what-the-consumer-generates)
  - [2.4 Obligations on the consumer's bootstrap](#24-obligations-on-the-consumers-bootstrap)
- [3. Discovery](#3-discovery)
  - [3.1 The entry point](#31-the-entry-point)
  - [3.2 Resolution](#32-resolution)
  - [3.3 Iterate; do not look up by name](#33-iterate-do-not-look-up-by-name)
  - [3.4 One entry per distribution](#34-one-entry-per-distribution)
  - [3.5 The distribution is the only carrier of the sidecar](#35-the-distribution-is-the-only-carrier-of-the-sidecar)
- [4. The sidecar file](#4-the-sidecar-file)
  - [4.1 Location and name](#41-location-and-name)
  - [4.2 One file for all platforms](#42-one-file-for-all-platforms)
  - [4.3 Contract version](#43-contract-version)
  - [4.4 Unknown declarations fail closed](#44-unknown-declarations-fail-closed)
  - [4.5 Platform support](#45-platform-support)
- [5. Requirements on the application](#5-requirements-on-the-application)
  - [5.1 Build floors](#51-build-floors)
  - [5.2 Values](#52-values)
  - [5.3 Actions](#53-actions)
  - [5.4 How a requirement is satisfied](#54-how-a-requirement-is-satisfied)
  - [5.5 Value kinds](#55-value-kinds)
  - [5.6 Instructions and acceptance criteria](#56-instructions-and-acceptance-criteria)
  - [5.7 Slots](#57-slots)
- [6. Android declarations](#6-android-declarations)
  - [6.1 Ownership](#61-ownership)
  - [6.2 Java and Kotlin source](#62-java-and-kotlin-source)
  - [6.3 Gradle dependencies](#63-gradle-dependencies)
  - [6.4 Maven repositories](#64-maven-repositories)
  - [6.5 Permissions and features](#65-permissions-and-features)
  - [6.6 Manifest components](#66-manifest-components)
  - [6.7 Shrinker keep patterns](#67-shrinker-keep-patterns)
  - [6.8 Manifest meta-data](#68-manifest-meta-data)
  - [6.9 Package visibility](#69-package-visibility)
- [7. iOS declarations](#7-ios-declarations)
  - [7.1 Symbol prefixes](#71-symbol-prefixes)
  - [7.2 Swift packages](#72-swift-packages)
  - [7.3 Swift source](#73-swift-source)
  - [7.4 Info.plist](#74-infoplist)
  - [7.5 Python modules](#75-python-modules)
  - [7.6 Objective-C categories](#76-objective-c-categories)
- [8. Consuming tool requirements](#8-consuming-tool-requirements)
  - [8.1 Conformance is per platform](#81-conformance-is-per-platform)
  - [8.2 Dispositions, and what recording is not](#82-dispositions-and-what-recording-is-not)
  - [8.3 Thematic index](#83-thematic-index)
  - [8.4 Requirements](#84-requirements)
  - [8.5 Advisory obligations](#85-advisory-obligations)
- [9. Recording and review](#9-recording-and-review)
  - [9.1 The lifecycle](#91-the-lifecycle)
  - [9.2 The report](#92-the-report)
  - [9.3 Hashed inputs](#93-hashed-inputs)
  - [9.4 What resolved artifacts bring with them](#94-what-resolved-artifacts-bring-with-them)
  - [9.5 Secrets are never recorded](#95-secrets-are-never-recorded)
  - [9.6 What a record must contain](#96-what-a-record-must-contain)
  - [9.7 Packaging collisions](#97-packaging-collisions)
- [10. Versioning](#10-versioning)
- [11. Out of scope](#11-out-of-scope)
- [12. Guidance for package authors](#12-guidance-for-package-authors)
  - [12.1 Framework bindings, where this guidance does not apply](#121-framework-bindings-where-this-guidance-does-not-apply)
  - [12.2 Sidecar authoring procedure](#122-sidecar-authoring-procedure)
- [Appendix A: a complete sidecar](#appendix-a-a-complete-sidecar)
- [Appendix B: declaration reference](#appendix-b-declaration-reference)
- [Appendix C: a record that satisfies §9](#appendix-c-a-record-that-satisfies-9)
- [Appendix D: why contributions stay per-distribution](#appendix-d-why-contributions-stay-per-distribution)
- [Appendix E: prior art](#appendix-e-prior-art)
- [Appendix F: the conformance record](#appendix-f-the-conformance-record)

<!-- /toc -->

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

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**,
**RECOMMENDED**, **MAY** and **OPTIONAL** are to be interpreted as described in
[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) — where **REQUIRED** is
**MUST**, and **RECOMMENDED** is **SHOULD**.

| Term | Meaning |
| --- | --- |
| **Distribution** | An installed Python distribution, as seen by `importlib.metadata`. |
| **Producer** | A distribution that declares a native integration. Where this document addresses the person who writes one, it says **package author**. |
| **Consumer** | A tool that reads declarations and generates a native app project. Consumers are build tools, not installers. |
| **Application** | The app being built. Its own configuration is outside this document. |
| **Dependency closure** | The application's direct dependencies and their transitive requirements, as resolved for the target platform. |
| **Effective set** | The distributions in that closure which ship a sidecar, together with everything those sidecars declare, after this document's validation and merge rules have been applied. What a build stages, reports and records is the effective set. |
| **Normalized name** | A distribution's name lowercased with each run of `-`, `_` and `.` replaced by a single `-`, as [PEP 503](https://peps.python.org/pep-0503/) defines it. Where this document fixes an order or a join by distribution name, it means this form. |
| **Sidecar** | The declaration file a producer ships. |
| **Contribution** | Native material the consumer stages on the producer's behalf. |
| **Value** | A string the application supplies and the consumer writes to a platform key. |
| **Action** | An outcome the application must achieve, which the consumer states and does not perform. |
| **Integration record** | The durable, diffable artifact of the last accepted resolution ([§9](#9-recording-and-review)). |
| **Report** | What a consumer shows for one build: each distribution, how it entered the closure, and the delta since the last accepted record. |
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
manifest components are contributed — [§6](#6-android-declarations) and
[§7](#7-ios-declarations) cover those per platform.

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

**Native surface changes are review-gated.** A consumer **MUST** record what it
resolved, report the delta against the last accepted record, and **MUST NOT**
build through a change the application has not accepted
([§9](#9-recording-and-review)).

> **Note:** This is the largest obligation in the document that is not about
> reading a sidecar, and it is deliberately part of the contract rather than
> left to each tool's policy. Without it the record is a lockfile and nothing
> more: a transitive dependency's new permission lands in the shipped
> application with a line in a report nobody had to read. What is mandated is
> narrow — *an unaccepted change does not pass silently* — and the form is the
> consumer's: a re-lock, a flag, a committed file. What is not optional is that
> some deliberate act stands between a new native surface and a build.

### 2.2 How the application answers

The application answers every requirement through the **consumer's own
configuration**. This document mandates the capability a consumer offers, never
its spelling. Two conforming consumers can ask for the same thing in different
words.

A consumer **MUST** provide a way for the application to:

| Answer | Joined by |
| --- | --- |
| Supply a value | `(distribution, id)` |
| Acknowledge an action, or dismiss a conditional one | `(distribution, id)` |
| Suppress a contributed permission | permission `name` |
| Approve an exported component | component `name` |
| Supply credentials for an authenticated repository or Swift package ([§6.4](#64-maven-repositories), [§7.2](#72-swift-packages)) | its `url` |
| Decide a resolved artifact's required feature ([§9.4](#94-what-resolved-artifacts-bring-with-them)) | feature `name` |
| Choose which artifact supplies a colliding file ([§9.7](#97-packaging-collisions)) | packaged `path` |

The consumer chooses the path; the producer fixes the leaf. If a producer
declares `id = "sentry_dsn"`, the application answers under that exact string,
wherever the consumer nests it.

**Four of those answers are deliberately not scoped to a distribution, and
apply to every contributor of the thing they name.** A permission suppression,
an export approval, a required-feature decision and a colliding-path choice all
address the **merged result** — one manifest entry, one registered component,
one installed file — which is a thing the application gets once no matter how
many distributions asked for it. So a suppression of
`android.permission.INTERNET` withdraws it on behalf of every distribution that
contributed it, and a consumer **MUST NOT** treat such an answer as applying to
only one of them. The record is where the breadth becomes visible: it **MUST**
show which contributions each answer affected, naming every distribution
involved.

> **Note:** The alternative — joining a suppression by `(distribution, name)` —
> would let an application withdraw a permission from one producer while a
> second producer's identical declaration silently put it back, which is a
> refusal that does not refuse. Values and actions are scoped by distribution
> for the opposite reason: two producers asking for a client ID are asking for
> two different strings, and answering one says nothing about the other.

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
that declared it, the `reason` — or, for a floor, the declared and configured
values, since a floor carries no `reason` ([§5.1](#51-build-floors)) — and, for
an action, the `summary` together with `instructions` and `acceptance`
**wherever the sidecar declares them**. Both are optional fields
([§5.3](#53-actions)) and a consumer reports what is there; what it **MUST NOT**
do is drop them when they exist, which would report that something is owed
without carrying what a person or agent needs to do the work and confirm it.

A consumer **SHOULD** scaffold declared placeholders into the application's own
configuration, so that what remains is visible where the author already works:

```toml
# Added by examplebuild. Required by pysentry.
[tool.examplebuild.native.pysentry.android.application_values]
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

**Why these bind every consumer, rather than being declarable.** A producer
could in principle state "I need a `ComponentActivity`" as a requirement, and
this document deliberately does not let it. The property is a **baseline every
package may assume**, not a per-package need: a binding author knows they wrap
Stripe, not that Stripe's Android SDK calls a method declared only on the
AndroidX class, and discovering that is not reasonably their job. Making it
declarable would also mean every producer that forgot to declare it ships a
package that fails on some consumers and not others, with nothing naming the
cause. Two clauses fixed here cost each consumer once; the alternative costs
every producer forever, and silently.

> **Note:** Some SDKs need this and already solve it themselves. Where a
> vendor's own SDK provides a declarative load hook — a manifest entry naming a
> class its own bundled loader reads before any component runs, as Android's
> Airship `Autopilot` and Sentry's `ContentProvider` trick do — a producer
> states that entirely through an ordinary value ([§5.2](#52-values)) and a
> contributed class ([§6](#6-android-declarations)), and no manual step
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
   application for the target platform. Every environment marker and extra
   **MUST** be evaluated for the **target** — its platform and its Python
   version — and never for the build host. A consumer operating in an isolated
   environment that contains exactly that closure **MAY** treat all installed
   distributions as candidates.
2. For each candidate, read entry points in the group `native_integration.v1`
   through `importlib.metadata`.
3. Interpret the value's dotted path as a directory within the distribution —
   `mypkg._native` becomes `mypkg/_native/` — and read `native.toml` inside it.

A consumer **MUST NOT** accept contributions from distributions outside the
closure, whatever else is installed alongside it.

> **Note:** A consumer runs on a desktop build host, and
> `sys_platform` there is `win32`, `darwin` or `linux` — never `android` or
> `ios`. A closure resolved against the host's own markers is a different set
> from the one that will be installed on the device: it can admit a
> distribution the target never sees, and drop one the target needs, and either
> way the sidecars read are the wrong sidecars.
>
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

> **Note: why this is a file, and not a table in `pyproject.toml`.** The obvious
> home for a declaration is the producer's own `pyproject.toml`, under
> `[tool.native_integration]`. It does not work: arbitrary `[tool.*]` tables are
> build-time configuration and do not survive into the wheel or into the
> installed distribution, so a consumer reading installed metadata never sees
> them. A build backend could copy them across — and that is a backend wrapper
> per backend, forever, excluding every backend nobody wrote one for. Package
> data and entry points are the two things every major backend already emits
> without knowing this document exists, which is why the declaration rides on
> those and on nothing else.

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

**The grammar is exact.** A `contract` value **MUST** match
`(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))?` — one component or two, ASCII digits, no
leading zeros, no third component, and no surrounding whitespace. A consumer
**MUST** reject anything else, naming the distribution and the value: `"1.0.0"`,
`"01"`, `"1."` and `" 1"` are invalid, not lenient spellings of `"1"`.

A consumer implementing contract *X.Y* **MUST** reject a sidecar that declares a
different major, or a minor greater than *Y*, with a message naming the
distribution and the contract the sidecar needs. It **MUST NOT** parse such a
sidecar partially.

A consumer **MUST** also reject a sidecar that **under-declares**: one using a
key, a table, **or a value from a closed vocabulary** introduced in a revision
later than the contract it names, even when the consumer implements all of
them.

> **Note:** Closed vocabularies are in the rule because they are where a minor
> is otherwise invisible. A 1.1 that adds a value `kind` adds no key: a sidecar
> using it still declares `id`, `kind`, `key` and `reason`, and a 1.1 consumer
> reading `contract = "1"` would find nothing structurally new to object to.
> Without this clause the gate would protect a 1.0 consumer, which rejects the
> unknown value anyway, and nobody else.

> **Note:** Without the under-declaration rule the gate protects only older
> consumers. A producer that mis-declares its contract is then caught by nobody
> until an older consumer meets it — at which point the diagnostic blames the
> consumer's age rather than the producer's declaration.

The declaration reference in [Appendix B](#appendix-b-declaration-reference) is the registry that makes the
under-declaration rule checkable. Every key **and every closed-vocabulary
value** it lists is contract 1.0 unless it carries a *Since* note, and a minor
revision that adds either **MUST** record the minor there. Without one normative
source for *which revision introduced this key or this value*, two conforming
consumers would reach different verdicts on the same sidecar.

A consumer **MUST** be able to state the contract it implements, and **SHOULD**
report it where a person can see it — a version string, a doctor check. That is
what lets a package author decide whether adopting a minor strands their users.

### 4.4 Unknown declarations fail closed

Within a platform table the consumer is **building for**, an unrecognized key
**MUST** be rejected, naming the distribution and the key. A consumer **MUST
NOT** ignore a declaration it does not understand in order to proceed.

**One exception exists, and this document contains no other.** The `<data>`
attributes of a `view_links` entry ([§6.6](#66-manifest-components)) are
Android's own names, and an unrecognized one is written through rather than
rejected. It is stated there, bounded to that one table, and argued on the same
ground as the pass-through rule below.

**Values divide by what the consumer does with them**, and the two halves get
opposite rules.

| The value | Examples | Rule |
| --- | --- | --- |
| **selects behaviour the consumer performs** | a Gradle `configuration`, a value `kind` ([§5.5](#55-value-kinds)) | **Closed** and enumerated here. A consumer **MUST** reject one it does not implement, naming the distribution and the value, and **MUST NOT** substitute a default |
| **is copied into a platform artifact** | a foreground service type, an Android `<data>` attribute, an Apple required-reason string | **Pass-through.** A consumer **MUST** validate the value's *shape* where this document gives one, and **MUST** write it through unchanged. It **MUST NOT** reject a value merely because it does not recognize it |

A consumer **SHOULD** say which values of a closed set it implements, so a
producer can tell an unsupported declaration from a misspelled one.

> **Note:** Pass-through is what keeps a producer's pace tied to the platform's
> releases rather than to this document's *or to its consumer's*. When Android
> adds a foreground service type, a producer may use it immediately: the
> consumer copies the string into the manifest, and AGP — which does know the
> value — accepts or rejects it. Rejecting unknown platform strings would mean a
> producer waits for every consumer to catch up, while the contract minor it
> declared says nothing is new. The cost is that a typo now fails in AGP rather
> than against the sidecar; the record shows the value and the distribution that
> declared it, so the error still has a trail.
>
> This is not a hole in *fail closed*. A pass-through value is not ignored — it
> reaches the artifact it was written for, and the platform's own validation is
> what it faces. Failing closed protects against a declaration going nowhere,
> and this one goes exactly where it was aimed.

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

**An `id` is unique within one platform table, across values and actions
alike.** A value and an action **MUST NOT** share an `id` on one platform: the
application answers both by `(distribution, id)`, so a shared name has no
unambiguous answer. A consumer **MUST** reject a sidecar in which two
requirements in one platform table share an `id` — two values, two actions, or
one of each — naming the distribution and the `id`. The same `id` on the two
platforms is a different requirement and is expected — an account identifier
usually differs per platform.

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

**A floor is always unconditional, and carries no `reason`.** It takes no
`conditional` key — a build either meets a minimum or does not, and there is
nothing for an application to dismiss — so
[§5.4](#54-how-a-requirement-is-satisfied)'s three states describe values and
actions only. It also carries no `reason` field, because the declaration is
self-describing: where [§5.4](#54-how-a-requirement-is-satisfied) and
[§2.3](#23-what-the-consumer-generates) require an unmet requirement to be
reported with its `reason`, an unmet floor is instead reported with **the
declared value and the application's configured one**, which is the whole of
what a reader needs.

**How the iOS and Android kinds compare.** `min_sdk`, `compile_sdk` and
`target_sdk` **MUST** be TOML integers, and compare as integers. A consumer
**MUST** reject any other type, naming the distribution and the key: `"24"` is
a string and `24.0` is a float, and a document that accepted either would be
inviting two consumers to differ over which coercions are allowed. The iOS
`deployment_target` is a string, and comparing it as one would make `"9.0"`
higher than `"15.0"`, so the comparison is fixed here:

- The value **MUST** match `[0-9]+(\.[0-9]+){0,2}` — one to three ASCII-decimal
  components. A consumer **MUST** reject anything else, naming the distribution
  and the value.
- Comparison is component-wise and numeric, with absent components read as
  zero. So `"15"`, `"15.0"` and `"15.0.0"` are one floor; `"15.0.1"` is higher
  than all three, and `"9.0"` is lower.

**A boolean floor is a floor, so only `true` says anything.** A consumer
**MUST** reject `core_library_desugaring = false`, naming the distribution:
version 1 has no way to require that a build setting be *off*, and a
declaration that requires nothing is far likelier to be a mistake than an
intent. [§7.6](#76-objective-c-categories)'s `objc_categories` carries the same
rule for the same reason.

**Floors compose by maximum, and that is why they are disclosed.** Two
distributions declaring `min_sdk = 24` and `min_sdk = 26` are not in conflict:
each states a minimum, and the higher one satisfies both. This is deliberately
unlike [§6.3](#63-gradle-dependencies)'s `configuration`, where two values are
mutually exclusive spellings of one setting and failing is the only honest
outcome. A consumer **MUST** record and report every declared floor with the
distribution that declared it, and **MUST** give a declared `target_sdk` the
same prominence it gives a repository contribution
([§6.4](#64-maven-repositories)).

> **Caution:** `target_sdk` is the reason that last clause exists. It changes
> behavior across the whole application, in code that has nothing to do with the
> producer's package, and it composes silently upward: a transitive dependency
> nobody chose can raise it. Declare it only when a specific behavior depends on
> it, and say which one. What a consumer owes in return is that the highest
> declared value, and who declared it, are visible rather than inferable.

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
| `id` | **yes** | A logical name, unique among the requirements in this platform table. Identity is `(distribution, platform, id)`. |
| `kind` | **yes** | Where the consumer writes the value. A closed set — see [§5.5](#55-value-kinds). |
| `key` | depends on `kind` | The platform key the value is written to. **REQUIRED** for every kind but `inline`, where it **MUST** be absent. |
| `reason` | **yes** | What the value is and where to obtain it. |
| `placeholder` | **SHOULD** | Text the consumer scaffolds until the application supplies the value. |
| `conditional` | no | Defaults to `false`. See [§5.4](#54-how-a-requirement-is-satisfied). |

Rules:

- The supplied value is a **non-empty string**. Version 1 defines no other type.
- A value **MUST** declare a `kind`. If there is nowhere for the consumer to
  write the string, the requirement is an action, not a value.
- Two values targeting the same `(kind, key)` **coalesce** when the supplied
  content is equal, preserving both provenance records. When it differs, the
  consumer **MUST** fail, naming both distributions. Equality is byte equality
  of the supplied string; where the other side of a shared key space is a typed
  contribution ([§6.8](#68-manifest-meta-data),
  [§7.4](#74-infoplist)), a value coalesces with it only when that contribution
  is a string of equal content. `1` and `"1"` are different content and
  **MUST** fail.
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
| `id` | **yes** | A logical name, unique among the requirements in this platform table. Identity is `(distribution, platform, id)`. |
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
- **An acknowledgement does not satisfy an action while a value it `uses` is
  unsupplied.** This matters most when the value is **conditional**: on its
  own, an unsatisfied conditional value never fails the build
  ([§5.4](#54-how-a-requirement-is-satisfied)), so without this rule an
  unconditional action could be acknowledged and pass even though the input it
  depends on never arrived. A consumer **MUST** treat such an action as
  unsatisfied — failing the build where the action is unconditional — and
  **MUST** report the action beside the value that is holding it open, naming
  both `id`s. A dismissed conditional value leaves the action unsatisfied on
  the same terms; only a supplied value clears it.
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
> kind = "inline"
> reason = "The App Group identifier this SDK shares data through"
> placeholder = "group.<TODO: your bundle id>.example"
>
> [[ios.requires.application_action]]
> id = "app_group_entitlement"
> summary = "Enable App Groups and add the identifier above to the entitlement"
> reason = """\
> The container is shared through the entitlement, which has to be on the App \
> ID and in the provisioning profile before anything can be signed."""
> uses = ["app_group_id"]
> ```
>
> The value is `inline` because nothing on iOS reads an App Group identifier
> from a platform key the consumer could write — the identifier belongs in an
> entitlement, on targets the consumer does not own. `uses` is what consumes it
> ([§5.5](#55-value-kinds)), and the author reads it out of the scaffolded
> placeholder while doing the work the action describes.
>
> Without `uses`, these would read as two unrelated line items, and nothing
> would stop an application author from acknowledging the action while the
> value it depends on is still an unfilled placeholder. `uses` makes that
> dependency checkable — the rules above reject a `uses` that resolves to
> nothing, and hold an acknowledged action open while a value it names is
> unsupplied — and lets a report show the action beside the value it needs,
> instead of asking the reader to notice the connection on their own. It does
> not collapse the two into one requirement — the value is still something a
> consumer can place automatically, and the action is still something only
> the application author can complete.

### 5.4 How a requirement is satisfied

| Shape | Satisfied when the application… |
| --- | --- |
| Floor | is configured at or above the declared value |
| Value | has supplied a non-empty string that is not the placeholder |
| Action | has acknowledged it by `(distribution, id)`, **and** every value in its `uses` is supplied ([§5.3](#53-actions)) |

A consumer **MUST**:

- fail the build when an **unconditional** (`conditional == false`)
  requirement is unsatisfied, naming the distribution and the `reason` — or,
  for a floor, which carries no `reason`, the declared and configured values
  ([§5.1](#51-build-floors));
- record an unsatisfied **conditional** (`conditional == true`) requirement in
  the integration record and **MUST NOT** fail the build for it.

Only values and actions take `conditional`; a floor is always unconditional
([§5.1](#51-build-floors)), so everything below is about those two shapes.

Declare `conditional = true` when you cannot tell whether the requirement
applies and the application can. State the triggering condition in `reason`.

A conditional requirement has **three** states, not two:

| State | How it is reached | Outcome |
| --- | --- | --- |
| satisfied | the application supplied the value or acknowledged the action | met, and recorded |
| dismissed | the application states that it does not apply | recorded, and no longer reported |
| unresolved | the application has answered neither | recorded, **and reported on every build** |

A consumer **MUST** provide a way for the application to dismiss a conditional
requirement, joined by `(distribution, id)`, and **MUST** record a dismissal
like any other answer. A consumer **MUST** report an unresolved conditional in
every build's report, not only in the record.

> **Note:** Unresolved is deliberately not blocking. A framework binding
> ([§12.1](#121-framework-bindings-where-this-guidance-does-not-apply)) may
> carry several conditional requirements, and forcing an answer to each would
> reimpose the worst case that `conditional` exists to avoid. What the three
> states buy is that *unanswered* stays visible: it does not decay into silence
> after the first build, and dismissing something is a decision the record
> attributes rather than an absence.

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
| `inline` | Android, iOS | *(omitted)* | nothing directly; the value is consumed where it was declared for — see below |

**The Platform column is normative.** A `kind` is valid only in a table for the
platform its row names: `manifest_meta_data` and `manifest_placeholder` under
`[android]`, `info_plist` and `usage_description` under `[ios]`, `inline` under
either. A consumer **MUST** reject a kind declared in the other platform's
table, naming the distribution, the `id` and the kind.

> **Note:** Without that, a consumer implementing both platforms has no reason
> to object to `kind = "info_plist"` inside `[android]`, and would write an
> `Info.plist` key from an answer the application filed under `android` —
> where, since identity is `(distribution, platform, id)`, it may have meant an
> entirely different string. A single-platform consumer catches this by
> accident, having never implemented the other platform's kinds, and two
> consumers disagreeing about the same sidecar is the outcome this column now
> prevents.

**The two `*UsageDescription` rules are a pair.** `info_plist` **MUST NOT** name
a key ending in `UsageDescription`, and `usage_description` **MUST** name one: a
consumer **MUST** reject either mismatch, naming the distribution and the key.
The kind exists so that a report can tell an author they are being asked for
user-facing text that App Store review reads, and a `usage_description` free to
write any `Info.plist` key would be that label attached to something else.

**`info_plist` reaches no key [§7.4](#74-infoplist) refuses.** A value of that
kind **MUST NOT** name a capability or external-reach key — `UIBackgroundModes`,
`UIRequiredDeviceCapabilities`, `CFBundleURLTypes`, `NSUserActivityTypes`, and
whatever a later minor adds to that closed list — nor a key the consumer manages
itself, such as `CFBundleIdentifier` or `CFBundleShortVersionString`. A consumer
**MUST** reject either, naming the distribution and the key.

> **Note:** Without this rule the requirement side is a way around the
> contribution side. [§7.4](#74-infoplist) refuses those keys as contributions
> because writing one grants the application a capability, restricts who may
> install it, or makes it reachable from outside; routing the same key through
> an application-supplied value changes none of that. It would change only who
> typed the string — and would produce exactly the false-complete state that
> list exists to prevent, with `UIBackgroundModes` set in the plist and the
> background mode not actually working, because the entitlement and the App
> Store declaration behind it were never part of the transaction.

**An `inline` value is consumed, not written.** It is the one kind with no
`key`, because the consumer places it somewhere another declaration in the
same sidecar already names. Exactly two sites do that:

| Site | What it looks like |
| --- | --- |
| A contribution field that takes an inline reference — in version 1, exactly the `<data>` attributes of `view_links` ([§6.6](#66-manifest-components)) | `scheme = { application_value = "oauth_redirect_scheme" }` |
| An action in the same sidecar and platform table that names the `id` in `uses` ([§5.3](#53-actions)) | `uses = ["app_group_id"]` |

A consumer **MUST** reject an `inline` value that neither site consumes, naming
the distribution and the `id`. It **MUST** also reject an inline reference —
`{ application_value = "…" }` — that names anything but a value of kind
`inline` declared by the same sidecar for the same platform: an unresolved
`id`, or an `id` belonging to a value of another kind, is invalid either way.

> **Note:** The second half of that rule keeps one string from having two
> destinations. A reference to a `manifest_meta_data` value would ask the
> consumer both to write the `<meta-data>` entry that value's `key` names and to
> splice the same string into a generated filter — a second delivery site the
> declaration never asked for, and one two consumers would disagree about
> allowing. A producer that genuinely needs both declares two values.

> **Note:** Without that rule `inline` is the hole the other four kinds were
> shaped to close. A value's whole contract is that the application supplies a
> string and the consumer puts it somewhere; an unconsumed `inline` blocks the
> build until the application answers, and then does nothing with the answer.
> The second site is what keeps the kind honest on iOS, where version 1 has no
> `{ application_value = … }` field at all: an App Group identifier is a real
> string the application supplies, and the thing that consumes it is the action
> whose `uses` names it — the author, doing the work the action describes.

> **Note:** `manifest_placeholder` exists for a value that a **declared
> dependency's own manifest** reads, which `manifest_meta_data` cannot reach.
> Auth0's and AppAuth's Android libraries ship the redirect intent filter
> pre-written with `${auth0Domain}` and `${auth0Scheme}` holes in it, and the
> application fills them through AGP's `manifestPlaceholders`. Without this
> kind, the application is back to transcribing a value into its own build
> file, which is the problem this convention exists to remove — and the
> dependency's filter cannot be reached any other way.

**Nothing in this section is pass-through.** Some contribution keys elsewhere
in this document are, because the *platform* owns the names and the consumer
only copies them — an Android `<data>` attribute, a foreground service type. A
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

**Hashing bounds the channel; it does not label it.** The delta is visible to
whoever reviews the record, and the party at risk is whoever reads the text
afterwards — often an agent, working from a scaffolded comment block
([§2.3](#23-what-the-consumer-generates)) with no other context. So a consumer
**MUST** attribute this text to the declaring distribution wherever it renders
it — in the report, and in every scaffolded block — as content that distribution
supplied. A consumer **MUST NOT** present it as the consumer's own guidance or
as the application author's own instruction.

> **Caution:** A scaffolded block is the one place in this document where a
> third party's prose ends up inside a file the application owns, addressed to
> whoever opens it next. `# Added by examplebuild. Required by mywechatpkg.`
> above the block is doing real work: it is the difference between an agent
> reading a task from its principal and an agent reading a request from a
> dependency, which is the distinction the party table above rests on.

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
extension (screen recording), a file provider extension, and a share
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
  This document enumerates none of them normatively.
- When two actions in the effective set share a slot, a consumer **MUST** report
  them together, naming both distributions.

**The identifiers the cases examined produced**, so that two producers reaching
the same surface reach the same string. Nothing below is normative, nothing is
closed, and a consumer that treated this as a vocabulary would be interpreting
slots:

| Surface | Identifier |
| --- | --- |
| Notification service extension | `com.apple.usernotifications.service` |
| Notification content extension | `com.apple.usernotifications.content-extension` |
| Broadcast upload extension (screen recording) | `com.apple.broadcast-services-upload` |
| File provider extension | `com.apple.fileprovider-nonui` |
| Share extension | `com.apple.share-services` |
| App Groups, across the application and its targets | `com.apple.security.application-groups` |

Take the identifier from the platform where the platform has one — an Apple
extension point identifier is what a built target carries in its own
`Info.plist` — rather than inventing a spelling. The failure mode of two
producers choosing different strings is a contention that goes unreported, which
is the state before `slot` existed; equality can miss a collision and cannot
invent one.

> **Note:** Every identifier above is Apple's, and the mechanism is not — `slot`
> is a field of the action table, which is one table with one field set on both
> platforms. What differs is how the two platforms compose. Android's manifest
> merges by union under distinct class names: two push SDKs each register their
> own service, each under its own namespace, and both work —
> [§6.6](#66-manifest-components) fails only where two producers name the *same*
> class. iOS caps certain capabilities at one target per extension point, so two
> SDKs needing a notification service extension contend however carefully each
> was written.
>
> The Android surfaces that *are* singletons make the point from the other side.
> `<application android:name>` and the generated entry-point activity are
> exactly one per application, and both belong to the consumer's bootstrap
> ([§2.4](#24-obligations-on-the-consumers-bootstrap),
> [§11](#11-out-of-scope)) — a producer cannot claim one, so no action asks an
> application author to hand one over, and no contention arises to report.
>
> A `slot` knows none of that. It is a string compared for equality, and its
> vocabulary is whichever platform owns the surface, so an application-owned
> Android singleton would need no change here.

Reporting a contention is disclosure, not a failure. The application resolves
it — by merging two vendors' code into the one target the platform allows, which
is work no consumer can do and no producer can anticipate.

**Why this discloses where a packaging collision
([§9.7](#97-packaging-collisions)) fails.** The two look alike — one surface,
two claimants, only the application can choose — and the difference is what the
consumer knows and what it is being asked to do. A packaging collision is a fact
the consumer verified: it holds both artifacts, it can see one path in each, and
the resolution is an act it performs — which file it packages. A slot is
opaque by rule, so a consumer does not know the surface is a singleton, only
that two producers named one string; and the resolution is work in the
application's own project that the consumer neither performs nor sees. Failing
would demand a second acknowledgement of the fact both actions already
acknowledge, and would block a build over a string comparison the consumer is
forbidden to interpret. Two acknowledgements of two merged handlers is what
being finished looks like here.

---

## 6. Android declarations

What a producer owns and contributes on Android. Requirements on the
application are [§5](#5-requirements-on-the-application)'s, whichever platform
they name.

| § | Key | Declares | How conflicts resolve |
| --- | --- | --- | --- |
| [6.1](#61-ownership) | `android.owns.java_namespaces` | A claim on a Java/Kotlin namespace | Overlapping claims **fail** the build |
| [6.2](#62-java-and-kotlin-source) | `android.contributes.src` | Java/Kotlin source under an owned namespace | N/A — one producer owns the namespace |
| [6.3](#63-gradle-dependencies) | `android.contributes.gradle_dependencies` | A Gradle dependency coordinate | Versions are requests Gradle resolves; two declarations differing in `configuration` fail |
| [6.4](#64-maven-repositories) | `android.contributes.gradle_repositories` | A Maven repository URL | Bounded to declared groups; overlapping scopes fail |
| [6.5](#65-permissions-and-features) | `android.contributes.permissions`, `.features` | A `<uses-permission>` or `<uses-feature>` entry | Union; the application may suppress a permission |
| [6.6](#66-manifest-components) | `android.contributes.components` | An `<activity>`, `<service>` or `<receiver>` entry | Two producers naming the same class **fail** the build |
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

Rule 3's operand is a *pattern* rather than a name, so it needs one more step
before this rule applies: [§6.7](#67-shrinker-keep-patterns) defines what part
of a keep pattern is compared.

Rule 1's operands need one too, since a path is not a namespace. Each directory
listed in [§6.2](#62-java-and-kotlin-source)'s `java` or `kotlin` is a **source root**, and for
every file staged from it:

| Operand | How it is derived |
| --- | --- |
| the **path** namespace | the file's directory, relative to its source root, with `/` replaced by `.` — `java/org/example/mypkg/Bridge.java` under root `java` yields `org.example.mypkg` |
| the **declared** namespace | the `package` the file itself declares |

A consumer **MUST** check both against the owned namespaces, and **MUST**
reject, naming the distribution and the file:

- a file directly in a source root, whose path namespace is empty, or one
  declaring no `package` — the default package is contained by nothing;
- a path segment that is not a valid Java identifier
  (`[A-Za-z_$][A-Za-z0-9_$]*`), since it cannot name a package;
- a file whose two namespaces are not equal, on either language.

Comparison is **case-sensitive** throughout, as the platform's own is.

> **Note:** `javac` enforces the path-to-package correspondence itself and
> `kotlinc` does not, which is exactly why the equality check is stated here
> rather than left to the toolchain: a Kotlin file at
> `kotlin/org/example/mypkg/Bridge.kt` declaring `package org.other` compiles
> cleanly and lands a class outside the namespace its distribution claimed.
> Checking the path alone would miss it, and checking the declaration alone
> would let a file sit anywhere in the tree.

An owned namespace **SHOULD** be reverse-DNS. A consumer **SHOULD** warn on a
single-label one: it is ownable and collision-checked like any other, but it
claims a top-level name for one distribution, which makes accidental overlap
with a sibling project far likelier.


### 6.2 Java and Kotlin source

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

A dependency **MUST** be spelled in exactly one of two forms. The first is the
exact coordinate above. The second is a bounded range:

```toml
[[android.contributes.gradle_dependencies]]
module = "com.onesignal:OneSignal"
version = { at_least = "5.6.1", below = "6.0.0" }
```

| Field | Rule |
| --- | --- |
| `coordinate` | `group:artifact:version`. A **single-version request**: one version, named exactly, which Gradle may still resolve higher |
| `module` | `group:artifact`. `version` is **REQUIRED**, and **both** `at_least` (inclusive) and `below` (exclusive) are **REQUIRED** within it. A range open at either end is invalid. |
| `configuration` | Optional. `implementation` (default), `api`, `compileOnly`, `runtimeOnly`. A **closed** set. |

A consumer **MUST** reject an entry declaring both `coordinate` and `module`, or
neither. Changing versions (`-SNAPSHOT`), unbounded dynamic versions (`+`,
`latest.release`), and ranges spelled inside `coordinate` are invalid in either
form.

**Which form to choose, and why the bounded one is usually right.** Neither is
preferred in general, and the trade is not about precision — a `coordinate` is
a minimum too, and Gradle may resolve above it either way.

| | `coordinate` | `module` + `version` |
| --- | --- | --- |
| The version a reader sees | exactly what the producer tested | a range they must reason about |
| Upper bound | **none** | `below`, which Gradle enforces |
| When another distribution asks for a higher major | resolves up, silently | fails in Gradle, naming both requests |

If a producer's own contributed Java or Kotlin source calls the dependency's
API directly, a major-version bump of that dependency can break that source at
compile time — an incompatibility the producer's own code cannot survive. Only
the bounded form (`module` + `version`) can prevent it, since only it has an
upper bound (`below`) that Gradle will actually enforce; `coordinate` has none,
so Gradle can silently resolve past the boundary. This producer **SHOULD**
therefore use the bounded form.

`coordinate` fits the opposite case: a dependency the producer bundles but
never compiles anything against — nothing the producer wrote calls its API, so
a major bump elsewhere in the graph cannot break code that never referenced it
in the first place.

> **Note:** Here is the failure `below` prevents. Two independently authored
> packages end up in one application. One of them requires a newer major of a
> shared library; Gradle picks that newer major for the whole app. The other
> package never asked for an upper bound, so it now compiles against a version
> of the library it never tested against — the build may fail against a moved
> API, or it may succeed and misbehave at runtime instead. Either way, the only
> name in the failure is a Gradle module; neither Python distribution is
> mentioned, because neither ever appears to Gradle. Setting `below` gives
> Gradle a version it will actually refuse, which turns this into an ordinary
> resolution failure — one [§6.3](#63-gradle-dependencies) can then attribute
> to the distributions that declared the conflicting requirements.

**The configuration set is closed, and deliberately not the platform's own.**
Adding a coordinate to `annotationProcessor`, `kapt` or `ksp` makes the build
*run code from that artifact*. A producer **MUST NOT** declare a processor
configuration, and a consumer **MUST** reject one, naming the distribution. The
four names above add a dependency and execute nothing.

**Two declarations of one module must agree on `configuration`.** Where two
distributions declare the same `group:artifact` with different `configuration`
values, a consumer **MUST** fail, naming both distributions and the module.
Equal values coalesce.

**Within one sidecar, a module is declared once.** Two entries naming the same
`group:artifact` — in either form, or one of each — **MUST** be rejected,
naming the distribution and the module, unless they are identical in every
field, in which case the duplicate coalesces. A producer contradicting itself is
a mistake to report, not a composition to resolve, and it is the one duplicate
case with a single author who can fix it.

**Across sidecars, every request goes to Gradle as declared.** Two
distributions may name one module in different forms — an exact `coordinate`
against a bounded range, or two ranges — and this document defines no second
resolver: Gradle selects, on the terms
[§6.3](#63-gradle-dependencies) already fixes, and either finds a version
satisfying every request or fails. **When it fails, a consumer MUST name every
distribution whose declaration contributed to the failure**, together with the
module and each declared form. Gradle's own message names Maven coordinates and
nothing else; only the consumer knows which Python distributions asked for them,
and an unattributed conflict is the failure this convention exists to prevent
a person from having to trace by hand.

> **Note:** The conservative rule, deliberately. `api` and `implementation`
> differ only in what they expose downstream, so a widest-wins merge would be
> defensible — but it would silently put a dependency on the application's
> compile classpath because some transitive producer asked for `api`. Failing
> tells two producers to agree, which is cheap, and can be relaxed if a real
> composition needs it.

**A declared version is a minimum, not a pin — within whatever bound it
states.** Gradle may select a higher version when something else in the graph
requires it: freely above a `coordinate`, which states no ceiling, and only
below `below` in the bounded form, where a request past the ceiling has no
solution and fails instead. A consumer **MUST NOT**
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
- record a **SHA-256** per resolved artifact — over the artifact's bytes as
  downloaded — verify each one on subsequent builds, and fail on a mismatch,
  naming the artifact and the distribution that declared it.

The algorithm is named rather than left to the consumer for the same reason
[§9.3](#93-hashed-inputs) names one: a record whose digests two implementations
compute differently cannot be compared, and comparing records against a shared
resolution is the whole point of locking.

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
`modules` (`group:artifact` pairs) is **REQUIRED**. `url` **MUST** be an
`https` URL; a consumer **MUST** reject any other scheme, naming the
distribution and the URL. The scheme is compared **case-insensitively**, as
[RFC 3986](https://www.rfc-editor.org/rfc/rfc3986#section-3.1) defines it, so
`HTTPS://` is the same scheme and is valid; nothing else about the URL is
normalized.

**The normative requirement is bounded participation.** The contributed
repository **MUST NOT** participate in resolution for anything outside the
declared groups or modules. A consumer implements that with its build system's
native mechanism; Gradle's repository content filtering expresses exactly this.

**Every entry is matched exactly, and a group is not a prefix.** A `groups`
entry names one Maven group ID and nothing beneath it: `groups =
["org.example"]` admits `org.example:widget` and **MUST NOT** admit
`org.example.tools:widget`. A `modules` entry names one `group:artifact` pair
exactly. A producer whose artifacts span several groups lists each one. A
consumer **MUST** implement this with an exact-match mechanism — Gradle's
`includeGroup` and `includeModule`, never `includeGroupByRegex` or a prefix
test.

> **Caution:** Prefix matching is the difference between admitting one vendor's
> artifacts and admitting every group anyone can register beneath a name the
> repository does not own. A repository scoped to `com.example` by prefix serves
> `com.example.anything`, and dependency confusion is exactly the substitution
> of an unexpected coordinate under an expected-looking name. Exactness also
> makes the overlap rule below decidable: two sets of literal strings either
> intersect or they do not.

**Overlapping scopes are rejected.** Two contributed repositories whose scopes
intersect **MUST** fail, naming both distributions and the contested
coordinates, unless they declare the same `url`, which is not a conflict. Two
scopes intersect when some coordinate is admitted by both: the same group ID in
`groups`, the same pair in `modules`, or a `modules` entry whose group another
repository names in `groups`.

**Two distributions may declare the same repository, and it merges by one
rule.** Repository identity is the `url`, compared with its scheme
case-insensitively and the rest byte-for-byte; a consumer **MUST NOT** normalize
further, since a trailing path segment is a different repository. For entries
sharing that identity:

| Field | How it merges |
| --- | --- |
| `groups`, `modules` | **Union.** Each distribution's bound is added; the result admits what any of them declared, and the overlap rule above does not apply between them |
| `credentials_required` | **Any `true` wins.** A repository one distribution says is authenticated is authenticated |
| `reason` | **Every one is kept**, each attributed to the distribution that wrote it, in the record and the report |

A consumer **MUST NOT** substitute Gradle's `exclusiveContent` for content
filtering.

> **Caution:** `exclusiveContent` is a different and stronger policy: it
> additionally makes the declared modules resolvable *only* from that
> repository, which can change first-time resolution results. Substituting it
> would make the same sidecar resolve differently depending on which mechanism
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

The application's answer, keyed by the repository `url`, is a *reference* —
here, the name of an environment variable the build environment already
provides — never the secret itself:

```toml
# the application's own pyproject.toml
[tool.examplebuild.android.repository_credentials."https://api.mapbox.com/downloads/v2/releases/maven"]
username = "mapbox"
password_env = "MAPBOX_DOWNLOADS_TOKEN"
```

The exact keys under an entry are the consumer's own spelling — a username and
a password-by-reference is one shape a conforming consumer might choose, not a
form this document mandates. What is fixed is the property this example
shows: the value the application writes is a pointer to where the real
credential lives, resolved at build time, never the credential in the file
itself.

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

**Features are never required.** `required` is not a field of a feature entry: a
producer **MUST NOT** declare it, and a consumer **MUST** reject it with a
diagnostic naming this rule — not the generic unknown-key message
([§4.4](#44-unknown-declarations-fail-closed)), which would send a producer
looking for a typo. A consumer **MUST** treat every producer-declared feature as
`required = false` and **MUST NOT** promote one on a producer's declaration
alone.

> **Note:** Whether an application *requires* Bluetooth or merely uses it when
> present is a property of the application. A producer promoting a feature to
> required would silently remove the application from devices lacking that
> hardware.

**Application-side suppression.** A consumer **MUST** provide a way for the
application to suppress any contributed permission. A suppressed permission
**MUST** be absent from the **effective merged manifest**, and the suppression
**MUST** appear in the record and report.

> **Note:** Suppression reaches the permission and stops there. Android derives
> *implied features* from certain permissions, and an earlier draft of this
> section had a consumer withdraw those too — which would have meant
> implementing the platform's permission-to-feature table, the vendor
> vocabulary the [Non-goals](#non-goals) exclude, for no benefit. A leftover
> feature restricts nothing: every feature this section admits is
> `required = false`, so it filters no device and grants no capability. The one
> case where a feature does restrict installation arrives inside a resolved
> artifact, and [§9.4](#94-what-resolved-artifacts-bring-with-them) gates it
> explicitly.

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

> **Example:** [Plyer](https://github.com/kivy/plyer) is a facade exposing many
> optional platform features — GPS, camera, accelerometer — behind one API, and
> declares the permission each feature needs. An application using Plyer only
> for its accelerometer has no use for the location permission its GPS feature
> declares, and can suppress it here; calling Plyer's GPS API afterward is then
> exactly the "fail or degrade" case above. [§12](#12-guidance-for-package-authors)
> covers the producer's side of this shape — splitting a facade like this into
> per-feature distributions so suppression is rarely needed in the first place.

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

> **Note:** `provider` is deliberately absent, and **not** because a producer
> cannot name an authority. AGP's `${applicationId}` placeholder makes
> `${applicationId}.mypkg.provider` perfectly deterministic, and AndroidX
> Startup's own manifest uses exactly that form. The reason is what a
> `<provider>` *does*: Android instantiates it before `Application.onCreate`,
> ahead of any application code. Registering one is therefore the startup
> execution seam [§11](#11-out-of-scope) defers, reached through a manifest
> attribute rather than through a hook — which is how Sentry initializes today.
> Admitting it here would grant that capability without deciding to, and the
> costs are asymmetric: excluding it costs each integrating application one
> manual step, once, while including it grants an unconditional execution seam
> to every transitive dependency. A producer that needs a provider declares an
> action ([§5.3](#53-actions)) meanwhile, with the manifest entry in
> `instructions`.
>
> **What would reopen it:** a producer that needs early initialization, whose
> vendor provides no declarative loader of its own, and for which publishing a
> Maven artifact is not reasonable. One such case justifies the narrow form —
> registration into AndroidX App Startup's shared `InitializationProvider`,
> where ordering and laziness are the platform's problem rather than this
> document's. Two justify reopening the general question, and it belongs to the
> lifecycle decision in [§11](#11-out-of-scope) rather than to this table.

**`view_links` and `intent_filters` are sub-tables of one component entry, not
tables of their own.** Both are spelled
`[[android.contributes.components.view_links]]`, and TOML attaches an
array-of-tables to the entry that most recently opened above it — so such a
block belongs to the `[[android.contributes.components]]` entry it follows, and
moving it below the next component silently makes it that component's instead.
The indentation in this document's examples is a reading aid with no meaning to
a parser. A producer that wants two components with filters writes each
component's filters directly beneath it.

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
own, written exactly as the platform defines it, and the consumer writes it
through without needing to know the value
([§4.4](#44-unknown-declarations-fail-closed)). Android also requires the matching
`FOREGROUND_SERVICE_*` permission, which is an ordinary
[§6.5](#65-permissions-and-features) contribution, and a producer declaring a
type **SHOULD** declare that permission in the same sidecar. A consumer
**SHOULD** warn when one appears without the other (8.S13), **except where the
declared type is one the platform exempts from a type permission** — today that
is `shortService`, and only that.

> **Note:** This is a warning, not a build failure, because turning it into one
> would require this document to maintain Android's own type-to-permission
> mapping — and that mapping is not fully mechanical. Most names line up
> directly (`mediaProjection` needs `FOREGROUND_SERVICE_MEDIA_PROJECTION`), but
> `shortService` needs no permission at all, and elsewhere on the platform is
> free to add exceptions like it. If this document encoded that mapping and
> got a case wrong, a consumer would fail a build that Android would have
> accepted — a false failure caused by this specification's own guess, not by
> anything the producer did.
>
> The warning avoids needing the mapping at all: it only checks whether a
> type was declared with *no* `FOREGROUND_SERVICE_*` permission alongside it —
> a real and common mistake — without claiming to know which specific
> permission that type needs. That is enough to catch the omission before it
> surfaces as the platform refusing the service at runtime, without risking a
> failure this document cannot actually justify.
>
> The one exemption is named because otherwise the advisory is unsilenceable
> for a legitimate producer: a `shortService` needs no type permission, so a
> warning about its absence can only be answered by declaring a permission the
> service does not use. One string is a far smaller obligation than the mapping,
> and it is stated as *what the platform exempts today* rather than as a closed
> set. If Android exempts another type, a consumer warns until it learns the
> new name — a false warning on an advisory check, which is the residual this
> design accepts and a blocking check could not.

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

**What this gate does not reach.** It binds only an export a *sidecar*
declares directly. A producer publishing the same component inside a compiled
Maven artifact, and declaring only the coordinate, gets it exported with no
approval step at all: AGP merges that artifact's own manifest automatically,
and nothing here ever runs, because nothing was declared through the
mechanism this gate polices. Approval is therefore **not required** through
that path — this convention has no way to block content already baked into a
compiled artifact the way it can block text in a sidecar. What it still
requires, per [§9.4](#94-what-resolved-artifacts-bring-with-them), is that
such a component be **reported** just as visibly as a sidecar-declared export
— not buried as a minor line — so the application author sees it even though
nobody had to approve it. Attribution
and review are what this convention offers for artifact content; restriction
is not.

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
- The fields are Android's own `<data>` attribute names in snake case. Only
  `scheme` is **REQUIRED**; `host`, `port`, `path`, `path_prefix`,
  `path_pattern`, `path_suffix`, `mime_type` and every other `<data>` attribute
  the platform defines are equally declarable.
- **An unrecognized attribute here is written through, not rejected**, and this
  is the one exception to [§4.4](#44-unknown-declarations-fail-closed)'s rule
  that an unknown key in a platform table fails closed. The names belong to
  Android, which adds to them — `ssp`, `ssp_prefix` and
  `path_advanced_pattern` all postdate the attributes above — and
  [§10](#10-versioning) already treats `<data>` attributes as pass-through
  vocabulary that needs no contract minor. The exception reaches the attributes
  of a `view_links` entry and nothing else.
- **The platform attribute name is derived mechanically**, so that two
  consumers write the same manifest: lower-case the first `_`-separated
  segment, capitalize the first letter of each later segment, join them, and
  write `android:<name>`. `path_prefix` becomes `android:pathPrefix`,
  `mime_type` becomes `android:mimeType`, `ssp` stays `android:ssp`. A consumer
  **MUST** reject a key that is not
  `[a-z][a-z0-9]*(_[a-z0-9]+)*`, naming the distribution and the key —
  the conversion is defined only for that shape.
- Every attribute's value is a **string**: a literal, or an inline application
  value ([§5.5](#55-value-kinds)). A consumer **MUST** reject any other TOML
  type, naming the distribution and the attribute.
- The consumer **generates** the filter: `android.intent.action.VIEW`, the
  `DEFAULT` and `BROWSABLE` categories, and one `<data>` element. Actions and
  categories are not spellable; they are implied by the type.
- The record and report **MUST** show the link data alongside the export.

> **Note:** The cost of the exception is the same one
> [§4.4](#44-unknown-declarations-fail-closed) accepts for pass-through values:
> a misspelled `path_prfix` reaches the manifest as `android:pathPrfix` and
> fails in AAPT rather than against the sidecar. What keeps that traceable is
> that the attribute and the distribution that declared it are in the record.
> Enumerating the attributes instead would buy a better message for a typo and
> charge a contract minor every time Android adds a `<data>` name — the
> maintenance trade this document makes the other way everywhere else.

Verified App Links are **not contributable**. `android:autoVerify` requires an
`assetlinks.json` file on the application's own domain, which is application
infrastructure. State the need as an action ([§5.3](#53-actions)).

**Putting the pieces together.** A browser-return activity is three
declarations in one sidecar — the component, the value its filter splices in,
and the link itself — satisfied by two answers from the application.

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

[[android.requires.application_value]]
id = "oauth_redirect_scheme"
kind = "inline"
reason = "The redirect URI scheme registered with your OAuth provider"
placeholder = "<TODO: your registered redirect scheme>"
```

```toml
# the application's configuration — two separate answers
[tool.examplebuild.android.exported_components]
"org.example.mypkg.RedirectActivity" = true

[tool.examplebuild.native.some-oauth-sdk.android.application_values]
oauth_redirect_scheme = "myapp-oauth"
```

The consumer combines both into the generated manifest — the export approval
and the spliced-in scheme:

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

> **Note:** Neither a plain Gradle project nor a sidecar-based one asks anyone
> to hand-write that XML. Gradle solves it the same way: AppAuth-Android ships
> the intent filter pre-written, with a placeholder for the one value the
> application supplies. `view_links` reproduces that split — the producer
> supplies the filter's shape, the application supplies one value, and the
> consumer does the substitution.

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
  ([§6.1](#61-ownership) rule 3), by the rule below.
- **`[[…r8.keep]]`** — a pattern belonging to a declared dependency.
  `from_dependency` **MUST** match a dependency the same sidecar declares. A
  consumer **MUST** evaluate the pattern against the **effective compilation
  classpath** and reject the entry when any class it matches originates outside
  that dependency's resolved artifacts — a listing of archive contents, not a
  parser — naming the distribution, the pattern, and the artifact the stray
  class came from.

**How a pattern is compared to a namespace.** A pattern is not a class name, so
[§6.1](#61-ownership)'s segment containment needs an operand. It is the
pattern's **literal prefix**: the longest run of leading dot-separated segments
in which no segment contains a wildcard character — `*` or `?`. A consumer
**MUST** compute it that way and **MUST** reject a `keep_classes` pattern whose
literal prefix an owned namespace does not contain, naming the distribution and
the pattern.

| Pattern | Literal prefix | Against `owns = ["org.example.mypkg"]` |
| --- | --- | --- |
| `org.example.mypkg.**` | `org.example.mypkg` | accepted |
| `org.example.mypkg.Foo` | `org.example.mypkg.Foo` | accepted |
| `org.example.mypkg.Api*` | `org.example.mypkg` | accepted |
| `org.example.**` | `org.example` | **rejected** — wider than the claim |
| `org.example.my*.Foo` | `org.example` | **rejected** — the wildcard segment ends the prefix |
| `okhttp3.**` | `okhttp3` | **rejected** — use `[[…r8.keep]]` |
| `**` | *(empty)* | **rejected** — an empty prefix is contained by nothing |

> **Note:** Truncating at the first wildcard segment rather than trying to
> decide whether `org.example.my*` can only match owned packages is what keeps
> this implementable in a few lines and identical between two consumers. It
> rejects a pattern that would in fact have been safe, and the producer's fix is
> to write the segment out.

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
value and reports the override. Equality is by type as well as content: `1` and
`"1"` are different declarations of one key and **MUST** fail, even though
`android:value` would render them the same way. An application-supplied value is
always a string ([§5.2](#52-values)), so it coalesces only with a string.

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
- A consumer **MUST** report every contributed entry with its `reason` and its
  distribution — in the report, not only in the record. Union merging without a
  veto means the report is the application's only view of what its dependencies
  ask to see.

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

## 7. iOS declarations

What a producer contributes on iOS. Requirements on the application are
[§5](#5-requirements-on-the-application)'s, whichever platform they name.

| § | Key | Declares | How conflicts resolve |
| --- | --- | --- | --- |
| [7.1](#71-symbol-prefixes) | `ios.contributes.src.symbol_prefixes` | A declared prefix for contributed Swift type names | N/A — a diagnostic aid, not an enforced claim |
| [7.2](#72-swift-packages) | `ios.contributes.swift_packages` | A SwiftPM package dependency | Locked to the resolved graph; a branch or path dependency **fails** |
| [7.3](#73-swift-source) | `ios.contributes.src` | Raw Swift source, compiled into the application target | N/A — no ownership or collision check |
| [7.3](#73-swift-source) | `ios.contributes.accessed_api_types` | A required-reason API disclosure for contributed source | Union; `reasons` de-duplicated per `type` |
| [7.4](#74-infoplist) | `ios.contributes.info_plist.values` | A scalar `Info.plist` key | Equal values coalesce, differing values **fail**, the application's own value always wins |
| [7.4](#74-infoplist) | `ios.contributes.info_plist.append`, `.skadnetwork_identifiers` | An array-valued `Info.plist` key, or an `SKAdNetworkItems` entry | Union |
| [7.5](#75-python-modules) | `ios.contributes.python_modules` | A Python-extension-module registration (name and init symbol) | Two producers naming the same `name` **fail** |
| [7.6](#76-objective-c-categories) | `ios.contributes.objc_categories` | A request to load Objective-C categories from static libraries | Union; one producer asking is enough |

### 7.1 Symbol prefixes

Contributed Swift compiles straight into the application's single target. iOS
lacks Android's per-package namespace to keep declarations apart.

```toml
[ios.contributes.src]
swift = ["swift"]
symbol_prefixes = ["MyPkg"]
```

A producer that contributes Swift source ([§7.3](#73-swift-source)) **SHOULD** do two
things: name every class, struct, enum, and protocol it declares — its
*types*, and in particular their `@objc` runtime names — with a consistent
prefix, and declare that same prefix here.

`symbol_prefixes` sits inside `[ios.contributes.src]` because it describes
contributed source and means nothing without it. A consumer **MUST** reject it
in a sidecar that contributes no Swift source, naming the distribution — the
same rule `accessed_api_types` carries, for the same reason.

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

`url` **MUST** be an `https` URL, on [§6.4](#64-maven-repositories)'s terms —
including that the scheme is compared case-insensitively: a
consumer **MUST** reject any other scheme, naming the distribution. `products`
is **REQUIRED** and **MUST** be a non-empty list of product names the package
vends; the consumer links exactly those and no others. A package whose products
are not stated is one whose effect on the application binary the record cannot
describe.

`requirement` **MUST** be exactly one of:

| Form | Meaning |
| --- | --- |
| `{ exact = "1.2.3" }` | That version only |
| `{ from = "1.2.0" }` | SwiftPM's up-to-next-major range |
| `{ revision = "<commit>" }` | A specific commit |

The grammar is closed: `branch` is not one of the three, so a consumer **MUST**
reject a sidecar declaring it, naming the distribution.

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
declaring distribution.

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

A **branch** dependency is rejected on the same terms, and in both places. The
sidecar grammar excludes it, and a consumer **MUST** additionally reject a
resolved graph in which any package — the one a sidecar named or a transitive
one — is pinned to a branch rather than to a version or a revision, naming the
distribution that declared the top-level package and the offending package.

In practice this is close to unreachable: SwiftPM itself refuses to resolve a
version-pinned package (which is what `exact` or `from` produces) against a
transitively branch-pinned one, so a producer would have to encounter a vendor
package that violates SwiftPM's own rules to hit it. The rule is stated anyway,
because that guarantee is SwiftPM's to keep rather than this specification's,
and because a reproducibility claim that rests on another tool's behavior should
say what happens when the behavior is not there. A branch is a moving pointer;
the record cannot pin it, which is the whole reason `revision` exists.

**Two distributions may declare the same package.** Their entries are combined
into one SwiftPM graph and **SwiftPM resolves the constraints**; this document
defines no second resolver. Package identity is the resolved package's, not the
sidecar's: `name` is a local handle, so two producers may call one package
different things without that being a conflict, and neither name reaches
SwiftPM.

- Compatible requirements resolve — `{ exact = "1.2.3" }` against
  `{ from = "1.2.0" }` selects 1.2.3.
- Incompatible ones fail in SwiftPM — `{ exact = "1.2.3" }` against
  `{ exact = "1.2.4" }` has no solution.
- `products` are unioned: the application target links every product any
  distribution asked for.

A consumer **MUST** record every distribution that requested a package, and
**MUST**, when resolution fails, name every distribution whose declaration
contributed to the failure — the obligation
[§6.3](#63-gradle-dependencies) carries on the Gradle side, for the same
reason: SwiftPM's own message names packages, and only the consumer knows which
Python distributions asked for them.

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

**A private package is declared, not smuggled.** Where the repository requires
authentication, set `credentials_required = true` on the entry:

```toml
[[ios.contributes.swift_packages]]
name = "VendorKit"
url = "https://git.example.com/vendor/vendorkit"
requirement = { exact = "3.1.0" }
products = ["VendorKit"]
credentials_required = true
```

Every rule [§6.4](#64-maven-repositories) states about an authenticated Maven
repository applies here unchanged, down to the shape of the application's own
answer — a reference keyed by the package `url`, not a literal secret,
exactly as §6.4's worked example shows: a producer **MUST NOT** put a
credential in the sidecar under any spelling; the application supplies one by
indirection ([§2.2](#22-how-the-application-answers)), joined by the package
`url`; `reason` on the entry — **REQUIRED** when `credentials_required` is set
— says what credential is needed and where to obtain it; a consumer **MUST**
fail when none is configured, naming the distribution, rather than surfacing
SwiftPM's own authentication error; and it **MUST NOT** write the credential
into the generated project, the record, or any diagnostic.

`reason` is **OPTIONAL** on a package that declares no `credentials_required`,
and a consumer makes no use of it there. The field is not otherwise reserved:
[§6.4](#64-maven-repositories), whose rules this section imports unchanged,
requires a `reason` on every repository, so a producer writing one here by habit
has not made an error.

Where two distributions declare the same package `url`,
[§6.4](#64-maven-repositories)'s merge rule applies unchanged: any `true` makes
the package authenticated, and every `reason` is kept and attributed. The
`products` union of [§7.2](#72-swift-packages) is that rule's counterpart for
what gets linked.

> **Note:** An `ssh` or `scp`-style git URL is refused rather than treated as
> the authenticated form, even though SwiftPM accepts one. The credential then
> lives in whatever key the build host's git configuration happens to hold: the
> requirement never appears in a report, no record can say the build depended on
> it, and a machine without the key gets a clone failure naming a host. An
> `https` URL with `credentials_required` puts the same fact where every other
> authenticated dependency in this document already is.

Swift Package Manager is the **RECOMMENDED** channel for anything larger than a
few glue files.

### 7.3 Swift source

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
  distribution's in normalized distribution-name order
  ([§1](#1-terminology)), with the `reasons` for one `type` unioned and
  de-duplicated.

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

- **`values`** — scalar keys, set verbatim. A consumer **MUST** fail on two
  distributions setting the same key to different values, naming the
  distributions. Two distributions setting the same key to the **same** value
  coalesce, preserving both provenance records. A key the **application** also sets is the application's:
  the consumer **MUST** keep the application's value and report the override.
- **`append`** — array-valued keys. Contributions from all distributions and the
  application are concatenated and de-duplicated in a deterministic order: the
  application's entries first, then each distribution's in normalized
  distribution-name order — **normalized** as [§1](#1-terminology) defines it,
  since an order fixed by a name that two consumers spell differently is not
  fixed at all.

**Consumer-managed keys are refused in every channel.** The identity and version
keys a consumer derives from the application's own project settings —
`CFBundleIdentifier`, `CFBundleShortVersionString`, `CFBundleVersion`,
`MinimumOSVersion` — are the consumer's to write. It **MUST** reject one in
`values`, in `append`, or as the `key` of an `info_plist` value
([§5.5](#55-value-kinds)), naming the distribution and the key.

**A key belongs to one mode, and the requirement side counts.** Across the
effective set — every distribution and the application — a key declared under
`append` is an array key; a key declared under `values`, **or delivered by a
value of kind `info_plist`** ([§5.5](#55-value-kinds)), is a scalar one, since
the consumer writes one string to it either way. A consumer **MUST** fail when
one key is claimed both ways, naming both declarers, and **MUST NOT** merge a
scalar into an array or an array into a scalar.

> **Note:** This is the general form of the rule
> `skadnetwork_identifiers` needed as a special case, and it deliberately
> requires no list of which Apple keys hold arrays. The declarations say which:
> `LSApplicationQueriesSchemes` is an array key because producers declare it
> under `append`, not because this document knows Apple's schema. Two
> declarations that disagree about a key's shape have no unambiguous plist form
> and no order-independent winner, which is the same ground
> [§5.2](#52-values)'s differing-content rule stands on.
>
> `LSApplicationQueriesSchemes` is also the likeliest thing the requirement half
> catches. It is the array key producers actually contribute, and a value of
> kind `info_plist` naming it would ask the consumer to write one string where a
> list belongs — the array-against-scalar collision this rule closes on the
> contribution side, arriving through the other channel.

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
`values` key whose name ends in `UsageDescription`, naming the distribution and
directing the producer to [§5.2](#52-values)'s `usage_description` kind. The
suffix is the whole test — every purpose string Apple defines carries it — and
a vaguer one ("or anything that is otherwise a purpose string") would be
unimplementable, leaving two consumers to reject different keys. That text is user-facing,
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
| `CFBundleURLTypes` | **make the application externally reachable** — register it as the handler for a URL scheme, which any other app on the device can then open it with |
| `NSUserActivityTypes` | the same, for activities the system and other apps hand to it |

The list is closed, and a minor revision may extend it. Three things put a key
on it — a producer's entry **changes what the application may do, who may
install it, or what may reach it from outside** — and none of them is that the
key is array-valued. `LSApplicationQueriesSchemes` does the opposite of the last
one: it asks what else is installed, reaches nothing, and stays an ordinary
contribution.

> **Note:** The last two rows are iOS's answer to
> [§6.6](#66-manifest-components)'s exported component, which needs the
> application's explicit approval before a consumer will register it. A URL
> scheme is the same surface reached by a different mechanism — an intent
> filter is to an Android activity what a claimed scheme is to an iOS bundle —
> so it takes the same route back to the application, as an action the author
> acknowledges. Version 1 has no per-key approval gate on the plist side, and
> inventing one to cover two keys would be a second gate to keep in step with
> the first.

**One key space, one merge rule, wherever a key arrives from.** An
`Info.plist` key a producer contributes through `values` and a key another
producer delivers through [§5.2](#52-values)'s `info_plist` kind are the same
plist entry, and they merge on the rule above: equal content coalesces with both
provenance records kept, differing content **MUST** fail naming both
distributions, and a key the application sets itself is the application's. A
supplied value is always a string ([§5.2](#52-values)), so it coalesces with a
contributed entry only where that entry is a string of equal content — `1` and
`"1"` differ.

> **Note:** [§6.8](#68-manifest-meta-data) says exactly this about the Android
> manifest's `<meta-data>`, and the two are deliberately identical. An earlier
> draft made the iOS case fail on any overlap, which is stricter for no stated
> reason and would have made one channel's answer depend on which platform it
> was written for.

**`LSApplicationQueriesSchemes` is disclosed like a `<queries>` entry.** A
consumer **MUST** report every contributed entry of that key in the record and
report, naming the distribution that declared it, rather than folding it into a
generic plist diff. It is the same fact
[§6.9](#69-package-visibility) requires a `reason` for on Android — a producer
asking what else is installed on the user's device.

> **Note:** The `reason` itself has nowhere to go here: `append` is a plain
> key-to-array table with no room for per-entry prose, and giving this one key a
> structured form would be modelling a single Apple key. The load-bearing half
> is the attribution, which the record carries either way, and an application
> that wants the *why* has the distribution to ask.

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

> **Note:** The two conditions catch a **malformed** identifier — wrong case, a
> missing suffix — and nothing more. They cannot catch a well-formed identifier
> that is simply the wrong one: these are values Apple issues, and
> `su67r6k2v4.skadnetwork` is as valid a string as `su67r6k2v3.skadnetwork`.
> That failure stays silent, losing attribution for one network's installs, and
> the record is the only place it is visible at all.

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
- **The implementing product must be one the sidecar links.** A producer
  **MUST** list, in that package's `products`, the product whose object code
  exports the module's `init` symbol; and a consumer **MUST** link every
  product the declaring sidecar named for that package into the application
  target, rather than only those some other sidecar also asked for. A consumer
  **SHOULD** verify the symbol is present in the linked binary where its
  toolchain can, and report its absence against the declaring distribution
  (8.S15).
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

> **Note:** `products` is the only binding between a registration and the code
> behind it, which is why the obligation is stated in both directions. A package
> may vend several products, and `swift_package` names the package rather than
> the product: without the producer's half, a sidecar can register `web_views`
> against a package whose linked products contain no `PyInit_WebViews` at all,
> and without the consumer's, a product the producer did list could go unlinked
> because no other distribution asked for it. Either way the build succeeds and
> the failure is an `ImportError` on device, which is the outcome this table
> exists to prevent. A `product` field on this table is the shape to reach for
> if a real package makes the package-level binding ambiguous in practice;
> nothing in the cases examined does.
>
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
- Only `true` says anything. A consumer **MUST** reject
  `objc_categories = false`, naming the distribution: there is no way to require
  that categories *not* be loaded — one other producer asking is enough — so the
  declaration would be a request the model cannot honour. This is
  [§5.1](#51-build-floors)'s rule for a boolean floor, for the same reason.
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

> **Caution:** This checklist can drift from the rules it restates. A
> requirement citing the right section does not guarantee it carries
> everything that section says. Reviewing a change here means checking each
> obligation against its section, not just that a citation exists.

Numbering is stable: a later revision appends rather than renumbering, so a
conformance claim can name the requirements it meets.

### 8.1 Conformance is per platform

A consumer that builds only for Android is not obliged to implement Xcode, and
one that builds only for iOS is not obliged to implement Gradle. **Conformance
is the core plus at least one platform profile**, and a consumer states which:
*a native-integration v1 Android consumer*, or *v1 Android and iOS*.

| Profile | Requirements |
| --- | --- |
| **Core** — every consumer | 1–22, 24, 26, 38–40, 42, 43 |
| **Android** | 23, 25, 27–32, 41, 44, 45 |
| **iOS** | 33–37, 46 |

Requirement 24 appears in the core, and **only** there, because contributed
source exists on both platforms — [§6.2](#62-java-and-kotlin-source) and [§7.3](#73-swift-source) —
and every consumer excludes it from the Python payload; its `javac` charset
clause binds only a consumer that compiles Java, which is why the Android row
does not repeat it. Requirement 26 locks whichever native graphs the consumer
resolves. Every requirement appears in exactly one row.

**A consumer MUST fail when asked to build for a platform whose profile it does
not implement** (requirement 9's second clause), rather than building it while
ignoring that platform's declarations. This is distinct from
[§4.4](#44-unknown-declarations-fail-closed)'s permission to ignore a platform
table during a build that *does* implement that platform's profile — §4.4
covers the other platform's tables in a build you support; this covers
attempting a platform you do not.

### 8.2 Dispositions, and what recording is not

A finding has one of two dispositions, named here so that two implementations
classify the same condition the same way:

| Disposition | Meaning | Produced by |
| --- | --- | --- |
| **blocking** | the build **MUST NOT** proceed | every numbered requirement below that says *fail* |
| **advisory** | reported; the build proceeds | the **SHOULD** list in [§8.5](#85-advisory-obligations) |

**Blocking and advisory classify findings, not requirements.** A numbered
requirement below that defines no finding is a **conformance obligation**: a
violation makes the consumer non-conforming, and carries no runtime disposition
unless the requirement explicitly says the build must fail. Requirement 45 is
the clearest case — a bootstrap either generates a `ComponentActivity` or does
not, and a consumer is not being asked to emit a diagnostic about itself.

> **Note:** This matters where a conformance suite is involved, because the two
> are checked differently. A finding is observed by running a build and reading
> what came out; an obligation is observed by inspecting what the consumer
> produced — the generated project, the payload it assembled, the record it
> wrote. Filing an obligation under *advisory* would say the build may proceed,
> which is not the question being asked about it.

**Recording is a separate axis, not a third disposition.** Most of what a
consumer writes to the integration record is not a finding at all: every
contribution, every satisfied requirement, and the resolved native graph are
recorded as a matter of course.

One case is worth naming because implementations miss it. An unsatisfied
**conditional** requirement ([§5.4](#54-how-a-requirement-is-satisfied)) is
recorded and reported, and is neither blocking nor advisory — it is not a
problem, it is an open question the application has not answered. A consumer
with only *error* and *warning* files it under one of them and is wrong either
way: as a warning it becomes noise to be silenced, and as nothing it stops being
the durable disclosure that was the point.

### 8.3 Thematic index

| Theme | Requirements |
| --- | --- |
| Discovery and the sidecar | 1–9 |
| Answering, reporting, and scaffolding | 10–11 |
| Never satisfy a requirement on the producer's authority | 12–16 |
| Composition between distributions | 17–22 |
| Generated project material | 23–37 |
| Recording, disclosure, attribution | 38–44 |
| The bootstrap | 45–46 |

### 8.4 Requirements

A conforming consumer **MUST**:

**Discovery and the sidecar**

1. Restrict candidate producers to the application's resolved dependency
   closure — evaluating environment markers and extras for the **target**
   platform and Python version, never for the build host — and never accept
   contributions from a distribution outside it, whatever else is installed
   ([§3.2](#32-resolution)).
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
7. Enforce the contract version gate including the minor, reject a malformed
   `contract` value, reject a sidecar that under-declares — by key, by table, or
   by a value from a closed vocabulary — and be able to state the contract it
   implements ([§4.3](#43-contract-version)).
8. Fail closed on an unrecognized key in a platform table it is building —
   excepting only a `view_links` attribute ([§6.6](#66-manifest-components)) —
   on an unrecognized top-level key that is not a table, and on a value from a
   closed vocabulary it does not implement — a value `kind`, a Gradle
   configuration, a capability key — substituting no default
   ([§4.4](#44-unknown-declarations-fail-closed), [§5.5](#55-value-kinds)).
9. Enforce `platforms` entirely: reject an empty list and a name this document
   does not define, reject a platform table for a name the key omits, and fail
   when building for a platform the key omits, naming the distribution and how
   it entered the closure. And fail, rather than building partially, when asked
   to build for a platform whose conformance profile it does not implement
   ([§4.5](#45-platform-support), [§8.1](#81-conformance-is-per-platform)).

**Answering, reporting, and scaffolding**

10. Provide a way for the application to answer **every** row of
    [§2.2](#22-how-the-application-answers)'s table — supply a value,
    acknowledge an action, **dismiss a conditional requirement**, suppress a
    contributed permission, approve an exported component, supply credentials
    for an authenticated repository or Swift package, **decide a resolved
    artifact's required feature**, and **choose which artifact supplies a
    colliding path** — each joined by the key that table names; apply the four
    answers joined by something other than `(distribution, id)` to **every**
    contributor of the name or path they address; and accept a
    build-time credential **by indirection** rather than only as a literal in a
    committed file ([§2.2](#22-how-the-application-answers),
    [§5.4](#54-how-a-requirement-is-satisfied)).
11. Report every unmet requirement, naming the distribution and the `reason` —
    or, for a floor, which carries none, the declared and configured values —
    and, for an action, the `summary` plus `instructions` and `acceptance`
    wherever the sidecar declares them, both being optional fields
    ([§2.3](#23-what-the-consumer-generates), [§5.1](#51-build-floors),
    [§5.3](#53-actions)).

**Never satisfy a requirement on the producer's authority**

12. Fail when the application's configuration is below a declared floor,
    reporting the declared and configured values; reject a non-integer Android
    floor and a malformed `deployment_target`, comparing the latter
    component-wise and numerically; reject a boolean floor declared `false`;
    never raise the application's configuration to satisfy a floor; and record
    and report every declared floor with its distribution, giving `target_sdk`
    the prominence [§5.1](#51-build-floors) requires.
13. Fail when a declared value is unsupplied, never treat a scaffolded
    placeholder as a supplied value, require `key` on every value kind but
    `inline` and reject it on that one, reject an `inline` value that
    neither a contribution references nor an action `uses`, and reject a `kind`
    declared in a table for the platform it does not belong to
    ([§5.2](#52-values), [§5.4](#54-how-a-requirement-is-satisfied),
    [§5.5](#55-value-kinds)).
14. Fail when an unconditional action is unacknowledged; record an unsatisfied
    conditional requirement without failing; take an acknowledgement as
    satisfying the requirement; and hold an acknowledged action unsatisfied
    while any value it `uses` is unsupplied
    ([§5.3](#53-actions), [§5.4](#54-how-a-requirement-is-satisfied)).
15. Never treat its own observation of the application's project as satisfaction
    of an action ([§5.4](#54-how-a-requirement-is-satisfied)).
16. Never **invent** the content of an application-owned artifact — an
    entitlement, a capability, a bundle file, a build target — on a producer's
    declaration alone. Placing a string the *application* supplied is exactly
    what [§5.5](#55-value-kinds)'s kinds are for and is not this
    ([§2.1](#21-design-principles)).

**Composition between distributions**

17. Fail when two values target the same `(kind, key)` with different content,
    naming both distributions, and coalesce them when the content is equal —
    comparing a supplied string against a typed contribution in the same key
    space by content *and* type ([§5.2](#52-values), [§6.8](#68-manifest-meta-data),
    [§7.4](#74-infoplist)).
18. Name the contributing distribution in **every** diagnostic it emits about
    declared material ([§2.1](#21-design-principles)).
19. Ignore entry-point groups for other major versions entirely, rather than
    attempting to read them ([§10](#10-versioning)).
20. Never modify a file the application owns unless the application asked it to,
    and never scaffold an action's acknowledgement other than commented out
    ([§2.3](#23-what-the-consumer-generates)).
21. Never execute, apply, or fetch anything named by `instructions` or
    `acceptance`; include both in the record's hashed inputs; and attribute both
    to the declaring distribution wherever it renders them, in the report and in
    every scaffolded block
    ([§5.6](#56-instructions-and-acceptance-criteria), [§9.3](#93-hashed-inputs)).
22. Reject two requirements in one platform table sharing an `id`; reject a
    `uses` entry naming no value the same sidecar declares for the same
    platform; and report two actions sharing a `slot` together, naming both
    distributions, without interpreting the slot
    ([§5](#5-requirements-on-the-application), [§5.3](#53-actions), [§5.7](#57-slots)).

**Generated project material**

23. Enforce every ownership rule, computing containment on dot-separated
    segments; derive a contributed file's namespace from its path relative to
    its source root and check it, its declared `package`, and their equality,
    case-sensitively; and fail on a collision naming the distributions
    responsible ([§6.1](#61-ownership), [§6.2](#62-java-and-kotlin-source)).
24. Compile contributed source with the application's own toolchain and exclude
    it from any Python payload, on both platforms; and, where it compiles Java,
    force UTF-8 for `.java` rather than the platform default
    ([§6.2](#62-java-and-kotlin-source), [§7.3](#73-swift-source)).
25. Reject a Gradle dependency declaring both or neither of `coordinate` and
    `module`, reject a changing or unbounded version, reject a processor
    configuration, reject two entries in one sidecar naming one module unless
    they are identical, fail when two declarations of one module disagree on
    `configuration` naming both distributions, name every distribution whose
    declaration contributed to a resolution failure, never convert a declared
    version into a `strictly` constraint, and show requested against resolved
    where they differ ([§6.3](#63-gradle-dependencies)).
26. Lock **whichever** native graphs it resolves — Gradle, SwiftPM, or both,
    transitives included — resolve from the record thereafter, record a SHA-256
    per Maven artifact and the declared checksum per Swift binary target, verify
    both on subsequent builds, and fail on a mismatch naming the artifact and
    the distribution. A single-platform consumer owes this for its own
    ecosystem's graph and nothing more
    ([§6.3](#63-gradle-dependencies), [§7.2](#72-swift-packages)).
27. Restrict a contributed repository to its declared groups or modules by
    **exact** match, never by prefix or pattern; reject a non-`https` URL;
    reject two whose scopes overlap at different URLs; never substitute an
    exclusivity mechanism for content filtering; report repositories with
    distinct prominence; reject a syntactically identifiable credential; fail
    when an authenticated repository has no credentials configured; merge two
    declarations of one `url` by unioning their scopes, taking any
    `credentials_required = true`, and keeping every `reason` attributed; and
    never persist a supplied credential anywhere
    ([§6.4](#64-maven-repositories)).
28. Merge permission attributes least-restrictively and report the merge;
    reject a producer-declared `required` on a feature and register every
    producer-declared feature `required = false`; and honor a suppression in the
    **effective merged manifest**, emitting a merger removal where a resolved
    dependency contributes the same permission
    ([§6.5](#65-permissions-and-features)).
29. Enforce component provenance and uniqueness, reject `foreground_service_type`
    on a non-service, fail when a component declaring `exported_required` has no
    application approval — never falling back to an unexported registration —
    and reject `view_links` or `intent_filters` in an invalid combination
    ([§6.6](#66-manifest-components)).
30. Validate `view_links` and generate their filters, including the action and
    the `DEFAULT` and `BROWSABLE` categories; write an attribute it does not
    recognize through, converting the snake-case key to the platform's
    attribute name by [§6.6](#66-manifest-components)'s rule and rejecting a
    key that rule does not cover or a value that is not a string; and show the
    link data and each `intent_filters` action in the record
    ([§6.6](#66-manifest-components)).
31. Validate shrinker keep patterns against owned namespaces by their
    wildcard-free literal prefix, reject a `from_dependency` keep whose pattern
    matches any class on the effective classpath originating outside that
    dependency's resolved artifacts, and apply keeps only when the application
    has enabled shrinking ([§6.7](#67-shrinker-keep-patterns)).
32. Merge contributed `meta_data` with [§5.2](#52-values)'s delivery as one key
    space, keeping and reporting the application's own entry where it sets the
    key; reject a `queries` entry declaring both or neither of `package` and
    `provider_authority`; and report every `queries` entry with its `reason` and
    its distribution ([§6.8](#68-manifest-meta-data), [§6.9](#69-package-visibility)).
33. Reject two Swift packages sharing a `name`, a missing or empty `products`,
    a non-`https` `url`, a `branch` requirement, and a resolved graph containing
    a path **or branch** dependency anywhere in it; apply
    [§6.4](#64-maven-repositories)'s credential and same-`url` merge rules to a
    package declaring `credentials_required`; and make visible in the record
    that a self-declared package is not pinned by the distribution's own
    version ([§7.2](#72-swift-packages)).
34. Reject `symbol_prefixes` ([§7.1](#71-symbol-prefixes)) and
    `accessed_api_types` ([§7.3](#73-swift-source)) from a sidecar contributing no
    Swift source, and merge what `accessed_api_types` declares into the
    application's `PrivacyInfo.xcprivacy` in the order
    [§7.3](#73-swift-source) fixes.
35. Enforce [§7.4](#74-infoplist)'s TOML-to-plist mapping; fail on two
    distributions setting one key differently, and on one key claimed both as
    an array (`append`) and as a scalar — `values` or a value of kind
    `info_plist` alike; keep and report the application's own value; reject a
    capability, external-reach or consumer-managed key wherever it arrives, in
    those three channels alike; reject a usage-description key in `values`, and
    a `usage_description` whose `key` does not end in `UsageDescription`
    ([§5.5](#55-value-kinds)); validate SKAdNetwork identifiers; render
    `SKAdNetworkItems` only from `skadnetwork_identifiers`; and report
    contributed `LSApplicationQueriesSchemes` entries naming the distribution.
36. Register declared Python modules against a Swift package the same sidecar
    declares, link every product that sidecar named for the package, reject a
    dotted or non-identifier `name`, fail on a duplicate module name, make each
    module importable from first use, and exclude `<name>.py` and `<name>.pyi`
    from the Python payload ([§7.5](#75-python-modules)).
37. Link the application target so Objective-C categories in statically linked
    libraries are loaded when any distribution asks, reject
    `objc_categories = false`, and report it naming the distributions that asked
    ([§7.6](#76-objective-c-categories)).

**Recording, disclosure, attribution**

38. Compute the resolution, compare it against the last accepted record, report
    the delta, require explicit acceptance — including on the first build — and
    update the **accepted resolution** only on acceptance, while persisting the
    application's own answers when they are given and never requiring
    acceptance of those ([§9.1](#91-the-lifecycle)).
39. Report the distribution, how it entered the closure, and the delta, keeping
    repository contributions, artifact-sourced material, unmet against
    conditional requirements, and **staged against remaining** distinct, for one
    platform's build ([§9.2](#92-the-report)).
40. Record a SHA-256 per input file, keyed by normalized relative path, and
    write every digest this document requires as 64 lowercase hexadecimal
    characters, unprefixed and unabbreviated ([§9.3](#93-hashed-inputs)).
41. Record and report every permission, feature and component declared by
    resolved Android artifacts' own manifests, attributed to the artifact;
    **fail** on a resolved artifact's `required="true"` feature until the
    application decides whether to keep or override it, resolving it
    automatically in neither direction and recording the decision; and report a
    resolved artifact's exported components with contribution-level prominence
    ([§9.4](#94-what-resolved-artifacts-bring-with-them)).
42. Never write an application-supplied credential or secret into the record, a
    report, or a diagnostic ([§9.5](#95-secrets-are-never-recorded)).
43. Make every row of [§9.6](#96-what-a-record-must-contain) recoverable from
    the record — every value and action with its state, and every
    application decision the integration as a whole carries: each permission
    suppression, export approval, required-feature decision and
    colliding-path choice, with what it affected and the date it was made.
44. Detect packaging collisions between the resolved artifacts of different
    distributions, resolve on its own authority only the packaging-metadata
    names [§9.7](#97-packaging-collisions) lists — never a file in a
    subdirectory of `META-INF/` — fail on any other colliding file the
    application has not chosen between, and record every collision against the
    distributions responsible ([§9.7](#97-packaging-collisions)).

**The bootstrap**

45. Make the Android activity its bootstrap generates an
    `androidx.activity.ComponentActivity` or a subclass
    ([§2.4](#24-obligations-on-the-consumers-bootstrap)).
46. On iOS, provide a documented means for application code to observe a URL
    callback delivered to the bootstrap's `application(_:open:options:)`,
    rather than consuming it
    ([§2.4](#24-obligations-on-the-consumers-bootstrap)).

### 8.5 Advisory obligations

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
| **S11** | Report the fully merged Android manifest's delta, beyond the per-artifact declarations requirement 41 requires | [§9.4](#94-what-resolved-artifacts-bring-with-them) |
| **S12** | Report consumer ProGuard rules embedded in a resolved `.aar` | [§9.4](#94-what-resolved-artifacts-bring-with-them) |
| **S13** | Warn when a component declares `foreground_service_type` and the same sidecar contributes no `FOREGROUND_SERVICE_*` permission — except for a type the platform exempts from one, today `shortService` | [§6.6](#66-manifest-components) |
| **S14** | Report a packaging collision detected between resolved Swift packages, which version 1 does not specify detection for | [§9.7](#97-packaging-collisions) |
| **S15** | Verify that a registered Python module's `init` symbol is present in the linked binary, and report its absence against the declaring distribution | [§7.5](#75-python-modules) |

> **Note:** [§9.4](#94-what-resolved-artifacts-bring-with-them) requires a
> consumer that stops at per-artifact declarations, rather than implementing
> S11, to say so in its own documentation. An advisory obligation quietly
> skipped is how a conformance claim overstates itself.

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

**Acceptance gates what producers originate, and nothing the application says
itself.** The record holds two kinds of thing, and only the first passes through
steps 2 to 4:

| | Contents | On a change |
| --- | --- | --- |
| **The accepted resolution** | every contribution, the hashed inputs, the resolved native graphs with their checksums and revisions, and the material resolved artifacts bring with them ([§9.4](#94-what-resolved-artifacts-bring-with-them)) | reported as a delta and **gated**: the build **MUST NOT** proceed until the application accepts it |
| **The application's answers** | supplied values, acknowledgements, dismissals, permission suppressions, export approvals, required-feature decisions, colliding-path choices | **recorded as they change**, with the date and the distribution version where [§9.6](#96-what-a-record-must-contain) requires them, and **MUST NOT** require acceptance of themselves |

A consumer **MUST** persist an answer when it is given, whether or not a
resolution is being accepted in the same build, and **MUST NOT** discard one
because the resolution has not changed.

> **Note:** Acceptance exists because a producer can change what an application
> ships without anyone asking. An answer is the opposite: the application is the
> accepting party, so requiring it to accept its own decision would be a
> confirmation dialog, and the click-through
> [§9.6](#96-what-a-record-must-contain) warns about is bought exactly this way.
> An answer still lands in a durable, diffable file — a suppression or an export
> approval is a decision review should see — but what it needs is a history, not
> a gate.
>
> The two halves are not independent: approving an export or deciding a required
> feature is what *unblocks* a contribution the resolution already carries as
> pending. Withdrawing such an answer changes the built surface, and the next
> build reports it as what it is — a change the application made, attributed to
> the application rather than to a producer.

### 9.2 The report

A report **MUST** carry three things: the distribution, **how it entered the
dependency closure**, and the delta. It covers **one platform's build**, since
that is what a consumer computes and what it conforms for
([§8.1](#81-conformance-is-per-platform)).

```
android build — 12 contributions staged, 1 floor, 1 value and 2 actions outstanding

analytics-shim 2.1.0  (via some-ui-lib)
  + permission   android.permission.ACCESS_FINE_LOCATION  ("optional BLE discovery")
  + feature      android.hardware.location.gps  (required=false)

map-sdk 4.1.0  (direct dependency)
  ! REPOSITORY  https://maven.example.com/releases  → groups: com.example.maps
                authenticated — no credentials configured        ✗ BLOCKING
  ! TARGET_SDK  requires 34, application is configured for 33     ✗ BLOCKING
  = floor       min_sdk 24  (application: 26)
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

The shape of that second entry is normative in five respects:

| Requirement | Why |
| --- | --- |
| A repository contribution is set apart, never folded into a list | [§6.4](#64-maven-repositories) |
| Every declared floor appears with the distribution that declared it, and a declared `target_sdk` is set apart with the same prominence a repository gets | [§5.1](#51-build-floors) — it changes behavior application-wide, and composes silently upward |
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

**Every digest this document requires is written the same way**, here and for
the artifact and binary-target checksums of [§6.3](#63-gradle-dependencies) and
[§7.2](#72-swift-packages): **64 lowercase hexadecimal characters, unprefixed
and never abbreviated**. A consumer **MUST** write that form and **MUST** reject
a stored digest that is not it, rather than comparing loosely. The algorithm is
already fixed, so a `sha256:` prefix carries nothing; an abbreviation carries
less than it appears to, since two records elided to different lengths cannot be
compared at all.

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

**What this section offers is attribution and review, not restriction.** The
gates in §§5–7 bind only what a *sidecar* declares. A producer that puts the
same material in a Maven artifact and declares the coordinate bypasses all of
them: an exported component inside a resolved `.aar` is merged by AGP with no
approval step, where the same component declared in a sidecar fails the build
until the application approves it ([§6.6](#66-manifest-components)). The rules
below cannot close that gap — policing arbitrary library code is not
attempted and would not succeed — so instead they require every such
component to be reported, attributed to the artifact and the distribution
that pulled it in, as visibly as a contributed one.

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

**Native dependencies are a trust boundary, and two rules cross it.** An `.aar`
may carry a manifest, resources, JNI libraries and consumer ProGuard rules; a
Swift package may vend binary targets. Those artifacts remain subject to their
own ecosystem's authority model, on the terms this section opened with.

This is not a claim that AGP's own manifest merge is unsafe — a developer
adding a Gradle dependency directly has always accepted the same merge, at
their own discretion, with the artifact visible to them if they choose to look.
What the two rules below address is narrower: an application author who chose
a **Python package**, not the Maven artifact underneath it, may never see that
artifact or the coordinate that pulled it in at all. The exceptions exist to
restore, for that specific path, the visibility a direct Gradle dependency
already has by construction.

Two exceptions exist, because otherwise moving material out of the sidecar and
into an `.aar` would launder past a rule this document treats as
security-sensitive:

- A resolved artifact declaring `<uses-feature required="true">` **MUST NOT**
  silently make hardware mandatory. A consumer **MUST** report it, naming the
  artifact and the distribution that pulled it in, and **MUST** fail until the
  **application** decides: keep it required, or override it to
  `required="false"`. The application's decision **MUST** be recorded.
- A resolved artifact declaring an **exported component** **MUST** be reported
  with the same prominence as a contributed one
  ([§6.6](#66-manifest-components)), so the application sees every externally
  reachable surface it is acquiring, whatever declared it.

> **Note:** A consumer resolving this automatically, in either direction,
> causes harm. Silently leaving the feature required shrinks device reach
> without the application choosing that. Silently overriding it to `false`
> instead widens device reach, and ships the application onto hardware where
> the SDK that declared the feature cannot actually work. Neither is the
> consumer's call — *do you want to be installable on devices without this?*
> is a question the application answers everywhere else in this document, and
> this is no exception.
>
> **Why the second exception stops at reporting**, where a sidecar-declared
> export needs approval. It is a practical line, not a principled one: exported
> components are ordinary inside resolved artifacts, and a single ads or maps
> dependency brings several. Gating each would mean approving dozens of
> components nobody chose, on every build, which earns click-through and then
> protects nothing. Required features are rare enough to gate; exported
> components are not. A producer determined to avoid the sidecar's approval gate
> can publish an artifact, which is the limit this section opened by stating.

Consumer ProGuard rules embedded in a resolved `.aar` **SHOULD** likewise be
reported: they are appended to the application's shrinker configuration without
passing through [§6.7](#67-shrinker-keep-patterns)'s scoping.

> **Note:** The Android half is required rather than advisory because it is the
> case this section exists for — a permission arriving through a transitive Python dependency the
> author has never heard of, carrying obligations beyond the build.
> `com.google.android.gms.permission.AD_ID` comes from an ads AAR and pulls the
> application into a Play Console data-safety declaration. [§11](#11-out-of-scope)
> also rests on it: an `.aar` embedded in a wheel is excluded there because its
> manifest merges with no attribution, while one reached through a declared
> coordinate is permitted because this section surfaces it — a justification
> that cannot stand on an optional feature.

### 9.5 Secrets are never recorded

A consumer **MUST NOT** write a **build-time credential** — the kind
[§6.4](#64-maven-repositories) and [§7.2](#72-swift-packages) declare with
`credentials_required`, supplied by indirection under
[§2.2](#22-how-the-application-answers) — into the integration
record, into a report, or into a diagnostic. Where a record must refer to one, it refers to the
*requirement* (that a repository or a package is authenticated) and never to the
value.

> **Note:** This rule is deliberately confined to that channel, because it is
> the only one this document can identify. An ordinary application value is
> embedded in the shipped application and readable by anyone who unzips it —
> committing an analytics DSN is not a leak — and nothing here marks a value as
> sensitive. A `sensitive = true` flag on [§5.2](#52-values) is the shape to
> reach for if a case appears; inventing it now would mean guessing which values
> deserve it.

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
| its requirements | every floor it declared with the value it declared; and every value and every action, **with its state** — supplied, dismissed, acknowledged, or unresolved. An acknowledgement or a dismissal **MUST** carry the distribution version it was made against and the date it was made, written as an [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339) full-date in UTC — `2026-08-24` — so that two records of one event compare equal |
| the native graph | every resolved artifact with its SHA-256 ([§6.3](#63-gradle-dependencies)), and every resolved package with its version **and** revision, plus the declared checksum per binary target ([§7.2](#72-swift-packages)) |

And for the integration as a whole — these are not per-distribution, because
each addresses a merged result or a decision the application made about one
([§2.2](#22-how-the-application-answers)):

| | |
| --- | --- |
| the build | the platform it was computed for, and the contract the consumer implements |
| every **permission suppression** | the permission `name`, and every distribution whose contribution it withdrew ([§6.5](#65-permissions-and-features)) |
| every **export approval** | the component `name`, the distribution that declared it, and the approval's absence where a component is still pending |
| every **required-feature decision** | the feature `name`, the resolved artifact that declared it `required="true"`, the distribution that pulled that artifact in, and which way the application decided ([§9.4](#94-what-resolved-artifacts-bring-with-them)) |
| every **packaging-collision choice** | the packaged `path`, the artifacts that collided, the distributions responsible, and the artifact chosen — by the application or, for packaging metadata, by the consumer's own rule ([§9.7](#97-packaging-collisions)) |
| every **authenticated repository or package** | that it requires a credential, and never the credential ([§9.5](#95-secrets-are-never-recorded)) |

Each of those decisions **MUST** carry the date it was made, in the same form an
acknowledgement carries, so that a record shows not only what was decided but
when. A record that cannot answer one of these rows, or one of the per-distribution
rows above, has not recorded the integration, whatever else it contains.

> **Note:** These are the answers [§2.2](#22-how-the-application-answers) joins
> by something other than `(distribution, id)`, and they are the rows an
> implementation is likeliest to leave out — a suppression looks like the
> absence of a permission rather than the presence of a decision, and a
> collision choice looks like a packaging detail. Both are the opposite: they
> are the places where the application, not a producer, changed what ships, and
> a record that drops them cannot answer *why is this permission missing* or
> *which copy of `libc++_shared.so` is in the APK* a year later.

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
| **Packaging metadata**, as enumerated below | A consumer **MAY** resolve these itself, by a rule that does not depend on resolution order, and **MUST** record what it did |
| **Anything else, and every native library** | A consumer **MUST NOT** choose silently. It **MUST** fail, naming the path and **both declaring distributions**, unless the application has chosen which artifact supplies the file; where the application has chosen, the consumer **MUST** record the choice |

**Packaging metadata is a closed list, not the `META-INF/` prefix.** It is a
file **directly** under `META-INF/` — never one in a subdirectory of it — whose
name is one of:

- `MANIFEST.MF`, `INDEX.LIST`, `DEPENDENCIES`;
- `LICENSE`, `LICENSE.txt`, `LICENSE.md`, `NOTICE`, `NOTICE.txt`, `NOTICE.md`,
  and the same names with a `-*` suffix (`LICENSE-EPL`);
- JAR signature files: `*.SF`, `*.DSA`, `*.RSA`, `*.EC`.

Everything else under `META-INF/` falls in the second row, and a consumer
**MUST NOT** resolve it on its own authority. `META-INF/services/…` is the case
that matters: a service-loader registration is code by any useful definition —
dropping one copy silently removes an implementation the losing library
registered, and the failure is a `ServiceConfigurationError` or a feature that
simply never activates. `*.kotlin_module` files are the same shape.

The application's choice is joined by the **packaged path**, and answers with
the coordinate of the artifact that supplies it — `(path, artifact)`. A consumer
**MUST** provide a way for the application to answer in those terms
([§2.2](#22-how-the-application-answers)). The path is the natural key: it is
what collided, it is stable across a re-resolution that does not change
versions, and it is what the diagnostic already names.

A consumer **MUST** record every collision it detected and how it was resolved,
attributed to the distributions whose declarations pulled the artifacts in.

**Version 1 defines this for Android, and requirement 44 is in the Android
profile for that reason.** iOS is not collision-free — two Swift packages can
vend resources under one name, or `.xcframework` slices that overlap — but the
detection has no equivalent bounded input: there is no set of resolved archives
to enumerate the way an `.aar` graph enumerates, and SwiftPM and Xcode surface
their own conflicts at different stages. A consumer that builds for iOS
**SHOULD** report a collision it does detect there, naming the packages and the
distributions that declared them, and an iOS-only consumer claiming conformance
is not thereby claiming to have solved a problem this document has not
specified.

> **Note:** This is a consumer obligation rather than a declaration because a
> collision is not a property of any producer: it exists only in a
> combination, and no producer can know what it will be composed with. What
> the consumer adds that the underlying build system cannot is which *Python
> distributions* asked for the colliding artifacts — the build system's own
> duplicate-path failure names only the two colliding artifacts, not the
> packages that pulled them in.

## 10. Versioning

The entry-point group carries the major version (`native_integration.v1`). A
consumer implementing version *N* **MUST** ignore groups for other major
versions entirely, rather than attempting to read them.

Within a major, the `contract` minor ([§4.3](#43-contract-version)) negotiates
capabilities: minor revisions add optional keys, tables, and values in closed
vocabularies; producers declare the smallest contract they use; and an older
consumer rejects a newer declaration visibly instead of mis-building it.

Any change that would alter the meaning of an existing key, or make a previously
valid sidecar invalid, requires a new major version and a new group name.

**That rule binds from the moment the draft marker at the top of this document
is removed, and not before.** While this document is a draft it is amended in
place.

**What a minor revision has to cover is smaller than it looks.** A minor is
required for a new key, a new table, or a new value in a **closed** vocabulary —
[§5.5](#55-value-kinds)'s value kinds, [§6.3](#63-gradle-dependencies)'s Gradle
configurations, [§7.4](#74-infoplist)'s capability-key list. It is **not**
required for:

| | Why not |
| --- | --- |
| A new kind of application requirement | An action is prose. A platform construct this document has never heard of is stated in `summary`, `reason` and `acceptance` without the document changing. |
| A new `slot` | Slots are opaque and compared only for equality ([§5.7](#57-slots)). |
| A new value in a **pass-through** vocabulary | `foreground_service_type` and Apple's required-reason strings are the platform's to extend, and a consumer copies them through without needing to know them ([§4.4](#44-unknown-declarations-fail-closed)). |
| A new `<data>` attribute on `view_links` | The one place where the *names* are open too, not only their values: a consumer converts an unrecognized attribute to Android's spelling and writes it through ([§6.6](#66-manifest-components)). |

That is the point of the split between contributions and actions. Contribution
vocabulary is closed and versioned because a consumer is being asked to modify
the build; requirement vocabulary barely exists, because a consumer is being
asked to report a sentence.

Anticipated minor-revision work, deliberately excluded from version 1: further
intent-filter forms beyond `view_links`; conditional contributions (a `when` key
with a **closed vocabulary** of conditions such as ABI or simulator/device — not
an expression language); further Gradle configurations; further
namespace-scoped shrinker rule forms; and `<meta-data>` on a component, which
the narrow form of provider registration would need
([§6.6](#66-manifest-components)).

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

**Three accepted limitations, stated together.** Each is a place where a
determined or careless producer reaches past a rule and version 1 answers with
disclosure rather than prevention. None is an oversight; each is argued where it
applies, and they are gathered here so that a reader assessing the model does
not have to find them scattered.

| Limitation | What version 1 does instead |
| --- | --- |
| **A component exported by a resolved artifact bypasses the sidecar's approval gate** ([§6.6](#66-manifest-components), [§9.4](#94-what-resolved-artifacts-bring-with-them)). Moving a class from a sidecar declaration into a published `.aar` turns an approval into a merge AGP performs | Reports it with the prominence a contributed export gets, attributed to the artifact and to the distribution that pulled it in. Gating it would mean approving dozens of components nobody chose, on every build |
| **Contributed Swift has no enforceable symbol boundary** ([§7.1](#71-symbol-prefixes), [§7.3](#73-swift-source)). Prefixes are guidance, and reach neither file-scope functions and constants nor extension members, all of which land in the application's own scope | Asks for prefixes, attributes a duplicate-symbol error to the distribution whose prefix matches (8.S10), and points a producer with more than shims at a Swift package, which is its own module |
| **Package visibility has no application veto** ([§6.9](#69-package-visibility)). A transitive producer's `<queries>` entry widens what the application can see without the application deciding | Requires a `reason` on every entry and reports both, since withholding one would not reduce what the application may do — it would make a dependency's code get a wrong answer with no diagnostic |

The first is the one with a security shape, and it is the reason
[§9.4](#94-what-resolved-artifacts-bring-with-them) opens by saying what this
convention offers for artifact content is attribution and review. A model that
claimed otherwise would be claiming to police arbitrary library code, which
nothing in this ecosystem does.

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

On Android specifically, the shape that decision would most likely take is
provider registration — [§6.6](#66-manifest-components) records why `provider`
is absent from the component vocabulary, and the trigger that would bring it
back. It is deferred with this question rather than separately from it, because
a producer that can register a provider can already run code first, whatever
the rest of the design says.

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
rather than in one package's sidecar. The union problem matters most for
**facade packages** — libraries exposing many optional platform features
behind one API, the [Plyer](https://github.com/kivy/plyer) shape (the real
Plyer today ships as one distribution and is unaffected by this section; it is
named here only to make the shape concrete). A facade declaring every
permission any feature *might* use hands every application its worst-case
manifest, and no amount of disclosure repairs that: per-permission suppression
([§6.5](#65-permissions-and-features)) becomes each application's cleanup
chore rather than a rare override.

A producer building a facade of this shape under this convention should ship
the conditional surface as optional distributions instead, each carrying its
own sidecar, with extras as the opt-in mechanism. For a hypothetical
Plyer-shaped facade, that would look like:

```toml
# the facade's pyproject.toml
[project.optional-dependencies]
gps = ["plyer-gps"]
camera = ["plyer-camera"]
```

`pip install plyer[gps]` would then install a `plyer-gps` distribution whose
own sidecar contributes exactly `android.permission.ACCESS_FINE_LOCATION` and
nothing else. An extra cannot vary the facade's *own* sidecar — extras select
dependencies; they do not change a distribution's contents — but it can select
a distribution that carries one, which is all that is needed.

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

**Conditional requirements are the answer for this shape.** A producer should
declare the binding's unconditional needs normally, and mark the rest
`conditional = true` with the triggering condition in `reason`. Nothing is
imposed on applications that do not use the feature, and nothing is silent for
applications that do.

Producers **SHOULD NOT** reach for `conditional` to avoid stating an
unconditional requirement.

> **Caution:** Marking an unconditional requirement conditional converts a build
> failure that names the problem into a line in a report, and the application
> discovers the requirement at runtime instead.


### 12.2 Sidecar authoring procedure

**Non-normative, and it introduces nothing.** Every decision below is made
somewhere else in this document, and each step says where. What is added is the
*order*: the guidance above is complete and is scattered across five sections,
so an author meets it as a set of principles rather than as a sequence, and the
one place they most often guess — whether an item is a contribution or a
requirement — is decided by a test stated under [Goals](#goals) and applied in
[§2.1](#21-design-principles).

Work one item at a time. An item is a single thing the vendor's integration
documentation asks for: one dependency, one permission, one key, one console
setting.

**1. Inventory.** List every item the vendor's native integration
documentation requires, for each platform separately. These are "the things an
application author would otherwise transcribe out of a README"
([Goals](#goals)), and the list is the input to every step that follows. Do not
classify while inventorying; a half-classified list hides the items that fit no
category, and those are the interesting ones.

**2. Classify into the three categories.**
[§2.1](#21-design-principles) fixes them and what each one means:

| The item is | Category |
| --- | --- |
| An exclusive namespace the package needs to hold across the whole closure | `owns` |
| Material the package supplies and a consumer can stage on its behalf | `contributes` |
| Anything else — a condition the application or its build must satisfy | `requires` |

§2.1's own examples settle most of the list: "A Java namespace is owned. An SDK
floor, a value the application supplies, and an action it performs are
required… Source files, dependency coordinates, permissions and manifest
components are contributed."

**3. Test every candidate contribution before accepting it.** A declaration is
automated when all three hold ([Goals](#goals)):

1. the producer knows exactly what is required;
2. the consumer can do it deterministically;
3. little or no application-specific policy is involved.

[§2.1](#21-design-principles) makes this the decision between the last two
categories: "material that passes all three is a contribution, and material
that fails any of them is a requirement." A failure on any one of the three is a
failure. Run the test honestly ([§12](#12-guidance-for-package-authors)) —
it is your own work that a passing answer saves, and every application's that a
wrong one costs.

**4. For a requirement, choose the shape.** [§5](#5-requirements-on-the-application)
gives three, and the boundary between the last two is "what the consumer can
place deterministically":

| The requirement is | Shape |
| --- | --- |
| A minimum the application's build configuration must meet | Floor ([§5.1](#51-build-floors)) |
| A string the application has, whose destination the consumer knows | Value ([§5.2](#52-values)) |
| An outcome the application must achieve that the consumer cannot produce | Action ([§5.3](#53-actions)) |

Classify by what the requirement *is*, not by which shape is easier to satisfy
([§5](#5-requirements-on-the-application)). A notification icon is a drawable
someone must draw: there is no string to write, so it is an action however
convenient a value would be.

**5. Where no declaration represents the item, it is an action.** This document
does not "model every platform construct Apple and Google ship"
([Non-goals](#non-goals)), so an item with no matching declaration is expected
rather than a gap. State it as an action
([§2.1](#21-design-principles): "state it as an action rather than forcing it
into a shape the consumer cannot honor"). Do not reach for a declaration that
almost fits: "a partial automation that looks complete is worse than a clear
task", and where the artifact is the application's, a producer "states a
requirement and stops".

**6. Decide whether the requirement is unconditional.** Declare only what every
application that imports the package needs
([§12](#12-guidance-for-package-authors)). For the rest, the shape of your
package decides the mechanism:

| Your package | Mechanism |
| --- | --- |
| A facade with a packaging seam — independent features behind one dispatcher | Ship the conditional surface as separate distributions, selected by extras ([§12](#12-guidance-for-package-authors)) |
| A 1:1 binding of a platform framework, with no seam to split along | Declare the unconditional needs normally and mark the rest `conditional = true`, with the triggering condition in `reason` ([§12.1](#121-framework-bindings-where-this-guidance-does-not-apply)) |

There is no conditional *contribution*: the dependency graph is the
conditionality mechanism, and only a requirement carries the flag
([§12](#12-guidance-for-package-authors)). And `conditional` is not a way to
avoid stating an unconditional requirement
([§12.1](#121-framework-bindings-where-this-guidance-does-not-apply)) — doing
that converts a build failure that names the problem into a line in a report.

**7. Check each declaration against the reference.**
[Appendix B](#appendix-b-declaration-reference) is the complete key list, and
[§4.4](#44-unknown-declarations-fail-closed) makes a consumer fail closed on
anything it does not recognize — so a misspelling is a build failure for every
application that installs the package, not a warning. A generated JSON Schema
covers what a schema can cover: presence, types, closed vocabularies, and array
shapes.

**8. Build the distribution and confirm what shipped.** The sidecar and its
resources are only useful if they are in the artifact:

- `native.toml` is named exactly that, sits in the directory the entry-point
  value identifies, and ships as ordinary package data
  ([§4.1](#41-location-and-name));
- one sidecar covers every platform the distribution supports
  ([§4.2](#42-one-file-for-all-platforms));
- every resource a declaration references ships too, since a consumer that
  cannot read one fails naming your distribution
  ([§3.2](#32-resolution), [§4.1](#41-location-and-name));
- the distribution registers exactly one entry point in the group
  ([§3.4](#34-one-entry-per-distribution)).

Building the wheel and reading its contents is the check. A sidecar that is
correct in the source tree and absent from the artifact is the one failure this
convention cannot report, because there is nothing to report on.

> **Note:** The procedure stops where the specification does. It cannot tell you
> whether a vendor's SDK needs a permission — that is the vendor's
> documentation's job — and it does not decide the contribution-versus-action
> boundary for you, because the three-part test does. What it removes is the
> guessing about *which question to ask next*, which is where an author who has
> read §2, §5 and §12 separately still ends up inventing a shape.

---

## Appendix A: a complete sidecar

**Non-normative.** Nothing here is special. This is an ordinary `native.toml`
for a wrapper around a hypothetical cross-platform analytics SDK — the shape an
application author would otherwise transcribe out of a README.

Read it as the three categories of [§2.1](#21-design-principles). It **owns** a
Java namespace. It **requires** three floors — two on Android, one on iOS — two
values only the application has, and an outcome the application must achieve.
Everything else it **contributes**.

Note what it does *not* do: nothing here is `conditional`. Attribution is an
optional feature of this SDK, and [§12](#12-guidance-for-package-authors) says
optional surface belongs in an optional distribution — `examplytics-attribution`,
with its own sidecar — rather than in this one behind a flag. `conditional` is
for the shape that cannot be split, which
[§12.1](#121-framework-bindings-where-this-guidance-does-not-apply) describes.

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

# The application supplies this; the consumer writes it to the manifest key the
# SDK reads at startup, before any Python runs.
[[android.requires.application_value]]
id = "analytics_key"
kind = "manifest_meta_data"
key = "com.example.analytics.API_KEY"
reason = "Your project key, from the vendor console under Settings → Client Keys"
placeholder = "<TODO: your Examplytics project key>"

# Java sources the consumer compiles into the application.
[android.contributes.src]
java = ["java"]

# The SDK itself, pulled in via Gradle. The bounded form, because the Java above
# calls this SDK's API: `below` is what stops Gradle resolving to a major that
# glue code will not compile against (§6.3).
[[android.contributes.gradle_dependencies]]
module = "com.example.analytics:android-sdk"
version = { at_least = "4.2.0", below = "5.0.0" }

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

# Keeps the SDK's classes through shrinking and obfuscation.
[android.contributes.r8]
keep_classes = ["org.example.analytics.**"]

# -------------------------------------------------------------------- iOS ---

# SDK floor the application must build against.
[ios.requires]
deployment_target = "15.0"

# A purpose string only the application can write. The consumer scaffolds the
# placeholder and blocks until it is gone.
[[ios.requires.application_value]]
id = "analytics_purpose"
kind = "usage_description"
key = "NSUserTrackingUsageDescription"
reason = """\
The sentence is yours to write: it is shown to the user and read by App Store \
review."""
placeholder = "<TODO: why this app asks to track, in one sentence>"

# An outcome the consumer cannot produce: the capability must be on the App ID
# and in the provisioning profile before anything can be signed.
[[ios.requires.application_action]]
id = "attribution_capability"
summary = "Enable the App Attribution capability on your App ID"
reason = """\
Without it the archive fails at codesign, with a message that names the \
entitlement and not this package."""
acceptance = [
  "The App Attribution capability is enabled on the App ID",
  "The provisioning profile used for release builds carries it",
]

# The SDK itself, pulled in via Swift Package Manager.
[[ios.contributes.swift_packages]]
name = "ExampleAnalytics"
url = "https://github.com/example/analytics-swift"
requirement = { from = "4.2.0" }
products = ["ExampleAnalytics"]

# Lets the SDK detect a companion app. Grants the application nothing.
[ios.contributes.info_plist.append]
LSApplicationQueriesSchemes = ["exampleanalytics"]
```

## Appendix B: declaration reference

Every key a sidecar may contain, with the section that defines it. Descriptions
are summaries; **where this table and the body differ, the body governs.**

**This table is also the contract-minor registry** ([§4.3](#43-contract-version)).
Every entry below is contract **1.0**; a key **or a closed-vocabulary value**
added by a later minor **MUST** be marked *Since 1.n* here, and a consumer
checks under-declaration against these marks. An unmarked entry is 1.0, which is
why nothing below carries a mark yet.

The closed vocabularies, gathered here because that rule needs them in one
place: the value kinds of [§5.5](#55-value-kinds), the Gradle configurations of
[§6.3](#63-gradle-dependencies), the component kinds of
[§6.6](#66-manifest-components), the Swift requirement forms of
[§7.2](#72-swift-packages), the platform names of
[§4.5](#45-platform-support), and the capability and external-reach keys of
[§7.4](#74-infoplist).

<!-- appendix-b -->

| Entry | Description |
| --- | --- |
| **Top level** | |
| `contract` | **Required.** Major of this document, optionally with a minor — `"1"` or `"1.1"`. [§4.3](#43-contract-version) |
| `platforms` | Optional. Where the distribution *functions*, not merely where it contributes; a build for an omitted platform fails. [§4.5](#45-platform-support) |
| **`[<platform>.requires]` — floors** [§5.1](#51-build-floors) | |
| `min_sdk` | An Android floor, and a **TOML integer** — `"24"` and `24.0` are rejected. The build fails when the application is lower; the consumer never raises it |
| `compile_sdk` | An Android floor, on the same terms as `min_sdk` |
| `target_sdk` | An Android floor, on the same terms. It changes behavior app-wide, so declare it only when a behavior depends on it, and a consumer gives it the prominence a repository contribution gets |
| `core_library_desugaring` | Optional boolean, and only `true` is valid — a consumer rejects `false`. A floor on a boolean axis: the build fails when the application has not enabled desugaring |
| `deployment_target` | The iOS floor, and a **TOML string** where the three above are integers. One to three ASCII-decimal components, compared component-wise and numerically with absent components read as zero |
| **`[[<platform>.requires.application_value]]`** [§5.2](#52-values) | A string the application supplies and the consumer places |
| `id` | **Required.** A logical name, unique among the requirements in one platform table; identity is (distribution, platform, `id`) |
| `kind` | **Required.** Where the consumer writes it. A **closed** set — [§5.5](#55-value-kinds). `info_plist` may not name a usage-description, capability, external-reach or consumer-managed key; `usage_description` may name only a `*UsageDescription` one |
| `key` | The platform key the value is written to. **Required** for every kind but `inline`, where it **MUST** be absent — an `inline` value is consumed by a contribution that references it or an action that `uses` it ([§5.5](#55-value-kinds)) |
| `reason` | **Required.** What the value is and where to obtain it |
| `placeholder` | **Recommended.** Text the consumer scaffolds; the build does not proceed while it stands |
| `conditional` | Optional, default `false`. Unsatisfied and conditional is recorded, not failed |
| **`[[<platform>.requires.application_action]]`** [§5.3](#53-actions) | An outcome the application must achieve |
| `id` | **Required.** A logical name, unique among the requirements in one platform table; identity is (distribution, platform, `id`), and the application acknowledges by it |
| `summary` | **Required.** One line, imperative. What a report shows |
| `reason` | **Required.** Why it is needed, and what breaks without it |
| `instructions` | Optional prose telling a reader how to do it. Never acted on by a consumer ([§5.6](#56-instructions-and-acceptance-criteria)) |
| `acceptance` | **Recommended.** Statements of the **end state**, never of an operation |
| `uses` | Optional. Value `id`s this action consumes, which **MUST** resolve to values the same sidecar declares for the **same platform** |
| `slot` | Optional. An opaque key naming a contended application-owned surface ([§5.7](#57-slots)) |
| `conditional` | Optional, default `false` |
| **`[android.owns]`** [§6.1](#61-ownership) | |
| `java_namespaces` | Java namespaces this distribution claims exclusively; overlapping claims fail the build. Required when contributing Java/Kotlin, producer-sourced components, or keep patterns |
| **`[android.contributes.src]`** [§6.2](#62-java-and-kotlin-source) | |
| `java` | Directories whose `.java` files the application's own toolchain compiles |
| `kotlin` | Directories whose `.kt` files the application's own toolchain compiles |
| **`[[android.contributes.gradle_dependencies]]`** [§6.3](#63-gradle-dependencies) | A dependency is spelled in **exactly one** of two forms — an exact `coordinate`, or a `module` with a bounded `version`. Declaring both, or neither, is rejected |
| `coordinate` | `group:artifact:version`, exactly versioned. The version is visible in the sidecar, but it states no upper bound: Gradle may resolve past a major the producer never compiled against |
| `module` | `group:artifact`, paired with a bounded `version`. **Recommended** where the producer's own source compiles against the dependency, because `below` is the only way to say which major it cannot survive |
| `version` | **Required** with `module` and **forbidden** with `coordinate`. **Both** `at_least` (inclusive) and `below` (exclusive) are required within it; a range open at either end is invalid, as are changing (`-SNAPSHOT`) and dynamic (`+`, `latest.release`) versions |
| `configuration` | Optional; `implementation` (default), `api`, `compileOnly`, `runtimeOnly`. A **closed** set: processor configurations execute code at build time |
| **`[[android.contributes.gradle_repositories]]`** [§6.4](#64-maven-repositories) | |
| `url` | A Maven repository to add to resolution, **`https` only** (scheme compared case-insensitively). The most powerful thing a sidecar can contribute |
| `reason` | **Required.** Why the artifacts are not on Maven Central, and — when authenticated — which credential is needed and where to get it |
| `groups` | **At least one of `groups`/`modules` required.** Bounds what the repository may serve, by **exact** match on a group ID — never a prefix, so `org.example` does not admit `org.example.tools` |
| `modules` | **At least one of `groups`/`modules` required.** Bounds the repository by **exact** match on a `group:artifact` pair |
| `credentials_required` | Optional. Declares the repository authenticated. A sidecar **MUST NOT** contain the credential itself |
| **`[[android.contributes.permissions]]`** [§6.5](#65-permissions-and-features) | |
| `name` | The canonical manifest string — `android.permission.INTERNET`, never a shorthand |
| `reason` | Recommended; carried into the record and report |
| `max_sdk_version` | Optional. `android:maxSdkVersion`. Minimization; where two distributions differ, the **widest** need wins and the merge is reported |
| `never_for_location` | Optional. `android:usesPermissionFlags="neverForLocation"`, and it holds only when **every** declaration of that permission asserts it |
| **`[[android.contributes.features]]`** [§6.5](#65-permissions-and-features) | |
| `name` | Always registered `required="false"`; only the application may promote a feature |
| `required` | **Not a field.** A producer **MUST NOT** declare it, and a consumer rejects it with a diagnostic naming this rule rather than the generic unknown-key one |
| **`[[android.contributes.components]]`** [§6.6](#66-manifest-components) | |
| `kind` | `service`, `activity` or `receiver`. `provider` is deliberately absent: a provider runs before application code, which is the startup seam §11 defers |
| `name` | The class. Under an owned namespace unless `from_dependency` says otherwise |
| `from_dependency` | `group:artifact` of a dependency the same sidecar declares, which owns the class |
| `foreground_service_type` | Android's own value, on a `service` only. Mandatory on Android 14+ for a foreground service |
| `exported_required` | Requests export. The build fails without explicit application approval — it never falls back to unexported |
| `reason` | **Required when `exported_required` is present.** Why the component is useless unless reachable |
| `exported` | **Not a field.** Components are registered `android:exported="false"` by default and a producer **MUST NOT** declare export directly; use `exported_required` |
| **`[[android.contributes.components.view_links]]`** [§6.6](#66-manifest-components) | Generates the browser-return filter. Valid only on an exported activity; values are strings, literal or inline. The **attribute names are open** — the one place an unrecognized key is written through rather than rejected — and snake case converts to the platform's name mechanically ([§6.6](#66-manifest-components)) |
| `scheme` | **Required.** The only `<data>` attribute a `view_links` entry must carry. `host`, `port`, `path`, `path_prefix`, `path_pattern`, `path_suffix`, `mime_type` and every other attribute the platform defines are equally declarable |
| **`[[android.contributes.components.intent_filters]]`** [§6.6](#66-manifest-components) | |
| `action` | One vendor-defined action, on a component that is neither exported nor carrying `view_links`. Exactly one per filter; no categories and no data element |
| **`[android.contributes.r8]`** [§6.7](#67-shrinker-keep-patterns) | |
| `keep_classes` | Class patterns the shrinker must keep; the consumer generates the `-keep` rules. Each must fall within an owned namespace, by its wildcard-free literal prefix |
| **`[[android.contributes.r8.keep]]`** [§6.7](#67-shrinker-keep-patterns) | |
| `pattern` | **Required.** Keeps a *dependency's* classes instead of an owned namespace's, checked against what the resolved artifact actually contains |
| `from_dependency` | **Required.** `group:artifact` of a dependency the same sidecar declares; the pattern is evaluated against the effective compilation classpath and rejected where it matches a class from outside that dependency |
| **`[[android.contributes.meta_data]]`** [§6.8](#68-manifest-meta-data) | |
| `key` | The manifest entry's name, written exactly as the vendor code reads it. **Not** scoped by the declaring distribution, and it shares one key space with [§5.2](#52-values)'s `manifest_meta_data` delivery |
| `value` | **Required.** A string, integer or boolean, mapped to `android:value` as the text verbatim, the digits, or `true`/`false`. Equality is by type as well as content, and the application's own entry wins. A value **MAY** be a resource reference — anything beginning `@` or `?` — only where the same sidecar declares an action asking the application to supply it |
| `reason` | **Required.** The key is global, its effect is invisible in Python, and the report is where an application sees what a transitive dependency turned on |
| **`[[android.contributes.queries]]`** [§6.9](#69-package-visibility) | |
| `package` | An application ID. **Exactly one** of `package` or `provider_authority` is required |
| `provider_authority` | A content provider authority. **Exactly one** of `package` or `provider_authority` is required |
| `reason` | **Required.** Package visibility for the producer's own code. No veto, because removing one breaks the producer silently |
| **`[[ios.contributes.swift_packages]]`** [§7.2](#72-swift-packages) | |
| `name` | **Required.** Local handle, unique within the sidecar; [§7.5](#75-python-modules) refers to packages by it |
| `url` | The package repository. **Required**, and **MUST** be `https` |
| `products` | **Required**, non-empty. Which of the package's products the application target links |
| `requirement` | Exactly one of `{ exact }`, `{ from }`, `{ revision }`. `branch` is invalid |
| `credentials_required` | Optional. Declares the repository authenticated; [§6.4](#64-maven-repositories)'s credential rules apply unchanged |
| `reason` | **Required when `credentials_required` is set**, and unused otherwise: which credential is needed and where to obtain it |
| **`[ios.contributes.src]`** [§7.3](#73-swift-source) | |
| `swift` | Directories of `.swift` staged into the application target. For small shims only |
| `symbol_prefixes` | Prefixes the producer puts on its contributed Swift type names ([§7.1](#71-symbol-prefixes)). Guidance only; it does not cover file-scope functions or extension members, and it is invalid without contributed source |
| **`[[ios.contributes.accessed_api_types]]`** [§7.3](#73-swift-source) — a sibling of `src`, not a child of it | |
| `type` | **Required.** Apple's canonical string for a required-reason API category, written exactly as Apple defines it. Valid only in a sidecar that also contributes Swift source |
| `reasons` | **Required.** Apple's canonical reason codes, merged into the application's `PrivacyInfo.xcprivacy` and de-duplicated per `type` |
| `reason` | Recommended prose. Apple's codes are opaque by design, and the record is where an application reads what its dependencies claim |
| **`[ios.contributes.info_plist]`** [§7.4](#74-infoplist) | |
| `values` | Scalar keys set verbatim. Collisions fail; `*UsageDescription`, capability, external-reach and consumer-managed keys are rejected. A key occupies **one** mode across the effective set — scalar here or through an `info_plist` value ([§5.5](#55-value-kinds)), array under `append` — and claimed both ways it fails |
| `append` | Array keys merged with the application's and other producers', de-duplicated in a deterministic order. Rejects the same capability, external-reach and consumer-managed keys `values` does, and claims the key as an array for the one-mode rule above |
| `skadnetwork_identifiers` | Ad network identifiers, lowercase and ending `.skadnetwork`. The consumer renders `SKAdNetworkItems` from them |
| **`[[ios.contributes.python_modules]]`** [§7.5](#75-python-modules) | |
| `name` | **Required.** The name Python imports. A single ASCII identifier, no dots |
| `swift_package` | **Required.** A package the same sidecar declares, which implements the module |
| `init` | Optional initialization symbol; defaults to `PyInit_<name>` |
| **`[ios.contributes]`** [§7.6](#76-objective-c-categories) | |
| `objc_categories` | Optional boolean, and only `true` is valid — a consumer rejects `false`. The consumer links the application target so Objective-C categories in static libraries are loaded. Names the behavior, not the flag; no veto |

<!-- /appendix-b -->

## Appendix C: a record that satisfies §9

**Non-normative.** [§9](#9-recording-and-review) mandates the content of an
integration record and deliberately not its format. This is one shape that
satisfies it, included so that a second implementation has a worked example to
disagree with rather than a blank page.

```json
{
  "collisions": [
    {
      "chosen": "com.example.maps:android:4.1.0",
      "decided": "application",
      "distributions": ["analytics-shim", "map-sdk"],
      "path": "lib/arm64-v8a/libc++_shared.so"
    },
    {
      "chosen": "com.example.maps:android:4.1.0",
      "decided": "consumer (packaging metadata; rule: lowest coordinate)",
      "distributions": ["analytics-shim", "map-sdk"],
      "path": "META-INF/LICENSE.txt"
    }
  ],
  "contract": "1",
  "decisions": [
    "suppressed permission  android.permission.ACCESS_FINE_LOCATION  withdrawn from analytics-shim  2026-08-24",
    "approved export  org.example.maps.RedirectActivity  (map-sdk)  2026-08-24",
    "artifact feature  android.hardware.location.gps  required=true → false  in com.example.maps:android:4.1.0, via map-sdk  2026-08-24"
  ],
  "distributions": [
    {
      "artifacts": {
        "com.example.maps:android:4.1.0": "0d3e4f9a17c2b85e6dd0341fbb9a72c5e08d41a6f3c7b2905ea18d43f6c07b21",
        "com.squareup.okhttp3:okhttp:4.12.0": "5b81c0f2d7a3946e18bb52c07f9d3a6418e2c5b09fa471d38c62e0ab7451f9d0"
      },
      "contract": "1",
      "entries": [
        "source java/com/example/maps/MapBridge.java",
        "dependency com.example.maps:android:4.1.0  requested 4.1.0 → resolved 4.1.0",
        "dependency com.squareup.okhttp3:okhttp:4.12.0  (transitive, via com.example.maps:android)",
        "REPOSITORY https://maven.example.com/releases → com.example.maps  authenticated — credentials configured",
        "from com.example.maps:android:4.1.0 (resolved artifact manifest): permission com.example.permission.MAPS_ID",
        "from com.example.maps:android:4.1.0 (resolved artifact manifest): feature android.hardware.location.gps required=true"
      ],
      "inputs": {
        "java/com/example/maps/MapBridge.java": "9f2c17b40ae83d6512cc0947fa2b81d35e07c6a94b1f28d0e35ba7c61804df92",
        "native.toml": "71ff3ac8250b91e7d4a6c03fb8215de9074c1a6b39f52840cbe7d1904a63f28c"
      },
      "name": "map-sdk",
      "origin": "direct dependency",
      "requirements": [
        "floor  min_sdk 24   (application: 26)",
        "value  maps_api_key → meta-data com.example.maps.API_KEY   supplied",
        "action map_deep_links   acknowledged 2026-08-24, map-sdk 4.1.0",
        "action map_offline_cache   conditional, unresolved",
        "action map_share_sheet   conditional, dismissed 2026-08-24, map-sdk 4.1.0"
      ],
      "swift": {},
      "swift_binaries": {},
      "version": "4.1.0"
    }
  ],
  "platform": "android",
  "record": 1
}
```

A record covers one platform's build ([§9.2](#92-the-report)), so the Swift
half of the same application lives in its own file. This is that file, cut to
the one distribution that shows the rows a Gradle graph cannot:

```json
{
  "collisions": [],
  "contract": "1",
  "distributions": [
    {
      "artifacts": {},
      "contract": "1",
      "entries": ["swift package Charting 2.4.0 (products: Charting)"],
      "inputs": { "native.toml": "c40a92f13b6d8571ee204cb7f3a915d068b4e27ca9013f6d5b82ec4a7091df63" },
      "name": "pycharting",
      "origin": "via some-ui-lib",
      "requirements": [
        "floor  deployment_target 15.0   (application: 16.0)"
      ],
      "swift": {
        "https://github.com/example/charting": {
          "requested": "from 2.4.0",
          "revision": "8a1f0c9e4b2d7f36a05c1e8b9d4427fa3c60e15b",
          "version": "2.4.0"
        },
        "https://github.com/example/charting-core": {
          "requested": "transitive",
          "revision": "b73c2ad91e604f8ab5d0c7e21f9836540ac1de77",
          "version": "1.2.0"
        }
      },
      "swift_binaries": {
        "ChartingRenderer.xcframework": "e11d5b0c93a726f4180dc35ba9f27e64108c3d95b2af7016e5c48d3b9207fa14"
      },
      "version": "2.4.0"
    }
  ],
  "platform": "ios",
  "record": 1
}
```

Between them the two files carry every row
[§9.6](#96-what-a-record-must-contain) requires: distribution and version,
contract, provenance, per-file input hashes, contributions, every requirement
with its state — a floor with the value it was met by, a supplied value, an
acknowledged action, an unresolved conditional and a dismissed one — both
resolved graphs with their checksums and revisions, and the decisions the
application made about the integration as a whole: a permission suppression, an
export approval, a resolved artifact's required feature, and both kinds of
packaging collision with who decided each. The `decisions` block is where the
answers joined by something other than `(distribution, id)` live, since a
suppression withdraws a permission from every distribution that contributed it
([§2.2](#22-how-the-application-answers)). The Swift file is shown short: everything
elided from it is a repeat of a row the Android file already shows.

Four properties are worth naming, because they are what make the file useful
rather than merely present:

- **One line per contributed thing.** A set difference over `entries` *is* the
  delta a reviewer reads, so the report needs no separate computation and a
  `git diff` is already legible.
- **Every requirement, with its state.** An action is satisfied by the
  application's claim that it was done ([§5.4](#54-how-a-requirement-is-satisfied)),
  so recording the claim — with the version and the date it was made — is what
  makes it attributable afterwards.
- **Sorted keys, distributions in normalized-name order, UTF-8, one entry per
  line.** The record is normally committed; anything that reorders between runs
  turns review into noise.
- **No credential, ever.** An authenticated repository appears as
  `REPOSITORY … authenticated — credentials configured`. That the repository
  needs a credential is a fact about the integration; the credential is not
  ([§6.4](#64-maven-repositories), [§9.5](#95-secrets-are-never-recorded)).
- **Digests in full.** Every hash is 64 lowercase hexadecimal characters with no
  prefix ([§9.3](#93-hashed-inputs)). The values here are invented, but their
  shape is not: an abbreviated digest cannot be compared against another
  consumer's, which is the one thing a record exists to make possible.

## Appendix D: why contributions stay per-distribution

The tempting implementation is to let every distribution write its material into
one shared location under `site-packages` and let the installer merge them. It
is less code, and it forecloses most of this document.

A merged tree **destroys provenance at install time**. Once files are overlaid,
nothing can determine which distribution contributed which file — so collision
detection, per-distribution attribution, the review record of
[§9](#9-recording-and-review), and every diagnostic required by requirement 18
all become impossible.

It also makes a shared source tree last-writer-wins by construction, which is
the substitution path [§6.1](#61-ownership) exists to close.

Keeping contributions inside each distribution costs an explicit merge step in
the consumer. That step is where validation, attribution, and collision
detection live.

## Appendix E: prior art

- **Cargo** — the `links` key gives a crate an exclusive claim on a native
  library, enforced across the graph; [§6.1](#61-ownership)'s ownership model is
  the same idea. Cargo's build scripts, by contrast, are exactly the capability
  [§2.1](#21-design-principles) excludes: powerful, and executable.
- **pkg-config and SwiftPM system libraries** — the abstraction this convention
  borrows: a dependency describes what consuming it requires, and the consumer's
  build system decides how to satisfy it. Declarative data, no executable hooks.
- **Gradle dependency locking and SwiftPM `Package.resolved`** — the
  locked-graph semantics [§6.3](#63-gradle-dependencies) and
  [§7.2](#72-swift-packages) require: exact coordinates are not
  reproducibility; recorded resolutions are.
- **AGP manifest placeholders**, as AppAuth uses them — the established
  mechanism behind [§5.2](#52-values)'s inline values and
  `manifest_placeholder` kind: the library declares the filter's shape, the
  application supplies the value.
- **PEP 561** — the standardization shape: a marker shipped as package data, a
  consumer that is not an installer, and normative obligations on that consumer,
  written down after the practice existed.
- **Expo config plugins** — the executable form of this problem: JavaScript
  functions a package ships to mutate the generated native project. Widely used,
  and precisely the capability [§2.1](#21-design-principles) excludes.
- **Cordova and Capacitor `plugin.xml`** — the *declarative* form, and the more
  instructive comparison, because it concedes the principle and keeps the
  capability anyway: `<config-file target="AndroidManifest.xml" parent="/manifest">`
  admits arbitrary XML at a chosen location. Fifteen years of practice, with the
  failure [Appendix D](#appendix-d-why-contributions-stay-per-distribution)
  predicts for merged material — plugin-contributed manifest entries no tool can
  attribute, refuse, or arbitrate between plugins.

  It is also the contrast for [§5.6](#56-instructions-and-acceptance-criteria).
  `plugin.xml` and an `instructions` block both let a producer describe work on
  the application's project, and the difference is who acts: a `<config-file>`
  is applied by the tool, so its content is build authority, while instructions
  are read by a person or an agent working with that person's authority. That
  is why instructions may be free prose and a fragment may not.

## Appendix F: the conformance record

**Non-normative.** [§9.6](#96-what-a-record-must-contain) fixes what an
integration record must contain and deliberately not how it is written, and
[Appendix C](#appendix-c-a-record-that-satisfies-9) shows one shape that
satisfies it. That freedom is right for a build tool and useless for comparing
two of them: two conforming consumers can agree on every fact and share no
bytes, and *two consumers read one sidecar and agree* is the test this document
is waiting on.

So the conformance corpus defines one serialization — a projection of the record
onto a fixed, line-sorted, diffable form — in
[`conformance/record-format.md`](conformance/record-format.md), with the corpus
itself under [`conformance/`](conformance/).

Three things about its status, because a test format is exactly the kind of
artifact that quietly becomes a second specification:

- It **adds no obligation**. A consumer's own record stays whatever §9.6 leaves
  it. What the format asks for is an export, on request, of facts §9.6 already
  requires to be recoverable.
- It is **binding only on a conformance claim made through the corpus**. A
  consumer that never runs the corpus owes it nothing.
- Where the format and this document disagree, **this document governs and the
  format is the defect**. The corpus states the same rule about its own
  fixtures.
