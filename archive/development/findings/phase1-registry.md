# Phase 1 — the declaration registry, and what regenerating Appendix B changed

`contract/v1.toml` is now the machine-readable source of truth for the contract-1
declaration vocabulary. Three generators read it, and `tools/check_spec.py`
fails when any of them would produce a diff against what is committed.

| Artifact | Written by | Contents |
| --- | --- | --- |
| `SPEC.md` Appendix B | `tools/gen_appendix_b.py` | 100 rows, between `<!-- appendix-b -->` delimiters |
| `schema/native-integration-v1.schema.json` | `tools/gen_schema.py` | draft 2020-12, structural validation only |
| `contract/diagnostics-v1.toml` | `tools/gen_error_ids.py` | 231 stable diagnostic IDs |

The registry holds **97 declarations**, **19 between-key constraints**, and
**4 refusal registers** (§7.4's capability keys and consumer-managed keys,
§6.1's reserved namespaces, §9.7's packaging-metadata filenames). Every entry is
contract 1.0; nothing carries a *Since* mark, which matches Appendix B's own
statement that nothing does yet.

**No declaration was added.** The registry covers exactly the Phase 0 inventory.

---

## 1. Decisions this phase was given

Seven ambiguities from `phase0-inventory.md` had to be resolved before a cell
could be written. All were decided by the specification's author.

| | Decision | Where it lands |
| --- | --- | --- |
| **A1** | A floor's platform is normative, on §5.5's terms for a value `kind` | `android.requires.min_sdk` and friends carry `platform = "android"`; `deployment_target` carries `"ios"`. A floor in the wrong table is an unknown key |
| **A5** | The consumer-managed plist keys are closed at four | `[registers.consumer_managed_keys]`, `closed = true` |
| **A7** | Only `platforms` and `products` are non-empty; every other array admits `[]` | `min_items = 1` on exactly those two |
| **A9** | `from_dependency` is **required** on an `[[…r8.keep]]` entry | The two keep forms stay exclusive |
| **A10** | `reason` on an unauthenticated Swift package is optional, accepted, unused | `required_when = "credentials_required"`, no forbidding rule. §7.2 amended — see §4 below |
| **A11** | `acceptance` is an array of strings | `type = "array"`, `items = "string"` |
| — | The registry carries Appendix B's description text; the generator emits one row per declaration | §2 below is the resulting diff, in full |

### A2, A3, A4, A12–A17 are not resolved, and did not have to be

**A4** turned out not to be a blocker: both readings put open key names under
`info_plist.values` and `.append`, so the schema emits an open key space either
way. What is left of A4 is whether §4.4's "this document contains no other"
sentence is accurate. It is a spec-text question and it is still open.

The rest are semantic — they decide code and fixtures, not registry cells — and
Phase 2 and Phase 3 need them.

**A2 deserves a note, because the registry now encodes a position on it.**
§7.4's heading says usage descriptions are not contributable; its rule refuses
them in `values` only, where the capability-key paragraph beneath it is explicit
about covering `values` and `append` alike. The registry encodes **the rule as
written**: `values.refuses` includes `usage_description_suffix`,
`append.refuses` does not. That is not a choice between A2's two readings — it
is standing rule 2. Adding a refusal §7.4 does not state would be inventing a
requirement. If A2 resolves toward the heading, the fix is one list entry in
`contract/v1.toml` and a regeneration.

---

## 2. What regenerating Appendix B changed

The acceptance criterion asks for byte-identical output **or** every difference
listed. Appendix B could not come out byte-identical, and the reason is not a
defect: its rows were not one per declaration. Eighty-two entry cells became a
hundred. Nothing was removed from the document's meaning; the split is
mechanical and the descriptions were rewritten only where one cell had to become
several.

### 2.1 Multi-key rows split — seven cases

Each of these named several keys in one cell and now names one per row. The
description was divided along the same line.

| Was one row | Is now |
| --- | --- |
| `min_sdk`, `compile_sdk`, `target_sdk` | three rows. `target_sdk`'s row keeps the app-wide-behavior warning; the other two say "on the same terms" |
| `java`, `kotlin` | two rows, `.java` and `.kt` respectively |
| `module` + `version` | two rows. `version` gains the explicit "**Required** with `module`" that the combined cell carried implicitly |
| `groups`, `modules` | two rows, each restating "**At least one of `groups`/`modules` required**" — which the combined cell said once |
| `max_sdk_version`, `never_for_location` | two rows. `never_for_location` gains §6.5's actual merge rule (it holds only when **every** declaration asserts it), which the shared "widest need wins" sentence did not state |
| `exported_required` + `reason` | two rows. `reason` gains "**Required when `exported_required` is present**" |
| `key`, `value`, `reason` (`meta_data`) | three rows |
| `package`, `provider_authority`, `reason` (`queries`) | three rows |
| `type`, `reasons`, `reason` (`accessed_api_types`) | three rows |

### 2.2 Nested containers promoted to header rows — three cases

`view_links`, `intent_filters` and `r8.keep` were abbreviated leaf-style rows
(`` `[[…view_links]]` — `scheme`, `host`, … ``) inside their parent's group.
They are now group headers with their own fields beneath, spelled in full:

```
| **`[[android.contributes.components.view_links]]`** [§6.6](…) | Generates the browser-return filter… |
| `scheme`                                                      | **Required.** The only `<data>` attribute… |
```

This is the change most visible to a reader, and it is the one that makes the
table copy-pasteable: the old cell's `[[…view_links]]` is not a TOML header
anyone can type.

### 2.3 Two forbidden keys gained rows

`[[android.contributes.features]].required` and
`[[android.contributes.components]].exported` are keys SPEC.md names and forbids
(§6.5, §6.6). Appendix B described both inside a neighbouring cell and neither
had a row. Both now have one, marked **Not a field** — a reader looking up
`exported` finds out why it is absent instead of concluding the appendix forgot
it.

### 2.4 The `*(both)*` row folded into the two rows it governed

`| *(both)* | A key occupies **one** mode across the effective set… |` had no
declaration to attach to. Its rule is now stated in the `values` row and
referenced from the `append` row. Nothing is lost; the sentence appears once
with a back-reference rather than in a row that names no key.

### 2.5 Cosmetic, and one pre-existing defect

- **A stray blank line split Appendix B into two markdown tables**, immediately
  before `[[ios.contributes.swift_packages]]`. Every renderer treats that as two
  tables with the second missing its header. This is a **pre-existing defect**,
  and the regenerated table is one table.
- The `accessed_api_types` header now reads
  `**[[…]]** [§7.3](…) — a sibling of `src`, not a child of it`, with the
  section link before the aside rather than after it, so every header row has
  the same shape.
- `swift_packages.name`, `python_modules.name` and `python_modules.swift_package`
  gained a **Required.** marker they lacked. All three are REQUIRED in §7.2 and
  §7.5; the appendix simply did not say so.

---

## 3. What the schema does and does not do

`schema/native-integration-v1.schema.json` validates presence, types, closed
vocabularies, array item shapes, `oneOf` forms, integer-versus-string, the
`https` scheme, and the ten between-key constraints. Its own description says
plainly that **passing it is not conformance**.

It does **not** reach namespace containment or closure-wide collision (§6.1),
cross-reference resolution (§5.3's `uses`, §6.6's `from_dependency`, §7.5's
`swift_package`), path escape or symlinks (§4.1), or any merge rule between
distributions. Those need the dependency closure or the wheel's own files, and
they are Phase 3's.

One shape is worth naming because it looks like a hole and is not: the schema's
top level is `"additionalProperties": {"type": "object"}`. §4.4 warns about an
unrecognized top-level *table* — a future platform and a misspelling are
indistinguishable — and rejects an unrecognized top-level key that is not a
table. That is exactly what the constraint expresses.

**Validated against it, all passing:** the seven current-model sidecars under
`development/redesign/examples/`, SPEC.md's own Appendix A, and every whole
sidecar in `README.md`.

**Refused by it, all failing as they must:** 67 cases in
`tools/check_spec.py`'s `MUST_FAIL` table. Each names the instance path and the
JSON Schema keyword — or schema-path fragment — that must do the rejecting, so a
case cannot pass for an unrelated reason and a removed rule cannot hide behind a
second violation in the same fixture.

### `examples/` is not among them, and this is the D7 problem

The Phase 1 acceptance criterion says *"a valid `examples/` sidecar validates
against the generated schema."* It cannot: `examples/pystripe/native.toml` is a
**first-attempt** sidecar (`[[android.requires.application_values]]` with no
`kind`, `[[ios.requires.url_schemes]]`), which Phase 0 recorded as drift **D7**.
Its current-model conversion is
`development/redesign/examples/pystripe/native.toml`, and that one validates.

`CONVERSION.md` says the converted set graduates to `examples/` when the reader
implements this specification — Phase 3. **This is left alone deliberately**;
moving it is out of Phase 1's scope, and doing it silently would make a Phase 3
gate pass for the wrong reason.

---

## 4. The one specification change

§7.2 gained a paragraph, and no rule:

> `reason` is **OPTIONAL** on a package that declares no `credentials_required`,
> and a consumer makes no use of it there. The field is not otherwise reserved:
> §6.4, whose rules this section imports unchanged, requires a `reason` on every
> repository, so a producer writing one here by habit has not made an error.

This states in §7.2 what Appendix B already said ("and unused otherwise"). It
adds no requirement and no vocabulary. The alternative — rejecting a `reason`
where `credentials_required` is absent — would have added a MUST the document
does not have, on the strength of an analogy to §5.2's `key`-on-`inline` rule
that does not hold: a stray `key` gives one application-supplied string two
destinations, and a stray `reason` is inert prose.

---

## 5. Diagnostic IDs

223, in four families, every one keyed to a name rather than a position so that
adding a rule renumbers nothing:

| Family | Count | Example |
| --- | --- | --- |
| `ni.decl.<declaration-id>.<check>` | 151 | `ni.decl.android.contributes.components.kind.value` |
| `ni.constraint.<scope>.<field>.<rule>.<other>` | 19 | `ni.constraint.<platform>.requires.application_value.key.forbidden-if-equals.kind` |
| `ni.req.<n>` | 46 | `ni.req.25` |
| `ni.adv.<Sn>` | 15 | `ni.adv.S13` |

Each carries its section, its anchor, its severity, and the summary Phase 4's
`explain` renders. The 46 requirement IDs carry the profile parsed from §8.1's
own table, which independently reproduces the 29 / 11 / 6 partition Phase 0
verified by hand.

The generator refuses to emit a duplicate ID. It caught one during this phase:
`view_links` carries two `requires_equals` constraints (`kind == "activity"` and
`exported_required == true`), which collided until the ID gained its `other` key
as a final segment.

---

## 6. CI

`tools/check_spec.py` grew four categories, 18 → 22:

| | |
| --- | --- |
| the registry's generated targets are current | the drift guard — all three regenerations, no diff |
| the registry agrees with SPEC.md's anchors and closed vocabularies | every `anchor` resolves to a real heading; the closed set is exactly the five Appendix B names plus §7.4's register |
| every current-specification sidecar validates against the generated schema | 7 sidecars + Appendix A + README |
| the schema refuses what SPEC.md refuses | the 35 negatives |

`.github/workflows/checks.yml` runs the three `--check` modes alongside the
existing three. `jsonschema` is a new dev dependency, declared as the `spec`
extra; the check reports its absence rather than passing quietly, because a
validator that silently does not run is the failure the whole drift guard exists
to prevent.

All 22 categories pass, and the reader's own suite is unchanged at 210 passed,
1 skipped.

---

## 7. For the adversarial review

The gate is a different model, prompted to find declarations the registry
misrepresents or silently widens. The places I would look first:

1. **The floor rows.** A1 was decided as *platform-bound*, which makes
   `deployment_target` inside `[android.requires]` an error. The registry
   encodes that as two concrete-platform id prefixes while every other
   both-platform declaration uses `<platform>`. If A1 was decided wrongly, this
   is where it shows.
2. **`view_links`.** It is the one open key space inside a platform table, and
   the schema gives it `additionalProperties: stringOrInlineValue` plus a
   `propertyNames` pattern. A widening here would let a producer write a
   non-string `<data>` value, which §6.6 refuses.
3. **`info_plist.values` accepting arrays.** §7.4's bullet calls `values`
   "scalar keys", and its TOML-to-plist mapping table lists "array of the above,
   homogeneous". The registry follows the mapping table. If the bullet governs,
   `values` should refuse arrays and the registry is wider than the spec.
4. **`meta_data.value` typed `["string","integer","boolean"]`.** §6.8 says
   exactly those three. The plist side admits floats; the manifest side does
   not, and the two are deliberately different.
5. **The `required` column generally.** Fifteen declarations are `required =
   true`. Appendix B marked some of those only in prose, and three were not
   marked at all before this phase (§2.5).
6. **The refusal registers.** A5 closed the consumer-managed list at four. §5.5
   still spells it "such as", so the specification now says one thing in two
   places — the registry follows §7.4.


---

## 8. The adversarial review, and what it changed

The Phase 1 gate ran and returned 22 findings. **Every one was reproduced before
being acted on**, and all 19 claimed widenings were real: probed against the
committed schema, each accepted a document `SPEC.md` rejects. The review also
caught a counting error of mine — `MUST_FAIL` held **37** cases, not the 35 this
document and two commit messages claimed.

### Closed

| | Was accepted | Now |
| --- | --- | --- |
| 1 | an `info_plist` value naming a `*UsageDescription`, capability, external-reach or consumer-managed key; a `usage_description` naming anything else | three new `[[constraints]]` rules, §5.5 |
| 2 | `coordinate = "x"`, `g:a:+`, `g:a:1-SNAPSHOT`, `g:a:[1.0,2.0)`, `module = "x"`, `at_least = "1-SNAPSHOT"` | grammar patterns on `coordinate`, `module`, and both version bounds, §6.3 |
| 3 | `https://user:pass@host/…` in a repository or package `url` | `forbids_user_info` on both, §6.4 |
| 4 | `platforms = ["ios"]` beside an `[android]` table | a root constraint per platform, §4.5 |
| 6 | an array under `info_plist.values`, which the registry already called scalar | a `plistScalar` `$def`; the generator was ignoring `value_type` |
| 7 | `credentials_required` with no `reason` | the `required_when` the registry recorded and the generator dropped, §7.2 |
| 8 | `symbol_prefixes` and `accessed_api_types` with no contributed Swift | `requires_present`, §7.1 and §7.3 |
| 9 | Java or Kotlin source with no `java_namespaces` | `required_if_any_present`, §6.1 |

Findings 10–15 were registry misstatements and are corrected: `slot` is no
longer marked `passthrough` (§5.5 says nothing in that section is), the
`java_namespaces` trigger is scoped to `keep_classes` under the distribution's
own namespace, `meta_data.value` carries its `@`/`?` resource-reference
condition, an action's identity says `(distribution, platform, id)` and its
`uses` says *same platform*, the Gradle rows state the two forms are exclusive,
and `deployment_target` says it is a **TOML string** where the three rows above
it are integers.

Findings 16–20 were diagnostic-generation defects, all fixed: six requirement
summaries were absorbing §8.4's next theme heading; `view_links` was emitting an
`unknown-key` ID that contradicts §4.4's one stated exception, and had no ID for
the key-shape rule it actually enforces; two failure states had two IDs each;
and one summary rendered TOML `true` as Python `True`.

Findings 21 and 22 were about the negatives themselves, and are the reason the
table grew from 37 cases to **67**. Each case now names where and how it must
fail, so a fixture violating several rules can no longer mask the removal of the
one under test, and the two forbidden keys fail through their own `false`
subschema rather than through the generic `additionalProperties`.

### Not closed, and why

**Finding 5 — TOML integers against JSON numbers — cannot be fixed in the
published schema.** JSON Schema defines `integer` as any number with a zero
fractional part, so *any* conforming validator accepts `min_sdk = 24.0` where
§5.1 says "`24.0` is a float" and rejects it. The registry's types were correct
and the review said so; the limitation is the format's.

Three things were done instead. `tools/check_spec.py` validates with a
TOML-strict type checker — `integer` means a TOML integer, `number` means a TOML
float — which also makes `[1, 1.5]` the mixed-type array §7.4 forbids. The
schema's own `description` records that it cannot carry the distinction. And the
check belongs to a consumer's code, which is where §8 requirement 12 already
puts it, so Phase 3 inherits it rather than it being lost.

**Finding 9 is closed only for its source trigger.** §6.1 also requires
`java_namespaces` when a sidecar contributes producer-sourced components or
keep patterns under its own namespace. Both need namespace containment, which
the work brief reserves for Phase 3 and the schema is explicitly not to reach
for.
