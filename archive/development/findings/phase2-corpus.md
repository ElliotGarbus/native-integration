# Phase 2 — the category-1 negatives, and what authoring them found

The work brief orders fixtures by danger: first "the cases where a
non-conforming consumer is dangerous rather than merely wrong". Those are
written. This records what authoring them turned up, which is the part a green
test run does not say.

## What is covered

Nine negatives — one per item on the brief's category-1 list, plus requirement
41 once `resolved.toml` made it expressible — and three accept cases so the
corpus is not only negatives.

| Case | Req | Also caught by the Phase 1 schema? |
| --- | --- | --- |
| `core/R05_resource_path_escape` | 5 | no — path escape needs the wheel's files |
| `core/R13_placeholder_not_an_answer` | 13 | no — needs the application's answers |
| `android/R23_owned_namespace_collision` | 23 | no — needs the closure |
| `android/R23_reserved_namespace` | 23 | no — needs §6.1's reserved list |
| `android/R28_feature_required_promotion` | 28 | **yes** — a forbidden key |
| `android/R29_export_without_approval` | 29 | no — needs the application's answers |
| `ios/R35_usage_description_contributed` | 35 | **yes** — a refused key name |
| `ios/R35_capability_key_contributed` | 35 | **yes** — a refused key name |
| `android/R41_artifact_feature_undecided` | 41 | no — needs the resolved graph |

Three of nine are structural, and Phase 1's schema already refuses them. That
split is worth keeping visible: it says the schema is carrying about a third of
the dangerous cases, and the other six are exactly the ones needing the
dependency closure, the application's answers, the wheel's own files, or the
resolved graph — which is the boundary Phase 1 drew and Phase 3 inherits.

Verified by running the corpus against two stubs: a conforming one passes all
thirty-eight, and one that accepts every negative fails all thirty-two and exits
1.

## The core profile

Every blocking requirement in §8.1's core row now has a fixture: 2, 4, 5, 7, 8,
9, 12, 13, 14, 17, 22, 26, 38, 40. Requirement 1 is the accept case the corpus
opened with.

Three of them needed a prior state, because §9.1's comparison cannot be
exercised in a single run: `input/accepted.record` carries the last accepted
record in the same canonical form a consumer emits, so the corpus needs no
second format and a consumer that can write one can read one.

Two are worth singling out for the same reason `R13` was — the input is not
malformed, and a plausible consumer gets them wrong:

- **`R14_action_held_by_unsupplied_value`.** The action *is* acknowledged. It
  stays unsatisfied because the value it `uses` is a placeholder, and that value
  is `conditional`, so on its own it never fails the build. §5.3 adds the rule
  precisely so an unconditional action cannot pass on an input that never
  arrived. A consumer checking "acknowledged?" ships.
- **`R40_stored_digest_malformed`.** The stored digest's *prefix matches*. A
  consumer comparing loosely reports agreement between two records that never
  agreed, which is what §9.3's "never abbreviated" exists to prevent.

### One clause in requirement 7 cannot be fixtured, and will not be until 1.1

§4.3's **under-declaration** rule — a sidecar using a key, table, or
closed-vocabulary value introduced in a revision later than the contract it
names — has no fixture, and cannot have one. Every entry in `contract/v1.toml`
is 1.0, so no declaration exists whose `since` a sidecar could under-declare.
`R07_contract_major_mismatch` covers the half that is testable today.

This is not a gap to close; it is a fixture that becomes writable the day a
minor adds its first key, and the registry's `since` field is what will make it
mechanical. Worth recording so the absence is not read later as an oversight.

## The Android profile

Every blocking requirement in §8.1's Android row now has a case: 23, 25, 27, 28,
29, 30, 31, 32, 41, 44, plus advisory S7. Two needed `resolved.toml` to grow a
`classes` listing alongside `files` — §6.7 asks a consumer to read "a listing of
archive contents, not a parser", and that is what both are.

Three are worth singling out, for the reason the core ones were:

- **`R30_view_link_passthrough` is the only accept case among them, and the
  dangerous consumer is the one that is *too strict*.** §4.4's single exception
  says an unrecognized `<data>` attribute is written through; a consumer that
  failed closed on `ssp_prefix` would make every producer wait for every
  consumer to learn an attribute Android already shipped. It is the one place in
  the corpus where rejecting is the wrong answer.
- **`R32_meta_data_type_conflict` fails a consumer that compares rendered
  output.** Both declarations produce `android:value="1"`; §6.8 makes equality
  "by type as well as content" precisely so the integer and the string do not
  coalesce. A consumer merging after rendering sees agreement.
- **`R25` and `R27_repository_scope_overlap` are valid sidecars individually.**
  Neither can be caught by a schema or by reading one file; the conflict exists
  only in the combination, and only the consumer knows which Python
  distributions to name — Gradle sees one module and one repository.

## The iOS profile, and coverage

Requirements 33, 34, 36 and 37 complete §8.1's third row. **Every blocking
requirement in all three profiles now has a case** — twenty-six of them,
verified by parsing §8.4 for the clauses that say *fail* or *reject* and
checking each against the corpus rather than asserting it. `check_spec.py` also
holds each case to §8.1's own profile assignment now, so a case cannot sit in a
directory whose consumers never owed the requirement.

Two of the four needed `resolved.toml` again, and for the reason §7.2 gives
directly: its strongest check is on the **resolved graph** rather than on the
declaration. `R33_path_dependency_in_graph` ships a clean sidecar — an `exact`
requirement on an `https` URL — whose transitive dependency points at a local
checkout. A consumer validating only what the sidecar says passes it, and the
package resolves for whoever published it and for nobody else.

`R37_objc_categories_union` is the quiet one worth keeping. Two distributions,
one asking; the record must name the one that asked and not the other. §7.6 has
no veto, so the only control the application has is seeing which dependency
caused its binary to grow — and a consumer that applied the link setting and
recorded nothing has met half the requirement while looking correct.

## What the harness verifies, and what it only records

A review round after the fixtures were written pointed at the harness rather
than the corpus, and was right on every count. Four of the findings were
protocol defects and are fixed; one is a boundary worth stating rather than
papering over.

**Fixed.** Diagnostics now carry the distributions they name, so requirement 18
is checked rather than left to a self-attested boolean — a consumer naming the
wrong distribution fails, and `check_spec.py` holds every case to naming
distributions its own closure declares. `capabilities.injected_resolution` lets
a consumer that cannot be told a resolution report those cases **unverified**,
which the README described and nothing implemented. The reported `outcome` is
now the single authority, with a contradicting exit status a failure in its own
right rather than a tie to break. And `ignore_digests` reaches **input** hashes
only — it was eliding Maven artifact and Swift binary-target checksums too,
which are the integrity §6.3 and §7.2 require a consumer to verify, so a
resolved-graph case could have had the behaviour it tests suppressed.

**The boundary.** An assertion was pure testimony: it passed because the
consumer returned `true`. Three of them now are not — the consumer writes its
assembled payload to an output directory and the harness inspects the files, so
`sidecar_excluded_from_payload`, `contributed_source_excluded_from_payload` and
`python_module_stubs_excluded` are checked against evidence.

The rest stay attested, and README.md labels them so. Closing that list means
giving the harness a generated Android or Xcode project it can parse, which is a
much larger interface than a conformance corpus should define on its own — and
claiming verification the harness does not perform would be exactly the
overstatement §8.5's note warns about. Better a table that says which is which.

## A second review, and what a passing case was worth

A later round found seven more, all valid. Three are worth setting down, because
each is the same failure in a different place: **a case can pass for a reason
that has nothing to do with the requirement it names.**

- **`R44_packaging_collision` could not tell §9.7's two rows apart.** It mixed a
  native library, a `META-INF/` subdirectory entry and `META-INF/LICENSE`, and
  expected blocking. A consumer that blocked on *every* colliding path — getting
  the first row backwards, and so refusing most real closures, since
  `META-INF/LICENSE` collides "from almost any pair of libraries" — produced the
  expected outcome and the expected id. It passed. `R44_metadata_collision_resolved`
  is the other half: metadata-only collisions, accepted, with §9.6's collision
  row in the record. Written as a 30-line consumer implementing exactly the naive
  rule, that consumer now passes the first case and fails the second.
- **`R36_python_module_registered` asserted an exclusion with nothing to
  exclude.** The distribution shipped no `web_views.py` and no `web_views.pyi`,
  so the payload check held vacuously against a consumer that implements no
  exclusion at all. Both files are now in the fixture, at the top level where
  `sys.path` would find them.
- **`R30` and `R41_artifact_feature_decided` checked the record, which is not
  the obligation.** R30's record carries `ssp_prefix` in the sidecar's own
  spelling — deliberately, so the record does not depend on the conversion, and
  therefore cannot show the conversion happened. R41's record states the
  application's decision, not that the decision was applied. Both passed a
  consumer that recorded its intention and did nothing.

The fix for the third is the one that moved the boundary above: the harness now
reads **one** more thing a consumer produces, the effective merged manifest at
`<outputs>/manifest.xml`, and two adapters check it — every view-link attribute
on a single element, and a `<uses-feature>` carrying the decision. Both derive
what they look for from the fixture rather than from a vocabulary of ours, which
is what keeps §6.6's open attribute set open. That is still far short of parsing
a generated project, and the rest of the table stays attested.

Also fixed: `--profile android` ran the eleven Android requirements *without the
core*, so the documented invocation reported green over a selection §8.1 does
not admit as a claim. A platform profile now brings the core with it. And
requirement 24's check rejected every `.java`, `.kt` and `.swift` in the payload
— including an application's own, which no requirement forbids — where it should
reject the files the sidecars contribute; it now derives them, by name and by
bytes.

### What actually establishes that a fixture discriminates

Every case in this corpus has been run against stubs, which pass by
construction: that is evidence about the harness, not about the fixtures. The
useful test is the opposite one — break exactly one thing and see exactly one
case fail.

| what was broken | result |
| --- | --- |
| nothing | 54 passed |
| drop `ssp_prefix` from the manifest | R30 alone |
| spread one view link across two `<data>` tags | R30 alone |
| merge the artifact's `required="true"` anyway | R41-decided alone |
| ship `web_views.py` | R36 alone |
| ship contributed source | R01, both platforms |
| ship the **application's** own `.java` | still green, which is the point |
| ship the sidecar | R01, both platforms |
| choose the other artifact for `META-INF/LICENSE` | still green — §9.7 leaves the rule to the consumer, and `run.py` elides `chosen` where a decision says `decided=consumer` |
| block on every collision | R44-metadata alone, R44-packaging still passing |

Three of those rows were green before this round, for the wrong reason.

**And the harness no longer crashes on a consumer that misbehaves.** A command
that cannot be launched, one that never returns, and a record carrying a lone
surrogate — which JSON accepts and UTF-8 cannot hold — each raised out of
`run.py` and abandoned every case after the offending one. A suite whose purpose
is to report on consumers that misbehave cannot treat misbehaviour as its own
bug.

## Core cases run for both platforms

The review round that found the harness defects ended with a correction worth
more than any of them: every core case shipped an Android closure, so
`core + ios` — a conformance claim §8.1 explicitly allows — rested on nothing.
Fifteen cases, all Android.

Each core case now ships `input/android/` and `input/ios/`, and `run.py` expands
it once per selected **platform** profile. The platform profiles chosen are what
decides, so `core + ios` runs twenty-three cases and none of them Android;
`core + android` runs thirty; all three run fifty-three. Naming no platform
profile runs both and says that this is a development run rather than a claim.

Writing the iOS halves was not mechanical, which is the interesting part. Three
cases are genuinely platform-neutral — the contract gate, the entry-point rule,
the misspelled top-level key — and their two inputs differ only in which empty
platform table they carry. The other twelve had to be *re-expressed*: a floor
becomes `deployment_target`, a value's `kind` becomes `info_plist`, and the
three record-comparison cases move from a Maven artifact's SHA-256 to a Swift
binary target's checksum, which is §7.2's counterpart to §6.3's and the only
place iOS pins bytes at all.

That last one is worth noting for Phase 3: requirements 26, 38 and 40 are core,
but what they bind a consumer to differs entirely by platform, and a reader that
implements the Android half has not implemented them.

## Three gaps — one closed here, two standing

### 1. §4.1's symlink clause has no portable fixture

Requirement 5 has two halves: a path that escapes after normalization, and a
**symlinked** resource, which §4.1 rejects outright in version 1. Only the first
is fixtured.

Git stores a symlink as a mode bit, and a checkout on a filesystem or platform
without symlink support silently materializes it as a regular file containing
the target path. The fixture would then test path escape on one machine and
nothing at all on another — a case that passes for the wrong reason is worse
than an absent one.

**What would close it:** a fixture format that describes the symlink rather than
being one — a `SYMLINKS.toml` the harness materializes at run time, skipping the
case where the platform cannot. That is a change to the input layout, which the
gate on the record format was explicitly about not making casually, so it is
recorded rather than done.

### 2. Requirement 41 needs resolved artifacts — CLOSED, by `resolved.toml`

§9.4's exception is squarely category 1: a resolved artifact declaring
`<uses-feature required="true">` **MUST NOT** silently make hardware mandatory,
and a consumer must fail until the application decides. It is the same harm as
`android/R28_feature_required_promotion` arriving by the path §9.4 exists to
surface.

`input/` described distributions and their sidecars, and requirement 41 needs a
resolved `.aar` with its own `AndroidManifest.xml` — which meant either shipping
binary artifacts in the corpus, or defining a fixture form for what resolution
would have returned.

**Closed, by the second.** `input/resolved.toml` states what a consumer's resolver would have
returned — artifacts with their digests, what each one's own manifest declares,
and the Swift-package counterpart with its binary-target checksums. Two cases
follow: `android/R41_artifact_feature_undecided`, the category-1 negative, and
`android/R41_artifact_feature_decided`, which is the only case exercising §9.4's
record facts at all.

Two consequences worth stating, because neither is free.

**It asks something more of a consumer.** A consumer under test must accept a
stated resolution in place of resolving, which is a second testability demand
after emitting a conformance record. Both are the same kind of demand — a way to
be driven without its usual inputs — and a consumer that cannot be told the
answer reports these cases unverified rather than passing them.

**It unblocks three more requirement families**, which is most of why it was
worth doing: §6.3's locked graph and per-artifact SHA-256, §9.7's packaging
collisions (the `files` list on an artifact is there for it), and §6.7's check
that a `from_dependency` keep matches no class from outside that dependency.
None is fixtured yet; all three are now expressible.

### 3. §7.4's refusal registers had no diagnostic id — CLOSED

`gen_error_ids.py` derived declaration ids from a registry entry's own
properties, and `refuses` was not among them — an `open_table` gets the container
checks, which are `exactly_one_of` and `at_least_one_of`, so
`ios.contributes.info_plist.values` produced no ids at all. Both iOS cases named
`ni.req.35`, a requirement spanning eleven clauses, which is precisely what
`explain` exists to avoid.

**Closed.** A refusal register is a rule of its own rather than a property of the
key it refuses, so each gets its own id — seven of them, `values` and `append`
across the four registers each refuses. The section and anchor come from the
register where `contract/v1.toml` defines one, and from the declaration
otherwise; the summaries sit beside `DECLARATION_CHECKS`' in the generator,
which is where that kind of text already lives.

Both iOS cases now cite the precise id alongside `ni.req.35`:
`…info_plist.values.refuses.usage-description-suffix` and
`…info_plist.append.refuses.capability-keys`. 231 ids became 238.

## A note on the placeholder case

`core/R13_placeholder_not_an_answer` is the one negative whose input looks
*valid* at every level. The sidecar is well-formed, the schema accepts it, the
application has answered, and the answer is a non-empty string. It is wrong only
because the string is the producer's own placeholder, which §5.4 excludes by
name.

That is the shape the brief means by a consumer being dangerous rather than
wrong: nothing about the inputs is malformed, and a consumer checking "is the
key present and non-empty?" ships an application whose analytics key is the
literal text `<TODO: your Examplytics project key>`.
