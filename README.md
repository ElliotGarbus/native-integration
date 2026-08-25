# native-integration

**A convention for Python packages to declare what they need from a native mobile app build.**

> **Status: draft, seeking review.** No build tool implements this yet. A
> [reference reader](#the-reference-reader) in this repository does, and is a
> draft alongside the text — it exists so the consumer obligations are tested
> against real sidecars rather than only asserted. This repository exists so the
> design can be argued over; feedback from maintainers of other toolchains is
> the point — see [Getting involved](#getting-involved).
>
> The spec has been stress-tested against **eighteen integration cases** — four
> existing Python packages, and fourteen clean-sheet sidecars covering Firebase,
> Sentry, Stripe, Mapbox, Meta, Airship, Agora, Health Connect, TensorFlow Lite
> and a three-package mediated-ads set — which changed it substantially, plus a
> survey of forty further SDKs. See
> [Tested against real packages](#tested-against-real-packages).
>
> **The contract is deliberately unfrozen.** Nothing here has been built into a
> build tool or run on a device yet, and freezing before that would freeze in
> guesses — see [What happens before a freeze](#what-happens-before-a-freeze).
>
> **Being restructured, right now.** What eighteen examples kept adding was
> *tables* — thirteen of them for application prerequisites alone — and that
> growth is unbounded while Apple and Google keep shipping constructs. The
> specification is being rewritten around a smaller automated core plus a
> generic way to tell an application author what remains to be done by hand.
> The first attempt is [`development/first-attempt.md`](development/first-attempt.md),
> kept whole for its reasoning and its evidence; the redesign, and the five
> hardest sidecars re-expressed against it, are in
> [`development/redesign/`](development/redesign/). Sections below still
> describe the first attempt's machinery.

## The problem

`pip install` faithfully installs what a wheel contains — but it has no
convention for translating a Python dependency's Android or iOS integration
requirements into the host application's Gradle or Xcode configuration.

Take [KivMob](https://github.com/MichaelStott/KivMob), AdMob support for Kivy on
PyPI. Installing it works. Then you hand-copy a screenful of settings out of its
README into your build config: Maven coordinates, a custom Maven repository,
manifest `meta-data`, permissions, and toolchain flags.

Every app repeats that transcription. Every version bump risks silent drift. And
when the package is a **transitive** dependency, the person on the hook may not
know it is in the tree at all.

The package knows what it needs. The app author is the one obliged to say it.
That inversion **is** the problem.

## The shape of the fix

A package ships a small TOML file declaring its native requirements — Maven
coordinates, permissions, manifest components, SwiftPM packages, `Info.plist`
keys, any glue source it must contribute, a Swift package that *is* its Python
extension module, and the prerequisites only the app can satisfy. A build tool discovers it through an entry point, reads it **without
importing the package**, validates its prerequisites, and stages its
contributions into the generated Gradle or Xcode project.

The package author adds two things to their own `pyproject.toml`:

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

[[android.contributes.gradle_dependencies]]
coordinate = "com.google.android.gms:play-services-ads:25.2.0"

[android.contributes.src]
java = ["java"]

[[android.contributes.permissions]]
name = "android.permission.INTERNET"
reason = "Ad delivery"

[[android.contributes.permissions]]
name = "android.permission.ACCESS_NETWORK_STATE"
reason = "Connectivity checks before ad requests"

# The floors the app author no longer has to look up.
[android.requires]
compile_sdk = 35
min_sdk = 23

# The one thing the package cannot know: your own AdMob account's ID.
# `id` is what the app answers under; `manifest_meta_data` is the key the SDK reads.
[[android.requires.application_values]]
id = "admob_app_id"
reason = "Your AdMob application ID, from the AdMob console"
manifest_meta_data = "com.google.android.gms.ads.APPLICATION_ID"
```

*(Illustrative. Today's KivMob also ships a separately-published bridge artifact
from its own Maven repository; a package adopting this convention would put that
Java in its own wheel via `contributes.src`, which is the shape shown here.)*

Its **native integration material** falls into three categories: **`owns`**
(exclusive claims, like a Java namespace — collision-checked across all
packages), **`requires`** (conditions the app must satisfy — SDK floors,
entitlements, iOS purpose strings, a config file, an app extension, or
credentials for an authenticated repository), and **`contributes`** (material the build tool
stages on the package's behalf).

The line between the last two is where most of the design lives, and it falls in
a specific place: **when the application owns the artifact, the package states
the need rather than writing it.** Your entitlements, your `Info.plist`, your
bundle, your extra build targets — a package can say it needs them and the build
tool reports it, but nothing reaches in. A contribution that writes half of a
two-part requirement is worse than a prerequisite naming both, because it looks
finished.

A package that binds a whole platform framework can also mark a prerequisite
**conditional** — *"you need this only if you call
`requestAlwaysAuthorization()`"* — so apps that never touch a feature are not
made to carry it.

The app author's `pyproject.toml` then carries the dependency and the one value
that is genuinely theirs:

```toml
dependencies = ["kivmob"]
```

plus the AdMob application ID, supplied once through the build tool's own
configuration — the spec requires that the tool offer a way to supply it, and
leaves the spelling to the tool.

Not zero configuration — **no transcription of what the package owns**. Gone
are the Maven coordinate, the repository, the permissions, the SDK floors and
the Java, none of which the app author ever had a reason to be holding. What
remains is the account identifier no package could know, and the build fails
naming KivMob if it is missing.

Toolchain settings stay where they are. KivMob's README also asks for an NDK
version, SDK-licence acceptance and an AndroidX flag; this convention models
neither those nor anything else that belongs to the build tool rather than to a
package.

Read the full [first attempt](development/first-attempt.md) — superseded, but
the most complete statement of the model so far. Every key a sidecar may
contain is listed with a one-line description in its
[Appendix D](development/first-attempt.md#appendix-d-declaration-reference),
which is the faster way in if you are writing one or reviewing one.

## What makes this different from "put the Java in a wheel"

It **is** in a wheel — the package's ordinary one. No new artifact is published,
and an otherwise pure-Python wheel can remain `py3-none-any`, because TOML and
`.java` are text rather than platform binaries. **What the wheel carries** is a declaration plus optional source, never a
compiled `.aar` or `.jar`. Native binaries may still enter the build through
declared Maven or SwiftPM dependencies, where the platform's own resolver
fetches them and the integration record attributes them — that is the
distinction the out-of-scope table below draws.

Three properties follow from that, and they are the reason for the design:

- **Contributions stay per-package.** The tempting alternative is to have every
  package write into one shared directory and let the installer merge them. That
  destroys provenance at install time — afterwards nothing can say which package
  contributed which file, which forecloses collision detection, attribution, and
  any review gate.
- **The app keeps authority over what a package declares.** A package may
  *request* a permission or register a component, but only the app may mark a
  feature `required` or a component `exported` — and the app can refuse any
  contributed permission outright. A package can never write an entitlement, and
  never writes an iOS purpose string: that text is user-facing, localized, and
  read by App Store review, so it belongs to the app that answers for it.

  Native artifacts resolved through Maven or SwiftPM carry their own manifests
  and are a **second, weaker boundary**, stated plainly because it would
  otherwise be a way around the first. A resolved Android library still cannot
  silently make hardware `required` — the same rule applies whoever authored it.
  Its exported components, however, are **reported with the same prominence as a
  contributed one rather than approval-gated**: attribution and review, not
  restriction. Policing arbitrary library code is not attempted.
- **Native integration changes are review-gated.** A conforming tool records the
  accepted native surface, reports any delta with provenance, and **does not
  build through an unaccepted change** — including the first build, where an
  application acquires all of its inherited native surface at once. A version
  bump surfaces as `+ android.permission.ACCESS_FINE_LOCATION` attributed to the
  package that brought it, not as an opaque hash change.

  That extends to what your dependencies drag in: an Android library's own
  manifest can add permissions no package declared —
  `com.google.android.gms.permission.AD_ID` arrives this way and pulls you into
  a Play data-safety declaration — so reporting those is required too. It is
  closer to a lockfile you review than to better build logging.

## What is deliberately out of scope

| Not covered | Because |
| --- | --- |
| Prebuilt `.aar` **embedded in the wheel** | Carries its own `AndroidManifest.xml`, which merges into the app's — a binary nobody reviews contributing permissions and exported components. (A *declared Maven coordinate* resolving to an `.aar` is in scope: it arrives through Gradle, locked and surfaced in the report.) |
| Prebuilt iOS binaries **carried by the wheel** | Forces a platform tag onto an otherwise pure-Python wheel, and is opaque to this convention's source-and-provenance checks |
| Extension modules and frameworks **shipped as binaries in wheels** | Already solved by platform-tagged wheels — [PEP 738](https://peps.python.org/pep-0738/) on Android, [PEP 730](https://peps.python.org/pep-0730/) on iOS |
| Android resources (`res/`) | Resource names are one flat namespace per type, so no ownership rule can be built for them — a package shipping `values/strings.xml` with `app_name` would rename your app. They arrive through an `.aar` instead. A package may still *require* one it cannot write — a notification icon, say — and point a manifest entry at it |
| Build plugins, run-script phases, hooks | Excluded **on principle**: a sidecar is data, and nothing in it is executed. This is permanent, and it puts one whole category of SDK out of reach — see below |
| **Arbitrary manifest, `Info.plist` or build-file fragments** | The declarative form of the same capability, excluded on the same principle. A fragment cannot be collision-checked, refused per-permission, gated per-component, or diffed in a record — a package's material stops being reviewable the moment its meaning is a merge nobody computes. Cordova's `plugin.xml` is fifteen years of evidence |
| **CocoaPods-only iOS SDKs** | Swift packages are the channel; nothing here resolves podspecs, and a second dependency channel is a larger commitment than any single vendor justifies. Google's ML Kit is the standing example |
| Compiler and linker flags | Arbitrary build mutation. One bounded exception: a package may ask that Objective-C categories in static libraries be loaded, which is a behaviour with a name rather than a flag to pass |
| Startup and lifecycle participation | A package cannot run code at launch or join an app-delegate callback. **Deferred, not refused**: real SDKs want it, and the shape it should take is not settled. The *declarative* route is now open, though — several vendors initialize from a manifest entry naming a class, which a package can contribute |

Everything the Python packaging ecosystem already handles stays there. This
convention covers only what wheels have no story for: the Gradle/JVM and
Xcode/SwiftPM side.

One qualifier on the binaries rows, because it is the difference between
"excluded" and "the main iOS use case": what is out of scope is a **binary in a
wheel**. A Swift package that *implements* a Python extension module in source —
compiled into the app target against the app's own interpreter, no binary
anywhere in the wheel — is in scope, and the spec registers it with the
interpreter so `import` finds it. That shape turns out to be how most
Python-Swift packages are built.

**The excluded category worth knowing about before you start** is any SDK whose
value depends on uploading build artifacts — symbol files, mapping files, source
maps. Those need build-time execution by construction, so this convention will
never carry them. Whether that matters depends on the SDK: Sentry's upload
plugin is optional and the rest of it is declarations, so a wrapper is worth
shipping with a known deficiency; Firebase Crashlytics without its plugin
reports unsymbolicated crashes, which is the part nobody wants.

## Why a convention rather than a PEP

Nothing here requires a change to any packaging standard. The entry-point
metadata and package data it relies on are standard wheel features every major
build backend can produce — the file-inclusion configuration is backend-specific
(setuptools `package-data`, with Hatchling, Flit, pdm, and maturin each having
their own) — so this is implementable today by a single tool, and by a second
tool without coordination.

If it spreads, the precedent for writing it up is
[PEP 561](https://peps.python.org/pep-0561/): a marker file, a consumer that is
not an installer (there, a type checker), and normative obligations on that
consumer — standardized *after* the practice existed. Entry points themselves
followed the same path: invented by setuptools, widely adopted, and standardized later as a PyPA
interoperability specification rather than a PEP.

## Tested against real packages

Before asking anyone to implement a consumer, **eighteen integration cases** were
expressed against this spec as `native.toml` sidecars — four existing Python
packages, and fourteen clean-sheet sidecars written from vendor documentation —
plus a survey of forty further SDKs read against the text without writing
sidecars for them.

| Case | Pressure on the spec | Outcome |
| --- | --- | --- |
| **PyGMA** | cross-platform third-party SDK | **fit cleanly** — exercises the Android half end to end |
| **PyOneSignal** | initialization, extensions, components | lifecycle deferred; app extensions became a prerequisite |
| **PyCoreLocation** | Swift-implemented Python module, privacy | module registration; purpose strings moved to the app |
| **PyWebViews** | SwiftPM-backed Python module | module registration confirmed; not a Python distribution at all |
| **Firebase** ×3 | build plugins, config files, FCM filters | boundaries named; `application_files`, `intent_filters` |
| **Sentry** | build-script exclusion, app values | first live use of application values; §11 corrected |
| **Stripe** | browser return, payments | `view_links` validated; iOS URL prerequisite added |
| **Mapbox** | private Maven repository | repository credentials, and a secrets rule for the record |
| **Meta SDK** | iOS account values, browser return | Android clean; iOS **blocked** — no iOS application-value table |
| **Airship** | Android configuration, two paths | iOS clean; Android **blocked** on both paths to one app key |
| **Agora** | real-time media, screen capture | calls clean; screen share **blocked** on both platforms |
| **Health Connect** | an application-owned class | **blocked** — package visibility, and a Play-required rationale activity |
| **Mediated ads** ×3 | three packages composed, plus the application's half | **clean** — two predicted stresses were structurally impossible; the application file corrected §2.2's join |
| **TensorFlow Lite** | a native library collision with Agora | **§9.1's first evidence** — and a packaging *option* no rule reaches; iOS out of reach |

**The findings were almost always missing vocabulary, not a missing shape.**
Across all eighteen sidecars and the forty-SDK survey, an inexpressible
requirement was nearly always a missing *table* — an application value, a
config file, a package-visibility declaration — never a missing way for the
application to answer. The clearest refusals held up too: Firebase's Gradle
plugin and Crashlytics' symbol upload stay unreachable because the spec
declines build-time execution, not because something is missing. What did land
from that pressure: iOS application values, package-visibility (`<queries>`),
an Android prerequisite family mirroring iOS's, verified App Links, and several
smaller vocabulary additions (SKAdNetwork identifiers, permission attributes,
manifest placeholders, core-library desugaring, Objective-C category loading) —
plus two obligations on **build tools** themselves: generating a modern Android
host activity and not swallowing iOS URL callbacks, and detecting packaging
collisions between two packages' artifacts rather than picking one silently.

[**examples/**](examples/) carries one integration in full — the package's
declaration and the application's reply side by side — if you would rather see
the authority split than read about it. The full round-by-round account, every
sidecar, and the design history behind each decision — including what was cut
back, deferred or withdrawn — are under [**development/**](development/):
[the sidecars](development/examples/) with their findings,
[SURVEY.md](development/SURVEY.md), and [PROPOSALS.md](development/PROPOSALS.md).

## Getting involved

This is aimed at toolchains that build Python apps for mobile — among them
[python-for-android](https://github.com/kivy/python-for-android),
[Briefcase](https://github.com/beeware/briefcase),
[Chaquopy](https://github.com/chaquo/chaquopy),
[ksproject](https://github.com/kivy-school/ksproject), and
[KivyForge](https://github.com/ElliotGarbus/kivyforge). A convention only one
tool reads is not worth defining.

Particularly wanted, most useful first:

1. **A sidecar written by someone who did not write the spec.** Eighteen have
   been written and every one by the same hand, which is the gap no further
   example of mine can close. Pick a package you know and try to declare its
   native half; where you get stuck is the finding.
2. **If you maintain a build tool: could your bootstrap meet §2.3?** That
   clause requires the bootstrap's Android activity to be an
   `androidx.activity.ComponentActivity`, and its iOS app delegate not to
   swallow URL callbacks. It is the only place this convention makes a demand
   on a tool's own architecture, and the cost of it is knowable only by
   whoever would pay it.
3. **Does the app-keeps-authority split land in the right place?** Where the
   application owns the artifact, a package states the need rather than writing
   it. Most of the design follows from that line, so it is the most valuable
   thing to disagree with.
4. **Would you plausibly read this at all?** A convention only one tool reads is
   not worth defining, and a clear "no, and here is why" is a better outcome
   than silence.

**[Start a discussion](https://github.com/ElliotGarbus/native-integration/discussions)**
for anything about the design — including "I am not sure this is right" with no
proposal attached, which is the most useful thing you can bring right now.
Issues are for concrete defects: a rule that contradicts another, an example
that no longer matches the specification, a requirement you could not implement.

Disagreement is more useful than agreement. The specification has been through
six rounds of examples and a forty-SDK survey, and each changed it
substantially; the places it is wrong now are the places nobody has looked yet.
The contract stays unfrozen until this has been built and run —
[what happens before a freeze](#what-happens-before-a-freeze) says in what
order, and what would make it ready.

## The reference reader

[**`src/native_integration/`**](src/README.md) is a reader for this
specification — discovery, parsing, validation, and rule enforcement — so that
the consumer obligations of [§8](development/first-attempt.md#8-consuming-tool-requirements) are code
paths a build tool gets by *using* it, rather than prose it has to remember to
implement. It is not a build tool: it never writes a Gradle or Xcode project,
never resolves a Maven coordinate, and never runs anything.

```python
integration = read(platform=Platform.ANDROID, closure=..., application=..., record_path=...)
print(integration.report())
integration.raise_for_errors()
```

[`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) maps every §8 requirement to the
code path that discharges it, generated from the rule registry and from first-attempt.md
so it cannot drift.

Two things it does deliberately, because they are the obligations most easily
lost:

- **A diagnostic cannot be constructed without naming a distribution.** That is
  requirement 8.15, enforced by a constructor rather than by discipline.
- **A missing port raises rather than passing.** Four obligations need something
  only a build tool has — a locked dependency graph with per-artifact checksums,
  an archive listing, the manifest inside a resolved `.aar`. Those are protocols
  a consumer implements, and a sidecar that needs one when none was supplied
  stops the read. A tool must not be able to pass validation by leaving a check
  unimplemented.

Writing a sidecar? `check_sidecar()` validates one on its own, before you
publish it.

## Checks

`python3 tools/check_spec.py` validates the specification against itself and
against the eighteen worked examples: that every `§` reference and link resolves, the
consumer requirements are sequentially numbered and fully indexed, every TOML
block parses, every documented sidecar obeys the rules the specification states,
every key appears in the reference table, and no RFC 2119 keyword is left
unmarked. It runs in CI on every push and pull request.

Each check exists because the corresponding mistake shipped at least once. They
cover mechanical drift only — a section that contradicts itself still needs a
reader, which is how two of the defects above were found.

`python3 tools/toc.py` and `python3 tools/requirements_table.py` regenerate the
specification's table of contents and the requirement map; both have a
`--check` mode that CI runs, because a contents list that silently omits a
section is worse than none.

`python3 -m pytest` runs the reference reader's own suite, which asks a
different question of the same files: not whether the documents agree with each
other, but whether all eighteen sidecars survive an implementation of the rules the
specification states. Both run in CI on every push and pull request.

## What happens before a freeze

Version 1 is a draft amended in place, and it stays that way on purpose. §4.3's
version gate exists so that a producer can declare which contract it needs and a
consumer can reject what it cannot implement — machinery that starts mattering
when **producers publish** against a fixed contract, not when a consumer starts
building. A tool built against a moving draft is cheap to keep in step. A
contract frozen before anything has been built freezes in guesses.

So, in order:

1. **Review from people who did not write this.** Eighteen sidecars, one hand.
   The specific asks are in [Getting involved](#getting-involved).
2. **A real consumer.** [KivyForge](https://github.com/ElliotGarbus/kivyforge) is
   the intended first one. §8's forty-one requirements and
   [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) are what an implementer works
   from; the reference reader shows one way to discharge them and is not the
   only way.
3. **Real packages, and applications that use them.** Sidecars shipped in
   wheels, resolved by that consumer, built into an APK and an `.ipa` that runs.
4. **Then consider a freeze.**

Stages 2 and 3 are also how the open questions get answered rather than argued.
Every deferral in [development/SURVEY.md](development/SURVEY.md) carries a
trigger that only a real build can pull: a toolchain floor a consumer genuinely
cannot meet, a second vendor needing a packaging option, a producer whose own
code contacts a tracking domain. And §2.3's host obligation lands directly on
whichever toolchain implements first — the cost of it is knowable only by trying.

**What would make it ready**, so the decision is a check rather than a judgement
call:

- **Two consumers read one sidecar and agree** — the point at which "conforming"
  means something. One implementation cannot demonstrate it.
- **A sidecar authored outside this repository**, by someone who read the spec
  rather than wrote it.
- **One integration on a device.** Nothing here has ever been run: eighteen
  sidecars, two hundred tests, zero installed applications.
- **A round that finds no new table.** Each round so far has added
  capability; the signal to stop is a round that produces only corrections.

## Planned

- A conformance test suite any consumer can run against itself. The reference
  reader is the start of one — its rule registry is the list of behaviours a
  suite would have to check — but a suite has to be runnable against a *tool*
  rather than against this library. It is also what makes the first exit
  criterion above checkable.

## License

[MIT](LICENSE) — covering the specification text and any code in this
repository, so any toolchain can implement against it without friction.
