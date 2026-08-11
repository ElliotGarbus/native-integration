# Worked examples

Four real packages from [PyPlatformPackages](https://github.com/PyPlatformPackages),
each expressed as a `native.toml` under contract 1, with the gaps recorded
beside it. The purpose is to find out whether version 1 has the right
primitives **before** a consumer implements it.

| Example | Chosen to stress | Outcome |
| --- | --- | --- |
| [PyOneSignal](pyonesignal/) | capabilities and components | **blocked** — no initialization surface, no app extensions |
| [PyCoreLocation](pycorelocation/) | native Swift, permissions, privacy | **blocked** — no module registration; usage descriptions in the wrong category |
| [PyWebViews](pywebviews/) | substantial package-owned Swift | **blocked** — not a Python distribution at all |
| [PyGMA](pygma/) | cross-platform third-party SDK | **clean** on Android; iOS unimplemented upstream |
| [Firebase](firebase/) | a vendor outside this ecosystem | **blocked** — build plugins, build scripts, service intent filters |
| [Sentry](pysentry/) | a check on §11's build-script exclusion | **mostly clean** — and the first live use of §6.3 |
| [Stripe](pystripe/) | `view_links`, and a financial SDK's demands | **clean on Android**; iOS has no browser-return form |
| [Mapbox](pymapbox/) | §6.6, the only table with no coverage | **§6.6 holds** — but cannot express the repository's credential |

The first four are existing packages from one toolchain lineage. Firebase,
Sentry, Stripe and Mapbox are **clean-sheet**: sidecars written against each
vendor's own documentation, for vendors that have never heard of this
convention, and run after the corrections and decisions below had landed.

They were also chosen differently. Firebase asked the open question — can this
express an SDK nobody here designed around? The last three test **specific
claims**:

- **Sentry** — §11's assertion that build-script SDKs are one excluded
  category. It half held: Sentry's plugin is optional where Crashlytics' is
  load-bearing, so §11 now distinguishes SDKs that degrade from those that
  fail. Sentry also produced the **first live use of §6.3** anywhere in the set,
  validating a table two earlier decisions had nearly orphaned.
- **Stripe** — §6.8's `view_links`, which nothing had exercised. It fits, and
  the export gate reads better under a payment SDK than under the hypothetical
  OAuth case it was designed for.
- **Mapbox** — chosen from a **coverage audit** rather than a hunch. After nine
  sidecars, §6.6 was the only declarable table nothing had used, and it carries
  the strongest safety language in the specification.

Proposed remedies live in [PROPOSALS.md](../PROPOSALS.md). Gap identifiers are
per-example: `A*`/`B*`/`C*` (PyOneSignal), `L*` (PyCoreLocation), `W*`
(PyWebViews), `G*` (PyGMA), `F*` (Firebase), `S*` (Sentry), `T*` (Stripe), `M*` (Mapbox).

> **Reading these after the fact.** Each `NOTES.md` describes SPEC.md **as it
> stood when that example was run**. For the four PyPlatformPackages examples
> that is the text before the corrections group landed, so several findings
> recorded there as defects — §7.6's usage-description example, §6.5's range
> ban, §7.4's ungoverned transitive graph, the undefined containment rules —
> are fixed in the current text. Where a later example overturned an earlier
> conclusion, the correction is added **in place** rather than edited away.
> The `native.toml` files **are** kept current and valid against the
> specification as it is now. PROPOSALS.md marks what landed and what did not.

## What held up

The **Android half of contract 1 is in good shape.** PyGMA exercises it end to
end — `owns`, floors, `src`, dependencies, permissions, and both shrinker scopes
— with no workaround, and several contested rules earned their place on
evidence:

- **§6.9's two keep scopes** are both needed, in one declaration, by one package.
- **§6.7's canonical permission names** are vindicated by
  `com.google.android.gms.permission.AD_ID` arriving in the same integration.
- **§6.1 rule 5** caught a latent bug: every KivySchool package would claim
  `com.kivyschool.android`, and the second to ship would collide.
- **§7.3's "never write an entitlement"** is vindicated by
  `com.apple.developer.location.push`, which requires approval from Apple —
  a gap between "declared" and "grantable" measured in weeks.
- **§7.5's "SHOULD NOT be used for a library"** is confirmed by artifact: both
  Swift packages reached for §7.4 unprompted, and PyWebViews' file-scope
  globals and `extension Double` show exactly what §7.5 would have broken.

## What did not

The iOS half is where version 1 runs out, and the failures are structural rather
than incidental.

**Three of the four packages could not be expressed without changing the
package.** PyOneSignal must delete its `Application` subclass and initialize
late from Python — a silent runtime behaviour change, not an omitted
convenience. PyCoreLocation and PyWebViews cannot register the Swift-implemented
Python module that *is* their implementation, so the build succeeds and `import`
fails.

**The organization's iOS architecture is not expressible.** PyCoreLocation,
PyWebViews, PyPHPicker, PyCamera, PyCoreBluetooth, PyCoreMidi, PyTextToSpeech
and PySpeechRecognizer are all SwiftPM packages that *are* Python extension
modules, statically compiled into the app target and registered into the
interpreter. Contract 1 has no way to say that, and §11 currently implies the
case is covered by PEP 730/738 wheels when it is not.

**Two distinct missing ideas** account for nearly all of it:

1. *Where a package plugs in* — initialization hooks, module registration,
   additional build targets, contributed manifest entries. Version 1 models what
   a package **brings**, not where it **attaches**.
2. *Who owns a value* — usage descriptions and purpose strings are
   application-authored text that §7.6 currently lets producers write.

## Findings that make the current text wrong

Distinct from missing capability — these are places the specification
contradicts itself, instructs producers to do the wrong thing, or leaves a
load-bearing rule undefined:

| Finding | Where |
| --- | --- |
| §7.6's own example has a library writing App Store review text | L3 |
| §6.5 forbids version ranges that §7.4 permits, under the same lock | A1 |
| §7.4 leaves the transitive Swift graph ungoverned; §6.5 governs Gradle's | L1, W5 |
| "Overlapping namespace" and "reserved prefix" never defined as string vs. segment | G3 |
| No rule covers native resolution *failing* — and 8.15 is unmeetable there | W3 |
| §6.3's flagship example is the legacy SDK's mechanism; the real package needs none | G1 |
| The Python distribution as carrier is assumed, never stated | W1 |

## The sharpest single case

PyWebViews depends on PySwiftKit `311.x`; PyCoreLocation on `313.x`. In this
ecosystem a Swift package's **major version encodes the CPython ABI** — 311 is
Python 3.11. An application depending on both cannot resolve, which is correct;
but the failure surfaces as a SwiftPM resolver error about `PySwiftKit`, with
nothing linking it back to either Python distribution. Requirement 8.15 — *"Name
the contributing distribution in every diagnostic"* — cannot be satisfied,
because the diagnostic is not the consumer's to write.

## Answering the question the exercise asked

> If the current spec expresses all four naturally, that's strong evidence that
> v1 has the right primitives.

It expresses one of four naturally. The other three each required either a
change to the package or a capability that does not exist.

The encouraging reading is that the **shape** held: nothing found here suggests
`owns` / `requires` / `contributes` is the wrong decomposition, no finding
required an executable hook or a build-system escape hatch, and the additions
proposed are a small number of narrow primitives rather than a different design.
Several rules that looked over-cautious on paper turned out to be load-bearing.

The discouraging reading is that version 1 was drafted around the Android
pyjnius shape, and the iOS Swift-module shape — which is what most of this
organization actually ships — is largely unaddressed.
