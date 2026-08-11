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
> **P11 and P20 have since been decided and landed**, both with amended
> reasoning; see the notes on those sections. **P8 has been adopted** as §7.7.
> **P4 has been decided against for now** — its contribution form is deferred
> and a minimal `requires` form landed in its place.
>
> **P1, P3 and P12 have since been decided**, closing the list. P12 landed in
> full (§12.1 and §7.3's `conditional`). P3 split — the resources half landed
> as an §11 exclusion, the `meta_data` half is deferred. **P1 is deferred.**
>
> **Withdrawn:** P2. **Deferred:** P1, P3's `meta_data` half, P4's contribution
> form — each with a stated trigger for reopening it.
>
> **Reopened by Firebase, and decided.** The list was closed after four
> examples, all from one toolchain lineage. Three clean-sheet Firebase sidecars
> ([examples/firebase/](examples/firebase/)) produced **P21–P24**. Landed:
> **P21** (narrowed), **P22**, **P23**, and P24's documentation half.
> **Deferred:** P24's BOM form. P1's deferral was sharpened, not reversed.
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
| P21 | Application-supplied **files** | F3 | Firebase |
| P22 | Single-action intent filters on services | F5 | Firebase (FCM) |
| P23 | Name the build-script SDK class as permanently excluded | F4 | Firebase (Crashlytics) |
| P24 | Cross-artifact version alignment (BOM) | F2 | Firebase |
| P25 | iOS URL schemes — a `view_links` counterpart | T2, T3 | Stripe |
| P26 | Entitlements that carry values | T5, B3 | Stripe, PyOneSignal, PyCoreLocation |

Gap identifiers refer to the NOTES.md beside each example:
[PyOneSignal](examples/pyonesignal/NOTES.md) (A*, B*, C*),
[PyCoreLocation](examples/pycorelocation/NOTES.md) (L*),
[PyWebViews](examples/pywebviews/NOTES.md) (W*),
[PyGMA](examples/pygma/NOTES.md) (G*),
[Firebase](examples/firebase/NOTES.md) (F*),
[Sentry](examples/pysentry/NOTES.md) (S*),
[Stripe](examples/pystripe/NOTES.md) (T*).

P6 and P11 each gained a second example from PyGMA (G2, G4).

---

## P1 — Startup hooks *(DECIDED: deferred)*

> **Decision.** Deferred, on the standard applied to P4, plus a design problem
> that only became visible after P2 was withdrawn.
>
> **The evidence is one instance, and half of it evaporates on inspection.**
> PyOneSignal genuinely ships an `Application` subclass, so the Android side is
> a real producer-side artifact — unlike P4, this is not zero. But the iOS side
> is not: `OneSignal.initialize(_:withLaunchOptions:)` lives in
> `YourProject/project_dist/xcode/Sources/IphoneOS/main.swift`, which is the
> **application's** file in the only working integration available. The other
> three packages need no launch hook at all — the two Swift packages register
> callbacks from Python at runtime, and PyGMA initializes from Python by SDK
> design.
>
> **Withdrawing P2 broke the design.** The proposed signature carried a
> `values` map, which was how an application-supplied value reached producer
> code without coupling it to a consumer. P2 was withdrawn because application
> values have zero live uses — so the map goes too. But then PyOneSignal's hook
> cannot obtain the OneSignal App ID: not from a resource (§11 now excludes
> them), not from an application value (withdrawn), and if it comes from Python
> then initialization can happen from Python and the hook is unnecessary.
> **P1 does not close its own motivating case.** That is a design that has not
> converged, not one waiting on nerve.
>
> **The capability is the largest here.** Contributed Java and Swift already run
> in the application, and a registered `service` or `receiver` already gets code
> running — but those run when the OS routes an event to them. A startup hook
> runs unconditionally, first, ahead of the application's own code, in every
> application that transitively depends on the package. It is the closest thing
> in this specification to "run my code," and it should not arrive on one
> instance and an unresolved value channel.
>
> **No minimal form is offered**, deliberately. P4's `requires` form works
> because an application can act on it — build an extension. There is no
> comparable action here: "initialize me early" is a constraint on the
> consumer's generated bootstrap, not a task an application performs.
>
> **Reopen when** a producer needs native initialization *and* has a channel for
> the values that initialization needs. The two questions are one question.

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

## P2 — Platform-neutral application values *(WITHDRAWN — reasoning replaced after Sentry)*

> **Revisited after S1, and the withdrawal stands on a different footing.**
>
> The original ground — quoted below — was that `application_values` had **zero
> live use cases**. **That is now false.** Sentry Android is configured through
> `io.sentry.dsn`, a manifest `<meta-data>` entry read by a `ContentProvider` in
> its own library before `Application.onCreate` and long before Python. Nothing
> at runtime can supply a value the SDK has already consumed. §6.3 as narrowed
> by P19 describes that requirement exactly, and §6.3's example is now Sentry's
> rather than a superseded AdMob mechanism.
>
> So the premise is gone. The proposal still does not come back, for a reason
> that is about the design rather than the evidence, and which should have been
> visible at the time:
>
> **A platform-neutral logical name cannot carry the delivery key.** `name` in
> this table is the **vendor's own platform-specific manifest key**, and that is
> the only thing that makes delivery possible — the consumer writes
> `<meta-data android:name="io.sentry.dsn" …/>`. A consumer handed a logical
> `sentry_dsn` has no way to learn what Android calls it; that is producer
> knowledge about one SDK on one platform. A neutral table would need
> per-platform key mappings inside it, which is two tables with extra steps.
>
> **What the iOS gap actually is.** Sentry's DSN *is* needed on iOS, where
> `SentrySDK.start` is a runtime call — so the missing piece there is not this
> table promoted upward. It is either initialization from Python (which works,
> and costs the crashes that happen before the interpreter starts) or the P1
> hook. A platform-neutral value table would not have closed it either way.
>
> The genuine iOS counterpart would be this same shape aimed at an `Info.plist`
> key an SDK reads at launch. No example has needed one: the iOS SDKs in the set
> take configuration at runtime or read a whole file (§7.3's
> `application_files`, from P21). Recorded as the shape to reach for if one
> appears — **not** as P2 revived.
>
> Original reasoning follows.

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

## P3 — No sidecar resources; add contributed `meta_data` *(DECIDED: split)*

> **Decision.** The two halves go opposite ways, which is why they should not
> have shared a proposal number.
>
> **Resources: landed**, as a row in §11's out-of-scope table. This half costs
> nothing — it is a decision *not* to add a primitive, and it forecloses a bad
> future addition. Its argument is structural rather than evidential: resource
> names are a flat global namespace per type, so §6.1's containment rule cannot
> reach them, and a producer shipping `values/strings.xml` with `app_name`
> renames the application. Resources arrive through an `.aar` from a declared
> coordinate, where AGP merges them and §9 now reports them.
>
> **`meta_data`: deferred.** Zero examples use it, and its stated justification
> — that ksp-builder already has the key, so migrating producers lose a
> capability — is weaker than it looked. The one documented use of that existing
> key is `com.google.android.gms.ads.APPLICATION_ID`, which P19 established is
> the **legacy** Mobile Ads mechanism; PyGMA wraps the Next-Gen SDK and needs
> nothing of the kind. A capability whose only cited use has been superseded by
> its own ecosystem is not a migration loss worth pre-empting.
>
> **Reopen when** a producer needs a fixed manifest `<meta-data>` entry that is
> not an application value in disguise — OneSignal Android's
> notification-extender class registration is the plausible shape, if a package
> ever implements it.

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

## P4 — iOS app extensions *(DECIDED: contribution form deferred; `requires` form landed)*

> **Decision.** The contribution form does not land. A minimal
> `[[ios.requires.app_extensions]]` did, in §7.3, with a closed `kind`
> vocabulary of `notification_service` and `location_push`.
>
> **The evidence for this proposal was miscounted, and the error was mine.**
> It was recorded above as having "two independent examples," which promoted it
> from hypothesis to finding. Checking the repositories directly:
>
> - **No package in the set ships an app extension of any kind.**
> - PyOneSignal's notification service extension is **application-authored** in
>   the only working integration that exists — the target is configured in
>   `YourProject/pyproject.toml` and `NotificationService.swift` lives in
>   `YourProject/project_dist/xcode/`, both the application's, not the
>   package's.
> - PyCoreLocation merely *exposes* `startMonitoringLocationPushes` in its
>   binding. It ships no extension, and the one an application would need has an
>   app-specific principal class and an entitlement Apple must approve.
>
> So the count of producer-side instances is zero. What the two examples
> actually demonstrate is that **applications** build these, which is an
> argument for stating the requirement, not for contributing the target.
>
> **The size of the capability argues the same way.** An app extension is a
> separate signed executable with its own bundle identifier and entitlements,
> launched by the OS when the application may not be running. That is a larger
> thing for a transitive Python dependency to introduce than anything else here,
> and it should not land on zero instances.
>
> The design below is not withdrawn and the argument for it remains good —
> identical boilerplate written once per application is exactly what a package
> should own. It needs a producer that wants to own it. The `requires` form
> meanwhile converts a silent capability loss into a reported prerequisite,
> which is the part today's evidence supports.

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

## P8 — Python module registration *(DECIDED: adopted, §7.7)*

> **Decision.** Adopted essentially as drafted, with three additions the draft
> did not have.
>
> **A payload-exclusion rule**, which turned out to matter more than the
> registration itself. Producers ship a same-named stub for off-device type
> checking — PyCoreLocation's says "do not try add this file to a real app" —
> and inittab registration normally shadows it. But if registration fails or is
> skipped, the stub is still on `sys.path`, so the failure surfaces as an
> application that imports successfully and returns `None` from every call
> rather than as `ImportError`. §7.7 requires consumers to exclude every
> registered name from the payload, on the same reasoning as 8.14.
>
> **A duplicate-name check.** Module names are a global namespace in the
> interpreter; two distributions registering one fails, naming both. This is not
> an `owns` claim — the Python module namespace is packaging's, not this
> specification's — but the collision is real and worth catching.
>
> **A §11 narrowing**, which the proposal called for and which is now written:
> §11 excludes extension modules **carried as binaries in wheels**, which the
> platform-tagged wheel PEPs solve and ordinary imports load. Source arriving
> through a declared Swift package and compiled into the application target is a
> different shape, and is in scope.
>
> Kept iOS-only. The shape occurs there; on Android §11's answer holds, and an
> Android form with no examples would be speculative.

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

## P11 — Declaring an unsupported platform *(DECIDED: adopted, §4.5)*

> **Decision.** Adopted. The counter-argument below — that this is packaging's
> job — turned out to be weaker than it reads, and the reason is worth
> recording, because the specification had just committed to the opposite
> principle in §3.5: *a sidecar MUST NOT restate an interpreter requirement.*
> Adding a platform key looked like an immediate contradiction of it.
>
> It is not, because the two cases are not symmetric. `Requires-Python` carries
> the interpreter constraint **enforceably**; nothing carries platform support
> enforceably for a distribution whose own content is pure Python. Wheel
> platform tags require platform-specific content — a pure-Python distribution
> would have to fabricate one to use them. Environment markers live on the
> *depending* project's requirement, so they are the application author's to
> write, and the application author is precisely the person who does not know.
> `Classifier: Operating System :: Android` exists, and both PyOneSignal and
> PyGMA set it, but it is informational and enforced by nothing.
>
> So the mechanism that ought to carry this does not exist, and §4.5 says so
> explicitly, along with a **SHOULD** to deprecate the key if one ever arrives.
>
> One refinement came out of PyGMA. The key claims the distribution *functions*
> on a platform, which is a stronger statement than "contributes native
> material" — a package that works fine on iOS and simply needs nothing there
> must not use it. PyGMA still should: a package whose entire purpose is ads,
> whose iOS branch is a bare `pass`, is not working there.

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

## P12 — §12 covers facades, not framework bindings *(DECIDED: adopted in full)*

> **Decision.** Both halves landed: §12.1 states the limit of §12's guidance,
> and §7.3 gained `conditional = true` on all three prerequisite tables.
>
> **The `conditional` flag stopped being speculative when P9 landed.** With
> usage descriptions now a `requires` that fails closed, a framework binding was
> left with two bad options: declare the union, and every application writes an
> "Always" location purpose string that App Store review scrutinizes whether or
> not it ever requests Always; or declare the minimum, and the caller of
> anything else meets a runtime trap with no build-time warning. PyCoreLocation's
> sidecar took the second, with a comment admitting it. The flag is less a new
> capability than the completion of one already adopted.
>
> Two independent examples, and they differ usefully: PyCoreLocation's
> conditions are *which methods the application calls*, PyWebViews' are *what
> content the application loads*. Both are facts the producer cannot know and
> the application can.
>
> **The abuse risk from the original proposal is real and is addressed in the
> text rather than by mechanism.** A producer can mark an unconditional
> requirement conditional and convert a build failure into a line in a report.
> §12.1 says so plainly, and §7.3 requires the `reason` to state the triggering
> condition and requires the consumer to record the unresolved prerequisite in
> §9 — durable and diffable — rather than emitting a build-log line that scrolls
> past. That is the same enforcement `reason` itself has: none, and disclosed.

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

## P20 — Reconsider §9's effective-delta SHOULD *(DECIDED: promoted in part, §9)*

> **Decision.** The Android half is now a **MUST**, scoped to what resolved
> artifacts declare in their own manifests. Merged-manifest fidelity and the
> iOS binary-target case stay **SHOULD**.
>
> Two things changed the answer from the hedge written below.
>
> **§11 already depends on this being reliable.** A prebuilt `.aar` embedded in
> a wheel is excluded there because its manifest merges "with no attribution,"
> while a coordinate-resolved `.aar` is permitted because it is "surfaced by
> §9's effective-delta reporting." Both merge identical manifests into the
> application. If the surfacing is optional, the two cases differ only by
> whether the consumer bothered — so §11's exclusion was resting on a SHOULD.
>
> **The cost objection was overstated, and it was mine.** "Running or emulating
> AGP's merger" is the cost of reproducing the *merged* result. It is not the
> cost of answering the question that matters: reading `AndroidManifest.xml`
> out of each resolved `.aar` is unzip-and-parse over a graph §6.5 already
> requires the consumer to record, and it catches the motivating case —
> `com.google.android.gms.permission.AD_ID` is declared in the ads AAR's own
> manifest. A consumer that drives Gradle can instead read AGP's merged
> manifest and blame report, which supply the attribution directly.
>
> Splitting the requirement along that line is what makes the MUST affordable:
> the hard part is merge *semantics* (`tools:node`, placeholders, ordering),
> and nothing about the motivating case needs them.

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

## P21 — Application-supplied files *(DECIDED: landed, narrowed to iOS bundle files)*

> **Decision.** Landed as `[[ios.requires.application_files]]` in §7.3 —
> disclosure only, consumer never creates or fetches the file. Two corrections
> to the reasoning below, both narrowing it.
>
> **Most of the gap dissolves.** Firebase accepts `FirebaseOptions`
> programmatically on both platforms, so a producer can initialize without any
> config file — which is exactly what the Android sidecar does, since the
> plugin path is excluded anyway. What survives is one hard case:
> **Analytics on Apple platforms** reads the static `GoogleService-Info.plist`
> and offers no programmatic alternative. That has no escape hatch, and an
> application that omits the file fails inside the SDK with nothing naming the
> distribution. §7.3 carries a **SHOULD NOT** against declaring a file when the
> vendor offers a programmatic path.
>
> **It does not reframe P1, and the claim below is withdrawn.** A file
> prerequisite is disclosure: the application puts the file in its bundle and
> the SDK reads it directly, so the producer's initialization code receives no
> values. P1's blocker is untouched.
>
> The durable finding is the one underneath that claim, and it is stronger:
> across six packages from two unrelated ecosystems, **application
> configuration reaches producers through Python, not through the build.** That
> is consistent with P2's withdrawal and P19's narrowing of §6.3, and it is why
> no platform-neutral value table exists.

**Problem.** Firebase needs `google-services.json` in the Android module root
and `GoogleService-Info.plist` in the iOS app bundle. §6.3's application values
are **scalars**; there is no file-shaped prerequisite anywhere. An application
that omits the plist crashes inside `FirebaseApp.configure()` with nothing
pointing back at the distribution that needed it.

**Proposal.** A prerequisite in the §7.3 mould — declared, reported, never
satisfied by the consumer, and platform-neutral because both platforms have the
same shape:

```toml
[[requires.application_files]]
name = "GoogleService-Info.plist"
location = "bundle"      # closed vocabulary: bundle | android_module_root
reason = "Download from the Firebase console; FirebaseApp.configure() reads it"
```

The consumer never supplies the file. It reports the requirement and fails when
the application has not provided one, exactly as for entitlements.

**This is the most important item on the list, because it reframes P1.** P1 was
deferred partly because withdrawing P2 removed the channel by which
application-supplied values reach producer code, with the reopening trigger:
*"a producer needs native initialization and has a channel for the values that
initialization needs."*

Firebase appears to trip that trigger — `FirebaseApp.configure()` takes no
arguments — and does not, which is the more useful result. The values did not
disappear; they moved into a **file** the specification also cannot describe.
OneSignal needed a scalar, Firebase needs a file, and both are the same missing
thing in different clothes. The initialization hook is downstream of it in both
cases.

So the deferral of P1 stands and is now better understood: **the blocker was
never the hook's signature.** It is that this specification has no vocabulary
for what the application must provide *to the producer*, beyond a scalar form
P19 narrowed nearly out of use. P21 is the prerequisite for reconsidering P1,
not merely adjacent to it.

## P22 — Single-action intent filters on services *(DECIDED: landed)*

> **Decision.** Landed in §6.8, scoped to components that are neither exported
> nor declaring `view_links`, with exactly one action and no categories or data.
>
> **The evidence is clean-sheet, and it lands anyway** — which needs
> justification given P4 was deferred on weaker-than-claimed evidence. The
> distinguishing test is whether the requirement has an escape hatch:
>
> - **P4** — the application can author the extension, and in the only working
>   integration it does. Deferred.
> - **P21** — most services accept programmatic configuration. Landed only for
>   the residue with no alternative.
> - **P22** — `FirebaseMessagingService` **must** be registered with that
>   intent filter. No programmatic registration, no swizzling, no app-authored
>   alternative: without it the service is never invoked, messages arrive, and
>   nothing runs. The question is not whether a producer would *want* this but
>   whether FCM works any other way, and it does not.
>
> The capability is also small: one vendor-defined action on a component no
> other application can reach. §6.8's export rules are untouched, so nothing
> externally reachable is opened. Compare P4's separate signed executable.

**Problem.** FCM's entire Android integration is a service registration with one
intent filter:

```xml
<service android:name="…MessagingService" android:exported="false">
  <intent-filter><action android:name="com.google.firebase.MESSAGING_EVENT"/></intent-filter>
</service>
```

§6.8 declares the component but not the filter. `view_links` is activity-only,
export-gated, and generates a fixed VIEW/DEFAULT/BROWSABLE shape. §6.8 already
lists "filters on non-activity components" as a v1 exclusion — FCM is the
canonical instance, and without the filter the service is never invoked:
messages arrive, nothing runs, and the build reported no problem.

**Proposal.**

```toml
[[android.contributes.components.intent_filters]]
action = "com.google.firebase.MESSAGING_EVENT"
```

**Why this is narrower than what §6.8 declined to model.** `view_links` exists
because the classic failure is a hand-written browser filter missing `DEFAULT`,
so the spec generates the filter and refuses to let producers spell one. This is
the opposite shape: a single vendor-defined action on a **non-exported** service,
with no categories and no data element — nothing to get subtly wrong, and no
externally reachable surface opened, since the export rules of §6.8 are
untouched.

Constrain it accordingly: one `action`, no categories, no data, and invalid on
any component that is exported or that declares `view_links`.

**Evidence.** One producer-side instance so far (FCM), but the pattern —
vendor-defined action on a non-exported service — is how most Android push,
work-scheduling and installer-referrer SDKs register. Worth a second instance
before landing, on the standard applied to P1 and P4.

## P23 — Name the build-script SDK class as permanently excluded *(DECIDED: landed)*

> **Decision.** Landed in §11. No new capability — §2.1's principle does not
> bend — but the category is now named, with Crashlytics as the canonical case
> and Sentry, Bugsnag, Instabug and Datadog as the shape. The text says plainly
> that such an SDK will link and build and then be useless, that the exclusion
> is permanent rather than deferred, and that the application must configure it
> outside this convention.
>
> This was the one proposal recommended without qualification, and it costs
> nothing.

**Problem.** Crashlytics cannot be integrated at all: the Android mapping-file
upload is a Gradle plugin, the iOS dSYM upload is a Run Script build phase with
five specific Input Files, and `DEBUG_INFORMATION_FORMAT = dwarf-with-dsym` is
an Xcode build setting. All three are §11 exclusions, two on principle.

The resulting sidecar links the SDK and delivers unsymbolicated crashes — the
part of Crashlytics nobody wants.

**This is a category, not a product.** Any SDK whose value depends on uploading
build artifacts — symbol files, mapping files, source maps — requires build-time
execution by construction. Sentry, Bugsnag, Instabug and Datadog share the
shape.

**Proposal.** No new capability; §2.1's principle should not bend for it. But
§11 should name the category explicitly rather than leaving it as an inference
from "scripts, hooks, build plugins." A producer in that class should learn from
the specification that this convention will never integrate it, instead of from
a sidecar that builds and under-delivers.

## P24 — Cross-artifact version alignment *(DECIDED: BOM form deferred; documentation landed)*

> **Decision.** Split. §6.5 now states that every version rule governs one
> dependency at a time, that a vendor BOM is a constraint over a *set* which
> neither form can express, and that producers publishing an SDK family
> **SHOULD** pin compatible versions deliberately and release together.
>
> The BOM form itself does not land. The failure mode is already honest —
> Gradle resolves one version per artifact, §6.5 locks it, and §8.16 requires a
> resolution conflict to name the declaring distributions — so the
> specification degrades correctly and merely cannot prevent the conflict. A
> BOM is also a genuinely new *kind* of declaration, the first that would
> constrain a set rather than an entry.
>
> **Reopen when** a producer demonstrates that the honest degradation bites in
> practice: an SDK family where independent pinning produces resolution
> conflicts that the per-distribution model cannot reasonably avoid.

**Problem.** Firebase documents a BOM: `platform("com.google.firebase:firebase-bom:34.17.0")`
followed by unversioned artifacts. §6.5 has no BOM form, so each sidecar pins
independently — and here the set spans three distributions, with nothing making
their choices agree.

**The bounded range landed in P5 solves the wrong half.** A range gives
*per-artifact* flexibility; a BOM gives *cross-artifact alignment*, asserting
that a set of versions was tested together. Nothing expressible per entry can
state a constraint over a set, and every version rule in the specification so
far governs one dependency at a time.

**Do not land yet.** The failure mode is already honest: Gradle resolves one
version per artifact, §6.5 locks the result, and §8.16 requires a resolution
conflict to name the declaring distributions. The specification degrades
correctly; it simply cannot express the constraint that would prevent the
conflict. A BOM form is also a genuinely new *kind* of declaration, and it
should wait for evidence that the honest degradation is not good enough in
practice.

## P25 — iOS URL schemes *(DECIDED: `requires` form landed; contribution form rejected)*

> **Decision.** `[[ios.requires.url_schemes]]` landed in §7.3, carrying
> `conditional` like the other prerequisites there. The `contributes` form
> proposed below **does not land, and is rejected rather than deferred** — the
> reasoning changed on inspection, twice.
>
> **The side-effect claim below is wrong.** It says a consumer-generated app
> delegate could forward URL callbacks to any producer declaring a scheme,
> "because the scheme *is* the registration." It is not. A scheme tells the
> consumer that a URL will arrive; it says nothing about **which producer symbol
> should receive it**. Generating `StripeAPI.handleURLCallback(with:)` requires
> naming a Swift symbol in the sidecar, which is precisely the startup-hook
> shape P1 proposes and §10 excludes. T3 is not closed as a side effect of
> anything.
>
> **And the Android parallel does not hold.** `view_links` is a *contribution*
> because an intent filter is attached to **the producer's own component** — the
> producer knows its shape, and an application could not sensibly write a filter
> for a class it does not own. iOS has no equivalent attachment:
> `CFBundleURLTypes` is bundle-level, bound to no class, and routing is decided
> at runtime in the application's delegate. The asymmetry is the platform's, not
> a hole in this specification.
>
> So a contribution form would register half of a two-part requirement and leave
> the application to do the other half — which is worse than reporting both,
> because it looks finished. The prerequisite form reports both.
>
> **P16 is untouched.** This was offered as the fourth dictionary case that
> "does not dissolve." It dissolves — into a prerequisite, not into dictionary
> support. P16's conclusion is now four-for-four.
>
> Original proposal follows.

## P25 — iOS URL schemes, a `view_links` counterpart

**Problem.** Stripe's 3D Secure return requires a custom URL scheme registered
in `CFBundleURLTypes` on iOS — the direct counterpart of the `view_links`
declaration §6.8 provides on Android, on the platform where Stripe's own
documentation says it is required. Nothing expresses it.

`CFBundleURLTypes` is an array of dictionaries, and P16 closed that door
deliberately: dictionary Info.plist support should never be added, because every
structured case found dissolved into a narrower primitive (three for three).

**This is the fourth case, and it does not dissolve** — or rather it dissolves
into a primitive the specification already has on the other platform and never
built here.

**Proposal.**

```toml
[[ios.contributes.url_schemes]]
scheme = { application_value = "stripe_return_scheme" }
reason = "Receives the 3D Secure redirect; StripeAPI.handleURLCallback consumes it"
```

The consumer generates the `CFBundleURLTypes` entry exactly as it generates the
Android intent filter, and dictionaries stay excluded. **P16's conclusion
survives** — no case yet wants *general* dictionary support — but its evidence
is now three-for-four, and the real defect is the asymmetry rather than the
dictionary question.

**It would also close T3 as a side effect.** Stripe requires
`StripeAPI.handleURLCallback(with:)` to be called from
`application(_:open:options:)` — lifecycle-callback participation, which nothing
in the specification addresses and which should not get a general mechanism (a
hook for one delegate method invites hooks for all of them, a larger capability
than the deferred P1). But a consumer-generated app delegate can forward URL
callbacks to any producer that declared a scheme, because the scheme *is* the
registration. The narrow primitive closes the broad problem.

**Evidence.** One vendor, clean-sheet. The mitigating argument is that this is
not a new capability but a missing half of one already adopted, tested, and
exercised — §6.8's `view_links`, validated by this same example.

## P26 — Entitlements that carry values

**Problem.** §7.3 entitlements are `key` + `reason`. Three unrelated vendors now
need to say more:

| Example | Entitlement | What cannot be said |
| --- | --- | --- |
| PyOneSignal | `com.apple.security.application-groups` | the value, and that it must match across two targets (B3) |
| PyCoreLocation | `com.apple.developer.location.push` | valueless, but needs Apple's approval |
| Stripe | `com.apple.developer.in-app-payments` | it carries merchant identifiers |

Each currently survives only as prose in `reason`.

**Constraint that must not be weakened.** §7.3's rule that a consumer **never
writes** an entitlement is correct and untouched by this — the values are the
application's, bound to its provisioning profile. What is missing is the ability
to state the *shape* the application's entitlement must take, so the consumer
can report a specific prerequisite rather than a sentence.

**Proposal, deliberately minimal.**

```toml
[[ios.requires.entitlements]]
key = "com.apple.security.application-groups"
value_kind = "string_array"     # closed vocabulary: none | string | string_array
shared_with_app = true          # cross-target agreement, from P4's draft
reason = "…"
```

**Evidence.** Three instances across three vendors, which is past the threshold
this file has been applying — but each wants something slightly different, and a
mechanism that covers all three risks being a schema language for entitlement
plists. Worth deciding deliberately rather than adopting the sketch above.

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

**Landed since, on their own decisions**: **P11** (adopted as §4.5) and **P20**
(Android half promoted to MUST, scoped to per-artifact manifests). Both entries
above record why the reasoning changed.

**Outstanding**: **P26**. **P25** has been decided — its `requires` form landed
in §7.3, its contribution form was rejected on the platform asymmetry, and its
claim to close T3 as a side effect turned out to be false.

P21–P24 have been decided: **P23** landed as documentation, **P22** landed in
full, **P21** landed narrowed to iOS bundle files, and **P24** split — its
guidance landed, its BOM form did not.

**Sentry and Stripe also moved three deferred items without reopening them**,
and the movement is recorded on each:

- **P1** (startup hooks) — Sentry is a **counter-example**, not evidence. It
  achieves pre-application initialisation with no producer code at all, using a
  `ContentProvider` in its AAR plus manifest meta-data. The vendor solved
  declaratively what P1 proposed a hook for (S2).
- **P2** (platform-neutral application values) — revisited and **still
  withdrawn**, on replaced reasoning. The "zero live uses" premise is false;
  Sentry's `io.sentry.dsn` is a live use, and §6.3's example is now Sentry's.
  But the proposal fails on design rather than evidence: a logical name cannot
  carry the vendor's platform-specific manifest key, which is the only thing
  that makes delivery possible. See P2's section.
- **P3**'s deferred `meta_data` half — Google Pay's
  `com.google.android.gms.wallet.api.enabled` is a fixed entry identical for
  every application, which is exactly the reopening trigger recorded for it
  (T4). First instance, and a better argument than the one it was deferred on.

**One landed decision was corrected.** §11's build-script exclusion said such an
SDK "will build. It will also be useless." True of Crashlytics, false of Sentry,
whose Gradle plugin is optional and whose configuration is declarative. §11 now
distinguishes SDKs that **degrade** from those that **fail** (S3) — a correction
in the direction of more being possible.

The suggested order recorded here before deciding put P21 first as "the pivotal
one, and the prerequisite for reconsidering P1." Both halves of that were wrong
and are corrected on P21's own section: the gap is narrower than it looked, and
a file prerequisite hands producer code no values, so P1 is untouched.

**Withdrawn**: **P2**. **Deferred**, each with a reopening trigger stated on its
section: **P1**, **P3**'s `meta_data` half, **P4**'s contribution form. P1's
trigger is now understood to depend on P21.

Status after all four examples and the decisions above:

- **P8** landed as §7.7, with a payload-exclusion rule the draft lacked.
- **P4** landed only as a `requires`. Its contribution form was recorded here as
  having two examples; it has **zero producer-side instances**, and the
  correction is written up under that proposal. This is the one place the
  hypothesis/finding distinction at the top of this file was applied wrongly,
  and it is worth remembering that the error ran toward *over*-counting a
  large capability.
- **P12** landed in full. Its `conditional` flag stopped being speculative once
  P9 made usage descriptions fail closed — it completes that change rather than
  extending it.
- **P1** is deferred, and not only for thin evidence: withdrawing P2 removed the
  value channel the hook's signature depended on, so it no longer closes its own
  motivating case.
- **P3** split. The half that removes a future primitive landed; the half that
  adds one did not.

**A pattern worth naming.** Of six capability additions proposed, two landed
(P8, P12), one landed in a reduced form (P4 as a `requires`), one was withdrawn
outright (P2), and two were deferred (P1, P3's `meta_data`). Every proposal that
survived contact had at least one producer-side artifact behind it. Every one
that did not had a plausible story instead — a guide showing an *application*
doing the thing, or a key an older tool happened to expose. The
hypothesis/finding rule at the top of this file was the right test; the failure
mode was applying it to the wrong noun, counting integrations rather than
producers.

**Firebase was the outside producer this file kept asking for**, and it behaved
like one. It did not challenge the shape — nothing wanted an executable hook in
a sidecar, nothing wanted out of owns/requires/contributes — and its two hardest
blockers are cases where the specification is **correctly refusing** rather than
failing. But it found one gap (P21) that the first four examples had only shown
in fragments, and it did so by approaching it from the opposite direction:
OneSignal needed a scalar the application supplies, Firebase needs a file. That
the same hole shows up from two unrelated vendors is the strongest single signal
in this file.

It also confirmed the value of the standard applied throughout: of the four new
proposals, only P23 is recommended without qualification, and it adds no
capability at all.
