# native-integration

**A convention for Python packages to declare what they need from a native mobile app build.**

> **Status: draft, complete, seeking review.** [**SPEC.md**](SPEC.md) is the
> specification — written end to end, validated in CI, through three rounds of
> review, and implemented by no build tool yet. It is the second attempt; the
> first is kept at [`development/first-attempt.md`](development/first-attempt.md)
> and what replaced it is in [`development/redesign/`](development/redesign/).
> The contract stays unfrozen until something is built against it and run on a
> device — see [Before a freeze](#before-a-freeze).
>
> **The reference reader under [`src/`](src/README.md) now implements this
> document.** It was rewritten against it rather than patched, and it is run
> against the [conformance corpus](conformance/README.md) in CI. Six of that
> corpus's case runs come back *unverified* — every one an assertion about
> generated output, which a reader does not produce. Closing them needs a build
> tool, and no build tool exists yet.

## The problem

`pip install` faithfully installs what a wheel contains — and has no convention
for translating a dependency's Android or iOS integration requirements into the
application's Gradle or Xcode configuration.

Take [KivMob](https://github.com/MichaelStott/KivMob), AdMob support for Kivy on
PyPI. Installing it works. Then you hand-copy a screenful of settings out of its
README: Maven coordinates, a custom repository, manifest `meta-data`,
permissions, toolchain flags. Every app repeats that transcription, every version
bump risks silent drift, and when the package is a **transitive** dependency the
person on the hook may not know it is in the tree at all.

The package knows what it needs. The app author is the one obliged to say it.
That inversion **is** the problem.

## The model

A package ships a `native.toml` sidecar. A build tool discovers every sidecar in
the application's dependency closure — reading, never importing — automates what
it can do deterministically, and tells the author what is left. The
specification calls the declaring package the **producer** and the build tool
that reads it the **consumer**, and both words are used that way below.

```text
SIDECAR
│
├── OWNS          these native surfaces are mine
│                   collision-checked across the whole closure
│
├── REQUIRES      the application or its build owes me something
│                   floors, values, actions — the consumer never
│                   satisfies one on the producer's behalf
│
└── CONTRIBUTES   here is native material I provide
                    staged, attributed, and recorded
```

**Automate what is deterministic; state the rest.** Material is a *contribution*
when the producer knows exactly what is required, the consumer can apply it
deterministically, and little or no application policy is involved. When any of
those fails it becomes a *requirement* rather than a reason to make contributions
more powerful — and **manual is a supported outcome, not a missing feature**.

### Requires, in three shapes

| Shape | The producer says | Satisfied when the application |
| --- | --- | --- |
| **floor** | your build must meet this minimum — `min_sdk`, a deployment target | is configured at or above it; the consumer never raises it for you |
| **value** | you have a string, and I know the platform key it goes to | replaces the scaffolded placeholder with the real value |
| **action** | you must reach an outcome I cannot hand a build tool as a string | acknowledges it, having done the work |

That boundary is the whole design in one line: **if the consumer can place it
deterministically it is a value; otherwise it is an action.** A notification icon
is a drawable someone must draw, so it is an action however convenient a value
would be.

### A sidecar, and the application's reply

The package author adds an entry point and package data to their own
`pyproject.toml`:

```toml
[project.entry-points."native_integration.v1"]
native = "kivmob._native"

[tool.setuptools.package-data]
kivmob = ["_native/**/*"]
```

and ships `kivmob/_native/native.toml`:

```toml
contract = "1"
platforms = ["android"]

[android.owns]
java_namespaces = ["org.kivmob"]

# Floors the app author no longer has to look up.
[android.requires]
min_sdk = 23
compile_sdk = 35

# The one thing the package cannot know: your own AdMob account's ID. `id` is
# what the app answers under; `kind` and `key` are where the build tool writes it.
[[android.requires.application_value]]
id = "admob_app_id"
kind = "manifest_meta_data"
key = "com.google.android.gms.ads.APPLICATION_ID"
reason = "Your AdMob application ID, from the AdMob console"
placeholder = "<TODO: ca-app-pub-…~… from the AdMob console>"

[[android.contributes.gradle_dependencies]]
module = "com.google.android.gms:play-services-ads"
version = { at_least = "24.0.0", below = "25.0.0" }

[android.contributes.src]
java = ["java"]

[[android.contributes.permissions]]
name = "android.permission.INTERNET"
reason = "Ad delivery"
```

The application depends on the package and answers the one thing that is
genuinely its own, in its own file, where the build tool scaffolded the TODO:

```toml
[project]
dependencies = ["kivmob"]

# Added by examplebuild. Required by kivmob.
[tool.examplebuild.native.kivmob.android.application_values]
admob_app_id = "ca-app-pub-3940256099942544~3347511713"
```

Not zero configuration — **no transcription of what the package owns**. Gone are
the coordinate, the permissions, the floors and the Java. The build fails naming
KivMob if the account ID is missing.

### Actions are tasks, not apologies

An action carries a `summary`, a `reason`, and optional `instructions` and
`acceptance` criteria — an end-state checklist a person, or a coding agent
working for them, can act on and check its own work against:

```toml
acceptance = [
  "A Notification Service Extension target exists",
  "The extension links the vendor SDK",
  "Incoming notifications are forwarded to the vendor handler",
]
```

Criteria state an end state, never an edit, so the specification never becomes an
Xcode-project modification language. The author acknowledges the action when it
is done; a consumer never writes that acknowledgement itself. **Version 1 defines
no verification:** a check that cannot satisfy an action buys only a better error
message, and one that can reports *done* for a requirement that is half met.

### Why the boundary matters

The specification does not model every Android and iOS feature, and the first
attempt is the evidence for why not: eighteen worked examples grew it thirteen
prerequisite tables, one per construct, against two vendors who ship new ones
every year. An action ends that. A capability Apple shipped last week is
stateable today and can be automated later if it proves common and
deterministic, rather than being unmentionable until the specification — and then
every consumer — catches up.

**Declarations stay data.** No scripts, hooks, build-system arguments or
manifest fragments, and a consumer executes nothing in a sidecar. `instructions`
describe an outcome for a human or an agent, and the record hashes them, so a
change between versions is a reviewable delta rather than a silent one.

**In one sentence:** a sidecar declares what a package owns, what it requires
from the application, and what native material it contributes; the build tool
automates the deterministic part, records it, and turns the rest into explicit,
checkable tasks.

## What the application keeps

- **Authority.** A package may *request* a permission or register a component,
  but only the application may mark a feature `required` or a component
  `exported`, and it can suppress any contributed permission outright. A package
  never writes an entitlement, and never an iOS purpose string — that text is
  user-facing and read by App Store review.
- **A review gate.** A conforming tool records the accepted native surface with
  per-file hashes and locked dependency graphs, reports any delta with
  provenance, and does not build through an unaccepted change — including the
  first build, where an application acquires all of its inherited native surface
  at once. A version bump surfaces as
  `+ android.permission.ACCESS_FINE_LOCATION` attributed to the package that
  brought it, not as an opaque hash change. Reporting covers what dependencies
  drag in, too: `com.google.android.gms.permission.AD_ID` arrives inside an ads
  AAR no package declared, and pulls you into a Play data-safety declaration.

## Out of scope

| Not covered | Because |
| --- | --- |
| Prebuilt `.aar` or iOS binaries **inside the wheel** | The manifest merges with no attribution, and a binary is opaque to a source-level model. Platform-tagged wheels already solve the binary case ([PEP 738](https://peps.python.org/pep-0738/), [PEP 730](https://peps.python.org/pep-0730/)). A Maven coordinate or Swift package *declared* in the sidecar is in scope: it arrives through the platform's resolver, locked and reported |
| Android resources (`res/`) | One flat namespace per type, so no ownership rule can be built for them — a package shipping `app_name` would rename your app. Ask for one as an action |
| Scripts, hooks, build plugins | Excluded on principle: a sidecar is data, and nothing in it is executed |
| Arbitrary manifest, `Info.plist` or build-file fragments | The declarative form of the same capability. A fragment cannot be collision-checked, refused per-permission, gated per-component, or diffed in a record. Cordova's `plugin.xml` is fifteen years of evidence |
| CocoaPods-only iOS SDKs | Nothing here resolves podspecs — SwiftPM is the one dependency mechanism this convention implements. The trend supports the bet: Firebase stops publishing to CocoaPods in October 2026, and Apple has pushed SwiftPM as the modern standard |
| Startup and lifecycle participation | A package cannot run code at launch or join an app-delegate callback. **Deferred, not refused** — the declarative route is open today, since several vendors initialize from a manifest entry naming a class a package can contribute, and an action can ask the application to make the call itself |
| SDKs whose value is a **build-time upload** — symbol files, mapping files | They need build-time execution by construction. Sentry's plugin is optional and the rest of it is declarations, so a wrapper is worth shipping; Crashlytics without its plugin reports unsymbolicated crashes, which is the part nobody wants. **Permanent** |

Three further limits are things the specification cannot *enforce*, rather than
things it declines to model:

- A component exported by a resolved Maven artifact bypasses the approval gate
  a sidecar-declared one faces.
- Contributed Swift has no symbol boundary a consumer can hold.
- Package visibility has no application veto.

[§11](SPEC.md#11-out-of-scope) states all three together, each answered with
disclosure instead.

## Why a convention rather than a PEP

Nothing here needs a change to any packaging standard: entry points and package
data are wheel features every backend already emits, so this is implementable
today by one tool and by a second without coordination. It is a *file* rather
than a `[tool.native_integration]` table because arbitrary `[tool.*]` tables do
not survive into the installed distribution — a consumer reading installed
metadata never sees them. If the practice spreads,
[PEP 561](https://peps.python.org/pep-0561/) is the precedent for writing it up:
a marker shipped as package data, a consumer that is not an installer, and
normative obligations on that consumer — standardized *after* it existed.

## Evidence

Eighteen integration cases were written as sidecars before anyone was asked to
implement this — four existing packages, fourteen clean-sheet ones covering
Firebase, Sentry, Stripe, Mapbox, Meta, Airship, Agora, Health Connect,
TensorFlow Lite and a three-package mediated-ads set — plus a survey of forty
further SDKs. They were written against the first attempt and are what condemned
it: nearly every gap they found was a missing *table*, the failure the action
shape exists to end. Seven have since been re-expressed against the current
model, and none needed a capability it lacks.

[**examples/**](examples/) carries one integration in full, both halves;
[`development/redesign/examples/pystripe/`](development/redesign/examples/pystripe/)
is the same pair converted, and reading the two together is the shortest account
of what changed. Everything else — every sidecar, every round, every finding — is
under [**development/**](development/).

## Getting involved

This is aimed at toolchains that build Python apps for mobile — among them
[python-for-android](https://github.com/kivy/python-for-android),
[Briefcase](https://github.com/beeware/briefcase),
[Chaquopy](https://github.com/chaquo/chaquopy),
[ksproject](https://github.com/kivy-school/ksproject) and
[KivyForge](https://github.com/ElliotGarbus/kivyforge). A convention only one
tool reads is not worth defining.

Most useful first:

1. **A sidecar written by someone who did not write the spec.** Eighteen have
   been written, every one by the same hand. Pick a package you know and declare
   its native half; where you get stuck is the finding.
2. **If you maintain a build tool: could your bootstrap meet
   [§2.4](SPEC.md#24-obligations-on-the-consumers-bootstrap)?** It asks for an
   `androidx.activity.ComponentActivity` and an app delegate that does not
   swallow URL callbacks — the only demand this convention makes on a tool's own
   architecture.
3. **Does the authority split land in the right place?** Where the application
   owns the artifact, a package states the need rather than writing it. Most of
   the design follows from that line.

**[Start a discussion](https://github.com/ElliotGarbus/native-integration/discussions)**
for anything about the design, including "I am not sure this is right" with no
proposal attached; issues are for concrete defects. Disagreement is more useful
than agreement — the places this is wrong now are the places nobody has looked
yet.

## The repository

The specification is the contract; **the reader** is the part of this
repository that runs. `src/` is a Python library that does the consumer's
reading half — discovery, validation, resolution, the record and the delta — so
a build tool gets §8's obligations as one call, `read()`, and starts its own
work where that call stops: generating the project. That is also why the
library cannot make a build tool conforming by itself; the
[conformance corpus](conformance/README.md) does that, and drives a tool's
command rather than importing anything. The same package installs
`native-integration`, the command line, which is how a **package author** uses
it without writing Python. [`src/README.md`](src/README.md) is the manual for
both halves, and opens by saying which half is yours.

| | |
| --- | --- |
| [**SPEC.md**](SPEC.md) | the specification. [Appendix A](SPEC.md#appendix-a-a-complete-sidecar) is a whole sidecar, [Appendix B](SPEC.md#appendix-b-declaration-reference) every key it may contain, [§8](SPEC.md#8-consuming-tool-requirements) the consumer's checklist — forty-six requirements in a core profile plus one per platform, so an Android-only tool can conform without implementing Xcode |
| [`examples/`](examples/) | one integration in full, both halves |
| [`src/`](src/README.md) | the reference reader, and its manual |
| [`conformance/`](conformance/README.md) | the corpus a consumer is tested against, its harness, and a reference consumer driving the reader in `src/` |
| [`src/native_integration/contract/`](src/native_integration/contract/) | the machine-readable vocabulary. Appendix B, the JSON schema and the diagnostic ids are all generated from it, and the reader is driven by it at run time — which is why it ships *inside* the package rather than beside SPEC.md |
| `native-integration` | the command line — `explain`, `inspect`, `validate`, `conformance`, `authoring-guide`. **Not normative**, and it says so in every answer it gives |
| [`AGENTS.md`](AGENTS.md) | one page, two playbooks — authoring a sidecar, implementing a consumer. Points at the tools rather than restating the specification |
| [`development/`](development/) | the first attempt, the rebuild, eighteen sidecars, a forty-SDK survey, and the findings from each round |
| `tools/`, `tests/` | `check_spec.py` (26 checks over both documents and every example), `toc.py`, `requirements_table.py`, and the reader's suite. All run in CI on every push |

Each check exists because the corresponding mistake shipped at least once. They
cover mechanical drift only — a section that contradicts itself still needs a
reader, which is how most of the recent defects were found.

## Before a freeze

Version 1 is a draft amended in place, on purpose: a contract frozen before
anything has been built freezes in guesses. In order — **review from people who
did not write this**, then **a real consumer**
([KivyForge](https://github.com/ElliotGarbus/kivyforge) is the intended first),
then **real packages built into an APK and an `.ipa` that run**, then consider a
freeze. Those stages are also how the open questions get answered rather than
argued: each deferral carries a trigger only a real build can pull.

What would make it ready, so the decision is a check rather than a judgement
call:

- **Two consumers read one sidecar and agree** — the point at which
  "conforming" means something.
- **A sidecar authored outside this repository.**
- **One integration on a device.** Nothing here has ever been run.
- **A round that produces only corrections**, with no capability to add.
- **A consumer that generates.** The reference reader now implements this
  document, which moved the pacing item rather than removing it: it validates
  and records, and the six assertions the conformance corpus cannot verify
  against it are all about generated output. The next thing that has never been
  done is writing the Gradle files and the Xcode project.

## License

[MIT](LICENSE) — covering the specification text and any code in this
repository, so any toolchain can implement against it without friction.
