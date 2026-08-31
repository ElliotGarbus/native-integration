# How the specification was tested

Eighteen integrations expressed as `native.toml` sidecars while the
specification was being written, with the gaps recorded beside each. The purpose
was to find out whether version 1 had the right primitives **before** a consumer
implemented it.

This is the working record. The curated example a reader should start from is
[`examples/pystripe/`](../examples/pystripe/), which carries both halves of one
integration; everything here is the evidence behind the decisions, not a
tutorial.

Four are existing packages from
[PyPlatformPackages](https://github.com/PyPlatformPackages). The other fourteen
are clean-sheet, written against the documentation of vendors who have never
heard of this convention.

| Example | Chosen to stress | Outcome |
| --- | --- | --- |
| [PyOneSignal](examples/pyonesignal/) | capabilities and components | **blocked** — no initialization surface, no app extensions |
| [PyCoreLocation](examples/pycorelocation/) | native Swift, permissions, privacy | **blocked** — no module registration; usage descriptions in the wrong category |
| [PyWebViews](examples/pywebviews/) | substantial package-owned Swift | **blocked** — not a Python distribution at all |
| [PyGMA](examples/pygma/) | cross-platform third-party SDK | **clean** on Android; iOS unimplemented upstream |
| [Firebase](examples/firebase/) | a vendor outside this ecosystem | **blocked** — build plugins, build scripts, service intent filters |
| [Sentry](examples/pysentry/) | a check on §11's build-script exclusion | **mostly clean** — and the first live use of §6.3 |
| [Stripe](../examples/pystripe/) | `view_links`, and a financial SDK's demands | **clean on Android**; iOS has no browser-return form. **The only worked pair** — see `app-pyproject.toml` beside the sidecar |
| [Mapbox](examples/pymapbox/) | §6.6, the only table with no coverage | **§6.6 holds** — but cannot express the repository's credential |
| [Meta SDK](examples/pyfacebook/) | round five: iOS application values | **Android clean; iOS blocked** — three account keys with no declaration form |
| [Airship](examples/pyairship/) | round five: Android configuration | **iOS clean; Android blocked twice** — one fact, two unstateable paths |
| [Agora](examples/pyagora/) | round five: real-time media | **calls clean; screen share blocked** on both platforms |
| [Health Connect](examples/pyhealthconnect/) | round five: an app-owned class | **blocked** — device detection and a Play-required rationale activity |
| [Mediated ads](examples/mediated-ads/) ×3 | round six: **composition** — three packages at once, **with the application's half** | **clean** — two predicted stresses did not materialize; the app file corrected §2.2's join |
| [TensorFlow Lite](examples/pytflite/) | round six: composition — **a native collision** with Agora | **§9.1's first evidence**; a new gap in packaging *options*; iOS out of reach |

The first four are existing packages from one toolchain lineage. Firebase,
Sentry, Stripe and Mapbox — the second round — are **clean-sheet**: sidecars
written against each vendor's own documentation, for vendors that have never
heard of this convention, and run after the corrections and decisions below had
landed.

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

Running `python3 tools/check_spec.py` from the repository root validates every
sidecar here against the specification — and the specification against itself.
It runs in CI on every push and pull request.

Proposed remedies live in [PROPOSALS.md](PROPOSALS.md). Gap identifiers are
per-example: `A*`/`B*`/`C*` (PyOneSignal), `L*` (PyCoreLocation), `W*`
(PyWebViews), `G*` (PyGMA), `F*` (Firebase), `S*` (Sentry), `T*` (Stripe), `M*`
(Mapbox). Round five uses two letters, the single ones being taken: `FB*`
(Meta), `AS*` (Airship), `AG*` (Agora), `HC*` (Health Connect). Round six is
`MA*` (mediated ads) and `TF*` (TensorFlow Lite).

[SURVEY.md](SURVEY.md) is the other kind of evidence: forty further SDKs read
for what they ask of a build, with `N*` identifiers for what this specification
cannot say. Depth found the refusals above; breadth found the missing tables.

**Round five is where the two meet.** The four sidecars above were written to
put depth behind the survey's most consequential findings before any of them was
allowed to change first-attempt.md — and three of the four changed the finding they were
testing. FB2 narrowed N6 (an `.aar` merges its own `<queries>`), AG1 removed
the hedge from N5 (a capture service is the producer's to declare, so the gap is
not narrow), and HC2 showed §6.8's single-action stereotype does not generalize
the way its rationale assumes. Two findings — FB3 and FB4 — appear in no survey
at all, because they only surface when you try to write the entry.

### What round five closed, and what it did not

The survey's twenty-one findings resolved as sixteen landed, four closed — the
proposed shape declined and a different change made instead — and one deferred
with a stated trigger. Against the four sidecars specifically:

| Finding | Now |
| --- | --- |
| FB1 — three account keys with no declaration form | **closed**: §7.3's `application_values`, the table §6.3 predicted |
| AS1, AS2 — Airship configurable by neither path | **closed**: §6.10's `meta_data` and §6.11's `application_files` |
| AS3 — the notification icon | **closed**: §6.11's `resources`, which §6.10 may point at |
| AS4, AG2 — rich push and screen-share extensions | **closed**: `app_extensions.kind` is an open vocabulary |
| HC1 — device detection | **closed**: §6.12's `queries` |
| HC2 — an application-owned class | **closed in part**: §6.11's `application_classes`; the activity-alias and its `android:permission` are not |
| AG3 — `libc++_shared.so` twice | **closed**: §9.1, as a consumer obligation |
| FB6 — `-ObjC` | **closed**: §7.8, §11's one bounded exception |
| AG1 — the capture service's `foregroundServiceType` | **closed**: §6.8's `foreground_service_type`, with 8.S4 on the permission half |
| FB5 — tracking domains | **deferred**, with a trigger |
| FB3 — `from_dependency` cannot name a transitive module | **open** |
| FB4 — an application value cannot be derived from another | **open**, recorded as a wart with a workaround |

Three of the four sidecars would now express what they could not, and the
`native.toml` files under [`examples/`](examples/) are **not** rewritten to use
the new tables: each records the integration as it was attempted, which is what
makes the gap list evidence rather than illustration.

**Round six is the first composition.** Every sidecar before it is one producer
as a direct dependency, which leaves the rules whose whole justification is
cross-distribution evidenced only by unit tests written beside the rules they
test. [Mediated ads](examples/mediated-ads/) is three packages at once because a
real ads integration holds three to six, so the overlaps are ordinary rather
than contrived — and the reader composes all three in
`tests/test_examples.py`, which is what makes the set evidence rather than
illustration.

[TensorFlow Lite](examples/pytflite/) is the second half of that round, written
to be composed with `pyagora` rather than read alone: both bundle a C++ runtime,
which is the collision §9.1 was landed for and which mediated ads could not
reach. It is also the first example to land on §11's new CocoaPods row, and it
found a gap next door to §9.1 — a packaging *option*, `noCompress`, that one
artifact needs and no rule reaches.

Mediated ads came out **clean**, and two of the three stresses it was chosen for turned
out to be structurally impossible: adapters cannot contest repository scopes,
because each vendor's repository serves that vendor's own group, and they cannot
duplicate an application value, because each needs its own vendor's key. Both
are arguments *for* the rules as written, arrived at by trying rather than by
asserting. What it did not reach — packaging collisions, the permission
attribute merge, namespace exclusivity — is recorded at the end of its NOTES so
the next composition is chosen against the gap.

> **Reading these after the fact.** Each `NOTES.md` describes first-attempt.md **as it
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

*Written after round one, and left standing — several of these have since been
answered, and the record is more useful showing where the text stood than
edited to agree with the text now. §7.7 answers the module-registration half;
§7.3's application values, §6.10 and §6.11 answer most of the "where a value
lives" half; startup hooks remain deferred.*

The iOS half is where version 1 runs out, and the failures are structural rather
than incidental.

**Three of the four round-one packages could not be expressed without changing
the package.** PyOneSignal must delete its `Application` subclass and initialize
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

It expressed one of four naturally. The other three each required either a
change to the package or a capability that did not exist.

**Round two answers a stronger version of the same question**, because those
four packages shared one toolchain lineage and could plausibly have been fitting
a spec written with them in view. Six clean-sheet sidecars for Firebase, Sentry,
Stripe and Mapbox — vendors with no knowledge of this convention — came out at
roughly the same rate, from an entirely independent direction.

More useful than the rate: **the hardest failures turned out to be correct
refusals.** Firebase's Gradle plugin and Crashlytics' dSYM upload are
unreachable because §2.1 declines build-time execution, not because anything is
missing. That is a different and much better position than "we have not got to
it yet", and it is only visible once you try.

Round two also caught two claims this document had made too strongly — that
build-script SDKs were one uniform category, and that application values had no
live use — which is the argument for running examples rather than reasoning
about them.

The encouraging reading is that the **shape** held: nothing found here suggests
`owns` / `requires` / `contributes` is the wrong decomposition, no finding
required an executable hook or a build-system escape hatch, and the additions
proposed are a small number of narrow primitives rather than a different design.
Several rules that looked over-cautious on paper turned out to be load-bearing.

The discouraging reading is that version 1 was drafted around the Android
pyjnius shape, and the iOS Swift-module shape — which is what most of this
organization actually ships — is largely unaddressed.

**Round five reversed that second reading, and produced a new one.** Breadth
found that the Android half had the structural hole: iOS had six prerequisite
tables and Android had none, which is why §6.11 exists. What the two readings
share is their cause — each round found the gaps on whichever platform the
previous round's examples had not stressed, which is an argument about
*selection* rather than about either platform. The next round should be chosen
against that, not against a hunch.

## Building against the specification

Everything above tested the specification by *writing* against it. Testing it by
*implementing* it came after, in phases, and each one recorded what it found the
same way an example's `NOTES.md` does — because a phase that ends green says
nothing about what it cost to get there.

| | |
| --- | --- |
| [`findings/phase0-inventory.md`](findings/phase0-inventory.md) | what the repository actually contained, and the nine defects that audit found |
| [`findings/phase1-registry.md`](findings/phase1-registry.md) | `contract/v1.toml` — the vocabulary as data, and the three artifacts generated from it |
| [`findings/phase2-corpus.md`](findings/phase2-corpus.md) | the conformance corpus, its harness, and the cases that were green for the wrong reason |
| [`findings/phase3-reader.md`](findings/phase3-reader.md) | the reader rewritten against SPEC.md, and the six assertions it cannot verify because it generates nothing |
