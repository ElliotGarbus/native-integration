# The conformance corpus

Cases a consuming tool is run against, so that "conforming" means something
checkable rather than claimed.

## Precedence

**Where a fixture and the specification disagree, [SPEC.md](../SPEC.md) wins and
the fixture is a defect.** File it as one.

This is stated first because the alternative is how a corpus quietly becomes the
contract: a fixture asserts something the specification never said, two
implementations are held to it, and the specification is the thing that gets
edited to match. Nothing here is normative. The corpus is evidence about
conformance, not a source of it.

## Fixtures are authored from the specification, never from a run

**No `expected/` file in this corpus was produced by executing an
implementation**, and none may be. If an expected output cannot be derived from
the specification's text alone, that is an ambiguity finding — record it under
[`development/findings/`](../development/findings/) with its section anchors and
stop.

The reason is the whole point of the exercise. A corpus derived from consumer #1
cannot establish that consumer #2 agrees with the specification; it establishes
only that consumer #2 agrees with consumer #1. Two consumers reading one sidecar
and agreeing is the bar [the README](../README.md#before-a-freeze) sets before a
freeze, and a corpus that bakes in one implementation cannot measure it.

## Layout

```
conformance/
  record-format.md          the normalized output two consumers are compared on
  run.py                    the harness
  core/                     requirements every consumer implements (§8.1)
  android/
  ios/
    <Rnn>_<slug>/
      case.toml             what this case asserts
      input/                the sidecars, and the application's answers
      expected/             the conformance record, and a diagnostics note
```

### A core case runs for every platform the consumer builds

[§8.1](../SPEC.md#81-conformance-is-per-platform) makes conformance "the core
plus at least one platform profile", so a **core** requirement binds a consumer
whichever platform it builds. A corpus that exercised the core only against
Android could not establish a `core + ios` claim at all — the Android cases
would never run, and the core ones would hand an iOS-only consumer a closure it
does not build for.

So a core case ships one input tree per platform:

```
core/R12_floor_unmet/
  input/android/    min_sdk 31 against an application configured for 26
  input/ios/        deployment_target 18.0 against 16.0
```

`run.py` runs it once per selected **platform** profile, and prints which:

```
FAIL   core/R12_floor_unmet [ios]   (requirement 12)
```

The platform profiles you select are what decides. `--profile ios` runs the core
cases for iOS only; naming no platform profile runs both and says that this is a
development run rather than a claim. An Android or iOS case ships a single flat
`input/`, since it has only one platform to begin with.

**A platform profile brings the core with it.** Conformance is the core plus at
least one platform profile, so `--profile android` runs both and `--profile
core --profile android` is the same selection said twice. A run of the platform
cases alone would report green over eleven requirements and establish nothing,
which is the overstatement [§8.5](../SPEC.md#85-advisory-obligations)'s note
names.

A core case is therefore compared against `expected/<platform>.record`, one per
platform. Naming a `record` in `case.toml` overrides that for **every** platform
the case runs for, so a core case names one only where a single record is right
for all of them.

`expected/` holds the conformance record where the case has one. A blocking case
has no resolution to record, so it carries `diagnostics.txt` instead — a
human-readable note saying what the diagnostic has to convey, authored from the
specification like everything else here. **`run.py` does not read it**: the case
asserts the diagnostic *id* and the outcome, because §8 fixes neither a consumer's
wording nor its format. The note is there so a reader can see what the id stands
for without resolving it.

### `input/`

```
input/
  closure.toml        the resolved dependency closure for the target platform
  application.toml    the application's own configuration and answers
  resolved.toml       optional — what the consumer's resolver would have returned
  accepted.record     optional — the last accepted integration record (§9.1)
  <distribution>/     one tree per distribution, as installed
    <package>/_native/native.toml
```

`closure.toml` is what a consumer's own resolver would have produced —
distribution name, version, how it entered ([§3.2](../SPEC.md#32-resolution)),
and the entry-point value. A distribution marked `origin = "not-in-closure"` is
installed alongside and outside the closure, which is the only way to exercise
requirement 1.

`application.toml` is a **neutral spelling**.
[§2.2](../SPEC.md#22-how-the-application-answers) fixes the capability a consumer
must offer and deliberately not its syntax, so a consumer under test adapts this
into whatever it actually reads. The corpus cannot mandate a spelling the
specification refuses to.

#### `accepted.record`

[§9.1](../SPEC.md#91-the-lifecycle) makes a consumer compare its resolution
against **the last accepted record**, report the delta, and refuse to build
through a change the application has not accepted. Requirements 26, 38 and 40
all turn on that comparison, and none can be exercised in a single run without
a prior state to compare against.

`input/accepted.record` is that state, in
[the same canonical form](record-format.md) a consumer emits — so the corpus
needs no second format, and a consumer that can emit a record can read one.

A case whose point is that the stored record is *wrong* says so:

```toml
malformed_inputs = ["accepted.record"]
```

Corpus hygiene then skips validating it, and validates every other one. Without
that, `core/R40_stored_digest_malformed` could not ship the abbreviated digest
its requirement is about.

#### `closure.toml`, and a distribution with two entry points

§3.4 makes a distribution declaring more than one entry in the group invalid, so
a closure entry may spell `entry_points` as a list in place of `entry_point`.
Only `core/R02_multiple_entry_points` does.

#### `resolved.toml`

[§9.4](../SPEC.md#94-what-resolved-artifacts-bring-with-them) binds a consumer to
what a **resolved artifact** declares — permissions, features and components in
an `.aar`'s own manifest, and a `required="true"` feature it must fail on until
the application decides. [§6.3](../SPEC.md#63-gradle-dependencies) and
[§7.2](../SPEC.md#72-swift-packages) bind it to the locked graph, and
[§9.7](../SPEC.md#97-packaging-collisions) to files colliding between artifacts.

None of that is expressible by shipping sidecars. A corpus carrying real `.aar`
files would be testing Gradle rather than the consumer, and could not run
offline. So a case that needs resolution states its **result**:

```toml
[[artifact]]
coordinate = "com.example.maps:android:4.1.0"
sha256 = "0d3e…"
declared_by = "pymaps"        # the distribution whose sidecar named it
transitive = false            # optional, default false
files = []                    # optional, the packaged paths §9.7 collides on
classes = []                  # optional, the classes §6.7 checks a keep against

  [[artifact.permission]]
  name = "com.example.permission.MAPS_ID"

  [[artifact.feature]]
  name = "android.hardware.location.gps"
  required = true

  [[artifact.component]]
  name = "com.example.maps.PublicActivity"
  kind = "activity"
  exported = true

[[package]]                   # the iOS counterpart, §7.2
url = "https://github.com/example/charting"
version = "2.4.0"
revision = "8a1f0c9e4b2d7f36a05c1e8b9d4427fa3c60e15b"
declared_by = "pycharting"
path = "/Users/…"             # optional — an unpinnable graph, §7.2
branch = "main"               # optional — likewise

  [[package.binary_target]]
  name = "ChartingRenderer.xcframework"
  checksum = "e11d…"
```

`path` and `branch` exist because [§7.2](../SPEC.md#72-swift-packages) puts its
strongest check on the **resolved graph** rather than on the declaration: a path
or branch dependency anywhere in it is rejected, however cleanly the sidecar
that pulled it in is written. Neither is expressible any other way, since the
offending package is one a producer never named.

`files` and `classes` are listings of archive contents, which is exactly what
[§9.7](../SPEC.md#97-packaging-collisions) and
[§6.7](../SPEC.md#67-shrinker-keep-patterns) ask a consumer to read — §6.7 says
so in as many words: "a listing of archive contents, not a parser".

**A consumer under test takes this in place of resolving.** That is one more
demand the corpus makes of a consumer's testability, alongside emitting a
conformance record — and it is the same kind of demand: a way to be driven
without its usual inputs. A consumer that cannot be told the answer cannot be
run against §9.4 at all, and reports those cases **unverified**.

Nothing in `resolved.toml` is normative. It is the corpus standing in for a
resolver, and the digests in it are the fixture's own — no bytes exist for them
to be computed from.

Profiles follow [§8.1](../SPEC.md#81-conformance-is-per-platform). Advisory
obligations carry no profile there, so each sits with the section it enforces:
S1–S4 are core, S5–S9 and S11–S13 Android, S10, S14 and S15 iOS.

## `case.toml`

Three axes, deliberately. [§8.2](../SPEC.md#82-dispositions-and-what-recording-is-not)
classifies **findings**; a numbered requirement that defines no finding is a
conformance obligation, checked by inspecting what the consumer produced. One
field cannot carry both, and collapsing them would invent a disposition the
specification declines to define.

```toml
requirement = 23           # the §8.4 number, or "S13" for an advisory
profile     = "android"    # core | android | ios
section     = "6.1"        # what it enforces, for `explain`

# Axis 1 — what happens to the build.
outcome = "blocking"       # accept | blocking

# Axis 2 — findings expected, and the distributions each must name.
diagnostics = [
  { id = "ni.req.23", distributions = ["pyalpha", "pybeta"] },
]
advisories  = []

# Axis 3 — observable postconditions, for obligations with no finding.
assertions = []
```

| Field | Meaning |
| --- | --- |
| `outcome` | `blocking` — the build **MUST NOT** proceed. `accept` — it proceeds |
| `diagnostics` | findings the consumer must report — an id from [`contract/diagnostics-v1.toml`](../contract/diagnostics-v1.toml) and **the distributions it names**. Requirement 18 makes attribution part of the obligation, so the corpus checks it rather than taking a consumer's word |
| `advisories` | the same shape. Reported, never blocking ([§8.5](../SPEC.md#85-advisory-obligations)) |
| `assertions` | named postconditions on what the consumer produced — the record, the payload, the generated project |
| `record` | the `expected/` file to compare against, when the case has one |
| `ignore_digests` | the case is not about hashing, so `input` digests compare loosely — in content only, never in syntax |

### Which ids a case expects

`run.py` compares the id set exactly: a diagnostic the case does not list fails
it, just as a missing one does. So the set has to be derivable rather than
guessed at, and one rule fixes it:

> A finding carries the most specific id
> [`contract/v1.toml`](../contract/v1.toml) defines for the check that failed,
> **and** the `ni.req.<n>` of the requirement it discharges. Where the registry
> defines no id for that check, the requirement id stands alone.

The registry defines an id where the rule is a property of a declaration — a
`forbidden` key, a `unique_within` uniqueness, a closed vocabulary, a refusal
register — or a `[[constraints]]` row between two keys. Those become
`ni.decl.…` and `ni.constraint.…`, and a consumer can enumerate them from the
registry without reading this corpus.

It defines none where the rule needs something no single sidecar holds: the
dependency closure, the application's answers, the wheel's own files, the
resolved graph. `core/R12_floor_unmet` cites `ni.req.12` alone because a floor
is unmet only against a configuration, and
`core/R07_contract_major_mismatch` cites `ni.req.7` alone because `"2"` is a
well-formed contract value and only the consumer's own version makes it wrong.

The pairing is what makes a failure retrievable: the requirement id says which
obligation went unmet, the precise id says which rule, and an author repairing a
sidecar wants the second.

An unsatisfied conditional requirement is neither blocking nor advisory
([§8.2](../SPEC.md#82-dispositions-and-what-recording-is-not)), and says so on
the axes rather than in a disposition:

```toml
outcome = "accept"
state    = "unresolved"
reported = true
```

### Assertions

An assertion names something observable about the consumer's own output. It is
not a diagnostic, and it may accompany an accepted build, a blocked one, or an
advisory — which is why it is a separate axis rather than a third disposition.

**Verified** assertions are checked by the harness against what the consumer
wrote to its output directory. **Attested** ones are the consumer's own claim,
labelled so that nobody reads testimony as evidence.

| Assertion | Requirement | |
| --- | --- | --- |
| `sidecar_excluded_from_payload` | 6 — the sidecar directory reaches no device payload | **verified** |
| `contributed_source_excluded_from_payload` | 24 — the source the sidecars contribute, by name or by bytes; an application's own `.java` is not checked, because no requirement forbids it | **verified** |
| `python_module_stubs_excluded` | 36 — `<name>.py` and `<name>.pyi` | **verified** |
| `view_link_attributes_written_through` | 30 — every view-link attribute reaches the manifest, including one this document does not list | **verified** |
| `artifact_feature_decision_applied` | 41 — the application's decision reaches the manifest, and not only the record | **verified** |
| `no_producer_import` | 3 | attested |
| `every_diagnostic_names_a_distribution` | 18 | attested, and largely superseded — `diagnostics` carries the names now, and the corpus checks them |
| `instructions_attributed_to_producer` | 21 | attested |
| `no_credential_in_record` | 42 | attested |
| `no_invented_value` | 16 | attested |
| `no_unexported_fallback` | 29 | attested |
| `objc_categories_linked` | 37 | attested |
| `record_contains` / `record_omits` | 43, and any row of [§9.6](../SPEC.md#96-what-a-record-must-contain) | attested |
| `activity_extends_component_activity` | 45 | attested |
| `url_callback_observable` | 46 | attested |

An assertion is verified by naming an output the harness can read. Two exist:
`<outputs>/payload/`, the assembled Python payload, and `<outputs>/manifest.xml`,
the effective merged manifest. They are deliberately few — the corpus should not
specify a consumer's generated project, and each file it does read is a piece of
interface this document defines on its own authority rather than §8's.

Where a requirement is about what ends up in one of those two, the assertion is
verified there. `view_link_attributes_written_through` and
`artifact_feature_decision_applied` are both that case, and both are ones a
record cannot show: R30's record carries `ssp_prefix` in the **sidecar's**
spelling precisely so it does not depend on the conversion, and R41's record
states the decision rather than its effect. Closing the rest of the list means
reading more of a generated project than this corpus should define, and
pretending otherwise would be the overstatement §8.5's note warns about.

A consumer that cannot observe an assertion reports it **unverified** rather
than passing it, and a run with any unverified case exits non-zero. The
assertion belongs to a *numbered* requirement, so failing to observe one means
conformance was not demonstrated — not that the consumer is conforming. An
assertion silently skipped is how a conformance claim overstates itself, which
is the failure [§8.5](../SPEC.md#85-advisory-obligations)'s note names.

### Unverified and unsupported are opposite things

| Status | Meaning | Exit |
| --- | --- | --- |
| **unverified** | the consumer cannot observe an assertion, so a numbered requirement went unchecked | non-zero |
| **unsupported** | the consumer does not claim an advisory the case names | 0 |

The distinction is [§8.5](../SPEC.md#85-advisory-obligations)'s. An advisory is
reported and never blocking, so declining one is a conforming consumer
exercising a choice the specification gives it, and a suite that failed the run
over it would be inventing an obligation. A numbered requirement is not
optional, and a suite that reported green having checked nothing would be worse
than one that failed.

### Advisories never fail a case

[§8.5](../SPEC.md#85-advisory-obligations) makes an advisory obligation
reported and never blocking, so a consumer that does not implement one is still
conforming. A case that names an advisory therefore reports **unsupported**
against such a consumer rather than failing it, and the run still exits 0.

That has a consequence for the record. Some operands exist only because an
advisory asks for them — a permission's `reason` is
[§6.5](../SPEC.md#65-permissions-and-features)'s RECOMMENDED field, carried into
the record by [S7](../SPEC.md#85-advisory-obligations). A fixed expected record
cannot hold one unconditionally without failing every consumer that declines the
advisory. So `record-facts.toml` marks those operands, and `run.py` compares one
**only against a consumer that claims the advisory governing it** — dropping it
from both sides otherwise. `android/S07_permission_reason` is the worked case:
a consumer implementing S7 passes it, one that does not is unsupported, and both
pass every case that does not name S7.

## What is here

Category 1 first, per the work brief: the cases where a non-conforming consumer
is **dangerous** rather than merely wrong.

| Case | Requirement | What a wrong consumer does |
| --- | --- | --- |
| `core/R05_resource_path_escape` | 5 | stages files from outside the sidecar directory |
| `core/R13_placeholder_not_an_answer` | 13 | takes the producer's own placeholder as the application's answer |
| `android/R23_owned_namespace_collision` | 23 | lets one distribution's class silently replace another's |
| `android/R23_reserved_namespace` | 23 | lets a package replace the toolchain's entry point |
| `android/R28_feature_required_promotion` | 28 | removes the application from every device lacking the hardware |
| `android/R29_export_without_approval` | 29 | exports without approval, or registers unexported and ships a broken app |
| `ios/R35_usage_description_contributed` | 35 | puts a producer's privacy claim in front of App Store review as the application's |
| `ios/R35_capability_key_contributed` | 35 | grants a capability that then does not work, with no task stated |
| `android/R41_artifact_feature_undecided` | 41 | lets an artifact make hardware mandatory without the application choosing |

Beyond category 1, **every blocking requirement in all three of §8.1's profiles
now has a case** — core, Android and iOS — and the core cases are exercised for
both platforms, so `core + android` and `core + ios` are each a claim the corpus
can actually check.

Four accept cases sit beside them so the corpus is not only negatives:
`core/R01_dependency_closure` compares a record,
`android/S07_permission_reason` exercises the advisory axis, and two are the
other side of a blocking case, which is the only way that case discriminates:

- `android/R41_artifact_feature_decided` — the application decided, so the build
  proceeds and §9.4's attribution has to appear in the record;
- `android/R44_metadata_collision_resolved` — the collisions are packaging
  metadata only, so §9.7's first row applies and the consumer resolves them
  itself. Without it, a consumer that failed on *every* colliding path would
  pass `R44_packaging_collision` with the right outcome and the right id while
  getting the section backwards.

## Running it

```
python3 conformance/run.py --profile android -- mytool build --conformance-record
```

That is a whole `core + android` claim: 30 cases, the 15 core ones run against
an Android closure. Add `--profile ios` for a consumer that builds both.

`run.py` invokes the consumer once per case with **two** arguments: the case's
`input/`, and an output directory to write what it produced into. It answers on
stdout with one JSON object:

```json
{
  "outcome": "blocking",
  "diagnostics": [{ "id": "ni.req.23", "distributions": ["pyalpha", "pybeta"] }],
  "advisories": [],
  "assertions": { "no_producer_import": true },
  "capabilities": { "injected_resolution": true },
  "record": "build contract 1.0…"
}
```

- **`outcome` is the only authority.** A consumer reporting `blocking` and
  exiting 0, or `accept` and exiting non-zero, has contradicted itself — a
  failure, rather than something to resolve by preferring one of the two.
- **`capabilities`** says what the consumer can be driven to do.
  `injected_resolution` is whether it accepts a stated `resolved.toml` in place
  of resolving; one that cannot reports every case needing one as **unverified**
  rather than failing it.
- **The output directory** is what turns an assertion from a claim into a
  check. Two paths in it are read:

  | | |
  | --- | --- |
  | `<outputs>/payload/` | the assembled Python payload, as it would ship |
  | `<outputs>/manifest.xml` | the effective merged manifest, for an Android case |

  A consumer that writes neither reports every verified assertion as
  **unverified**, which is non-zero — not a pass.

The consumer under test supplies the command. Nothing here imports a consumer,
and nothing here is a consumer.
