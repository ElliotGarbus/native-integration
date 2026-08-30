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
twelve, and one that accepts every negative fails all nine and exits 1.

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

### 3. §7.4's refusal registers have no declaration-level diagnostic id

`ios/R35_usage_description_contributed` and `ios/R35_capability_key_contributed`
both name `ni.req.35`, the requirement-level id, because no finer one exists.

`gen_error_ids.py` derives declaration ids from a registry entry's own
properties, and `refuses` is not among them — an `open_table` gets the container
checks, which are `exactly_one_of` and `at_least_one_of`, so
`ios.contributes.info_plist.values` produces no ids at all. The generator is
consistent; the property list is short by one.

This matters for Phase 4 rather than here: `explain` is meant to turn a failure
into one retrievable paragraph, and `ni.req.35` resolves to a requirement
covering eleven separate clauses. **Not fixed in this phase** — it is a
one-property change to a Phase 1 generator, and doing it inside the fixture work
would put a registry change in a commit about fixtures.

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
