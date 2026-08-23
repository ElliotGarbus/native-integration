# Coverage survey: the next forty SDKs

**Status: survey findings, not proposals.** This file records what forty
further SDKs — the tier below the ten worked in [`examples/`](examples/) — ask
of a native build, and which of those asks SPEC.md cannot express. Nothing here
is normative and nothing here has been decided. Remedies belong in
[PROPOSALS.md](PROPOSALS.md); this is the evidence that would justify one.

Gap identifiers are `N1`–`N21`, continuing the per-example scheme
(`A*`/`B*`/`C*`, `L*`, `W*`, `G*`, `F*`, `S*`, `T*`, `M*`) with one prefix for
the whole batch, because these findings come from breadth rather than from any
single integration.

## Method

The ten worked examples were chosen for *pressure* — each was picked to break
something. This survey is the opposite: it takes the SDKs an application is
statistically likely to acquire, reads each vendor's own integration
instructions, and asks only whether SPEC.md can say what the vendor asks for.
No sidecars were written for the survey itself. A finding here is a claim about
**expressiveness**, not about whether a wrapper would be worth shipping — and
four of them have since been put to a sidecar, which changed three of the four
it touched (see [Since this survey](#since-this-survey), below).

Selection is by prevalence within category — ads, attribution, engagement,
analytics, crash/APM, identity, payments, maps, media/RTC, support, ML,
storage, platform frameworks — anchored on public SDK-prevalence rankings and
on the categories those rankings use. Three regionally dominant or
policy-forcing cases (WeChat, Health Connect, BLE scanning stacks) are included
because each produces a finding nothing else in the set does.

Where a claim below is load-bearing it was checked against vendor
documentation in August 2026; where it was not, it is marked *(unverified)*.

## The forty

**Verdict** is about the specification, not the SDK: *expressible* means a
sidecar could say everything the vendor's integration guide asks for.

| # | SDK | What it asks of the build | Verdict |
| --- | --- | --- | --- |
| 1 | AppLovin MAX | Maven deps; ~100 `SKAdNetworkItems` dicts; adapter repos; `-ObjC` | **N2**, N15 |
| 2 | Unity Ads | Maven dep; SKAdNetwork ids | **N2** |
| 3 | ironSource LevelPlay | Maven dep; SKAdNetwork ids; adapter repos | **N2** |
| 4 | Meta Audience Network | Maven dep; SKAdNetwork ids; Meta app id | **N2**, **N1** |
| 5 | Liftoff / Vungle | Maven dep; SKAdNetwork ids | **N2** |
| 6 | Google UMP (consent) | Maven dep; app-id `meta-data` | expressible |
| 7 | AppsFlyer | dep; tracking domains in privacy manifest; associated domains | **N3**, N17 |
| 8 | Adjust | dep; associated domains; ATT purpose string | N17 (values); rest expressible |
| 9 | Branch | `branch_key` in `Info.plist`; `autoVerify` App Links; fixed `meta-data` | **N1**, **N7**, N19 |
| 10 | Kochava / Singular | deps; attribution plist keys *(unverified)* | likely **N1** |
| 11 | Braze | notification icon drawable; NSE + content extension; app group | **N9**, **N17** |
| 12 | CleverTap | `CleverTapAccountID`/`CleverTapToken` in `Info.plist`; push icon | **N1**, **N9** |
| 13 | Airship | `airshipconfig.properties` in `assets/`; Autopilot `meta-data` | **N4**, **N7** |
| 14 | Iterable / MoEngage | push icons, rich-push extensions *(unverified)* | likely **N9**, N17 |
| 15 | Amplitude | plain dep, runtime config | expressible |
| 16 | Mixpanel | plain dep, runtime config | expressible |
| 17 | Twilio Segment | plain dep; destination plugins are deps | expressible |
| 18 | Datadog RUM | dep + optional mapping-upload plugin | §11 exclusion (degrades) |
| 19 | New Relic Mobile | **mandatory** Gradle plugin, bytecode instrumentation | **N21** |
| 20 | Embrace | **mandatory** `embrace-swazzler` plugin; `embrace-config.json` | **N21**, **N4** |
| 21 | Instabug | dep + symbol-upload plugin | §11 exclusion (degrades) |
| 22 | Bugsnag | dep + optional plugin | §11 exclusion (degrades) |
| 23 | Google Sign-In / Credential Manager | `GIDClientID` in `Info.plist`; reversed-client-id scheme | **N1** |
| 24 | Meta (Facebook) SDK | `FacebookAppID`, `FacebookClientToken`, `FacebookDisplayName`; `fb<id>` scheme; `<queries>`; `-ObjC` | **N1**, **N6**, N15 |
| 25 | Auth0 | `manifestPlaceholders` (`auth0Domain`, `auth0Scheme`) consumed by the AAR | **N8** |
| 26 | Microsoft MSAL / Okta | redirect activity + scheme; broker `<queries>` | **N6**; rest expressible |
| 27 | Play Billing / StoreKit 2 | `com.android.vending.BILLING`; platform framework | expressible |
| 28 | RevenueCat | Maven dep + Swift package; runtime key | expressible |
| 29 | PayPal / Braintree | return-URL scheme; `<queries>`; `-ObjC`; wallet app checks | **N6**, N15 |
| 30 | Adyen / Razorpay / Klarna | deps; redirect activity; some private repos *(unverified)* | expressible (§6.6 covers repos) |
| 31 | Google Maps SDK | API key `meta-data` (Android); runtime key (iOS) | expressible |
| 32 | Radar / HERE (background location) | foreground service with `foregroundServiceType="location"` | **N5** |
| 33 | Agora RTC | Broadcast Upload Extension; `libc++_shared.so` collision; background modes | **N17**, **N14** |
| 34 | Twilio Voice & Video / LiveKit | CallKit/PushKit; `voip` background mode; VoIP entitlement | expressible; **N17** for screen share |
| 35 | AndroidX Media3 (ExoPlayer) | `coreLibraryDesugaring`; `MediaSessionService` with an FGS type | **N12**, **N5** |
| 36 | Intercom | dep; push; runtime config | expressible |
| 37 | Zendesk | private Maven repo; activity themes | §6.6 covers the repo; **N9** for the theme |
| 38 | Sendbird / Stream Chat | deps; push; notification icons | **N9** |
| 39 | Google ML Kit | **CocoaPods-only on iOS**; bundled-model `meta-data` on Android | **N16**, **N7** |
| 40 | TensorFlow Lite / OpenCV | `noCompress` for `.tflite`; duplicate `.so` packaging | **N14** |

Three further cases were sampled because each produces a finding the forty do
not:

| # | Case | Finding |
| --- | --- | --- |
| 41 | Health Connect | `<queries>` for the health app, plus an **application-owned** rationale activity and activity-alias | **N6**, **N20** |
| 42 | WeChat / Alipay | `${applicationId}.wxapi.WXEntryActivity` — a class in the *application's* namespace, exported, `singleTask`, with a matching `taskAffinity` | **N20**, **N5** |
| 43 | Nordic / beacon BLE stacks | `usesPermissionFlags="neverForLocation"`; `maxSdkVersion` on legacy Bluetooth permissions | **N18** |

## Tier A — gaps that change what a producer can express

### N1 — iOS application-supplied values *(five vendors)*

§6.3's rationale predicts this precisely: *"When one does appear, the shape is a
parallel `[[ios.requires.application_values]]` table with its own delivery
field."* Five have appeared, each reading an account-specific value out of
`Info.plist` before any application code runs:

| Vendor | Keys |
| --- | --- |
| Meta (Facebook) | `FacebookAppID`, `FacebookClientToken`, `FacebookDisplayName` |
| Branch | `branch_key` |
| CleverTap | `CleverTapAccountID`, `CleverTapToken` |
| Google Sign-In | `GIDClientID`, optionally `GIDServerClientID` |
| Meta Audience Network | the Meta application id |

There is no expressible form today, and not merely an awkward one. §7.6's
`values` is for producer-known constants and could not carry an account
identifier even if a producer were willing to hard-code one; §7.3's six tables
have no entry for *"the application supplies a scalar."* The producer cannot
even **state the requirement**, which is the failure mode this specification
exists to eliminate: the application builds, launches, and dies on first use
— or worse, reports quietly to nobody's project.

The predicted shape holds — `[[ios.requires.application_values]]` with `id`,
`reason`, and an `info_plist_key` delivery field mirroring
`manifest_meta_data`. §6.3's argument for *parallel* tables rather than one
promoted table is confirmed rather than weakened: the Meta application id and
the Google client id genuinely differ between platforms.

One wrinkle: Branch's `branch_key` may be a **dictionary** of `live`/`test`
keys. §6.3's non-empty-string rule can express the single-environment form
only, which is a documentable restriction rather than a blocker.

### N2 — `SKAdNetworkItems`, and the dictionary exclusion *(six vendors)*

§7.6 says dictionary-valued keys are *"excluded by design, not deferred"*, on
the ground that *"every structured case encountered so far is better served by
a narrower primitive."* The single most prevalent SDK category in the ecosystem
supplies the counter-case. Every ad network and mediation adapter requires
`SKAdNetworkItems` — an array of `{ SKAdNetworkIdentifier = "…" }` dictionaries,
one per network, running to roughly a hundred entries for a mediated
integration. AppLovin publishes the list as a JSON/XML feed and ships an
"Info.plist Generator" precisely because hand-merging it is unmanageable.

This is the exact shape §7.6's `append` was designed for — producer-known,
order-insensitive, de-duplicable by identifier, granting the application
nothing — and it is unreachable because of a type restriction rather than an
authority argument.

**The doctrine survives; the claim does not.** The right fix is the narrower
primitive §7.6 says it prefers, and this case has one:

```toml
[ios.contributes]
skadnetwork_identifiers = ["su67r6k2v3.skadnetwork", "…"]
```

The consumer renders the dictionary array and de-duplicates across
distributions on the identifier. No general dictionary support, no new merge
semantics beyond `append`'s, and the sentence in §7.6 becomes true instead of
merely confident.

### N3 — privacy manifests

Apple has required, since May 2024, that an application declare its
required-reason API usage and tracking domains in `PrivacyInfo.xcprivacy`, and
App Store Connect rejects uploads that do not. SDKs distributed as
XCFrameworks, Swift packages or source are expected to carry their own;
**contributed raw source (§7.5) cannot**, because it compiles into the
application target and is therefore the *application's* code as far as Apple is
concerned. §7.7 sharpens this: a Swift-implemented Python module is a
producer's code living inside the application's binary by design.

So a producer that touches `UserDefaults`, file timestamps, disk space or
system boot time — a set most non-trivial shims touch — silently obliges the
application to declare reason codes it has no way of knowing about. The failure
arrives at upload, weeks after the build, naming nothing. That is the
archetypal §7.3 shape.

Two candidate forms, both worth writing up: a **contribution** of accessed-API
categories and reason codes that the consumer merges into the application's
manifest (defensible — the codes are facts about the producer's own code), and
a **prerequisite** for `NSPrivacyTrackingDomains`, which is a claim about what
the application does and is the application's to make.

### N4 — Android has no `requires` family

iOS has six prerequisite tables; Android has SDK floors and
`application_values`, and nothing else. There is no Android form of *"the
application must supply this file"*, which §7.3's `application_files` provides
on the other platform. Evidence: Airship reads `airshipconfig.properties` from
`assets/`, Embrace requires `embrace-config.json` in the source root, Adobe's
SDK reads `ADBMobileConfig.json`, Huawei's requires `agconnect-services.json`,
and Firebase's `google-services.json` is application-supplied even where the
excluded plugin is what consumes it.

The asymmetry is not a platform property. It is an artifact of which examples
were run: the four PyPlatformPackages sidecars are Android-first and needed no
prerequisite beyond a floor, and the iOS tables were written under pressure
from OneSignal and CoreLocation. This is the structural finding in the survey —
N9 and N20 are further members of the same missing family.

### N5 — component attributes, and `kind = "provider"` being unusable

§6.8 models a component as `kind` + `name` + provenance + export. Real
registrations need more:

- **`android:foregroundServiceType`** is **mandatory** on Android 14+ for any
  foreground service, together with the matching `FOREGROUND_SERVICE_*`
  permission. Any producer-source service that goes foreground — background
  location (Radar, HERE), media playback (Media3's `MediaSessionService`),
  screen capture — cannot be registered validly today.
- **`android:launchMode` and `android:taskAffinity`** — WeChat's entry activity
  requires `singleTask` and a specific affinity; OAuth redirect receivers
  commonly need `singleTask` to avoid duplicate task stacks.
- **`android:authorities`** on a provider is required by the manifest schema. A
  `kind = "provider"` entry cannot be written into a valid manifest, so one
  quarter of §6.8's vocabulary is **unimplementable in v1**. This is a defect
  rather than a gap.
- Lesser: `android:permission`, `android:process`, `android:enabled`,
  `android:directBootAware`.

The design tension is real — §6.8 deliberately models stereotypes, not the
manifest grammar — but `foregroundServiceType` and `authorities` are not
grammar, they are **validity**.

*Amended by the sidecars.* [pyagora](examples/pyagora/NOTES.md) (AG1) removes
the "an `.aar` brings its own declaration" hedge: a media-projection capture
service is the **producer's** to declare, because it is the producer's capture
lifecycle that runs inside it. The permission half of that requirement is
already expressible, which makes the declaration look complete while the
attribute that gives it meaning is missing. The `authorities` half was settled
the other way and has landed — `provider` left the §6.8 vocabulary rather than
gaining a field it could not validly carry.

### N6 — Android `<queries>`

Android 11+ package visibility means a producer's own Java (§6.4) that resolves
an intent or checks for an installed application sees nothing unless the
manifest declares a `<queries>` entry. Evidence: wallet and social flows
(Meta's `com.facebook.katana`, WeChat, Alipay, PayPal), broker-based auth
(MSAL), Chrome Custom Tabs browser resolution, and Health Connect's
`com.google.android.apps.healthdata`.

The iOS counterpart is explicitly supported — §7.6 names
`LSApplicationQueriesSchemes` as *the* example of an ordinary contribution that
"grants nothing." The Android equivalent grants nothing either, and by the same
reasoning belongs in `contributes`.

**Severity is bounded by provenance.** An SDK arriving as an `.aar` carries its
own `<queries>` through manifest merging, which covers most of the vendors
above. The hole is for §6.4 source contributions — and there the failure is
silent, because `PackageManager` reports "not installed" rather than an error.

*Amended by the sidecars.* [pyfacebook](examples/pyfacebook/NOTES.md) (FB2)
confirms the narrowing — Meta's entry does arrive from `facebook-common`. But
[pyhealthconnect](examples/pyhealthconnect/NOTES.md) (HC1) is the case where
nothing merges anything in: the entry is the application's to declare, and its
absence makes `getSdkStatus()` return a wrong answer rather than an error, on
every device, for the API the whole SDK is gated behind.

### N7 — producer-fixed manifest `meta-data` *(P3's deferred half, now a finding)*

Today `<meta-data>` reaches the manifest only as the *delivery mechanism* for
an application-supplied value (§6.3). A producer-known constant has no path at
all. Six vendors in this survey need one:

| Vendor | Entry |
| --- | --- |
| Firebase Messaging | `default_notification_icon`, `default_notification_color`, `default_notification_channel_id` |
| ML Kit | `com.google.mlkit.vision.DEPENDENCIES = "barcode,face"` |
| Airship | `com.urbanairship.autopilot = <producer class>` |
| Branch | `io.branch.sdk.TestMode` |
| Google Mobile Ads | `DELAY_APP_MEASUREMENT_INIT`, `OPTIMIZE_INITIALIZATION` |
| AndroidX Startup | `<meta-data android:name="<Initializer class>" android:value="androidx.startup"/>` |

P3 recorded this with one motivating example, which PROPOSALS.md's own rule
calls a hypothesis. Six makes it a finding.

**The interlock with §11's lifecycle deferral is the interesting part.**
SPEC.md argues for waiting on startup hooks partly because *"some vendors reach
the same result declaratively"*, citing Sentry's `ContentProvider`. Airship's
Autopilot is a second instance of exactly that — a `meta-data` key naming a
producer-owned class, so `takeOff` runs before any component receives an intent
— and AndroidX Startup is a third, generic one. Both are **unreachable today
for want of `meta-data`, not for want of a startup hook.** Landing N7 would
give two vendors the declarative path §11 says it is waiting for, without
opening P1.

The residual case N7 does not solve is a `meta-data` value that is a *resource
reference* (`@drawable/ic_stat_notify`), which is N9.

### N8 — `manifestPlaceholders` as a third delivery for application values

Auth0.Android and AppAuth-Android both consume an application-specific value
through Gradle's `manifestPlaceholders`, which AGP substitutes into **the
dependency's own merged manifest** — the intent filter lives inside the AAR,
with `${auth0Domain}` and `${auth0Scheme}` holes in it. §6.3 can deliver a
value to `manifest_meta_data`, or splice it inline into a contribution the
sidecar itself declares; neither reaches into an AAR's manifest.

§6.8 already cites this mechanism approvingly — "AppAuth-Android ships the
intent filter pre-written, with a placeholder for the one value the application
supplies via `manifestPlaceholders`" — and then provides no way to use it. One
optional field, `manifest_placeholder = "auth0Domain"` alongside
`manifest_meta_data`, closes it: same satisfaction rules, same reporting, no
new authority.

### N9 — application-supplied Android resources, as a prerequisite

§11 excludes resource *contribution*, and the reasoning is sound: resource
names are a flat per-type namespace with no containment rule. That argument
says nothing about a producer **requiring** that the application supply one.
Three recurring cases:

- **A notification icon.** Every push SDK needs a small monochrome drawable
  (FCM, Braze, CleverTap, Airship, Sendbird, Iterable). Android draws a white
  square when it is missing — on the application's brand.
- **A theme.** Stripe Identity documents that the hosting activity must use a
  Material theme; several support SDKs say the same.
- **A string.** Mapbox's Android access token is conventionally a string
  resource.

The shape is `application_files`' twin: the application supplies it, the
consumer checks only that a resource of that name and type exists, and the
producer never writes into `res/`.

### N10 — the host-activity contract

Stripe's `PaymentSession` requires a `ComponentActivity`, and Stripe Identity
requires an `AppCompatActivity` with a Material theme. On iOS the analogue is
an SDK that needs a presenting `UIViewController`, or that expects URL
callbacks forwarded from a `UISceneDelegate` rather than the app delegate.

**The evidence is one vendor, and it did not grow.** This entry first claimed
that anything built on `ActivityResultContracts` or on fragments needs the same
— a category inferred rather than observed, and the obvious candidates do not
hold: Facebook Login routes through its own callback manager and the legacy
result callback, and Google Pay's documented path uses a helper doing the same.
Both work against a plain platform activity. Round five then wrote four sidecars
against Meta, Airship, Agora and Health Connect, and **none needed a host
capability**. By this directory's own rule that makes N10 a hypothesis rather
than a finding, which is a reason to leave the specification alone until a
second vendor appears.

For this specification's actual audience this is not a footnote. A
Python-mobile toolchain owns exactly one activity, and whether that singleton
extends `Activity` or `AppCompatActivity` decides whether a whole tier of SDKs
functions at all. A producer cannot declare the requirement, and a consumer —
which generates the bootstrap — is precisely the party that could satisfy or
refuse it.

It is adjacent to §11's lifecycle deferral but distinct: nothing here asks to
*run code*. It asks about the **type** of a singleton the consumer already
owns. A `requires`-shaped declaration — `host_activity_base`, or a capability
token such as `activity_result_api` — would be checkable by the one party that
knows the answer.

## Tier B — build-configuration floors

### N11 — toolchain floors beyond the SDK level

§6.2 has `compile_sdk`/`min_sdk`/`target_sdk`; §7.2 has `deployment_target`.
Vendors also require AGP, Gradle, JDK, Kotlin, Xcode and Swift-tools floors —
Kotlin-compiler compatibility in particular is a recurring hard failure for
compiler-plugin SDKs (Realm's Kotlin 2.0 lag is the documented case). A floor
is the shape this specification already trusts most: fail when lower, never
raise.

### N12 — core library desugaring

Media3 documents that consuming applications must enable
`coreLibraryDesugaring` for older API levels, and several AndroidX and Firebase
paths inherit the same requirement. It needs a compile option *and* a
dependency on a special configuration, so it is inexpressible twice over. It is
a bounded, boolean, floor-like fact — `core_library_desugaring = true` under
`[android.requires]` — not the arbitrary build mutation §11 excludes.

### N13 — dependency configurations beyond `implementation`

§6.5 anticipates this as a minor revision; the survey supplies the demand.
`coreLibraryDesugaring` (N12), `ksp`/`kapt` for any producer glue built on
Room, Glide, Hilt or Dagger, and `compileOnly` for optional Play Services
surfaces.

### N14 — packaging collisions between independently-authored producers

Two producers composing is this specification's whole point, and it is exactly
where Android packaging breaks: duplicated `META-INF/*` entries (OkHttp,
coroutines and Bouncy Castle in combination), duplicated `libc++_shared.so`
(Agora, TensorFlow Lite, OpenCV, anything WebRTC-derived), and `noCompress` for
`.tflite` assets.

**The recommendation here is not a producer declaration.** No producer can know
what it will be composed with. This is better stated as a **consumer
obligation**: detect the collision, resolve it by a defined rule, and report it
in the record of §9 — so a broken combination is attributable rather than
mysterious.

### N15 — the `-ObjC` linker flag and system framework linkage

§11 excludes linker flags but invites revisiting "with a concrete, bounded
need." `-ObjC` is one: Meta's SDK, Braintree and most ad adapters vend
Objective-C categories in static libraries that are silently dropped without
it, producing `unrecognized selector` crashes at runtime. SwiftPM packages
declare their own `linkerSettings`, which covers §7.4 and shrinks the residual
to §7.5 raw source and binary XCFrameworks. If it is admitted at all it should
be a closed vocabulary — an `objc_load_all_categories` boolean plus named
system frameworks — never a free-text flag list.

## Tier C — vocabulary and channel coverage

### N16 — CocoaPods-only SDKs have no channel, and no exclusion either

§7.4 is SwiftPM-only, and §11 does not mention CocoaPods at all. Google's ML
Kit for iOS remains CocoaPods-only, as do a long tail of ad adapters and
regional SDKs. The trend supports the specification's choice — Firebase stops
publishing to CocoaPods in October 2026 — but silence is the wrong way to make
a deliberate decision. §11 should carry the row, saying that a CocoaPods-only
SDK is out of reach and what a producer's options are: a vendor-published SwiftPM
distribution, or a wrapper package the producer publishes and declares under
§7.4.

### N17 — `app_extensions`, and entitlement values

The `kind` vocabulary has two entries. Four more have live demand:
`notification_content` (rich push UI — OneSignal, Braze, Airship, CleverTap),
`broadcast_upload` (screen sharing — Agora, Twilio, LiveKit, Zoom; confirmed
against Agora's own instructions, including its `NSExtensionPrincipalClass`
substitution), `widget` for push-to-start Live Activities, and `share`.

Alongside it, the survey repeatedly hits the limitation §7.3 accepted
knowingly — that an entitlement's **value** is unmodelled.
`com.apple.security.application-groups` must carry the same group identifier in
the application and the extension (OneSignal, Braze);
`com.apple.developer.associated-domains` carries vendor-specific domains
(Branch, AppsFlyer, Adjust, and passkeys' `webcredentials:`);
`com.apple.developer.in-app-payments` carries merchant identifiers (Stripe,
Braintree, Adyen). The decision to leave the value in `reason` was defended on
the ground that a consumer can neither write nor check it. That holds — but a
marker saying *this entitlement takes a value the application must supply*
would at least let a consumer ask, rather than leaving it to prose.

### N18 — permission attributes

§6.7 models a permission as `name` + `reason`. Two attributes change what the
declaration *means*:

- **`android:maxSdkVersion`** — `WRITE_EXTERNAL_STORAGE` (≤28), legacy
  `BLUETOOTH`/`BLUETOOTH_ADMIN` (≤30), `ACCESS_COARSE_LOCATION` on BLE stacks
  (≤30). Without it a producer over-asks on every modern device.
- **`android:usesPermissionFlags="neverForLocation"`** — the assertion that
  `BLUETOOTH_SCAN` will not be used to derive location. It is both a Play
  policy matter and the difference between requesting Bluetooth and requesting
  the user's location.

Both are minimization, which is what §6.7 is *for*. Two optional fields.

### N19 — verified App Links

§6.8 already records `android:autoVerify` as not expressible, on the ground
that `assetlinks.json` is application infrastructure. The survey shows the
demand is not marginal — Branch, AppsFlyer OneLink, Adjust and passkeys all
need it. The `assetlinks.json` argument points at the answer: this is a
**prerequisite**, not a contribution, and it is the Android twin of iOS
associated domains (N17). The application owns the domain; the producer can
only say a verified link is needed, and why.

### N20 — a class the *application* must own

WeChat requires an exported `${applicationId}.wxapi.WXEntryActivity`, in the
application's own namespace, with `singleTask` and a matching `taskAffinity`.
Health Connect requires an application-owned permissions-rationale activity and
an activity-alias guarded by `android.permission.START_VIEW_PERMISSION_USAGE`.

§6.1 rightly forbids a producer writing outside its own namespace, and nothing
should change there. What is missing is the `requires` form: *the application
must provide a class at this path, doing this.* Without it the only honest
option is a README — which is the transcription problem this specification
exists to end.

## Tier D — a claim SPEC.md makes that the survey contradicts

### N21 — build-time execution is three categories, not two

§11 says an SDK whose build step is excluded "can be *linked* through §6.5 or
§7.4 and the result will build", then splits the consequences two ways: the SDK
**degrades** (Sentry) or the SDK **fails** (Crashlytics). Three SDKs in this
survey fit neither, because their build step is **code transformation, not
upload**:

- **Embrace** applies `embrace-swazzler`, which instruments bytecode to insert
  the SDK's hooks.
- **New Relic Mobile** instruments bytecode at build time for its interaction
  traces.
- **Realm Kotlin** ships a **Kotlin compiler plugin**; without it, model
  classes never acquire their generated members.

For these, "linked without the plugin" does not produce a degraded integration.
It produces a build that succeeds and an SDK that is inert, or code that does
not compile at all. §11's own instruction — that a producer "should work out
which case it is in" — needs a third row: **the SDK cannot be integrated**, and
no wrapper should be published. The exclusion itself is untouched; the taxonomy
under it is incomplete.

## What the survey confirms

Findings are more legible against what did not move.

- **§6.6 is well-founded and heavily exercised.** Private Maven repositories
  turn up across ad adapters, support SDKs and regional vendors, several of
  them credentialed. Nothing in the survey strains the bounded-participation
  rule.
- **§6.5's lock-and-checksum model needs no change.** Not one vendor asks for
  something the two declaration forms cannot spell.
- **The §11 build-time-upload exclusion holds**, and gains members: Datadog,
  Instabug and Bugsnag all sit in the category, and Sentry's "degrades" reading
  is confirmed by three more.
- **§6.7's suppression capability earns its keep.**
  `com.google.android.gms.permission.AD_ID` is exactly the permission a
  children's-category application must remove, and §6.7 is the only mechanism
  in the design that lets it.
- **Platform frameworks need almost nothing.** StoreKit, Play Billing,
  ARKit/ARCore, CallKit and CameraX are reachable with a permission, a
  background mode and a floor. The most-installed SDK on iOS asks the least of
  this specification.
- **§2.2's join-key model absorbed every new prerequisite shape** the survey
  produced. Where something was inexpressible it was always a missing *table*,
  never a missing way for the application to answer.

## Since this survey

**Six corrections have landed in SPEC.md** — the batch that fixes something
wrong rather than adding capability: `provider` left §6.8's vocabulary (it
cannot carry a device-unique authority a producer could know), §7.6 gained the
application-wins rule §6.3 always had, §11 gained a third build-time outcome
for instrumentation SDKs and two new exclusion rows (arbitrary fragments,
CocoaPods-only vendors), and §7.6's dictionary paragraph now names
`SKAdNetworkItems` as the counter-case it has rather than implying none exists.

**Four sidecars were then written** against the findings with the most at stake
— [Meta](examples/pyfacebook/), [Airship](examples/pyairship/),
[Agora](examples/pyagora/) and [Health Connect](examples/pyhealthconnect/) —
before any of the remaining findings is allowed to change the specification.
Three of the four changed the finding they were testing (N5 and N6 above), and
two findings appeared that no amount of reading documentation produced:

- **FB3** — `from_dependency` may only name a dependency the sidecar declares
  itself, but SDK families put the class in a transitive module. Meta's
  `CustomTabActivity` lives in `facebook-common`, arriving under
  `facebook-login`, so the sidecar must declare the internal module purely to
  have something to point at.
- **FB4** — an application value cannot be **derived** from another. Meta's
  login scheme is the app ID with `fb` prepended, so the application answers the
  same fact twice with nothing checking that the two agree.

Both are warts with workarounds rather than blockers, and both are the kind of
finding that only exists once someone writes the entry — which is the argument
for not landing the seven new tables on survey evidence alone.

## Suggested disposition

Ordered by evidence weight, not by implementation cost. Sizes are estimates.

| Finding | Shape | Size | Vendors |
| --- | --- | --- | --- |
| **N1** iOS application values | new `[[ios.requires.application_values]]` | medium | 5 |
| **N2** SKAdNetwork ids | one narrow contribution key | small | 6 |
| **N7** fixed `meta-data` | new contribution table (P3's deferred half) | medium | 6 |
| **N5** component attributes | fields on §6.8; **`provider` is a defect** | medium | 4 |
| **N3** privacy manifests | contribution + prerequisite pair | large | many |
| **N4** Android `requires` family | structural: `application_files` + N9 + N20 | large | 5 |
| **N9** required resources | new `requires` table | medium | 6 |
| **N10** host-activity contract | new `requires` key | medium | **1** |
| **N8** manifest placeholders | one optional field on §6.3 | **small** | 2 |
| **N18** permission attributes | two optional fields on §6.7 | **small** | 3 |
| **N6** `<queries>` | new contribution table | small | 5 |
| **N17** extension kinds | extend a closed vocabulary | small | 6 |
| **N12** desugaring | one boolean under `[android.requires]` | **small** | 2 |
| **N11** toolchain floors | fields under both `requires` tables | small | 3 |
| **N21** §11 taxonomy | documentation only | **small** | 3 |
| **N16** CocoaPods | one §11 row, documentation only | **small** | 2 |
| **N19** verified App Links | prerequisite form | medium | 4 |
| **N13** configurations | extend §6.5's `configuration` | small | — |
| **N15** `-ObjC` | closed vocabulary; revisit §11 | medium | 3 |
| **N14** packaging collisions | **consumer obligation**, not a declaration | medium | 3 |
| **N20** application-owned class | prerequisite form | medium | 2 |

Six of these are single-field or documentation-only changes with multi-vendor
evidence behind them — N8, N18, N12, N2, N21, N16 — and three of those correct
something SPEC.md currently gets wrong rather than adding capability.
