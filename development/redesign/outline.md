# Outline for the new specification

A section plan, written before prose so the structure is cheap to argue with.
Every section of [the first attempt](../first-attempt.md) is accounted for
below — carried, adapted, rewritten, moved or dropped — so nothing is lost by
being forgotten rather than by being decided.

Status key: **verbatim** (moves with at most a cross-reference fix) ·
**adapted** (same argument, edits for the new model) · **rewritten** ·
**new** · **dropped**.

## The shape of the change

The first attempt is organised platform-first: everything Android in §6,
everything iOS in §7, with prerequisites as a subsection of each. That put
`application_values` in §6.3, Android prerequisites in §6.11 and iOS
prerequisites in §7.3 — four sections and thirteen tables saying the same kind
of thing in two places.

The new model has **two prerequisite tables whose fields are identical across
platforms** and whose only per-platform part is a `kind` vocabulary. So they
collapse into one section, and the platform sections keep only what genuinely
differs: Gradle against SwiftPM, a manifest against a plist.

| | First attempt | New |
| --- | --- | --- |
| Sections defining prerequisites | 4 (§6.2, §6.3, §6.11, §7.2, §7.3) | 1 |
| Prerequisite tables | 13 | 2 |
| Sections classifying the tables | 1 (§2.4) | 0 |
| Platform contribution sections | 2 | 2 |

## The plan

### 1. Terminology — **adapted**

Carries. Two entries added: **action** (a requirement the consumer states and
does not perform) and **placeholder** (the value a consumer scaffolds and
blocks on until it is replaced).

### 2. Overview

| § | Status | Note |
| --- | --- | --- |
| 2.1 Design principles | **adapted** | Keeps *declarations are data*, *never originate what belongs to the application*, *unrecognized declarations fail closed*, *contributions stay per-distribution*, *resolution is reproducible*. Gains one: **automate only what is portable and deterministic, and state the rest.** The three-part test goes here, as the rule the rest of the document is derived from. |
| 2.2 How the application answers | **adapted** | The join-key model survives intact and is the part of the first attempt that aged best. Its sixteen-row table collapses to four: a value by `(distribution, id)`, an action by `(distribution, id)`, a permission suppression by `name`, an export approval by component `name`. |
| 2.3 What the consumer generates | **new** | Scaffolding placeholders into the application's configuration, and reporting what remains. The capability is mandated, the spelling is not — §2.2's existing stance. Includes the rule that a consumer never edits a file the application owns without being asked to. |
| 2.4 Obligations on the consumer's bootstrap | **verbatim** | Recently reworded; moves as-is. |
| ~~2.4 The patterns behind the tables~~ | **dropped** | It existed to classify thirteen tables and keep their merge rules honest. With two, the classification is the table definition. Its one durable idea — that a satisfaction mode is a claim about *what the consumer can check* — becomes three paragraphs in §6. |

### 3. Discovery — **verbatim**

§§3.1–3.5 move unchanged. The entry point, resolution and the closure, iterate
not lookup, multiple entries, the distribution is the carrier. Eighteen
examples exercised this and none of it is implicated in the restructure. The
entry-point group stays `native_integration.v1`.

### 4. The sidecar file — **adapted**

§§4.1, 4.2, 4.3, 4.5 verbatim: location, one file for all platforms, the
contract version and its under-declaration rule, `platforms`.

§4.4 is where the redesign's load-bearing rule lands. Today it says everything
fails closed. It must now say **two things**:

- a contribution, a key, or a value in a *closed* vocabulary still fails
  closed — unchanged, and for the reason the first attempt gives;
- **an action whose `kind` a consumer does not implement degrades to a manual
  instruction, and does not fail the build** (V1). Safe here and nowhere else,
  because an action is a `requires` and grants the producer nothing; the worst
  case is a person reading a sentence.

That asymmetry is the whole maintenance argument and needs to be argued in
place, not assumed.

### 5. Structure — **rewritten**

5.1 a complete sidecar, 5.2 every table at a glance. Same job, much shorter
list. Worth writing last, once the tables are settled.

### 6. What the application must supply — **new section, replacing four**

The centre of the change. Replaces §6.2, §6.3, §6.11, §7.2 and §7.3.

- **6.1 Floors** — `min_sdk`, `compile_sdk`, `target_sdk`,
  `core_library_desugaring`, `deployment_target`. Adapted from §6.2 and §7.2,
  which are the same rule written twice.
- **6.2 Values the application supplies** — one table. `id`, `kind`, `key`,
  `reason`, `placeholder`, `conditional`. **A value requires a delivery site**
  (V4): if there is nowhere for the consumer to write it, it is an action.
  Carries over §6.3's inline-reference form and its rules about identity being
  `(distribution, id)` scoped by platform, which the mediated-ads trio proved.
- **6.3 Actions the application performs** — one table. `id`, optional `kind`,
  optional `slot`, `summary`, `reason`, optional `instructions`, `conditional`.
  Carries §7.3's `conditional` semantics unchanged — they are the part of the
  prerequisite machinery that earned its place twice over.
- **6.4 What counts as satisfied** — the three tiers (V7): a value is satisfied
  when its placeholder is gone, an action with a known `kind` by that kind's
  check, an opaque action by acknowledgement. This is where §2.4's one durable
  idea lands.
- **6.5 Kinds** — the per-platform vocabularies, explicitly **non-normative and
  open**. A consumer implements what it can and degrades on the rest.
- **6.6 Instructions** — the new channel and its rule: data shown to a human, a
  consumer never acts on it, and the file is a declared resource so §10's
  per-file hashing surfaces a change between versions.

### 7. Android contributions — **adapted**

Everything from §6 that is a contribution, unchanged in substance:

| From | Status |
| --- | --- |
| §6.1 Ownership | **verbatim** |
| §6.4 Source | **verbatim** |
| §6.5 Gradle dependencies | **verbatim** — including the lock, the checksum, and requested-versus-resolved |
| §6.6 Maven repositories | **verbatim** — bounded participation is the strictest rule in the document and nothing here weakens it |
| §6.7 Permissions and features | **verbatim** — including suppression, which is a policy hook that survives inside the automated core |
| §6.8 Manifest components | **adapted** — the component model is unchanged; `view_links` and `intent_filters` carry; the export approval gate carries |
| §6.9 Shrinker keep patterns | **adapted, and re-examined** — see the open question below |
| §6.10 Manifest meta-data | **adapted** — its shared key space is now shared with §6.2 rather than §6.3 |
| §6.12 Package visibility | **verbatim** |

### 8. iOS contributions — **adapted**

| From | Status |
| --- | --- |
| §7.1 Symbol prefixes | **verbatim** |
| §7.4 Swift packages | **verbatim** — the lock, the revision, binary-target checksums |
| §7.5 Source and `accessed_api_types` | **verbatim** |
| §7.6 `Info.plist` | **adapted** — `values`, `append` and `skadnetwork_identifiers` carry; the rejection lists now point at §6.2 and §6.3 |
| §7.7 Python modules | **verbatim** |
| §7.8 Objective-C categories | **verbatim** |

### 9. Consuming tool requirements — **rewritten**

Same job, renumbered from 1. Six to eight of the first attempt's forty-one go
with the prerequisite tables; two or three arrive with §2.3's scaffolding and
reporting. The expensive obligations are untouched and should be flagged as
such in the introduction, because a reader who is told the specification got
simpler and then meets the locked-graph requirement will feel misled.

Keeps: the three-outcomes table (blocking, advisory, recorded), the thematic
index, and the rule that the body governs where the two differ.

### 10. Recording and review — **adapted**

§9 and §9.1 carry almost entirely: the lifecycle, the report, per-file input
hashes, what resolved artifacts bring with them, the secrets rule, what a
record must contain, packaging collisions. Three additions:

- the record carries **unresolved actions**, not only unsatisfied conditionals;
- an `instructions` file is a hashed input, so changed instructions surface as
  a delta;
- the report distinguishes **automated from remaining**, which is the new
  document's whole thesis and should be visible in its worked example.

### 11. Versioning — **adapted**

Carries, plus the paragraph the redesign needs: the `kind` vocabularies are
open and extend **without a contract minor**, because an unknown one degrades
rather than failing. A minor is still required for a new key, table or closed
vocabulary value.

### 12. Out of scope — **adapted, and shorter**

The reasoning carries — prebuilt binaries in wheels, resources, scripts and
hooks, arbitrary fragments, CocoaPods, compiler flags, build-time uploads.
What changes is that several rows stop being silences (V15): a deferral now has
a form. Lifecycle composition is the largest — *call `init()` early in your
application* is an action, stated and reported, where today it is a gap the
specification can only apologise for.

### 13. Guidance for package authors — **adapted**

§12 and §12.1 carry: declare only what you unconditionally require, split
facades into optional distributions, and the framework-binding exception that
justifies `conditional`. One norm added, and it matters more than it reads:
**do not reach for an action where the automated core covers it.** A manual
action is the cheapest thing for a producer to write and the most expensive
thing for every application to act on. Worth pairing with a report that counts
them.

### Appendices

| | Status |
| --- | --- |
| A: why contributions stay per-distribution | **verbatim** |
| B: why not a build backend | **verbatim** |
| C: prior art | **adapted** — one entry to add, since Cordova's `plugin.xml` is now the *contrast* for instructions as well as for fragments |
| D: declaration reference | **rewritten** — the same job over a much smaller vocabulary; still the contract-minor registry |
| E: a record that satisfies §10 | **adapted** — gains a remaining-actions section |

## Open questions this outline does not decide

1. **Where the requires section goes.** Placed at §6, before the platform
   contributions, because it carries the new model's weight and because a
   reader who understands values and actions reads the contribution sections as
   ordinary. The alternative — provide first, ask second — is the conventional
   order and the first attempt's. Cheap to swap while the document is an
   outline.
2. **Whether a value can live inside an action** (forward test, FT1 and FT3).
   An associated domain and an app group are values supplied *within* something
   the application must separately configure. Splitting them works; it means
   one requirement appears twice with nothing tying the halves together.
3. **Whether `kind` values need a registry.** Open-and-degrading is what makes
   the model cheap and also means two consumers check different things. A
   non-normative list extended without a version bump is probably right, and it
   is the seam where this design could regrow what it replaced.
4. **Whether `[[android.contributes.r8.keep]]` earns its cost.** Its
   `from_dependency` check needs an archive-listing port — one of the four
   obligations that need something only a build tool has — to verify a keep
   pattern's scope. Under an adoption-first target that is a heavy consumer
   obligation for a modest guarantee, and it is the one item in the automated
   core the probe did not re-test.
5. **What happens to the eighteen sidecars and the reference reader.** The
   sidecars are the first attempt's evidence and are frozen with it; the new
   example set starts from the six already converted on paper. The reader's
   architecture survives and its rule set does not, and whether it moves with
   the specification or lags it decides how fast the text can move.
