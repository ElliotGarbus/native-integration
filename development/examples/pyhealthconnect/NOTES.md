# Health Connect against the current spec

Clean-sheet, from [Get started with Health Connect](https://developer.android.com/health-and-fitness/health-connect/get-started).
No `pyhealthconnect` distribution exists.

Chosen from [SURVEY.md](../../SURVEY.md) as the second instance of **N20** — an
SDK that requires the *application* to own a class — after WeChat. The point of
running it rather than WeChat is that N20 is easy to dismiss as a regional
quirk. It is not: the same shape appears in a first-party AndroidX library,
and Google Play policy is what enforces it.

## HC1 — `<queries>` decides whether the SDK works at all *(blocking)*

`HealthConnectClient.getSdkStatus()` asks the package manager whether
`com.google.android.apps.healthdata` is present. Under Android 11+ package
visibility that call returns "not installed" on every device unless the
manifest declares:

```xml
<queries>
  <package android:name="com.google.android.apps.healthdata" />
</queries>
```

No declaration reaches it. And unlike Meta's case in
[pyfacebook](../pyfacebook/NOTES.md) (FB2), **nothing merges it in from an
`.aar`** — the entry is the application's to declare, so the integration fails
closed at the API this SDK's entire surface is gated behind, silently, with a
status code that reads like the user simply does not have the app.

That is the strongest form of the argument for N6: a permission-shaped
declaration whose absence produces not an error but a wrong answer.

## HC2 — a class the producer must not write, and cannot ask for *(blocking)*

Google Play requires a health application to show a permissions rationale.
Health Connect's mechanism is three things at once:

- an **activity in the application's own namespace** that displays the
  rationale;
- an `<activity-alias>` for it, guarded by
  `android:permission="android.permission.START_VIEW_PERMISSION_USAGE"`;
- an intent filter matching action `android.intent.action.VIEW_PERMISSION_USAGE`
  **with** category `android.intent.category.HEALTH_PERMISSIONS`.

Every one of the three is outside version 1, and each for a different reason:

1. **The class is the application's.** §6.1 rightly forbids a producer writing
   outside its own namespace, and there is no `requires` form for *the
   application must provide a class here, doing this*. This is N20, in a
   Google library.
2. **`activity-alias` is not a `kind`**, and the `android:permission`
   attribute a component needs has no field (N5).
3. **The filter carries an action and a category.** §6.8's `intent_filters`
   models exactly one action, no categories — deliberately, and with a good
   rationale drawn from FCM, where the action is vendor-fixed and the component
   stays unexported so there is no reachable surface to model.

Point 3 is the finding worth carrying back. **The stereotype does not
generalize as confidently as its rationale claims.** FCM's shape — one action,
unexported, no data — is real, but it is one vendor's shape rather than the
category's. Health Connect's filter is reachable by the system, carries a
category that is load-bearing, and is guarded by a permission instead of by
non-export. A second stereotype may be the answer; assuming one covers the
class is not.

## What this validated

- **§6.7's canonical-permission rule, on a whole vendor family.** Every Health
  Connect permission is `android.permission.health.<RECORD>` — dozens of them,
  under a prefix that is neither `android.permission.` in the ordinary sense
  nor a third-party vendor string. §6.7 defines **no prefix expansion**, which
  is exactly why these declare with no additional rule. A shorthand scheme
  would have needed a special case here.
- **Per-permission `reason`, where it does more than usual.** A health
  application's permission list is the thing its reviewers, its users and its
  store listing all argue about. §9's report carrying "reading step counts
  written by other applications" beside `READ_STEPS` is the disclosure this
  convention promises, on the data where it matters most.
- **The exact-coordinate form.** `androidx.health.connect:connect-client:1.1.0`
  is a stable AndroidX release with a slow cadence, which is the case §6.5's
  recommendation is written for: the floor is visible in the sidecar without
  opening the record.

## Verdict

**Blocked**, and unusually cleanly: the sidecar's data half is complete and
correct, while the two things that make a Health Connect integration
*shippable* — device detection and the Play-required rationale — are both
outside version 1. This is the one example in the set where the missing pieces
are enforced by a store policy rather than by an SDK, which puts them beyond a
producer's ability to work around in Python.
