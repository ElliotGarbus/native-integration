# native-integration

**A convention for Python packages to declare what they need from a native mobile app build.**

> **Status: draft, seeking review.** Nothing is implemented yet. This repository
> exists so the design can be argued over before anyone writes code. Feedback
> from maintainers of other toolchains is the point — see
> [Getting involved](#getting-involved).
>
> The spec has been stress-tested by expressing four real packages against it,
> which changed it substantially — see
> [Tested against real packages](#tested-against-real-packages).

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
coordinates, permissions, manifest components, SPM packages, `Info.plist` keys,
any glue source it must contribute, and the prerequisites only the app can
satisfy. A build tool discovers it through an entry point, reads it **without
importing the package**, and stages it into the generated Gradle or Xcode
project.

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
```

Everything a package declares falls into one of three categories: **`owns`**
(exclusive claims, like a Java namespace — collision-checked across all
packages), **`requires`** (conditions the app must satisfy — SDK floors,
entitlements, iOS purpose strings, an app extension the package needs), and
**`contributes`** (material the build tool stages on the package's behalf).

The line between the last two is where most of the design lives. A package that
binds a whole platform framework can also mark a prerequisite **conditional** —
*"you need this only if you call `requestAlwaysAuthorization()`"* — so apps that
never touch a feature are not made to carry it.

The app author's `pyproject.toml` simplifies to:

```toml
dependencies = ["kivmob"]
```

Read the full [specification](SPEC.md).

## What makes this different from "put the Java in a wheel"

It **is** in a wheel — the package's ordinary one. No new artifact is published,
and an otherwise pure-Python wheel can remain `py3-none-any`, because TOML and
`.java` are text rather than platform binaries. What ships is a *declaration* plus optional *source*, never a
compiled `.aar` or `.jar`.

Three properties follow from that, and they are the reason for the design:

- **Contributions stay per-package.** The tempting alternative is to have every
  package write into one shared directory and let the installer merge them. That
  destroys provenance at install time — afterwards nothing can say which package
  contributed which file, which forecloses collision detection, attribution, and
  any review gate.
- **The app keeps authority.** A package may *request* a permission or register a
  component, but only the app may mark a feature `required` or a component
  `exported` — and the app can refuse any contributed permission outright. A
  package can never write an entitlement, and never writes an iOS purpose
  string: that text is user-facing, localized, and read by App Store review, so
  it belongs to the app that answers for it. A dependency's *declaration* cannot
  silently shrink your Play device reach or open an IPC surface.
- **Changes are never invisible.** A conforming tool records each package's
  resolved contribution and reports the delta, so a version bump surfaces as
  `+ android.permission.ACCESS_FINE_LOCATION` in a diff rather than as an opaque
  hash change. That extends to what your dependencies drag in: an Android
  library's own manifest can add permissions no package declared —
  `com.google.android.gms.permission.AD_ID` arrives this way and pulls you into
  a Play data-safety declaration — so reporting those is required too.

## What is deliberately out of scope

| Not covered | Because |
| --- | --- |
| Prebuilt `.aar` **embedded in the wheel** | Carries its own `AndroidManifest.xml`, which merges into the app's — a binary nobody reviews contributing permissions and exported components. (A *declared Maven coordinate* resolving to an `.aar` is in scope: it arrives through Gradle, locked and surfaced in the report.) |
| Prebuilt iOS binaries **carried by the wheel** | Forces a platform tag onto an otherwise pure-Python wheel, and is unauditable |
| Extension modules and frameworks **shipped as binaries in wheels** | Already solved by platform-tagged wheels — [PEP 738](https://peps.python.org/pep-0738/) on Android, [PEP 730](https://peps.python.org/pep-0730/) on iOS |
| Android resources (`res/`) | Resource names are one flat namespace per type, so no ownership rule can be built for them — a package shipping `values/strings.xml` with `app_name` would rename your app. They arrive through an `.aar` instead |

Everything the Python packaging ecosystem already handles stays there. This
convention covers only what wheels have no story for: the Gradle/JVM and
Xcode/SPM side.

One qualifier on that third row, because it is the difference between "excluded"
and "the main iOS use case": what is out of scope is a **binary in a wheel**. A
Swift package that *implements* a Python extension module in source — compiled
into the app target against the app's own interpreter, no binary anywhere in the
wheel — is in scope, and the spec registers it with the interpreter so `import`
finds it. That shape turns out to be how most Python-Swift packages are built.

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
followed the same path: invented by setuptools, adopted universally, documented
afterward, never a PEP.

## Tested against real packages

Before asking anyone to implement a consumer, four packages from
[PyPlatformPackages](https://github.com/PyPlatformPackages) were expressed
against this spec, chosen to pull in different directions: **PyOneSignal**
(push, capabilities, components), **PyCoreLocation** (native Swift, permissions,
privacy), **PyWebViews** (substantial package-owned Swift), and **PyGMA**
(cross-platform third-party SDK).

**One of the four fit without a workaround.** The other three each needed either
a change to the package or a capability that did not exist, and the spec changed
as a result:

- **A Swift package can now *be* the Python module.** Most of that
  organization's iOS packages are SwiftPM libraries that implement a Python
  extension module directly. Nothing could make one importable — the build
  succeeded and `import` failed.
- **Purpose strings and required app extensions moved to the app.** The spec's
  own example had a library writing the sentence App Store review reads.
- **A package can say where it does *not* work.** "I contribute nothing on
  Android" and "I do not run on Android" were the same declaration, so a
  pure-Python wheel bound to an iOS framework would install, build, and fail at
  `import`.
- **A dozen corrections**, several of them the text disagreeing with itself —
  version ranges forbidden on Android while permitted on iOS under the same
  locking rule; three namespace-containment rules that never said whether they
  compared strings or dotted segments.

Each package's `native.toml` and the findings behind it are in
[examples/](examples/). [PROPOSALS.md](PROPOSALS.md) records what was adopted,
what was cut back, and what was deferred — with the reasoning, including the
places the evidence turned out weaker than first claimed.

## Getting involved

This is aimed at toolchains that build Python apps for mobile — among them
[python-for-android](https://github.com/kivy/python-for-android),
[Briefcase](https://github.com/beeware/briefcase),
[Chaquopy](https://github.com/chaquo/chaquopy),
[ksproject](https://github.com/kivy-school/ksproject), and
[KivyForge](https://github.com/ElliotGarbus/kivyforge). A convention only one
tool reads is not worth defining.

Particularly wanted:

1. Is the declaration set right — what is missing, what is unnecessary? The
   four packages above are all from one toolchain lineage, so a package built
   against a *different* toolchain is worth more than a fifth from the same one.
2. Does the app-keeps-authority split land in the right place?
3. If you maintain a build tool: is this something you would plausibly read?

Open an issue. Disagreement about the design is more useful right now than
agreement.

## Planned

- A reference reader library — discovery, parsing, validation, and rule
  enforcement — so the consumer obligations are code paths a tool gets by *using*
  it, rather than prose it has to remember to implement.
- A conformance test suite any consumer can run against itself.

## License

[MIT](LICENSE) — covering the specification text and any code in this
repository, so any toolchain can implement against it without friction.
