# PyGMA against contract 1

Source: [PyPlatformPackages/PyGMA](https://github.com/PyPlatformPackages/PyGMA)
— a pyjnius wrapper for the Google Mobile Ads **Next-Gen** SDK
(`com.google.android.libraries.ads.mobile.sdk`, not the legacy
`play-services-ads`).

This was the cross-platform third-party-SDK case, expected to stress §6.3 and
Android/iOS symmetry. It is the cleanest Android fit of the four — and both of
its findings are about things that turned out **not** to be needed.

## What fits, with no workaround

PyGMA is the first example to exercise the Android half end to end:

| Requirement | Mechanism |
| --- | --- |
| `package PyGMA;` across 7 Java files | §6.1 `owns.java_namespaces` + §6.4 `src.java` |
| minSdk 24 / compileSdk 34 | §6.2 floors |
| `…:ads-mobile-sdk:1.2.1` | §6.5, already exactly versioned upstream |
| `INTERNET`, `ACCESS_NETWORK_STATE` | §6.7 |
| Reflective reach into owned classes **and** the SDK's | §6.9, both scopes |

Two things are worth calling out as the specification working rather than merely
not breaking:

**§6.9's two scopes are both genuinely needed, in one declaration.**
`listener.py` implements the package's own `PyGMA/PyGMAListener` from Python via
`PythonJavaClass`, so the interface is reached only reflectively — scope 1. The
Java then reaches `com.google.android.libraries.ads.mobile.sdk.*` — scope 2, the
group of a coordinate the same sidecar declares. No earlier example used both.

**§6.5's exact-version rule costs nothing here.** PyGMA already pins `1.2.1`.
That is a useful counterweight to PyOneSignal, where the vendor documents a
range: P5's friction is real but not universal, and the exact form is what a
producer writes when left alone.

## G1 — §6.3's flagship example is obsolete for this package

§6.3 illustrates application-supplied values with exactly this SDK:

```toml
[[android.requires.application_values]]
name = "com.google.android.gms.ads.APPLICATION_ID"
reason = "Your AdMob application ID, from the AdMob console"
```

That is the **legacy** Mobile Ads SDK's mechanism, where a missing manifest
`<meta-data>` entry crashes the app at startup. The Next-Gen SDK PyGMA wraps
takes the app ID programmatically:

```java
MobileAds.initialize(activity,
    new InitializationConfig.Builder(appId).build(), …);
```

and PyGMA passes it from Python — `GMAManager.initialize(app_id)`. **Nothing
needs to reach the manifest**, so the sidecar declares no application values at
all.

**This matters beyond one example.** After four packages, `application_values`
has **zero live use cases**:

- PyGMA: app ID is a runtime argument by SDK design.
- PyOneSignal: app ID is a runtime argument too, once the `Application`
  subclass is dropped (which contract 1 forces anyway — see A2).
- PyCoreLocation, PyWebViews: nothing of the kind.

The only surviving consumer of the mechanism in the whole specification is
§6.8's **inline** form, where `view_links` substitutes a redirect scheme into a
generated intent filter.

**The distinction the specification should draw**, and currently blurs: §6.3 is
for values the **build** must embed — manifest placeholders, intent filters,
things baked into generated XML that no runtime call can supply. Values an SDK
accepts at runtime belong in the application's own Python code, and a producer
should not route them through build configuration merely because it can.

That sharpening makes §6.3 smaller and better justified. It also means **P2 —
promoting application values to a platform-neutral table — has lost its
motivating case** and should be reduced to the §6.3 correction it already
contains. See PROPOSALS.md.

## G3 — "overlapping" and "prefix" are undefined *(specification defect)*

PyGMA owns the single-label namespace `PyGMA`. That is legal under §6.1 and
makes a latent ambiguity concrete.

§6.1 rule 5: *"Two distributions claiming overlapping namespaces MUST fail."*
Rule 4: *"An owned namespace under a **reserved prefix** MUST be rejected."*
§6.9 scope 2: a keep pattern must fall within *"the **group** of a Gradle
coordinate."*

All three are containment tests, and the specification never says whether
containment is computed on **strings** or on **dot-separated segments**. The
difference is not theoretical:

| Naive string prefix | Correct segment containment |
| --- | --- |
| `PyGMA` "contains" `PyGMAKit` | siblings — unrelated packages |
| `org.kivy.android` "contains" `org.kivy.androidx` | siblings — the reserved-prefix rule false-positives |
| group `com.google.android.libraries.ads` "contains" `…adsx` | siblings — a keep pattern wrongly accepted or rejected |

A string-prefix implementation produces both false collisions (blocking a
legitimate distribution) and, in the §6.9 case, false acceptances. PyGMA's
single-label claim makes the first column likely rather than exotic: any future
`PyGMAKit` or `PyGMAExtras` collides with it under a naive check.

**Fix:** state that a namespace *A* contains *B* when *B* equals *A* or begins
with *A* followed by a dot, and apply the same rule to the reserved-prefix list
and to §6.9's group check. One sentence, and it removes the most likely
implementation divergence in §6.

This is the kind of defect the exercise was meant to surface: not a missing
capability, but a rule that two conforming implementations would read
differently.

## G5 — the most important disclosure in this example is the one §9 only SHOULDs

The sidecar declares `INTERNET` and `ACCESS_NETWORK_STATE`. The GMA AAR's own
manifest merges in more, and the notable one is
**`com.google.android.gms.permission.AD_ID`** — the Android 13+ advertising ID
permission, which carries Play Console **Data Safety** declaration obligations
and is exactly the kind of thing an application author needs to know arrived.

It is declared by no sidecar. It arrives through AGP manifest merging from a
resolved coordinate, which §9 addresses:

> A consumer **SHOULD** include in the record and report the permissions and
> components the effective merged manifest contains beyond those declared by
> sidecars and the application…

**SHOULD.** So the single most consequential contribution in this integration —
a privacy-relevant permission, reaching the application through a transitive
Python dependency, with regulatory paperwork attached — is the one thing a
conforming consumer may omit, provided it documents the omission.

This is worth revisiting. The argument for SHOULD is implementation cost:
computing the effective merged manifest means running or emulating AGP's merger.
That is real. But §9's own framing — *"The middle element matters most for the
case that motivates the requirement — a transitive dependency the application
author has never heard of"* — describes this case precisely, and then makes the
coverage optional.

At minimum the specification should say that a consumer omitting effective-delta
reporting has not covered the motivating case, in stronger terms than the
current "the record's coverage is the declarations, not the full effective
manifest."

**A related vindication.** §6.7 requires canonical permission names
(`android.permission.INTERNET`, not `INTERNET`) specifically so that vendor
permissions need no extra rule. `com.google.android.gms.permission.AD_ID` is
that case, arriving in the same integration. The existing ecosystem uses the
shorthand form — PyGMA's `pyproject.toml` declares `permissions = ["INTERNET",
"ACCESS_NETWORK_STATE"]` — so migration costs a mechanical rewrite, and the
specification's choice is right.

## G2 — a second data point for P6

`package PyGMA;`, reached as `autoclass("PyGMA.PyGMAManager")`. A single-label
Java package is legal and ownable but a poor claim, and it is what makes G3
live. Confirms P6's proposed **SHOULD** for reverse-DNS namespaces, and argues
for pairing it with a consumer **SHOULD**-warn on single-label claims.

## G4 — "cross-platform" that builds and does nothing

PyGMA's own description is *"Cross-platform wrapper for Google Mobile Ads."* Its
`platform_detection.py` returns `"ios"`, and `manager.py` has an iOS branch:

```python
elif platform == "ios":
    # from .ios.manager import IOSGMAManager
    # IOSGMAManager.initialize(app_id)
    pass
```

There is no iOS implementation. Under §5 an absent platform table is valid and
contributes nothing, so an application depending on PyGMA and building for iOS
gets a successful build, no diagnostic, and an app that silently shows no ads —
`initialize()` reaches `pass`.

This is L6 from PyCoreLocation, in a sharper form: PyCoreLocation never claimed
to support Android, while PyGMA claims cross-platform support it does not have.
Second independent example for **P11** (`platforms = ["android"]`), and an
argument that the declaration should be about what the *sidecar* supports rather
than what the package aspires to — a producer that adds iOS later adds the
table and the platform in the same release.

## G6 — the reserved-prefix list is a de-facto API, not only a hazard

`bridge.py` reads:

```python
activity_env = os.environ.get("APP_ACTIVITY", "org.kivy.android.PythonActivity")
```

§6.1 rule 4 reserves `org.kivy.android` so that no distribution can *contribute*
into it. Correct. But producers still **read** from it: the bootstrap class is
the integration point between a pyjnius package and whatever built the app, and
portability across consumers here rests on an environment variable that this
specification does not mention and does not govern.

No change proposed — this is runtime behaviour, outside the declaration surface.
It is worth recording that the reserved namespaces are not merely dangerous
ground; they are the informal API these packages already depend on, which is a
further argument for rule 4 rather than against it.

## Verdict

PyGMA is the result the exercise wanted from at least one case: the Android half
of contract 1 expresses a real third-party SDK integration completely, and two
of its more contested rules — §6.9's dual scopes and §6.7's canonical names —
are validated by concrete need rather than by argument.

The findings are correspondingly narrow, and two of them shrink the proposal set
rather than growing it:

- **G1 removes P2's motivating case.** Application values have no live use
  outside §6.8's inline form. §6.3 should be sharpened to build-time values and
  left where it is.
- **G3 is a genuine specification defect** — three containment rules with
  undefined semantics — and is the cheapest fix in the whole set.
- **G5 questions a SHOULD** that covers the case §9 says matters most.
- **G2 and G4** are second examples for P6 and P11.

Nothing here needed a workaround, and nothing here was inexpressible.
