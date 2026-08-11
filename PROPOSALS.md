# Proposals for contract 1.1

**Status: proposals, not specification.** Nothing here is normative. This file
records design work driven by the worked examples under `examples/`, so it
survives while more examples are run. It moves into SPEC.md only after the
example set stops changing it.

> **Landed.** The corrections group — **P5, P6, P7, P9, P10, P13, P14, P15,
> P16, P17, P18, P19**, plus the §6.3 satisfaction correction recorded under
> P2 — is now in SPEC.md. Those sections below are kept as the reasoning
> behind the change, not as outstanding work.
>
> **Still outstanding:** P1, P3, P4, P8, P11, P12, P20. **Withdrawn:** P2.
>
> Nothing landed adds a capability a producer must adopt, with two exceptions
> worth noting: §6.5's bounded range form and §7.3's `usage_descriptions` are
> both new spellings. Because the specification is still a draft amended in
> place, no contract minor was allocated for them, and the restriction that
> §7.6 now rejects usage-description keys would otherwise have required a new
> major under §10.

Each proposal names the example that produced it. A proposal with exactly one
motivating example is a hypothesis; a proposal with several is a finding.

| # | Proposal | Fixes | Motivated by |
| --- | --- | --- | --- |
| P1 | Startup hooks | A2, B5 | PyOneSignal |
| P2 | ~~Platform-neutral application values~~ **withdrawn** | B6, C1, A3 | withdrawn by **PyGMA** (G1) |
| P3 | No sidecar resources; contributed `meta_data` | A3, A4 | PyOneSignal |
| P4 | iOS app extensions | B1, B2, B3, B4, L5 | PyOneSignal, **PyCoreLocation** |
| P5 | Bounded Maven version ranges | A1 | PyOneSignal (and §7.4's own rule) |
| P6 | Reverse-DNS namespace guidance | A5 | PyOneSignal, PyGMA |
| P7 | State why `target_sdk` is absent | A6 | PyOneSignal |
| P8 | Python module registration | L2, W2 | PyCoreLocation, **PyWebViews** |
| P9 | Usage descriptions are a `requires` | L3 | PyCoreLocation |
| P10 | Govern the transitive Swift graph | L1, W5 | PyCoreLocation, **PyWebViews** |
| P11 | Declaring an unsupported platform | L6 | PyCoreLocation |
| P12 | §12 does not cover framework bindings | L4, W6 | PyCoreLocation, **PyWebViews** |
| P13 | Self-declared Swift packages | L1, W3 | PyCoreLocation, **PyWebViews** |
| P14 | Unsatisfiable native resolution | W3 | PyWebViews |
| P15 | The Python distribution is the carrier | W1 | PyWebViews |
| P16 | Do not add dictionary Info.plist support | W6 | all three iOS examples |
| P17 | Narrow §7.5, and say what §7.1 misses | W4 | PyWebViews |
| P18 | Define namespace containment | G3 | PyGMA |
| P19 | Sharpen §6.3 to build-time values | G1 | PyGMA |
| P20 | Reconsider §9's effective-delta SHOULD | G5 | PyGMA |

Gap identifiers refer to the NOTES.md beside each example:
[PyOneSignal](examples/pyonesignal/NOTES.md) (A*, B*, C*),
[PyCoreLocation](examples/pycorelocation/NOTES.md) (L*),
[PyWebViews](examples/pywebviews/NOTES.md) (W*),
[PyGMA](examples/pygma/NOTES.md) (G*).

P6 and P11 each gained a second example from PyGMA (G2, G4).

---

## P1 — Startup hooks

**Problem.** `<application android:name>` on Android and `main.swift` on iOS are
the points where an SDK initializes, and version 1 can express neither.
PyOneSignal's entire Java half is an `android.app.Application` subclass;
its iOS half must call `OneSignal.initialize(_:withLaunchOptions:)` before
`SDLmain()`.

**Why not a fifth `kind` in §6.8.** `<application android:name>` is a singleton
slot, not a repeatable component. It fits neither category: not `contributes`,
because two producers cannot both have it; not `owns`, because a producer
claiming it locks every other SDK out of initialization — strictly worse than
the status quo, where the application author writes one `Application` class that
calls both SDKs.

**Proposal.** The consumer owns the slot; producers attach to it.

```toml
[[android.contributes.startup]]
class = "com.kivyschool.pyonesignal.Init"
reason = "OneSignal must initialize before any activity receives a notification intent"

[[ios.contributes.startup]]
function = "pyOneSignalStart"
reason = "OneSignal.initialize must run before SDLmain()"
```

Rules:

- **The signature is fixed by this specification, not declarable.**

  ```java
  public static void onApplicationCreate(android.app.Application app,
                                         java.util.Map<String, String> values)
  ```
  ```swift
  func <name>(launchOptions: [UIApplication.LaunchOptionsKey: Any]?,
              values: [String: String])
  ```

  No arguments to spell, no return value, no overloads. A producer writes to a
  known shape or it does not compile.
- **Owned namespace only.** The declared class must fall under an owned
  namespace (§6.1 rule 2 extends to it). There is no `from_dependency` form: a
  hook naming a dependency's class would let a producer invoke arbitrary
  third-party code by declaration, and a three-line shim costs nothing.
- **Deterministic order** — normalized distribution name — recorded in §9.
- **A throwing hook is not swallowed.** The consumer's generated wrapper logs,
  naming the distribution, and rethrows. A silently half-initialized SDK is the
  "fails far from the cause" failure §2.1 exists to prevent.
- The consumer generates or extends its own `Application` subclass. A producer
  **MUST NOT** be able to set `android:name`.

**This does not violate §2.1, and the spec should say so where it lands.** It
looks like a violation at a glance. It is not, for two reasons:

1. The *declaration* is a class name and a method name — data. The consumer
   executes nothing at build time; it generates a call into source the producer
   already ships (§6.4, §7.5) and the consumer already compiles.
2. It grants no new capability. A producer that registers a `service` or
   `receiver` under §6.8 today already gets code running in the application.
   The hook converts an existing capability from undeclarable into declared,
   ordered, and recorded.

**Open question — answered by PyCoreLocation.** The question was whether one
fire-once hook is enough or whether some producers need a registration shape.
They do, and the registration case wants **data, not a hook**: see P8. P1 is
therefore narrower than first drafted — it covers launch-time initialization
only, and it keeps the fixed signature and the ordering rule, both of which P8
does not need.

## P2 — Platform-neutral application values *(WITHDRAWN by PyGMA)*

**Withdrawn.** After four examples, `application_values` has **zero live use
cases**, so there is nothing to make platform-neutral.

PyGMA wraps the GMA **Next-Gen** SDK, which takes the app ID programmatically
via `InitializationConfig.Builder(appId)` — so §6.3's own flagship example, the
AdMob `APPLICATION_ID` manifest `<meta-data>` entry, is the *legacy* SDK's
mechanism and PyGMA needs no application value at all. PyOneSignal's app ID is
likewise a runtime argument once the `Application` subclass is dropped, which
contract 1 forces anyway (A2). Neither Swift package has anything of the kind.
The only surviving consumer of the mechanism in the entire specification is
§6.8's **inline** form, where `view_links` substitutes a redirect scheme into a
generated intent filter.

**What survives is P19**, which sharpens §6.3 rather than generalizing it, and
the §6.3 satisfaction correction recorded below — that one is independent of the
motivating case and still stands.

The original proposal is kept below for the record.

---

**Problem.** The OneSignal App ID is needed on both platforms. §6.3
`application_values` lives under `[android.requires]` with no iOS counterpart,
so one logical requirement is either declared twice under two mechanisms or goes
undeclared on iOS.

**Proposal.** Promote it to a top-level table, with a **logical** name:

```toml
[[requires.application_values]]
name = "onesignal_app_id"
reason = "Your OneSignal App ID, from Dashboard → Settings → Keys & IDs"
```

**Correction to §6.3.** The current text says such a value "is satisfied when the
application's own configuration supplies a manifest `<meta-data>` entry with that
`name`." That is over-specific and does not match the spec's own inline form —
`view_links` substitutes an application value into an intent filter, never
through meta-data. Split the two concerns:

- The **application supplies** values through the consumer's configuration.
- The **consumer delivers** them: into the P1 hook's `values` map, and by
  substitution wherever a contribution references one inline.

`<meta-data>` becomes one possible delivery mechanism among several, not the
definition of satisfaction.

**Why the hook map matters.** It is how a value reaches producer code without
the producer knowing anything about the consumer. The alternative — a
consumer-generated constants class the producer imports — would couple producer
source to a specific consumer, which is the coupling this whole convention
exists to avoid.

This is also what dissolves gap A3: PyOneSignal's
`getIdentifier("onesignal_app_id", "string", …)` becomes
`values.get("onesignal_app_id")`.

## P3 — No sidecar resources; add contributed `meta_data`

**Two halves, opposite answers.**

**Resources: do not add them.** A sidecar `res/` tree is worse than it looks —
Android resource names are a flat global namespace per type, so a producer
shipping `values/strings.xml` with `app_name` renames the application, and there
is no ownership handle to check it against (resource names have no dots, so
§6.1's namespace check cannot apply).

The answer already exists and is consistent with §11's reasoning: **resources
arrive through an AAR via a declared Gradle coordinate**, where AGP merges them
and §9's effective-delta reporting surfaces them. The remaining case from
PyOneSignal — the default notification icon — is **application branding**, not
producer material, and belongs in the application's own configuration.

If a later example produces a resource need that neither channel covers, the
narrow form to consider is typed, prefix-constrained resource contributions, not
a tree.

**`meta_data`: add it.** §6.3 lets a producer *require* an application-supplied
value but gives no way to contribute a **fixed** one. OneSignal Android uses
meta-data to name its notification-extender class, and the existing ecosystem
already has this key — ksp-builder reads `[tool.kivy-school.android] meta_data`
and merges it into the manifest. A producer migrating to this specification
would **lose** a capability it has today.

```toml
[[android.contributes.meta_data]]
name = "com.onesignal.NotificationServiceExtension"
value = "com.kivyschool.pyonesignal.NotificationExtender"   # or { application_value = "…" }
reason = "Registers the notification-modifying class with the OneSignal SDK"
```

- Two distributions setting the same `name` to different values **MUST** fail,
  naming both — the §7.6 `info_plist.values` rule.
- If the **application** also sets the key, the application wins and the
  consumer **MUST** report the override.
- Recorded and attributed per §9.

## P4 — iOS app extensions

**Problem.** The largest single gap. OneSignal's iOS integration requires a
Notification Service Extension: a second build target with its own Swift source,
entitlements, deployment target, Info.plist `NSExtension` **dictionary**, bundle
identifier derived from the app's, and a *different* SwiftPM product
(`OneSignalExtension`, where the app target links `OneSignalFramework`).
Version 1 has no notion of a target other than the app. Without the extension,
OneSignal loses confirmed delivery, badge counts, and image attachments.

**Proposal.** Apply the `view_links` move — model one stereotyped shape, not the
grammar.

```toml
[[ios.contributes.app_extensions]]
kind = "notification_service"        # closed vocabulary — NOT a raw NSExtensionPointIdentifier
reason = "Confirmed delivery, badge counts, and image attachments"
principal_class = "PyOneSignalNotificationService"
src = { swift = ["swift/nse"] }
deployment_target = "12.0"           # optional; defaults to the app's

  [[ios.contributes.app_extensions.package_products]]
  package = "OneSignal"              # a package this same sidecar declares (§7.4)
  products = ["OneSignalExtension"]

  [[ios.contributes.app_extensions.requires.entitlements]]
  key = "com.apple.security.application-groups"
  shared_with_app = true
  reason = "OneSignal expects group.<main-app-bundle-id>.onesignal on both targets"
```

Design rules:

- **`kind` is a closed vocabulary.** Contract 1.1 would define
  `notification_service` (PyOneSignal) and `location_push` (PyCoreLocation's
  `startMonitoringLocationPushes`), and nothing else. The consumer generates
  `NSExtensionPointIdentifier` and the whole `NSExtension` dictionary from it —
  so **B4 never arises** and dictionary-valued Info.plist support (§7.6) is not
  needed to reach this case. An open extension-point identifier would be a
  declaration that runs arbitrary background code under its own entitlements.
- **The bundle identifier is the consumer's**, derived from the application's.
  A producer cannot spell it.
- **One extension per `kind` across all producers.** iOS permits exactly one
  notification service extension, so two claimants is a real conflict: fail,
  naming both.
- **Extension entitlements stay `requires`.** §7.3 is unchanged — reported,
  never written. `shared_with_app = true` is what expresses the cross-target
  equality constraint that today survives only as prose in a `reason` (B3).
- `package_products` referencing a package the same sidecar declares mirrors
  §6.8's `from_dependency`, fixing B2 without adding a target dimension to §7.4.

**Note on the category model.** This introduces exclusivity *inside*
`contributes`, where §2.1 currently locates exclusivity only in `owns`. That is
acceptable and does not need an `owns` table: the consumer owns the slot, and the
rule is a collision check between producers, not a claim a producer holds.

**Cost.** This is the largest addition proposed here. It was drafted against a
single example; PyCoreLocation supplied a second, independent one (L5), so the
question is no longer whether app extensions are a real requirement but how
narrow the `kind` vocabulary can stay.

PyCoreLocation also sharpens the entitlement half. `com.apple.developer.location.push`
[requires approval from Apple](https://developer.apple.com/documentation/BundleResources/Entitlements/com.apple.developer.location.push)
before it can be granted at all — the strongest case yet for §7.3's rule that a
consumer must never write an entitlement, since here the gap between "declared"
and "grantable" is measured in weeks.

## P5 — Bounded Maven version ranges

**Problem.** OneSignal's documented coordinate is
`com.onesignal:OneSignal:[5.6.1, 5.9.99]`. §6.5 rejects it as a dynamic version,
so a producer must pin and cut a wheel release for every SDK patch.

**The decisive argument is not the friction — it is that the specification
disagrees with itself.** §7.4 already permits `{ from = "5.4.1" }`, which is an
up-to-next-major **range**, and makes it reproducible by pinning the resolved
version in §9. §6.5 forbids the identical construct on Android while mandating
the same lock. One of the two rules is wrong.

**Proposal.** Permit a bounded range, resolution pinned by the record:

```toml
[[android.contributes.gradle_dependencies]]
module = "com.onesignal:OneSignal"
version = { at_least = "5.6.1", below = "6.0.0" }
```

Open-ended (`+`, `latest.release`) and changing (`-SNAPSHOT`) versions stay
rejected — those are the ones no lock can make honest. The exact-coordinate form
remains valid and **RECOMMENDED**.

**The counter-argument, for the record.** An exact coordinate tells a reviewer
what they get from the sidecar alone, without consulting the record. That is a
genuine auditability benefit. It is a trade, not a self-evident rule, and §6.5
currently presents it as the latter. If the ban survives this proposal, the
rationale must say what it costs and why §7.4 differs.

## P6 — Reverse-DNS namespace guidance

PyGMA's Java lives in a bare top-level `PyGMA` namespace. That is ownable and
collision-checked under §6.1, but a single-label Java package is a poor claim.

Add a **SHOULD** to §6.1 that owned namespaces be reverse-DNS, and a consumer
**SHOULD** warn on a single-label claim.

Separately, PyOneSignal's `com.kivyschool.android` — a namespace every
KivySchool package would share — is correctly rejected by §6.1 rule 5 as soon as
a sibling ships. No change needed; the rule works. Recorded here only because it
is evidence for the rule rather than against it.

## P7 — State why `target_sdk` is absent

`POST_NOTIFICATIONS` runtime behavior keys off `targetSdk`, not `compileSdk`, so
its absence from §6.2 is noticeable. It is almost certainly the right call —
`targetSdk` is application policy, and a producer floor would change behavior
across the entire application, not just the producer's surface. One sentence of
rationale in §6.2 prevents the question from being rediscovered.

## P8 — Python module registration

**Problem.** PyCoreLocation is a SwiftPM library that *is* the Python extension
module — `@PyModule struct PyCoreLocation: PyModuleProtocol`, with the wheel
carrying only a generated typing stub. The module is compiled into the
application and must be registered with the interpreter before Python can import
it. Version 1 cannot say this, so the Swift builds, the app links, and
`import py_core_location` fails at runtime.

**Scope.** This is not one package. PyCoreLocation, PyWebViews, PyPHPicker,
PyCamera, PyCoreBluetooth, PyCoreMidi, PyTextToSpeech and PySpeechRecognizer are
all built this way. A specification that cannot express module registration
cannot express the organization's iOS strategy at all.

**Proposal.** Pure data — no hook, no ordering, no signature:

```toml
[[ios.contributes.python_modules]]
name = "py_core_location"
swift_package = "PyCoreLocation"   # a package this same sidecar declares
init = "PyInit_PyCoreLocation"     # optional; defaults from name
```

The consumer adds an inittab entry. Nothing is executed at build time and
nothing is ordered.

**Why this is separate from P1.** Registration happens before interpreter start,
wants no arguments, and has no failure mode worth ordering. Folding it into the
hook table would force a fixed signature and a deterministic order onto a case
that needs neither.

**Tension with §11 that must be resolved either way.** §11 says extension
modules are "solved by `android_<api>_<abi>`-tagged wheels (PEP 738)" and iOS
frameworks by "`ios_*`-tagged wheels (PEP 730)". That is right for a
dynamically-loaded extension module and wrong here: these are statically
compiled into the application target against the app's own CPython, which is
exactly why they need inittab registration rather than `dlopen`. §11 currently
reads as though the case is covered. Either narrow the claim, or accept that
"extension module" has two shapes on mobile and only one is out of scope.

## P9 — Usage descriptions are a `requires`, not a `contributes`

**Problem, and it is a design bug in the current text.** CoreLocation requires
`NSLocationWhenInUseUsageDescription`, and version 1's only mechanism is
`[ios.contributes.info_plist.values]` — so the **producer writes the string**. A
purpose string is user-facing, localized, read by App Store review, and is a
claim about what the *application* does with the data. A framework binding
cannot know it.

§7.6's own example instructs producers to do this:

```toml
[ios.contributes.info_plist.values]
NSBluetoothAlwaysUsageDescription = "Connects to your fitness tracker."
```

A library cannot know the application connects to a fitness tracker.

**Proposal.** The same authority model as §6.7 and §7.3 — producer states the
need, application supplies the substance:

```toml
[[ios.requires.usage_descriptions]]
key = "NSLocationWhenInUseUsageDescription"
reason = "requestWhenInUseAuthorization() traps if this key is absent"
```

Reported as a prerequisite, never written. A consumer **SHOULD** reject any
`info_plist.values` key ending in `UsageDescription` once this exists.

**A second problem it disposes of for free.**
`NSLocationTemporaryUsageDescriptionDictionary` — needed by
`requestTemporaryFullAccuracyAuthorization(purposeKey:)`, which PyCoreLocation
exposes — is **dictionary-valued**, and §7.6 excludes dictionaries. As a
`requires` it never has to be spelled, so the exclusion stops mattering. That is
two of the four dictionary cases found so far removed by narrowing rather than
by adding dictionary support (the other is P4's generated `NSExtension`).

## P10 — Govern the transitive Swift graph

**Problem.** §7.4 forbids a `branch` requirement and demands exact/from/revision
— but those rules govern **the sidecar's declaration only**. Once the consumer
resolves a declared package, that package's own `Package.swift` may contain
anything.

PyCoreLocation proves this is not hypothetical. Its manifest declares

```swift
.package(path: "/Volumes/CodeSSD/PythonSwiftGithub/PyFileGenerator")
```

— a local filesystem path on one developer's machine — and its
`Package.resolved` pins `PySwiftAST` to `"branch": "master"`.

Compare §6.5, which is explicit that the recorded Gradle graph covers "every
artifact and version, **including transitives**." §7.4 says only "the version
actually resolved," singular. The Android side of the specification closed this
hole; the iOS side left it open.

**Proposal.** Mirror §6.5: record the full resolved Swift graph including
transitives, and state what happens when that graph contains a branch or path
dependency. Rejection is the likely answer — `Package.resolved` pins a revision,
so a branch dependency is reproducible after first resolution but its recorded
revision has no stable meaning, and a path dependency does not resolve on
another machine at all.

## P11 — Declaring an unsupported platform

**Problem.** PyCoreLocation is iOS-only. Its sidecar declares `[ios]` and
nothing else, which §5 blesses: *"A sidecar declaring no platform table is valid
and contributes nothing."* But **"I contribute nothing on Android" and "I do not
work on Android" are the same declaration**, and they are very different facts.

An application depending on PyCoreLocation and building for Android gets a
successful build and an app that fails at `import` — or, because the wheel is
pure-Python and untagged, silently ships the typing stub and returns `None` from
every call. That is the failure mode §4.4 exists to prevent, arriving through a
door §4.4 does not watch.

**Proposal.**

```toml
platforms = ["ios"]      # top level; consumer fails when building for another
```

**Counter-argument, worth stating in the text.** This is partly packaging's job
— environment markers, platform-tagged wheels. But the wheel here is pure-Python
and installs everywhere, the application author lists the dependency by name,
and the consumer is already reading the sidecar at exactly the moment the
question can be answered. One line converts a runtime mystery into a build-time
diagnostic naming the distribution.

## P12 — §12 covers facades, not framework bindings

**Problem.** §12 tells producers to split feature-conditional native surface
into optional distributions, with Plyer as the model. That works for a facade
dispatching to independent implementations. It does not work for a **1:1
framework binding**.

PyCoreLocation's requirements vary by API — `requestAlwaysAuthorization`,
`allowsBackgroundLocationUpdates`, `requestTemporaryFullAccuracyAuthorization`
and `startMonitoringLocationPushes` each pull in something different — but the
API surface is Apple's, it is one Swift module and one `@PyModule`, and there is
no seam along which `pycorelocation-background` could be carved without
splitting the class. The union-of-permissions problem §12 warns about is
unavoidable for this shape, and §6.7's suppression is **Android-only**, with no
iOS equivalent for Info.plist keys or entitlements.

**Proposal, two parts.**

1. §12 acknowledges the limit of its own guidance and says what a binding should
   do instead.
2. Introduce a **conditional prerequisite** — a declaration the consumer reports
   but cannot verify:

```toml
[[ios.requires.usage_descriptions]]
key = "NSLocationAlwaysAndWhenInUseUsageDescription"
reason = "Required only if your application calls requestAlwaysAuthorization()"
conditional = true      # reported as guidance; does not fail the build
```

Unconditional prerequisites fail closed as today; conditional ones are pure
disclosure, which §9 already treats as a legitimate mode. This is the smallest
thing that lets a binding tell the truth about a requirement it cannot know the
application will trigger.

**Risk to weigh.** `conditional = true` is an escape hatch, and escape hatches
get overused. If it lands, the rationale should say plainly that a producer
marking an unconditional requirement conditional has converted a build error
into a paragraph nobody reads.

## P13 — Self-declared Swift packages

**Problem.** `[[ios.contributes.swift_packages]]` was written for third-party
SDKs. PyCoreLocation points it at its own repository, which version 1 permits
without comment. Two consequences:

- **§9's per-file hashing covers nothing.** The record hashes "`native.toml` and
  every resource it references." Here the sidecar references no resources — the
  implementation is a git URL — so what §9 calls "the useful identity for *this*
  protocol" identifies a typing stub.
- **Wheel and tag can drift.** Nothing requires the declared version to
  correspond to the distribution's own. `py_core_location 0.4.0` may declare
  `{ exact = "0.1.0" }` of its own package and no rule notices.

**Proposal.** Self-declaration is legitimate and the specification should say
so, with a note that §9's file-hash coverage does not extend to it. Related to
P10, which governs what the declared package then drags in.

**Amended by PyWebViews — drop the version-correspondence SHOULD.** This
originally proposed a **SHOULD** that a self-declared package pin the
distribution's own version. That is unimplementable here. PyWebViews' git tags
are `311.0.0` … `311.1.3`, because in this ecosystem a Swift package's **major
version encodes the CPython ABI** it targets (311 = CPython 3.11; PyCoreLocation
depends on PySwiftKit `313.x`). The wheel version tracks features; the tag
tracks the interpreter. They cannot be made to agree.

Worse for the original PyCoreLocation reading: that repository has **no git tags
at all**, so it cannot be declared by version in any form — `revision` is the
only §7.4-legal option, and the distribution's version then appears nowhere in
the declaration. The sidecar in `examples/pycorelocation/` has been corrected to
pin a commit.

What survives is narrower and still worth saying: a self-declared package
**MUST** be resolvable by the form declared (a tagless repository cannot use
`exact` or `from`), and the record **MUST** make clear that the distribution's
version does not pin the native half.

## P14 — Unsatisfiable native resolution

**Problem.** PyWebViews depends on PySwiftKit `311.x`; PyCoreLocation depends on
PySwiftKit `313.x`. An application depending on both **cannot resolve** — and
that is correct, since the two target different interpreters. The problem is the
diagnostic: SwiftPM emits a resolver error about `PySwiftKit`, and nothing
connects it back to `py_web_views` and `py_core_location`.

Requirement 8.15 — *"Name the contributing distribution in every diagnostic"* —
cannot be met, because the diagnostic is not the consumer's to write.

**The specification never covers this case at all.** §6.5 and §7.4 lock
resolution and §9 records it, but every rule assumes resolution *succeeds*. Two
producers declaring incompatible Gradle coordinates is the identical situation
on Android, and the text is equally silent.

**Proposal.** On native resolution failure, a consumer **MUST** report the full
set of declared coordinates and Swift packages **with their declaring
distributions**. That mapping is the one thing the consumer knows and the
underlying resolver does not. This is a small obligation with a large payoff:
without it, the most confusing failure mode in the whole system — two transitive
Python dependencies that cannot coexist natively — surfaces as a native
toolchain error with no Python-side trail.

**Related mitigation worth stating in the text.** This particular conflict is
already expressible one layer down, as `requires-python` in the wheel: a closure
correctly resolved for CPython 3.13 would never contain a 3.11-only
distribution. The specification should say plainly that the **closure's Python
version governs** and the sidecar does not restate it.

## P15 — The Python distribution is the carrier

**Problem.** PyWebViews has no `pyproject.toml`, no wheel, no `dist-info`. It is
a SwiftPM package whose only `.py` file lives under `Sources/` as Swiftonize
code-generation input. §3.2 discovers producers through `importlib.metadata`
over the resolved dependency closure — there is nothing here to find. The
package cannot participate in any form, and not because a key is missing.

**Proposal.** State it. §3 should say that the Python distribution is the
carrier, that a native-only project must ship a distribution (however thin) to
participate, and that the sidecar cannot reach a package the closure does not
contain.

This is a legitimate boundary, not a gap to close — but it is currently a silent
assumption, and it imposes a real packaging obligation on projects that have no
other reason to produce a wheel. Two of the four examples are Swift packages
first and Python packages second; one of them has not built the Python half at
all.

## P16 — Do not add dictionary Info.plist support

§7.6 says typed contributions for dictionary-valued keys "may be added in a
minor revision." On the evidence of all three iOS examples, they should not be.
Every dictionary case found dissolved under a **narrower** primitive:

| Example | Key | Resolved by |
| --- | --- | --- |
| PyOneSignal | `NSExtension` | consumer generates it from `kind` (P4) |
| PyCoreLocation | `NSLocationTemporaryUsageDescriptionDictionary` | a `requires` the application supplies (P9) |
| PyWebViews | `NSAppTransportSecurity` | not the producer's at all — depends on what the app loads |

Three for three. The general form would hand producers the ability to write
arbitrary structured application configuration, for cases that keep turning out
to be better modelled as something else. **Proposal:** replace §7.6's "may be
added" with a statement that dictionary contributions are excluded by design,
and that structured cases are expected to be met by typed primitives or by
`requires`.

## P17 — Narrow §7.5, and say what §7.1 does not cover

**Evidence.** `WebViews.swift` declares at file scope: `retinaScale`,
`screen_size`, `ui_scale`, `invertedHeight(_:)`, `protocol WKBase`, and
`extension Double { var retinaScaled }`. Staged into the application target via
§7.5, `ui_scale` and `invertedHeight` are prime collision candidates and the
`Double` extension is visible to everything the target compiles — including the
application's own code.

**Two conclusions, pointing away from the current text.**

- **§7.1's guidance is narrower than the problem.** It asks producers to prefix
  "contributed type names, and in particular `@objc` runtime names." Nothing in
  that reaches file-scope functions, global constants, or extension members —
  precisely what collides here. §7.1 should say what it does **not** cover.
- **§7.1's deferred hardening already exists, and it is §7.4.** The text defers
  per-producer Swift modules to §10 as future work. A SwiftPM package *is* a
  separate module, so any producer following §7.4's own
  RECOMMENDED-for-anything-larger advice has the hardening today. The move is
  not to build module separation for §7.5 — it is to ask whether §7.5 should
  exist beyond a genuinely small shim, and to make the discouragement concrete
  by naming this failure mode.

Both PyCoreLocation and PyWebViews reached for §7.4 over §7.5 unprompted. The
specification's own recommendation is being confirmed by practice.

## P18 — Define namespace containment

**Problem — a specification defect, and the cheapest fix in the set.** Three
rules perform a containment test, and none says whether containment is computed
on **strings** or on **dot-separated segments**:

- §6.1 rule 5: *"Two distributions claiming **overlapping** namespaces MUST fail."*
- §6.1 rule 4: *"An owned namespace under a **reserved prefix** MUST be rejected."*
- §6.9 scope 2: a keep pattern must fall within *"the **group** of a Gradle coordinate."*

PyGMA makes it concrete by owning the single-label namespace `PyGMA`:

| Naive string prefix | Correct segment containment |
| --- | --- |
| `PyGMA` "contains" `PyGMAKit` | siblings — unrelated packages |
| `org.kivy.android` "contains" `org.kivy.androidx` | siblings — reserved-prefix false positive |
| group `com.google.android.libraries.ads` "contains" `…adsx` | siblings — keep pattern wrongly accepted |

A string-prefix implementation produces false collisions that block legitimate
distributions, and in the §6.9 case a false *acceptance* that widens a keep
scope. Two conforming implementations would disagree.

**Proposal.** One sentence: namespace *A* contains *B* when *B* equals *A* or
begins with *A* followed by a dot. Apply it to rule 4, rule 5, and §6.9's group
check alike.

## P19 — Sharpen §6.3 to build-time values

**Problem.** §6.3 illustrates application-supplied values with the AdMob
`APPLICATION_ID` manifest entry — the legacy Mobile Ads SDK's mechanism. The
package that actually wraps that SDK family needs nothing of the kind (G1), and
no example in the set needs the standalone form.

**Proposal.** Keep §6.3, narrow its stated purpose, and replace the example.

§6.3 is for values the **build** must embed: manifest placeholders, intent
filter data, anything baked into generated XML that no runtime call can supply.
Values an SDK accepts at runtime belong in the application's own Python code,
and a producer should not route them through build configuration merely because
it can. §6.8's `view_links` redirect scheme is the honest example — a value that
genuinely cannot arrive any other way — and it is already in the text.

This makes §6.3 smaller and better justified, and it removes an example that now
teaches the wrong lesson.

## P20 — Reconsider §9's effective-delta SHOULD

**Problem.** PyGMA's sidecar declares `INTERNET` and `ACCESS_NETWORK_STATE`. The
GMA AAR merges in **`com.google.android.gms.permission.AD_ID`** — the Android
13+ advertising ID permission, which carries Play Console **Data Safety**
declaration obligations. It is declared by no sidecar and arrives through AGP
manifest merging from a resolved coordinate.

§9 covers exactly this, as a **SHOULD**:

> A consumer **SHOULD** include in the record and report the permissions and
> components the effective merged manifest contains beyond those declared by
> sidecars and the application…

So the most consequential contribution in this integration — a privacy-relevant
permission reaching the application through a transitive Python dependency, with
regulatory paperwork attached — is the one thing a conforming consumer may omit.

Meanwhile §9's own framing says the motivating case is *"a transitive dependency
the application author has never heard of."* That is this, precisely, and the
coverage for it is optional.

**Proposal.** The argument for SHOULD is implementation cost — computing the
effective merged manifest means running or emulating AGP's merger, which is
real. So this is not a straightforward promotion to MUST. At minimum, §9 should
state plainly that a consumer omitting effective-delta reporting **has not
covered the case §9 exists for**, in stronger terms than the present "the
record's coverage is the declarations, not the full effective manifest."

Worth deciding deliberately rather than inheriting.

---

## Sequencing

**Land now** — corrections and statements of existing intent, not new
capability. Each is the specification either disagreeing with itself, instructing
producers to do the wrong thing, or leaving a load-bearing assumption unsaid:

- **P5** (§6.5 forbids what §7.4 permits)
- **P9** (§7.6's example has libraries writing App Store review text)
- **P10** (§7.4 leaves ungoverned what §6.5 governs)
- **P14** (no rule covers native resolution *failing*, and 8.15 is unmeetable there)
- **P15** (the carrier assumption is silent)
- **P16** (close a door §7.6 currently leaves open)
- **P17** (§7.1 overstates its reach; §7.4 already provides the deferred fix)
- **P18** (three containment rules with undefined semantics — the cheapest fix here)
- **P19** (§6.3's example now teaches the wrong lesson)
- the §6.3 satisfaction correction recorded under **P2**, plus **P6**, **P7**, **P13**

**Land as cheap additions**: **P11**.

**Decide deliberately**: **P20** — a SHOULD that covers the case §9 says matters
most. Not a straightforward promotion to MUST; the implementation cost is real.

**Hold**: **P1**, **P4**, **P8**, **P12**, **P3**.

**Withdrawn**: **P2**.

Status after all four examples:

- **P8** is ready in shape. Two independent examples, four distinct names for
  one component confirming the name/package split, no unresolved questions. Held
  only because it is new capability.
- **P4** has two independent examples and a settled `kind` vocabulary
  (`notification_service`, `location_push`).
- **P12**'s `conditional` flag has two examples (PyCoreLocation's authorization
  variants, PyWebViews' ATS and `getUserMedia` keys). Likely, not certain.
- **P1 is the weakest remaining proposal.** It still rests on PyOneSignal alone.
  Neither Swift package needs a launch hook — they register callbacks from
  Python at runtime — and PyGMA initializes from Python by SDK design. The fixed
  signature is the least-tested decision in this file, and P1's `values` map lost
  its second justification when P2 was withdrawn.
- **P3**'s `meta_data` half is unexercised by any of the four. It rests on the
  fact that ksp-builder already has the key, not on a demonstrated need.

The example set is exhausted. The next thing that would move these is either a
consumer implementation of the "land now" group, or a producer outside this
organization — every example here shares one toolchain lineage, and P1/P3 are
precisely the proposals that lineage does not test.
