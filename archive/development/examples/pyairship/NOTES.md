# Airship against the current spec

Clean-sheet, from [Airship's Android SDK setup](https://docs.airship.com/developer/sdk-integration/mobile/setup/sdk/android/)
and its Apple SDK equivalent. No `pyairship` distribution exists.

Chosen from [SURVEY.md](../../SURVEY.md) for **N4** (no Android
`application_files`) and **N7** (producer-fixed `meta-data`). What it actually
demonstrates is sharper than either finding on its own: **the same requirement,
in the same package, is expressible on iOS and unstateable on Android.**

## AS1 — Autopilot, and the declarative path §11 is waiting for *(blocking)*

Airship's Android SDK does not require an `Application` subclass. It ships
**Autopilot**: the application adds one manifest line naming a class, and
Airship loads it before any component receives an intent.

```xml
<meta-data android:name="com.urbanairship.autopilot"
           android:value="org.pyairship.PyAirshipAutopilot"/>
```

A producer can contribute the class (§6.4) — the sidecar does. It cannot
contribute the line that makes anything load it, because §6.3 emits
`<meta-data>` only as the *delivery* of an application-supplied value, and this
value is the producer's own class name. What is staged is dead code.

This matters beyond one vendor. §11 defers startup hooks partly on the ground
that *"some vendors reach the same result declaratively"*, citing Sentry's
`ContentProvider`. Autopilot is a second instance, AndroidX Startup is a third,
and **both are out of reach for want of a `meta-data` table, not for want of a
startup hook.** The deferral's own escape route is behind a gap the deferral
does not mention.

## AS2 — the configuration file, on the wrong side of an asymmetry *(blocking)*

Airship needs an app key and secret. Two paths exist on Android:

| Path | Status |
| --- | --- |
| `airshipconfig.properties` in `assets/` | no Android form of §7.3's `application_files` |
| `AirshipConfigOptions` from an Autopilot subclass | blocked by AS1 |

Both are blocked, so the Android integration cannot be configured at all.

The same requirement on iOS is one table entry:

```toml
[[ios.requires.application_files]]
name = "AirshipConfig.plist"
reason = "App key and app secret from the Airship dashboard…"
```

It fits with no argument, and P21's reasoning transfers word for word — the
file is account-specific, sometimes credential-adjacent, and always the
application's to provide. Nothing about that reasoning is iOS-shaped. The
asymmetry is an artifact of which examples were written first, which is exactly
what N4 claimed structurally and what this package demonstrates concretely.

## AS3 — the notification icon

Airship reads a small monochrome drawable and an accent colour by resource
name. §11 excludes contributed resources, correctly and for a stated reason.
It says nothing about a producer *requiring* that the application supply one,
and without that the failure is a white square on the application's brand, at
runtime, in production.

## AS4 — a notification content extension

Rich push UI needs a **notification content** extension. `kind` has
`notification_service` and `location_push`. The notification service extension
Airship also wants is declarable and is in the sidecar; the content extension
beside it is not, so the sidecar declares half of one feature.

## What this validated

- **§7.3 `application_files` on its second vendor.** Written for Firebase's
  `GoogleService-Info.plist`, it fits Airship's plist unchanged, including the
  rule that a producer should not declare a file when a programmatic path
  exists — here there genuinely is not one early enough for a launch push.
- **§6.2's `target_sdk` floor, on the case its own rationale describes.**
  `POST_NOTIFICATIONS` is requested at runtime only when `targetSdk >= 33`, so
  a push package declaring the floor turns a silently broken install into a
  build failure. First live use.
- **`conditional` earning its keep twice.** The app group and the service
  extension both apply only if the application wants confirmed delivery and
  images. Declaring them unconditionally would force every application to
  create an extension target it may not need; omitting them would leave the
  feature silently missing.
- **§6.9's two forms in one sidecar** — an owned-namespace `keep_classes` and a
  dependency keep naming `com.urbanairship.**`.

## Verdict

**iOS: clean.** **Android: blocked twice over**, on AS1 and AS2, which are the
same fact — Airship's app key — approached from two directions. A wrapper
shipped today would be an iOS package with an Android half that compiles and
does nothing.
