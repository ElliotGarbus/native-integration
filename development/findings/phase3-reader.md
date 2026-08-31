# Phase 3 — the reader, rewritten against SPEC.md

Phase 0 found that the reader under `src/` implemented `development/first-attempt.md`
and that nothing in the repository said so loudly enough. Phase 3 replaced it.
This records what the rewrite turned up, which is the part a green test run does
not say.

## What was built

Sixteen modules, none of them carrying the vocabulary:

| Module | Section |
| --- | --- |
| `registry`, `obligations` | the contract, loaded, and which §8.4 requirement each check answers to |
| `contract` | §4.3's version grammar and §10's entry-point group, both derived from the registry |
| `resources`, `discovery` | §3, §4.1 |
| `document`, `structure` | §4.3's gate and §4.4's fail-closed walk |
| `findings` | the diagnostic type |
| `application`, `integration` | §2.2 and §5 |
| `semantics` | the rules that are not properties of one sidecar |
| `graph` | §9.4, §9.7 |
| `advisories` | §8.5 |
| `recording`, `acceptance` | §9 |
| `reader` | the order §4.3 fixes |

Fourteen first-attempt modules were deleted rather than migrated —
`answers`, `context`, `crossrules`, `diagnostics`, `effective`, `model`,
`native`, `naming`, `ports`, `record`, `resolution`, `rules`, `schema`,
`sidecar` — along with `testing.py` and four test files. Phase 0's judgement
that "the architecture survived and the rule set did not" turned out to be half
right: the *boundary* survived, and almost none of the architecture did. The
first attempt had a `rules.py` holding ninety-three rules as data and a
`ports.py` of `Protocol`s for everything a build tool knows. Neither shape
returned. Rules now come from `contract/v1.toml`, and the one port that mattered
— a resolved dependency graph — is an ordinary argument that defaults to empty.

## The registry paid for itself here

Phase 1 built `contract/v1.toml` on the argument that a vocabulary written twice
drifts. Phase 3 is where that was cashed: `structure.py` is a walk over 97
declarations, and it contains no key names, no closed vocabularies and no
refusals. The generated JSON schema, Appendix B, the 238 diagnostic ids and the
reader all read the same file.

The concrete test is that adding a declaration to the registry requires no edit
to `structure.py`. That held. The parts of the reader that *did* need hand-written
rules are exactly the ones the registry deliberately excludes — anything needing
the closure, the application's answers, or a resolved graph — which is `semantics.py`,
`integration.py` and `graph.py`, and is the boundary Phase 1 drew.

### The exception, and it is the interesting one

`obligations.py` is the only hand-derived table in the library: 2 entries by
check, 23 by declaration family, 19 by named constraint. `contract/v1.toml`
carries mechanical properties only — Phase 1's whole discipline — so it cannot
say which numbered requirement a failed check answers to. §8.4 is prose, and
somebody has to read it.

This was nearly wrong in a way worth recording. The first version mapped by
declaration family alone, with longest-prefix matching, and `ios.contributes`
resolved 37 ids where 34 were correct. The fix was not a better prefix: it was
accepting that §6.6 carries two requirements and §5.2 carries three, so a
*section* is the wrong grain and a family is only mostly the right one. Nineteen
constraints now name their requirement explicitly. `tests/test_obligations.py`
holds the table total — every id any generator emits resolves to exactly one
requirement, and that requirement's §8.1 profile agrees with the platform the
declaration belongs to — which is what makes a hand-derived table safe to keep.

## Where the obligations landed

Sixty-one rows: 46 numbered and 15 advisory.

| | Count |
| --- | --- |
| discharged by a check in a module | 39 |
| discharged by the shape of the API | 9 |
| beyond this reader | 13, of which 7 also carry a module |

The nine structural ones are the entries worth arguing about, because "the API
makes it unforgettable" is the kind of claim that is easy to make and hard to
hold. Requirement 18 — name the distribution in every diagnostic — is the clean
case: `Finding.__post_init__` raises, so there is no call site at which it can
be forgotten. Requirement 3 (never import the producing package) is the weakest:
it is discharged by nothing in the package doing it, which is a property of the
code as written rather than one the code enforces. It is listed as structural
because the alternative was leaving it blank, and a blank reads as an oversight.

The seven split rows are the honest ones. Requirement 30 validates a view-link's
attributes here and writes them into a manifest in a build tool; the reader does
the first half and says so. `tools/requirements_table.py` renders both notes
rather than picking one, which took two attempts — the first version treated
"beyond this reader" as exclusive and `tests/test_requirements.py` caught five
requirements marked excused that were partly implemented.

## The corpus defect: R01 passed for the wrong reason

`core/R01_dependency_closure` asserts that a distribution outside the closure
contributes nothing. `pyunrelated` was listed in `input/closure.toml` as
`not-in-closure` and shipped **no sidecar directory at all**.

So a consumer that ignored the closure entirely and enumerated every entry point
in the environment would look for `pyunrelated`'s sidecar, not find it, and
report nothing — passing the case without ever exercising the rule. The case was
green against the first-attempt reader and would have been green against
anything.

Both platforms now ship a deliberately loud sidecar for it: a permission nothing
asked for, and a `min_sdk` above what the application configures, either of
which would fail the build if read. The rule is now what breaks.

This is the second corpus defect of this shape — Phase 2 found three cases green
for the wrong reason by mutating a conforming consumer. The pattern is the same
both times: a negative fixture that is *missing* something tests less than it
appears to, because the consumer fails to find rather than failing to accept.
A fixture for "must not accept X" needs an X.

## The packaging gap: six unverified, and why that is the right answer

Against the corpus this reader passes every case it can and reports six runs as
**unverified**:

| Case | Assertion |
| --- | --- |
| `core/R01` (both platforms) | `sidecar_excluded_from_payload` |
| `android/R30_view_link_passthrough` | `view_link_attributes_written_through` |
| `android/R41_artifact_feature_decided` | `artifact_feature_decision_applied` |
| `ios/R36_python_module_registered` | `python_module_stubs_excluded` |
| `ios/R37_objc_categories_union` | `objc_categories_linked` |

Every one is an assertion about generated output. The harness asks for a
`manifest.xml` or a `payload/` to inspect and there is none, because a reader
does not produce either. `run.py` exits non-zero on an unverified run, which is
correct and should stay that way: an obligation quietly skipped is how a
conformance claim overstates itself, and this reader does not conform to the
whole of §8. It conforms to the reading half and reports the rest as unmeasured.

Closing them needs a build tool. That is now the pacing item in `README.md`'s
freeze list, replacing the reader rewrite.

## Four things the specification said that only writing this made concrete

### Requirements 26, 38 and 40 are core, and platform-specific anyway

Phase 2 predicted this in one sentence and it was still surprising in practice.
The three record-comparison requirements are in §8.1's **core** row, so a
consumer claiming `core` implements them. But what they compare differs
completely: on Android a Maven artifact's `sha256`, on iOS a Swift binary
target's `checksum`. The first implementation handled the Android half, passed
`core/R26` on Android, and reported `core/R26` on iOS as requirement 38 — an
unaccepted change — because the digest it knew how to compare was not there.

A reader that implements the Android half of a core requirement has not
implemented it. The fix generalizes over "bytes this record pins" rather than
over artifacts.

### An invalid sidecar has to stop being read

`core/R22` declares two requirements with the same `id`, and the reader reported
three findings: the id collision, plus the value it never supplied and the action
nobody acknowledged. All three are true. Only the first is useful — the other two
are statements about a document the reader has already refused to interpret, and
they would send an application author to fix answers to questions that will not
exist once the sidecar is corrected.

`document.read` now returns `None` when structural validation produces anything
blocking, so an invalid sidecar is never resolved. This is not a rule §8.4
states; it emerged from the corpus expecting exactly one diagnostic, which is
the corpus being a better specification of consumer behaviour than the prose in
this instance.

### A consumer-decided record needs a date the consumer is told

`android/R44_metadata_collision_resolved` expects a record carrying the date the
collision was resolved. Nothing in the input supplied one, and reading the clock
would make the record differ from yesterday's for no reason — which §9.1's gate
would then report as an unaccepted change on every build.

`Application.date` is the answer: the build date is told to the reader rather
than observed. `SOURCE_DATE_EPOCH` exists for the same reason in the same shape,
and a consumer that already honours it has the value to pass.

### §9.5 costs the record a demonstration

The mediated-ads records used to show `GADApplicationIdentifier` carrying a
different value from `com.google.android.gms.ads.APPLICATION_ID` — finding MA5,
visible as output. They cannot any more: §9.5 keeps supplied values out of the
record, so what it shows is `state=supplied` and the key the answer lands on.

The finding survives, in a weaker form: one declared `id` reaching two different
platform keys. The demonstration of *different values* now lives only in
`app-pyproject.toml`. Worth recording because the earlier record was written by
hand, and a hand-written record can show something the real one is forbidden to.

## The examples were stale, and the check that should have caught it could not

`tools/check_spec.py` verified that every key an example uses appears somewhere
in the relevant specification. `examples/pystripe/native.toml` declared
`[[android.requires.application_values]]`, and the string `application_values`
appears in SPEC.md — in prose about the application's side — so the check passed
on a declaration the reader refuses.

A substring search cannot tell a key from a mention. `tests/test_examples.py`
now runs the actual reader over every live example on both platforms, and it
failed immediately on three things the substring check could not see: the
renamed declaration, a missing `kind`, and a contributed source directory that
did not exist. The last is now a real `.java` file whose path and `package` fall
under the namespace the sidecar claims, so §6.1 rule 1 has something to check.

Two smaller consequences:

- **A check stopped checking, silently.** `check_spec.py` verifies that
  `app-pyproject.toml` answers every value its sidecar declares. It read them
  through the key name `application_values`, so after the rename it compared
  against an empty set and reported success. It now fails if any of the three
  sets it reads is empty, on the grounds that a pair which teaches §2.2's answer
  surface has something to answer in each.
- **Examples were being held to the wrong document.** The live set and the
  frozen design-exploration set were both routed through the first attempt's
  rules. `check_spec.py` now splits them once and every check routes on it, and
  a new check verifies that every `§N.N` a live example cites resolves to a
  heading SPEC.md actually has. It found one on its first run: `pyadmob`
  attributed Objective-C categories to §7.8, which does not exist.

That check initially caught a *dangling* citation and not a *wrong* one: four
more stale citations pointed at real sections about the wrong subject and sailed
through it, found only by reading. Closing that is the next section.

## Making a citation checkable

A bare `§6.8` asserts one thing — that a section numbered 6.8 exists — so that
is the most a checker can get from it. Five wrong-but-real citations survived a
check that verified exactly that.

The obvious fix was to infer the subject: `contract/v1.toml` maps all 97
declarations to their anchors, so "a comment mentioning `view_links` should cite
§6.6" looked mechanical and free. It was measured against the examples *after*
they were corrected, and produced 10 false positives on 22 checkable lines. The
declaration leaf names are ordinary English — `value`, `action`, `package`,
`requirement`, `conditional` — so "this line mentions a declaration" fires on
almost any sentence. A check that is wrong 45% of the time on correct input
trains people to write around it, which is worse than no check.

So the citation was made to carry its subject instead: `§6.6, Manifest
components`, verified against the heading exactly. Two details earned their
keep:

- **Once per file, not once per citation.** A file that has said which section
  §5.5 is may then use the number. Requiring the title at all 46 sites produced
  prose visibly written for a checker; requiring it at the 34 first mentions did
  not.
- **Beside the number, not merely near it.** The first version accepted the
  title anywhere in three lines, which is loose enough that an ordinary sentence
  vouches by accident: "values" turning up somewhere in a comment is prose,
  while "values" touching `§5.2` is a claim. Tightening to twenty characters of
  slack was measured before it was chosen — it left 32 of the 35 citations
  alone. The three lines survive only so that a title and a number split by a
  line break still count.

The honest limit is narrower than it first appears. The check is strong when a
citation drifts *away* from the right section, because the stale number's title
will not be beside it — and writing the title you mean while typing another
section's number fails for the same reason, however generic either title is.
What slips through is only an author writing a word that is exactly the *cited*
section's title while meaning a different section: §5.2 is "Values" and §5.3 is
"Actions". That is a rarer mistake than a number going stale under renumbering,
which is the one that actually happened five times.

One pair is beyond it entirely: **§6.2 and §7.3 are both titled "Source"**, the
only duplicate heading in SPEC.md, so no check of this shape can tell a citation
of one from a citation of the other. That is worth fixing as a documentation
matter rather than a checker one — a cross-reference reading "see Source" is
ambiguous to a reader too — and it is recorded here rather than acted on.

And the mechanism is not really the checker. Writing the title beside the number
makes the author read the title, which is where a wrong number becomes obvious.

Two things fell out of writing it. The rule moved to `tools/citations.py` with
`tests/test_citations.py` beside it, because the check it replaced failed by
being untested and green — most of that test file is input the rule must
*reject*. And one citation turned out to be inside a `reason` string, which
means it was being emitted into the integration record and into diagnostics read
by application developers; a spec section number is noise there, and it is gone.

A convention the check imposes, worth knowing before writing a live example:
**`§` means SPEC.md and nothing else.** An example with something to say about
the first attempt writes "section 7.3 of first-attempt.md" in words. The two
documents number the same subjects differently, so an unqualified § pointing at
the wrong one is the confusion the check exists to end.

## What is not done

- **No consumer generates anything.** Six assertions stay unverified until one
  does.
- **§4.3's under-declaration rule still has no fixture**, for the reason Phase 2
  gave: every entry in `contract/v1.toml` is 1.0, so nothing can under-declare.
  The reader implements it; nothing exercises it.
- **`development/examples/` is frozen against the first attempt** except for
  `mediated-ads`, which was converted. The other sixteen are design arguments in
  the vocabulary that produced this document, and rewriting them would destroy
  the evidence. They are checked against `first-attempt.md` and should stay that
  way.
