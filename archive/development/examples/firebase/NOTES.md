# Firebase against contract 1

Three clean-sheet sidecars — [core](core/native.toml),
[crashlytics](crashlytics/native.toml), [messaging](messaging/native.toml) —
written against Google's documented integration rather than an existing Python
package. No `pyfirebase-*` distribution exists; these are what one would have to
ship.

**Why this set matters more than a fifth PyPlatformPackages example.** Every
earlier example came from one toolchain lineage, and PROPOSALS.md has been
saying for several rounds that a producer from outside it is worth more than
another from inside. Firebase is that: requirements designed by Google, with no
awareness of this convention, and the most widely integrated mobile SDK there
is. If the spec cannot express Firebase, "the declaration set is right" is not a
claim that can be made.

Sources: Firebase's Android setup guide (BOM 34.17.0, minSdk 23, the
google-services plugin), the FCM Android client guide (the service intent
filter, notification meta-data), and Crashlytics' Apple-platforms setup (the run
script and its Input Files).

## Scorecard

| | Expressible | Blocked by |
| --- | --- | --- |
| **Core/Analytics** | partially | Gradle plugin, BOM, config file |
| **Crashlytics** | barely | build-time scripts on both platforms |
| **FCM — Android** | no | intent filter on a service |
| **FCM — iOS** | nearly fully | — |

One of four halves comes out clean. That is roughly the hit rate of the
PyPlatformPackages set, from a completely independent direction.

## F1 — Gradle plugins *(blocking, Core and Crashlytics)*

Firebase's documented Android setup requires the `com.google.gms.google-services`
plugin, which reads `google-services.json` and generates the string resources
the SDK reads at runtime. Crashlytics adds `com.google.firebase.crashlytics`,
which uploads the R8 mapping file. §11 excludes build plugins **on principle**,
citing §2.1 — not as a deferral.

The principle is right and should not bend. A Gradle plugin is arbitrary
build-time code execution chosen by a transitive dependency, which is exactly
the capability §2.1 exists to deny. But the consequence has to be stated
plainly: **the standard integration path for the most-used mobile SDK in the
world is outside this specification, permanently.**

There is an escape hatch for Core, and the sidecar takes it:
`FirebaseApp.initializeApp(context, FirebaseOptions.Builder()…build())`
initializes Firebase without the plugin, from values the application passes in.
That is why `pyfirebase-core` ships Java at all. It costs the application author
a transcription of four or five fields out of `google-services.json` — the
transcription this whole convention exists to abolish, reintroduced one layer
down.

There is **no** escape hatch for Crashlytics (F4).

## F2 — The BOM, and why the new range form does not help

Firebase documents:

```kotlin
implementation(platform("com.google.firebase:firebase-bom:34.17.0"))
implementation("com.google.firebase:firebase-analytics")   // no version
```

§6.5 has no platform/BOM form, so each sidecar pins its own artifact
independently.

**The bounded range added in this revision solves the wrong half.** A range
gives *per-artifact* flexibility. A BOM gives *cross-artifact alignment* — it is
a constraint over a **set**, asserting that these versions were tested together.
Nothing expressible per entry can say that, and here the set spans three
distributions: `pyfirebase-core`, `-crashlytics` and `-messaging` each pin
Firebase artifacts, and nothing makes their choices agree.

This is a genuinely new shape. Every version rule in the specification so far
governs one dependency at a time.

Mitigating: Gradle will still resolve to a single version per artifact, and §6.5
locks the result, so the failure is a build-time resolution conflict rather than
silent skew — and §8.16 now requires that conflict to name the declaring
distributions. The spec degrades honestly here. It just cannot express the
constraint that would prevent the conflict.

## F3 — Application-supplied *files*, and why this is the pivotal gap

Both platforms need an application-specific config file:
`google-services.json` in the Android module root, `GoogleService-Info.plist` in
the iOS app bundle. §6.3's application values are **scalars**; there is no
file-shaped prerequisite anywhere in the specification.

On iOS this is arguably not a gap in substance — putting a plist in your own
bundle is application configuration, which §11 excludes deliberately. But the
package cannot **state the requirement**, and that is the part §7.3 exists to
do for entitlements, purpose strings and extensions. An application that omits
`GoogleService-Info.plist` gets a runtime crash inside `FirebaseApp.configure()`
with nothing pointing back at the distribution that needed it.

The obvious small primitive is a file-shaped prerequisite in the §7.3 mould —
declared, reported, never satisfied by the consumer:

```toml
[[requires.application_files]]
name = "GoogleService-Info.plist"
location = "bundle"        # closed vocabulary
reason = "Download from the Firebase console; FirebaseApp.configure() reads it"
```

> **Correction, added when P21 was decided.** This finding was written as
> "the pivotal one" and as the prerequisite for reconsidering P1. Closer
> analysis narrowed it on both counts. Most Firebase services accept
> `FirebaseOptions` **programmatically** on both platforms, so the file is
> avoidable — the Android half of this gap dissolves entirely along with the
> plugin. What survives is narrow and real: **Analytics on Apple platforms**
> reads the static plist and offers no programmatic alternative. §7.3 now takes
> that case as `[[ios.requires.application_files]]`.
>
> The P1 argument below also does not survive intact. A file prerequisite is
> *disclosure* — the application puts the file in its bundle and the SDK reads
> it — so it hands the producer's initialization code no values at all. P1's
> blocker is unchanged. The durable conclusion is the last paragraph of this
> section, and it is stronger than the reframing: across six packages,
> application configuration reaches producers through **Python**, not through
> the build.

**This reframes P1.** P1 (startup hooks) was deferred partly because withdrawing
P2 removed the channel by which application-supplied values reach producer code
— and the deferral note said to reopen it when "a producer needs native
initialization *and* has a channel for the values that initialization needs."

Firebase looks at first like it trips that trigger: `FirebaseApp.configure()`
takes no arguments, so no values channel seems necessary. It does not, and the
reason is more interesting than if it had. The values did not go away; they
moved into a **file** the specification also cannot describe. OneSignal needed a
scalar; Firebase needs a file. **Both are the same missing thing wearing
different clothes, and the initialization hook is downstream of it in both
cases.**

So P1 stays deferred, and its trigger is now better understood: the blocker was
never the hook's signature. It is that this specification has no vocabulary for
*what the application must provide to the producer*, beyond scalars it has since
narrowed almost out of existence.

## F4 — Build-time scripts *(blocking, Crashlytics, both platforms)*

Crashlytics is the case where the specification's boundary is not merely
inconvenient but total:

- **Android:** the `com.google.firebase.crashlytics` plugin uploads the R8
  mapping file. Without it, every stack trace stays obfuscated.
- **iOS:** a Run Script build phase invoking the Crashlytics `run` script from
  the resolved SwiftPM checkout, with five specific Input Files covering the
  dSYM bundle, `GoogleService-Info.plist` and the built executable. Without it,
  no dSYMs are uploaded and crash reports are raw addresses.
- **iOS:** `DEBUG_INFORMATION_FORMAT = dwarf-with-dsym`, an Xcode build setting.

All three are §11 exclusions, two of them on principle. The resulting sidecar
links the SDK and delivers unsymbolicated crashes — which is to say it delivers
the part of Crashlytics nobody wants.

**This is a whole SDK class, not one product.** Any SDK whose value depends on
uploading build artifacts — symbol files, mapping files, source maps, bitcode —
requires build-time execution by construction. Sentry, Bugsnag, Instabug and
Datadog all have the same shape.

The specification should say so. §11 currently frames script exclusion as a
consequence of §2.1's design principle, which is correct but reads as though the
cost is hypothetical. It is not: it is an identifiable category of SDK that this
convention will never integrate, and a producer in that category should learn it
from the specification rather than from a sidecar that builds and under-delivers.

## F5 — Intent filters on services *(blocking, FCM Android)*

FCM's entire Android integration is a service registration:

```xml
<service android:name="…PyFirebaseMessagingService" android:exported="false">
  <intent-filter><action android:name="com.google.firebase.MESSAGING_EVENT"/></intent-filter>
</service>
```

§6.8 declares the component but not the filter. `view_links` is the only filter
form; it is activity-only, export-gated, and generates a fixed
VIEW/DEFAULT/BROWSABLE shape rather than an arbitrary action. §6.8 already lists
"filters on non-activity components" among its v1 exclusions.

**FCM is the canonical instance of that exclusion**, and it is worse than a
missing convenience: without the filter the service is never invoked. Messages
arrive, nothing runs, and the build reported no problem.

Notably this is the *opposite* shape from `view_links`. That form exists because
the classic bug is a hand-written filter missing `DEFAULT`, so the spec
generates the filter and refuses to let producers spell one. Here the filter is
a single vendor-defined action on a non-exported service — no categories, no
data element, nothing to get subtly wrong:

```toml
[[android.contributes.components.intent_filters]]
action = "com.google.firebase.MESSAGING_EVENT"
```

That is a narrower thing than the intent-filter grammar §6.8 declined to model,
and it is what the second-most-common Android integration pattern after
`Application` subclassing actually needs.

## F6 — Non-class shrinker directives

Crashlytics documents `-keepattributes SourceFile,LineNumberTable` so that
deobfuscated traces carry line numbers. §6.9 accepts class-keep patterns only,
and its own rationale names `-keepattributes` as a form it deliberately
excludes, on the grounds that validating R8's grammar would need a substantial
parser.

The reasoning holds — but this is the second documented v1 exclusion that a real
SDK walks straight into, and it suggests a narrow typed form
(`keep_attributes = ["SourceFile", "LineNumberTable"]`, closed vocabulary) would
pay for itself. Unlike class patterns, attributes are a short fixed list with no
namespace question at all.

## F9 — Three distributions, one integration *(a validation)*

Crashlytics and Messaging both require Core's setup. Nothing in the sidecars
expresses that, and nothing needs to: `pyfirebase-crashlytics` depends on
`pyfirebase-core` in ordinary Python metadata, the closure resolves both, and
§3.2 discovers both sidecars. The per-distribution model in Appendix A holds up
under a genuine multi-package SDK family, with each contribution attributable to
the piece that made it.

This is also §12's guidance working as intended: the family splits along feature
lines, so an application that wants analytics but not crash reporting installs
`pyfirebase-core` and gets exactly its native surface.

## What the spec got right

- **`platforms`** (§4.5) is unnecessary here — all three work on both — which is
  the correct behaviour for a key that should be used rarely.
- **§9's effective-delta MUST** earns itself immediately: `firebase-analytics`
  merges `com.google.android.gms.permission.AD_ID` into the manifest from its
  own AAR, declared by no sidecar, with Play data-safety consequences. Under the
  previous SHOULD this could have gone unreported.
- **§7.3's conditional prerequisites** fit FCM's image-attachment extension
  exactly — needed only if you send images, and unknowable to the producer.
- **§6.5's locked graph plus §8.16** turn F2's BOM problem into a named
  resolution conflict rather than silent version skew.
- **The reverse-DNS SHOULD** (§6.1) is what these sidecars naturally follow.

## Verdict

Firebase does not break the specification's shape, and that is worth saying
first: nothing here wanted an executable hook in a sidecar, nothing wanted to
escape the owns/requires/contributes split, and the two hardest blockers (F1,
F4) are cases where the specification is **correctly** refusing rather than
failing.

But three findings are load-bearing:

- **F3 is the pivotal one.** The specification has no way to say *what the
  application must provide to the producer* beyond a scalar it has narrowed
  nearly out of use. That single gap is why F1's workaround is ugly, why P1
  cannot be reopened cleanly, and why an app that forgets a config file gets a
  runtime crash with no attribution.
- **F5 is a concrete, bounded addition** — a single-action intent filter on a
  service — for the pattern FCM, and every SDK shaped like it, depends on.
- **F4 defines a permanent boundary** that the specification should name
  explicitly, because a producer in that category deserves to find out from
  §11 rather than from a build that succeeds and under-delivers.
