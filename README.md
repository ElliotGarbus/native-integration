# native-integration

**A convention for Python packages to declare what they need from a native mobile app build.**

> **Status: draft, seeking review.** Nothing is implemented yet. This repository
> exists so the design can be argued over before anyone writes code. Feedback
> from maintainers of other toolchains is the point — see
> [Getting involved](#getting-involved).

## The problem

`pip install` delivers a package's Python and drops everything else.

Take [KivMob](https://github.com/MichaelStott/KivMob), AdMob support for Kivy on
PyPI. Installing it works. Then you hand-copy five settings out of its README
into your build config: a Maven coordinate, a custom Maven repository, manifest
`meta-data`, two permissions, and an AndroidX flag.

Every app repeats that transcription. Every version bump risks silent drift. And
when the package is a **transitive** dependency, the person on the hook may not
know it is in the tree at all.

The package knows what it needs. The app author is the one obliged to say it.
That inversion **is** the problem.

## The shape of the fix

A package ships a small TOML file declaring its native requirements — Maven
coordinates, permissions, manifest components, SPM packages, `Info.plist` keys,
and any glue source it must contribute. A build tool discovers it through an
entry point, reads it **without importing the package**, and stages it into the
generated Gradle or Xcode project.

The package author adds two things to their own `pyproject.toml`:

```toml
[project.entry-points."native-integration.v1"]
native = "kivmob._native"

[tool.setuptools.package-data]
kivmob = ["_native/**/*"]
```

and ships `kivmob/_native/native.toml`:

```toml
contract = "1"

[android]
java_namespace = "org.kivmob"

[android.gradle]
dependencies = ["com.google.android.gms:play-services-ads:25.2.0"]

[android.src]
java = ["java"]

[android.permissions]
uses = ["INTERNET", "ACCESS_NETWORK_STATE"]
```

The app author's `pyproject.toml` gains nothing:

```toml
dependencies = ["kivmob"]
```

Read the full [specification](SPEC.md).

## What makes this different from "put the Java in a wheel"

It **is** in a wheel — the package's ordinary one. No new artifact is published,
and the wheel stays `py3-none-any`, because TOML and `.java` are text rather than
platform binaries. What ships is a *declaration* plus optional *source*, never a
compiled `.aar` or `.jar`.

Three properties follow from that, and they are the reason for the design:

- **Contributions stay per-package.** The tempting alternative is to have every
  package write into one shared directory and let the installer merge them. That
  destroys provenance at install time — afterwards nothing can say which package
  contributed which file, which forecloses collision detection, attribution, and
  any review gate.
- **The app keeps authority.** A package may *request* a permission or register a
  component, but only the app may mark a feature `required` or a component
  `exported`. A dependency cannot silently shrink your Play device reach or open
  an IPC surface.
- **Changes are never invisible.** A conforming tool records each package's
  resolved contribution and reports the delta, so a version bump surfaces as
  `+ ACCESS_FINE_LOCATION` in a diff rather than as an opaque hash change.

## What is deliberately out of scope

| Not covered | Because |
| --- | --- |
| Prebuilt `.aar` | Carries its own `AndroidManifest.xml`, which merges into the app's — a binary nobody reviews contributing permissions and exported components |
| Prebuilt iOS binaries | Forces a platform tag onto an otherwise pure-Python wheel, and is unauditable |
| Native `.so`, extension modules | Already solved by `android_<api>_<abi>`-tagged wheels ([PEP 738](https://peps.python.org/pep-0738/)) |
| iOS frameworks in wheels | Already solved by `ios_*`-tagged wheels ([PEP 730](https://peps.python.org/pep-0730/)) |

Everything the Python packaging ecosystem already handles stays there. This
convention covers only what wheels have no story for: the Gradle/JVM and
Xcode/SPM side.

## Why a convention rather than a PEP

Nothing here requires a change to any packaging standard. Entry points and
package data already work with every build backend — setuptools, hatchling,
flit, pdm, maturin — so this is implementable today by a single tool, and by a
second tool without coordination.

If it spreads, the precedent for writing it up is
[PEP 561](https://peps.python.org/pep-0561/): a marker file, a consumer that is
not an installer (there, a type checker), and normative obligations on that
consumer — standardized *after* the practice existed. Entry points themselves
followed the same path: invented by setuptools, adopted universally, documented
afterward, never a PEP.

## Getting involved

This is aimed at toolchains that build Python apps for mobile — among them
[python-for-android](https://github.com/kivy/python-for-android),
[Briefcase](https://github.com/beeware/briefcase),
[Chaquopy](https://github.com/chaquo/chaquopy),
[ksproject](https://github.com/kivy-school/ksproject), and
[KivyForge](https://github.com/ElliotGarbus/kivyforge). A convention only one
tool reads is not worth defining.

Particularly wanted:

1. Is the declaration set right — what is missing, what is unnecessary?
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
