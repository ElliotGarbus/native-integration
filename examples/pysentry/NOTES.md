# Sentry against the current spec

Clean-sheet, from [Sentry's Android and Apple documentation](https://docs.sentry.io/platforms/android/configuration/manual-init/).
No `pysentry` distribution exists.

Sentry was picked as a **check on a claim I made rather than a search for new
gaps**. P23 landed §11 text naming "any SDK whose value depends on uploading
build artifacts" as permanently excluded, with Crashlytics canonical and
"Sentry, Bugsnag, Instabug and Datadog" named as sharing the shape. Sentry is
the obvious one to verify, since if the claim is wrong anywhere it is wrong
there.

It half holds, and the half that fails is worth correcting. Sentry also produced
the single most useful positive result in the whole example set.

## S1 — the first live §6.3 case *(a validation, and an overdue one)*

Sentry Android is configured through **manifest meta-data**, read by
`SentryInitProvider` — a `ContentProvider` shipped in the AAR and merged into
the application automatically:

```xml
<meta-data android:name="io.sentry.dsn" android:value="https://…@sentry.io/…"/>
```

The DSN is per-application, secret-adjacent, and **must be in the manifest**
before the SDK reads it, which happens during ContentProvider initialisation —
before `Application.onCreate`, and long before Python. No runtime call can
supply a value the SDK has already consumed.

That is exactly what §6.3 is for, and until now **nothing had used it**:

- §6.3's own example (AdMob `APPLICATION_ID`) turned out to be the legacy SDK's
  mechanism, superseded in the package that wraps it (G1).
- P2 — promoting application values to a platform-neutral table — was
  **withdrawn** on the grounds that four packages produced zero live uses.
- P19 narrowed §6.3 to "values the build must embed" partly because nothing
  demonstrated the broader form.

Sentry is that missing instance, and it arrived from a vendor with no knowledge
of any of those decisions. §6.3 as narrowed by P19 describes Sentry's
requirement precisely, with no adjustment. That is the strongest evidence in
this repository that a narrowing decision was right rather than merely tidy.

## S2 — Sentry needs no startup hook, and shows why

The interesting part is what Sentry does **not** need. Its early initialisation
— the hard requirement that motivated P1 for OneSignal — is solved entirely by
declarations:

| Need | Mechanism |
| --- | --- |
| Run before application code | `ContentProvider` in the AAR, merged by AGP |
| Obtain per-app configuration | manifest meta-data, §6.3 |

No `Application` subclass, no startup hook, no producer code at launch at all.
The vendor solved the problem the specification cannot express, using only
mechanisms the specification already has.

This is a **counter-example to P1**, not evidence for it. It demonstrates that
"initialise before the app runs" is achievable declaratively on Android, and it
strengthens the case that a startup-hook primitive is not the general answer it
appeared to be when only OneSignal was in view.

## S3 — P23 is half wrong about Sentry, and the correction matters

§11 now says that SDKs in the build-artifact-upload class "can be *linked* … and
the result will build. It will also be useless." That is true of Crashlytics.
**It is not true of Sentry**, and the difference is structural rather than
incidental:

| | Crashlytics | Sentry |
| --- | --- | --- |
| Gradle plugin | **required** for mapping upload | **optional** |
| Without it | traces obfuscated | traces obfuscated |
| Crash capture | works | works |
| Event delivery | works | works |

Both lose deobfuscation. But Crashlytics' plugin is also how the SDK is wired in
Google's documented path, whereas Sentry documents plain
`implementation 'io.sentry:sentry-android:…'` as a first-class option and reads
its configuration from the manifest. **A `pysentry` built under this
specification is a genuinely useful package with a real deficiency; a
`pyfirebase-crashlytics` is not a package at all.**

So the category §11 names is real, but it has two tiers, and the text currently
describes only the worse one:

- **Degrades** — the plugin adds symbolication to an SDK that already works.
  Sentry. Worth shipping.
- **Fails** — the build-time step is load-bearing for the SDK's core value.
  Crashlytics. Not worth shipping.

§11 should say so. A producer reading the current text would conclude that
wrapping Sentry is pointless, which is wrong, and the error runs in the
direction that discourages work this convention should welcome.

## S4 — the DSN on iOS, and P2's missing instance

`SentrySDK.start { $0.dsn = "…" }` runs at launch and needs the same value the
Android sidecar declares. §6.3 lives under `[android.requires]` and has no iOS
counterpart, so **the same logical requirement is expressible on one platform
and not the other** — which is exactly what P2 proposed to fix, and exactly the
justification P2 was withdrawn for lacking.

P2's withdrawal rested on a specific claim: *"after four examples,
`application_values` has zero live use cases."* That is no longer true. Sentry
uses it on Android and needs it on iOS.

Two things temper this:

- iOS still needs a **launch hook** to call `start()`, so the value alone does
  not close the case. This is the same P1/P2 coupling recorded under P21 — and
  Sentry is the second vendor to land on it, after OneSignal.
- Sentry can be initialised from Python instead, at the cost of missing every
  crash before the interpreter starts. For a crash reporter that is a large
  fraction of the crashes worth having.

> **Decided since.** P2 was revisited on this finding and **stays withdrawn**,
> on replaced reasoning. The premise it was withdrawn on — zero live uses of
> §6.3 — is indeed false, and §6.3's example is now Sentry's. But promoting the
> table to a platform-neutral logical name fails on design: `name` carries the
> **vendor's platform-specific manifest key**, which is the only thing that
> makes delivery work. A consumer handed a logical `sentry_dsn` cannot know
> Android calls it `io.sentry.dsn`.
>
> The iOS gap here is therefore not a missing *value table*. `SentrySDK.start`
> is a runtime call, so what iOS lacks is a caller — P1, or Python-init at the
> cost of pre-interpreter crashes. A neutral table would not have closed it.
>
> The residual observation stands: two independent vendors (OneSignal, Sentry)
> now want "initialise natively, with an application-supplied value." That is
> P1's territory, not P2's.

## Verdict

Sentry is the first example to **validate** more than it broke.

- §6.3 survived two decisions that nearly orphaned it and turned out to describe
  a real vendor requirement exactly (S1).
- §6.5's bounded range, §7.4, and the ordinary permission and floor machinery
  all fit without comment.
- The one correction it forces (S3) is to text I wrote two commits ago, and it
  is a correction toward *more* being possible, not less.

The gap it leaves is the same one Firebase left, from a different direction:
this specification can express what an SDK needs on Android and not the
equivalent on iOS, because §6.3 never grew a counterpart.
