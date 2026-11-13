# PyCoreLocation against contract 1

Source: [PyPlatformPackages/PyCoreLocation](https://github.com/PyPlatformPackages/PyCoreLocation).

This was supposed to be the control case — native Swift plus permissions and
privacy, expected to fit cleanly. It did not, and it failed in a more
interesting way than PyOneSignal did.

## What this package actually is

It is not a Python package with a Swift shim. It is a **SwiftPM library that is
the Python extension module**:

```swift
@PyModule
struct PyCoreLocation: PyModuleProtocol {
    static let py_classes: [any (PyClassProtocol & AnyObject).Type] = [
        CLBeacon.self, CLLocation.self, PyLocationManager.self, …
    ]
}
```

`PyLocationManager` is a `@PyClass` wrapping `CLLocationManager`; every method is
a `@PyMethod`. The wheel's `src/py_core_location.py` is a generated typing stub
carrying nothing but `pass` bodies, and says so in a header comment: *"only
intended for venv usage while writing code / do not try add this file to a real
app."*

So the distribution's Python content is documentation, and its native content is
the product. That inverts the assumption running through §6.4, §7.5, and §12,
where native material supplements a Python implementation.

## What version 1 expresses

| Requirement | Mechanism | Verdict |
| --- | --- | --- |
| iOS 13 floor | §7.2 `deployment_target` | clean |
| The Swift library itself | §7.4 `swift_packages` | works, with L1 |
| PySwiftKit, CPython, swift-syntax… | resolved transitively by SwiftPM | correct — not the sidecar's business |
| `NSLocationWhenInUseUsageDescription` | §7.6 `info_plist.values` | **wrong shape** — L3 |

One genuine validation: §7.1's symbol-prefix guidance is **not needed here**,
because a SwiftPM library is its own module. The hardening §7.1 defers to §10
("compiling each producer's Swift into a separate module") is what this
ecosystem already gets for free by using §7.4 instead of §7.5. That is an
argument for strengthening §7.5's discouragement, not for adding machinery.

## L2 — no way to register the Python module *(blocking, and ecosystem-wide)*

A PySwiftKit module is compiled into the application and must be registered with
the interpreter before Python can import it. The OneSignal iOS guide shows the
mechanism from the application side:

```swift
KivyLauncher.pyswiftImports = [ .ios, ]
```

Version 1 cannot express this. The consequence is total: the Swift builds, the
app links, and `import py_core_location` fails at runtime — or worse, finds the
stub on `sys.path` and returns `None` from every method.

**This is not one package's problem.** PyCoreLocation, PyWebViews, PyPHPicker,
PyCamera, PyCoreBluetooth, PyCoreMidi, PyTextToSpeech, PySpeechRecognizer and
the rest of the organization's iOS packages are all built this way. A
specification that cannot express module registration cannot express the
ecosystem's iOS strategy at all.

**It also answers the open question left in P1.** The startup-hook shape
proposed for PyOneSignal — call this static method once at launch — does not fit
this case. Registration happens before interpreter start, has different timing,
and does not want a hook at all. It wants pure data:

```toml
[[ios.contributes.python_modules]]
name = "py_core_location"
swift_package = "PyCoreLocation"   # a package this sidecar declares
init = "PyInit_PyCoreLocation"     # optional; defaults from name
```

That is strictly better than a hook for this case: nothing is executed, nothing
is ordered, the consumer just adds an inittab entry. **P1 should therefore be
split** — a declarative module-registration table (this) and a launch-time hook
(PyOneSignal) are two primitives, not one, and only the second needs a fixed
signature and an ordering rule.

**Tension with §11.** The table there says extension modules are "solved by
`android_<api>_<abi>`-tagged wheels (PEP 738)" and iOS frameworks by
"`ios_*`-tagged wheels (PEP 730)". That is the right answer for a
dynamically-loaded extension module. It is not the answer here: these modules
are statically compiled into the application target against the app's own
CPython, which is why they need inittab registration rather than `dlopen`. §11
currently reads as though the case is covered when it is not. Either §11 must
narrow its claim, or the specification must accept that "extension module" has
two shapes on mobile and it only excludes one.

## L1 — a producer declaring itself as a Swift package

`[[ios.contributes.swift_packages]]` was written for third-party SDKs. Here the
producer points it at its own repository, which version 1 permits without
comment. Three consequences worth naming:

**The record covers nothing.** §9 requires a SHA-256 per file "covering
`native.toml` and every resource it references." Here the sidecar references no
resources — the implementation is a git URL. The per-file hashing that §9 calls
"the useful identity for *this* protocol" identifies a stub.

**Wheel and tag cannot even be made to correspond.** The repository carries
**no git tags at all**, so SwiftPM cannot resolve it by version: the only forms
left are `revision` and `branch`, and §7.4 forbids `branch`. The declaration has
to pin a commit, and the distribution's own version (`0.1.0`) appears nowhere in
it. Nothing requires the two to agree, and here nothing could.

This was worse than first drafted — the initial version of the sidecar beside
this file declared `{ exact = "0.1.0" }`, which would never have resolved.
PyWebViews then showed the problem is not just missing tags: its tags are
`311.0.0` … `311.1.3`, because in this ecosystem a Swift package's major version
encodes the **CPython ABI** it targets. So a "SHOULD pin the distribution's own
version" rule is not merely unmet here, it is unimplementable — the two version
lines mean different things. See P13 in [PROPOSALS.md](../../PROPOSALS.md).

**§7.4's rules do not reach the transitive graph, and this repository proves
it.** PyCoreLocation's `Package.swift` declares:

```swift
.package(path: "/Volumes/CodeSSD/PythonSwiftGithub/PyFileGenerator")
```

— a local filesystem path that exists on one developer's machine. And its
`Package.resolved` pins `PySwiftAST` to `"branch": "master"`.

§7.4 forbids a `branch` requirement and requires exact/from/revision, but those
rules govern the **sidecar's declaration only**. Once the consumer resolves a
declared package, that package's own manifest can contain a branch dependency, a
local path, or any URL, and nothing in the specification looks. Compare §6.5,
which is explicit that the recorded Gradle graph covers "every artifact and
version, **including transitives**." §7.4 says only "the version actually
resolved," singular.

**Fix:** §7.4 should mirror §6.5 — record the full resolved Swift graph
including transitives, and state what happens when that graph contains a branch
or path dependency. (Reject, most likely: `Package.resolved` pins a revision, so
a branch dependency is reproducible after first resolution but its recorded
revision has no stable meaning, and a path dependency is not resolvable on
another machine at all.)

## L3 — usage descriptions are the wrong category *(design bug in §7.6)*

CoreLocation requires `NSLocationWhenInUseUsageDescription`; its absence is a
hard crash the first time authorization is requested. Version 1's only mechanism
is `[ios.contributes.info_plist.values]`, so **the producer writes the string**.

That is the wrong authority. A purpose string is user-facing, localized, read by
App Store review, and is a claim about what *the application* does with the
data — which a framework binding cannot know. Every application shipping
PyCoreLocation would carry the same "This app uses your location," which is both
useless to users and a rejection risk.

§7.6's own example makes exactly this mistake:

```toml
[ios.contributes.info_plist.values]
NSBluetoothAlwaysUsageDescription = "Connects to your fitness tracker."
```

A library cannot know that the application connects to a fitness tracker.

**Fix:** usage descriptions are a `requires`, not a `contributes` — the same
authority model as §6.7 and §7.3, where the producer states the need and the
application supplies the substance:

```toml
[[ios.requires.usage_descriptions]]
key = "NSLocationWhenInUseUsageDescription"
reason = "requestWhenInUseAuthorization() traps if this key is absent"
```

Reported as a prerequisite, never written. This also disposes of a second
problem for free: `NSLocationTemporaryUsageDescriptionDictionary` — needed by
`requestTemporaryFullAccuracyAuthorization(purposeKey:)`, which this package
exposes — is **dictionary-valued**, and §7.6 excludes dictionaries. As a
`requires` it never needs to be spelled, so the exclusion stops mattering.

Consumers should probably reject any `info_plist.values` key ending in
`UsageDescription` outright once the `requires` form exists.

## L4 — §12's remedy does not apply to a framework binding

PyCoreLocation's API surface implies different native requirements per feature:

| API | Requires |
| --- | --- |
| `requestWhenInUseAuthorization` | `NSLocationWhenInUseUsageDescription` |
| `requestAlwaysAuthorization` | `NSLocationAlwaysAndWhenInUseUsageDescription` |
| `allowsBackgroundLocationUpdates` | `UIBackgroundModes = ["location"]` |
| `requestTemporaryFullAccuracyAuthorization` | `NSLocationTemporaryUsageDescriptionDictionary` |
| `startMonitoringLocationPushes` | `com.apple.developer.location.push` **and a second app extension** |

This is §12's facade problem, and §12's remedy — split feature-conditional
surface into optional distributions — **does not work here**. Plyer can be split
because its features are independent implementations behind one dispatcher.
PyCoreLocation is a 1:1 binding of `CLLocationManager`: the API surface is
Apple's, it is one Swift module and one `@PyModule`, and there is no seam along
which `pycorelocation-background` could be carved without splitting the class.

So the union-of-permissions problem §12 warns about is unavoidable for this
package shape, and version 1 offers no recourse: §6.7's application-side
suppression is defined **for Android permissions only**, with no iOS equivalent
for Info.plist keys or entitlements.

Two things follow. §12 should acknowledge that its guidance covers facades and
not framework bindings, and say what a binding should do instead. And the honest
answer for a binding is probably a **conditional prerequisite** — a declaration
the consumer reports but cannot verify:

```toml
[[ios.requires.usage_descriptions]]
key = "NSLocationAlwaysAndWhenInUseUsageDescription"
reason = "Required only if your application calls requestAlwaysAuthorization()"
conditional = true      # reported as guidance; does not fail the build
```

Unconditional prerequisites fail closed as today; conditional ones are
disclosure, which §9 already treats as a legitimate mode.

## L5 — a second app extension kind, and a stronger case for P4

`startMonitoringLocationPushes` needs a **Location Push Service Extension**: its
own target, a `CLLocationPushServiceExtension` principal class, and the
`com.apple.developer.location.push` entitlement — which
[requires approval from Apple](https://developer.apple.com/documentation/BundleResources/Entitlements/com.apple.developer.location.push).

Two consequences:

- **P4 is no longer a single-example proposal.** App extensions now have two
  independent motivating cases from two unrelated packages, and P4's closed
  `kind` vocabulary needs at least `notification_service` and `location_push`.
- **It is the strongest evidence yet for §7.3's rule** that a consumer must
  never write an entitlement. This one cannot be granted by any amount of local
  configuration — it requires a request to Apple. A consumer that wrote it would
  produce a signing failure with no trace to the cause, which is precisely
  §7.3's stated rationale, now with a case where the gap between "declared" and
  "grantable" is weeks long.

## L6 — no way to say "I do not support this platform"

PyCoreLocation is iOS and macOS only. Its sidecar declares an `[ios]` table and
nothing else, which §5 explicitly blesses: *"A sidecar declaring no platform
table is valid and contributes nothing."*

But **"I contribute nothing on Android" and "I do not work on Android" are the
same declaration in version 1**, and they are very different facts. An
application that depends on PyCoreLocation and builds for Android gets a
successful build and an app that fails at `import`, or — because the wheel is
pure-Python and untagged — silently ships the typing stub and returns `None`
from every call.

This is the failure mode §4.4 exists to prevent, arriving through a door §4.4
does not watch. A cheap fix:

```toml
platforms = ["ios"]        # top level; consumer fails when building for another
```

The counter-argument is that this is packaging's job — environment markers or
platform-tagged wheels — and that is partly true. But the wheel here is
pure-Python and installs everywhere, the application author lists the dependency
by name, and the consumer is already reading the sidecar at exactly the moment
the question can be answered. A one-line declaration converts a runtime mystery
into a build-time diagnostic naming the distribution.

## L7 — macOS has nowhere to go

`Package.swift` declares `.macOS(.v11)` alongside `.iOS(.v13)`, and the
organization's existing tooling has a `[tool.kivy-school.macos]` table. §5
defines `android` and `ios`. §4.4 says a consumer **SHOULD** warn about an
unrecognized top-level table "since it cannot distinguish a future platform from
a misspelled one" — so a producer supporting macOS today gets warned at for
telling the truth.

Not urgent, but the specification should say whether the platform set is closed
in version 1 and what a producer targeting something else is meant to do.

## Verdict

PyCoreLocation was picked as the easy case and turned out to be the harder one.
PyOneSignal's gaps were about **attachment** — where a package plugs into the
generated project. PyCoreLocation's are about **identity**: version 1 assumes a
producer is a Python package that brings native material along, and this
producer is native material with a Python name.

Three findings change the shape of the proposals rather than adding to them:

- **L2 splits P1.** Module registration is data, not a hook. Two primitives.
- **L3 moves a key from `contributes` to `requires`**, and fixes an example in
  the spec that currently instructs producers to do the wrong thing.
- **L1 opens a hole §6.5 already closed on the Android side** — transitive
  native dependency graphs are governed on Gradle and ungoverned on SwiftPM,
  and this repository contains both a branch dependency and a local path
  dependency to prove it is not hypothetical.

L5 promotes P4 from hypothesis to finding. L4, L6 and L7 are new.

Running order from here: **PyWebViews** next, which should stress §7.5 and the
module-registration finding at volume, then **PyGMA** for cross-platform
symmetry and §6.3.
