# PyOneSignal against contract 1

Source material:

- [PyPlatformPackages/PyOneSignal](https://github.com/PyPlatformPackages/PyOneSignal)
  — the package as it exists (Android only, pyjnius).
- [PyPlatformPackages/IntegrationGuides](https://github.com/PyPlatformPackages/IntegrationGuides)
  `xcode/one_signal/README.md` — a working iOS integration, in PSProject form.
- OneSignal's own Android and iOS setup documentation.

`native.toml` beside this file is valid under contract 1 and is what the spec can
express today. This file records what it maps cleanly, what it cannot express,
and what the package must give up to fit.

## What version 1 expresses well

| Requirement | Mechanism | Notes |
| --- | --- | --- |
| `com.onesignal:OneSignal` | §6.5 `gradle_dependencies` | but see A1 |
| `INTERNET`, `POST_NOTIFICATIONS` | §6.7 `permissions` | canonical names, `reason` carried into the record |
| min API 23, compile 34 | §6.2 floors | exact fit |
| Reflective JNI reach into `com.onesignal.**` | §6.9 `r8.keep_classes` | scope 2 (group of a declared coordinate) is exactly this case |
| OneSignal-XCFramework | §7.4 `swift_packages` | `upToNextMajor = "5.4.1"` → `{ from = "5.4.1" }`, resolved version pinned by §9 |
| `aps-environment`, app groups | §7.3 `requires.entitlements` | reported, never written — correct; but see B3 |
| `UIBackgroundModes` | §7.6 `info_plist.append` | array-valued, merges with the application's |
| OneSignal's own AAR manifest (FCM service, receivers) | §9 effective delta | arrives through Gradle, surfaced not declared |

Nothing above needed a workaround. The dependency-and-permission surface is the
part v1 was designed for, and it holds.

## What version 1 cannot express

### A2 — the Android `Application` subclass *(blocking)*

`src/java/com/kivyschool/android/PyOneSignal.java` is the entire Java half of the
package, and it is an `android.app.Application` subclass. OneSignal's
documentation requires it: *"Initialize OneSignal in the `onCreate` method of
your `Application`"*, registered as `android:name` on `<application>`.

§6.8 `kind` is `service | activity | receiver | provider`. There is no way to
declare this, and adding a fifth `kind` would be wrong: `<application
android:name>` is a **singleton slot**, not a repeatable component. It belongs to
neither category cleanly — it is not `contributes` (two producers cannot both
have it) and it is not `owns` (a producer claiming it locks every other producer
out of initialization, which is strictly worse than today's world where the app
author writes one `Application` class that calls both SDKs).

What the case actually needs is a **startup hook**: *call this static method from
whatever `Application.onCreate` you generate*. That is data — a class name and a
method name — not executable build logic, so it stays inside §2.1. It composes
n-ways, which the singleton slot does not.

### B1 — the iOS Notification Service Extension *(blocking, largest gap)*

The working iOS integration declares a second build target:

```toml
[tool.psproject.extra_targets.OneSignalNotificationServiceExtension]
type = "app_extension"
dependencies = [{ package = { products = ["OneSignalExtension"], reference = "OneSignal" } }]
[tool.psproject.extra_targets.OneSignalNotificationServiceExtension.entitlements]
"com.apple.security.application-groups" = ["group.org.pyswift.your_project.onesignal"]
[tool.psproject.extra_targets.OneSignalNotificationServiceExtension.info_plist.NSExtension]
NSExtensionPointIdentifier = "com.apple.usernotifications.service"
NSExtensionPrincipalClass = "OneSignalNotificationServiceExtension"
```

plus a `NotificationService.swift` implementing `UNNotificationServiceExtension`.

Version 1 has no notion of a target other than the app. Every part of this is
unexpressible: the target itself, its Swift source, its own entitlements, its own
deployment target, its bundle identifier (derived from the app's), the
`NSExtension` **dictionary** in its Info.plist (§7.6 excludes dictionary values),
and its distinct SwiftPM product linkage — §7.4's `products` list has no target
dimension (**B2**), so `OneSignalFramework` and `OneSignalExtension` cannot be
routed to different places.

This is not optional polish. Without the extension OneSignal loses confirmed
delivery, badge counts, and image attachments.

### B5 — launch-time initialization on iOS

`OneSignal.initialize(appId, withLaunchOptions:)` must run in `main.swift`
before `SDLmain()`. Nothing in v1 lets a producer declare that. Same shape as
A2, same proposed remedy: a declared symbol the consumer's generated launch code
calls.

Between A2 and B5, **v1 can express what PyOneSignal depends on but not how it
starts**, on either platform.

### A3 — Android resources

The Java reads a **string resource**:

```java
int resId = getResources().getIdentifier("onesignal_app_id", "string", getPackageName());
```

§6.3 defines an application value as satisfied by a manifest `<meta-data>` entry
— resources are not reachable. More broadly there is no way to contribute *any*
`res/` material, which notification SDKs routinely need (OneSignal's own default
status-bar icon is `res/drawable/ic_stat_onesignal_default`). Coupling §6.3
satisfaction specifically to `<meta-data>` also looks over-specific; the spec's
own `view_links` inline form does not go through meta-data.

### A4 — producer-contributed `<meta-data>`

§6.3 lets a producer *require* an application-supplied meta-data value. There is
no way to contribute a **fixed** one. OneSignal Android uses meta-data to name
its notification-extender class, and the existing ecosystem already has this key
— ksp-builder reads `[tool.kivy-school.android] meta_data` and merges it into the
manifest. A producer migrating to this spec loses a capability it has today.

### B6 / C1 — application values are Android-only

The OneSignal App ID is needed on both platforms. §6.3 lives under
`[android.requires]` and has no iOS counterpart, so the same logical requirement
either gets declared twice under two different mechanisms or goes undeclared on
iOS. This argues for a platform-neutral `[requires.application_values]` with
per-platform delivery, rather than a second copy under `[ios.requires]`.

### B3 — entitlement values and cross-target agreement

§7.3 is `key` + `reason`, deliberately: the consumer must not write entitlements.
That is right. But the app-group case carries two facts the schema cannot state
— a **value convention** (`group.<main-app-bundle-id>.onesignal`) and a
**cross-target equality** constraint (the app and the extension must use the
identical group). Both currently survive only as prose in `reason`. Acceptable
for v1 if we say so; it should not be discovered by a consumer implementer.

### A1 — the version range

OneSignal's documented coordinate is `com.onesignal:OneSignal:[5.6.1, 5.9.99]`,
and that is exactly what PyOneSignal ships. §6.5 rejects it as a dynamic version.

This one deserves a second look rather than a shrug. §6.5 *also* mandates a
locked resolved graph in §9 — which is the mechanism Gradle dependency locking
exists to provide, and it makes a range reproducible. Requiring both means the
producer must cut a wheel release for every SDK patch, for a guarantee the lock
already delivers. The defensible reason to keep the ban is auditability: an exact
coordinate tells a reviewer what they get from the sidecar alone, without
consulting the record. That is a real argument — but it is a trade, and the spec
currently presents it as self-evident. Either state the trade, or define a
bounded range form (`[low, high)`) whose resolution the record pins.

### A5 — namespace collision *(a finding, not a gap)*

PyOneSignal's Java is in `com.kivyschool.android` — a namespace every KivySchool
package would share. §6.1 rule 5 rejects the second claimant, which is correct:
two distributions writing into one package directory is last-writer-wins on
same-named files. The spec surfaces a latent ecosystem bug, which is a point in
its favor.

Adjacent: PyGMA's Java is in a bare top-level `PyGMA` namespace. That is ownable
under v1 and collision-checked, but a top-level Java package is a poor claim.
Worth a **SHOULD** for reverse-DNS namespaces.

### A6 — no `target_sdk` floor

`POST_NOTIFICATIONS` runtime behavior keys off `targetSdk`, not `compileSdk`.
Probably correct to omit — `targetSdk` is an application policy decision, not a
producer's — but the omission should be deliberate and stated.

## The workaround v1 forces

PyOneSignal *can* be shipped under contract 1 today: **delete the `Application`
subclass** and initialize from Python instead. The package already supports it —
`examples/main.py` calls `onesignal.initialize(APP_ID)` from `App.on_start`, and
the App ID then comes from Python rather than a resource, which also dissolves
A3. That is what the accompanying `native.toml` assumes, and it is why that file
declares no `[android.owns]` and no `[android.contributes.src]`: with the
`Application` class gone, the package contributes no Java at all.

The cost is not cosmetic. Initializing from `on_start` is late — a cold start
from a notification tap reaches the activity before the SDK exists, which is the
case OneSignal's Application-subclass requirement is written for.

So version 1 does not merely omit a convenience here. It changes the package's
runtime behavior, and it does so silently: nothing in the sidecar records that
the integration was reshaped to fit the schema.

## Verdict

Two of the three categories hold up. `requires` and the dependency half of
`contributes` express OneSignal cleanly and in some places better than the
status quo — the r8 scope rule, the entitlement-reporting rule, and the
namespace collision check each caught something real.

The gap is concentrated and describable: **v1 models what a package brings, not
where a package plugs in.** Initialization hooks (A2, B5), additional build
targets (B1), and producer-contributed manifest/resource entries (A3, A4) are all
the same missing idea in different clothes — a producer attaching itself to a
point in the generated project that the consumer owns.

Before changing SPEC.md, the other three cases are worth running:

- **PyCoreLocation** should stress §7.6 `values` and the permission/purpose-string
  path — likely a clean fit, and a useful control.
- **PyWebViews** should stress §7.5 source contribution and §7.1 symbol prefixes
  at real volume.
- **PyGMA** should stress §6.3 (the AdMob App ID is the spec's own example) and
  cross-platform symmetry.

If PyCoreLocation and PyGMA come out clean, the finding is specific rather than
structural, and the remedy is a small number of new primitives rather than a
different shape.
