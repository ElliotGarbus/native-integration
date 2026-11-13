# Review 01: the value/action boundary, and what follows from it

A response to the first outside reading of the redesign. It audits the boundary
the probe proposed, answers seven schema questions, and records where the
redesign moves complexity rather than removing it.

Findings continue at **V16**. Where this contradicts
[README.md](README.md) or [forward-test.md](forward-test.md), those files carry
a pointer here rather than being rewritten: the original reasoning is worth more
than a tidy record.

## The boundary, restated

The probe's version (V4) was a schema rule: *a value requires a delivery site;
without one it is an action.* The review's is better, because it says why:

> **Values are things the consumer can place deterministically. Actions are
> outcomes the application must achieve.**

The schema rule falls out of it rather than standing alone, and the semantic
form answers cases the schema form cannot — *is a drawable a value?* has no
answer from "does it have a delivery site" and an immediate one from "can the
consumer place it".

Adopt the semantic form as the principle and keep the schema rule as its test.

## 1. Does the boundary hold? — audit, and three corrections

Every `kind` the probe and the forward test used, against the question *can the
consumer place this deterministically?*

| Case | Probe said | Can the consumer place it? | Verdict |
| --- | --- | --- | --- |
| usage description | value | writes the string into `Info.plist` | **value** ✓ |
| manifest `meta-data` | value | writes the entry | **value** ✓ |
| `Info.plist` account key | value | writes the entry | **value** ✓ |
| manifest placeholder | value | substitutes at build | **value** ✓ |
| inline (a `view_links` scheme) | value | substitutes into a filter it generates | **value** ✓ |
| bundle / asset file | action | no — account-specific, obtained by hand | **action** ✓ |
| app-owned class | action | no | **action** ✓ |
| App Link verification | action | no — a fact about a domain | **action** ✓ |
| URL scheme registration | action | no — plus a forward it cannot see | **action** ✓ |
| app extension target | action | no | **action** ✓ |
| **resource (notification icon)** | *open question* | **no** — a drawable is authored, not placed | **action** ✗ corrected |
| **entitlement with a value** | *value* (FT1) | **partly** — it can write the file, it cannot get the entitlement into the provisioning profile | **action + `uses`** ✗ corrected |
| **app group identifier** | *value* (FT3) | **partly** — same, across three targets | **action + `uses`** ✗ corrected |

> **V16 — the boundary holds, and it corrects three of the probe's own
> placements.** Two of them were the probe's open questions and one was a
> mistake. The drawable is the clean case: *does it have a delivery site* gave
> no answer, *can the consumer place it* gives one immediately. That a rule
> proposed in the probe overturns three of the probe's own decisions is the best
> evidence available that it is doing work rather than describing what was
> already there.

The entitlement correction matters most, because FT1's whole point was that the
first attempt's key-only check is a **false pass** — an application that enables
Associated Domains and lists no domains satisfies it completely. Making it a
value fixed the false pass and broke the boundary. The correct shape keeps both:

```toml
[[ios.requires.application_value]]
id = "adjust_link_domain"
kind = "inline"
placeholder = "applinks:<TODO: your Adjust link domain>"
reason = "Your Adjust link domain, from the dashboard."

[[ios.requires.application_action]]
id = "adjust_associated_domains"
summary = "Enable Associated Domains and add the Adjust link domain"
reason = """\
The entitlement must be on the App ID and in the provisioning profile before it \
can be signed, and the domain must serve an apple-app-site-association file."""
uses = ["adjust_link_domain"]
slot = "com.apple.developer.associated-domains"
verify = { kind = "entitlement", key = "com.apple.developer.associated-domains" }
```

The value is scaffolded and blocked on; the action states the outcome; `uses`
ties them; `verify` lets a capable consumer notice the key is missing entirely.
Nothing claims to have checked what it cannot check.

## 2. Composition semantics — not needed in v1, and the reason is structural

The review asks for a minimum design for values targeting array-valued keys, and
warns against teaching the model which Apple keys hold arrays. The right answer
is smaller than a `mode` field: **after the audit, no application-supplied value
targets an array.**

| Array-valued target | What it actually is |
| --- | --- |
| `LSApplicationQueriesSchemes` | producer-known → a **contribution**, with `append`'s union merge already specified |
| `SKAdNetworkItems` | producer-known → a contribution, de-duplicated on the identifier |
| `UIBackgroundModes` | grants a capability → an **action** |
| `com.apple.developer.associated-domains` | needs provisioning → an **action** (§1 above) |
| `com.apple.security.application-groups` | needs provisioning, across targets → an **action** |
| every value `kind` that survives the audit | scalar: one string, one key |

Arrays live on the two sides where merge rules already exist or are not needed:
producer-known contributions, which the automated core has merged since the first
attempt, and application-owned outcomes, where the *application* does the merging
and contention is reported through `slot`.

So v1 needs one rule, not one mechanism:

> Two values targeting the same `(kind, key)` coalesce when their supplied
> content is equal and **fail, naming both distributions**, when it differs.

That is §6.3's delivery rule from the first attempt, unchanged, and it is
already implemented.

> **V17 — a composition mechanism for values is unnecessary while the boundary
> is enforced, and needing one would be evidence the boundary had slipped.** The
> trigger for revisiting is specific: an application-supplied value that must be
> placed deterministically into a key that legitimately holds several
> contributors' entries. None of the twenty-three cases examined produces one.
> If it appears, `delivery = { …, mode = "append_unique" }` is the shape, and
> two modes are enough.

## 3. `verify` — **removed from v1**

> **Decision.** `verify` does not go into version 1, in any form. The analysis
> below stands and reaches the wrong conclusion; what it missed is that
> separating `verify` from the action does not resolve the dilemma underneath
> it, it only makes the dilemma legible.
>
> **Either a check can satisfy an action, or it cannot.** If it cannot, the
> action blocks on acknowledgement anyway and `verify`'s whole contribution is
> a better error message. If it can, a partial check reports *satisfied* for a
> requirement that is not met — which is FT1's false pass, generalised and made
> systematic, and which the first attempt already forbids in terms: *"A consumer
> MUST NOT treat that inspectable half as sufficient on its own, since it would
> only prove half of what was asked for."*
>
> Of the first attempt's checks, exactly two are complete — a packaged file's
> presence, and a plist key holding a stated value. Four normative concepts to
> keep two checks, one of which the consumer can perform anyway because it is
> the party assembling the bundle.
>
> **What is given up**, stated plainly: four sound checks
> (`plist_capabilities`, `application_files` on both platforms, `resources`).
> The mistake they would have caught is *acknowledged but not done* — a false
> claim rather than an omission, since a forgotten action still blocks. It
> surfaces between a `codesign` error at archive and a white notification icon
> in production, which is the range the first attempt already accepts for the
> four tables it made acknowledgement-only.
>
> **What is gained**: a consumer that never tells anyone they are finished when
> they are not. A missed check fails the author who made the false claim, and
> §9's record proves the claim. A false pass fails someone who did everything
> they were asked.
>
> **Revisit when** support traffic shows the pattern — applications
> acknowledging a packaged-file requirement and failing on it — rather than on
> argument. That is the falsifiable form, and it needs a consumer with users
> before it can produce evidence.
>
> Original reasoning follows.

The probe put `kind`, `key` and `value` on the action itself. That conflates two
questions, and the review is right to split them.

With `kind` on the action, an unrecognized value is ambiguous: does the consumer
not understand **the requirement**, or only **the check**? The fail-open rule has
to answer that, and it cannot while one field means both.

Separated, it is unambiguous and the fail-open surface shrinks to one field:

- the **action** is always understood, because it is prose addressed to a person;
- `verify` is an optimization, and an unknown `verify.kind` means *this consumer
  cannot check it*, never *this sidecar is invalid*.

It also stops `key` and `value` from looking like properties of the requirement
when they are properties of the checker, and it lets `verify` grow later without
touching the action's shape.

**One practical correction.** The review's example is not valid TOML: inline
tables must be on a single line, and no newlines are permitted between the
braces. Every example must be written

```toml
verify = { kind = "entitlement", key = "aps-environment" }
```

which also serves as a size limit worth keeping — if `verify` grows past about
three fields it will not fit on a line, and that is the signal to ask whether the
check belongs in the specification at all.

> **V18 — separating `verify` makes the fail-open rule precise.** It is the
> difference between "unknown things degrade" as a slogan and a rule with one
> named field as its surface.

## 4. `slot` — opaque, platform-derived, compared only for equality

The review's principle is right and the probe's spelling was wrong. The probe
invented `ios:extension:notification_service`. The stable name already exists:
Apple's own extension point identifier, `com.apple.usernotifications.service`,
which is **what a built target carries in its own `Info.plist`** — the argument
the first attempt already made when it opened `app_extensions.kind`.

So:

- a `slot` is an **opaque string**; a consumer compares equality and never
  interprets;
- it **SHOULD** be the platform's own identifier for the contended surface where
  one exists — an extension point identifier, an entitlement key, a manifest
  attribute — and the specification enumerates none of them;
- two actions in one effective set sharing a slot are **reported together**,
  naming both distributions. That is disclosure, not a failure: the application
  merges, which is what iOS's one-target-per-kind rule demands anyway.

The failure mode is honest: two producers spelling a slot differently means a
contention goes unreported, which is exactly the status quo before `slot`
existed. It cannot produce a false collision, only a missed one.

> **V19 — `slot` carries no vocabulary, and the specification must not grow
> one.** Deriving from platform identifiers is what keeps it out of the
> maintenance surface; a curated list of slot names would be the taxonomy
> returning under a new name.

## 5. The action shape for v1

| Field | In v1? | Why |
| --- | --- | --- |
| `id` | **yes** | the join key, `(distribution, id)` |
| `summary` | **yes** | one line; what a report renders |
| `reason` | **yes** | required everywhere else in the model |
| `instructions` | **yes**, inline string | HC2's XML is fifteen lines and fits; a file path adds resource rules for nothing yet |
| `acceptance` | **yes** | see §6 — the idea that makes *manual* mean something |
| `uses` | **yes** | without it §1's split requirements are incoherent |
| `slot` | **yes** | §4 |
| `conditional` | **yes** | carries from the first attempt, where it earned its place twice |
| `template` | **defer** | see below |
| `reference` | **defer** | a URL fits in `instructions`; nothing in the case set needs it structured |
| `destination_hint` | **defer, and the one to resist** | a producer does not know the consumer's project layout, and guessing it dates the declaration — the failure mode §2.3's class name was accepted with eyes open, for a much better reason |

**`template` deferred, with a trigger.** It is application-owned starter code
shipped in a wheel: it needs path and encoding rules, it raises a licensing
question the specification has never had to answer, and every case in the set —
`WXEntryActivity`, `NotificationService.swift` — is short enough to sit in
`instructions`. The trigger is a producer whose starter code is long enough that
inlining it is absurd. That is a real possibility and not a hypothetical one, so
the deferral should be written as a deferral.

## 6. `acceptance` — the idea, and the line it must not cross

The review's framing is the strongest new idea since the probe: **manual should
mean the consumer does not own the change, not that the requirement is
unstructured.**

```toml
acceptance = [
  "WXEntryActivity exists under <applicationId>.wxapi",
  "The activity implements IWXAPIEventHandler",
  "The activity is declared in the Android manifest",
  "WeChat callbacks are forwarded to the SDK",
]
```

Four properties follow, and the fourth is the one that matters most here: a
requirement stays useful **even where the specification does not understand the
platform feature involved**. That is the same property the fail-open rule buys,
reached from the other end.

**The line, and it needs stating normatively.** An acceptance criterion is a
statement of **end state**, never of operation:

| Allowed | Refused |
| --- | --- |
| "The activity is declared in the Android manifest" | "Insert an `<activity>` element into `AndroidManifest.xml`" |
| "The extension target shares an app group with the application" | "Add `com.apple.security.application-groups` to `Extension.entitlements`" |

Without that rule, `acceptance` becomes the build-operation DSL the review's
point 8 refuses, one helpful criterion at a time. With it, criteria are
checkable by a person, by an agent, or eventually by a consumer, and none of them
needs the specification's permission.

`acceptance` and `verify` are deliberately not the same thing and are allowed to
overlap: `verify` is what **this consumer** can check today; `acceptance` is the
statement of done for whoever does the work. A consumer with neither falls back
to acknowledgement.

> **V20 — `acceptance` is what makes *manual* a first-class outcome rather than
> a polite word for unspecified.** It is also the cheapest field in the
> proposal: an array of strings, no vocabulary, no parser, no maintenance.

## 7. What else becomes an action, and one thing that could go

Re-running the audit over the whole first attempt, the constructs that become
actions are the thirteen already identified in [README.md](README.md), plus the
two corrected in §1. Nothing else does — every remaining contribution is
producer-known and deterministically placed, which is what the automated core is
for.

One removal candidate the review's standard exposes: **`swift_symbol_prefixes`**
(§7.1). It is guidance a consumer cannot enforce, its own section says so, and
its only consumer-side use is attributing a duplicate-symbol error. Under *fewer
normative concepts*, it is a paragraph in the contributed-source section rather
than a declared key. Not urgent, and worth deciding rather than inheriting.

Three policy hooks stay inside the automated core, and the new document should
say so plainly rather than implying the core is policy-free: permission
suppression, export approval, and repository scope bounding.

## 8. Where the redesign moves complexity rather than removing it

Asked for honestly, and there are four places.

1. ~~The taxonomy moves into `verify.kind`.~~ **Retired by §3's decision.**
   This was the most likely way the redesign fails — consumers competing on how
   many kinds they implement, regrowing the taxonomy informally outside the
   document where nobody can audit it. Removing `verify` removes it.
2. **Prose quality replaces schema coverage.** A bad `instructions` block is
   worse than a missing table, because it looks complete. The first attempt
   could be wrong in ways a checker caught; this cannot.
3. **Verification moves to the human or the agent.** `acceptance` is a genuine
   transfer of work, not an elimination of it. It is a better place for the work
   — the party doing the change evaluates the criteria — but the claim should be
   *relocated*, not *removed*.
4. **The consumer's expensive obligations do not move at all.** Locked
   resolution with per-artifact checksums, packaging collisions, reading
   resolved `.aar` manifests, the record and its acceptance gate.

## 9. The security boundary around instructions

The first attempt's `reason` fields are short, advisory, and read inside a
report. `instructions`, `acceptance` and a future `template` are longer,
actionable, and — this is new — may be read by an **agent acting with the
application author's authority**. That is a channel by which producer-supplied
text becomes changes to an application, and the specification has never had one.

Three parties, stated separately:

- **The consumer never acts.** It renders, records and hashes. It does not
  execute, apply, fetch, or follow. This is §2.1's *declarations are data* rule
  reaching a new kind of data, and it should be written where the field is
  defined rather than left to inference.
- **A human or agent acting for the application author may act**, with that
  author's authority, and should treat the content as **untrusted input from a
  third party** — not as instruction from the person they are working for.
- **The producer is the untrusted party**, and the review gate is what bounds
  it: instruction text is a hashed input, so a change between versions surfaces
  as a delta in the record. **That is load-bearing.** Without it, `instructions`
  is a channel that changes silently on a version bump, which is precisely the
  drift §9 exists to prevent for permissions and dependencies.

## 10. What is actually simpler, in three parts

The review is right that these must be distinguished, and the honest scoring is:

| | Change | Size |
| --- | --- | --- |
| **The interoperability model** | thirteen prerequisite tables to two; §2.4's classification section gone; one satisfaction story in three tiers instead of eleven per-table rules | **large** |
| **Producer authoring** | one table to learn instead of choosing among seven iOS prerequisite types; a requirement that has no table is now stateable instead of unstateable | **large** |
| **Consumer implementation** | six to eight of forty-one requirements go, two or three arrive; every expensive obligation survives | **modest** |

And the fourth axis, which is the one the redesign was undertaken for and does
not fit those three:

| **Maintenance** | a new Apple or Android construct needs a `verify.kind` at most, and usually nothing | **large** |

That is a substantial success, and it is a different claim from "the
specification is simpler to implement". The new document should make it in those
words.

## 11. What removing `verify` does to the rest of the model

Larger than the field it deletes, and it corrects the probe's headline finding.

**V1 claimed that failing open on an unknown `kind` was the load-bearing
maintenance property.** It is not. What delivers the maintenance win is that
**an action is prose and carries no vocabulary at all** — a new Apple or Android
construct needs no specification change because the action describes it in
words. The fail-open rule was invented to protect an open `kind` that the probe
had put on the action, and once `verify` is gone there is no open vocabulary in
the requires section for it to protect:

| Field | Kind of thing | Rule |
| --- | --- | --- |
| `application_value.kind` | delivery semantics — the consumer writes something | **closed**, fails closed (the review's own division) |
| `slot` | opaque contention key | compared for equality, never interpreted |
| `summary`, `reason`, `instructions`, `acceptance` | prose | not a vocabulary |

So **§4.4 needs no new rule.** The first attempt's *everything fails closed*
stands unchanged, and the redesign's maintenance property comes from a table
that has nothing to enumerate rather than from an exception carved into the
rule. One fewer normative concept, and the concept removed is the one that
would have been hardest to defend.

> **V21 — the redesign needs no change to §4.4, and V1 is withdrawn.** A rule
> proposed to protect a field, deleted along with the field. Worth recording
> because the probe presented that rule as the centre of the design, and the
> centre turns out to be something simpler that was true all along.

## Satisfaction, reduced to two tiers

V7 described three. With `verify` gone there are two:

| Form | Satisfied when | Strength |
| --- | --- | --- |
| value | the placeholder is gone | strong, and machine-checked |
| action | the application acknowledges by `(distribution, id)` | a claim, recorded and attributable |

A consumer **MAY** still report what it inherently knows — it is the party
assembling the bundle, so it knows whether a named file is in it — and the new
document should say so where it defines actions. Removing the mechanism is not
a prohibition on diligence, and leaving that unsaid would read like one.

## Revisions to earlier findings

| Finding | Change |
| --- | --- |
| **V3** (`slot`) | superseded by **V19**: slots are platform-derived and carry no vocabulary. The probe's `ios:extension:notification_service` spelling is withdrawn. |
| **V4** (delivery site) | restated semantically as §1's boundary; the schema rule survives as its test. |
| **V8** (Airship's two paths) | *"the model should have no way to say either/or"* is too strong. Corrected: **v1 omits alternatives deliberately**, the producer chooses, and the case for revisiting is a vendor whose two paths are genuinely equivalent and both common. |
| **V1** (fail open) | **withdrawn** — see §11. The maintenance win is that actions carry no vocabulary; there is nothing left to fail open on. |
| **V7** (three tiers) | reduced to two: placeholder for values, acknowledgement for actions. |
| **V18** (`verify` as a block) | **withdrawn** with `verify` itself. |
| **V12** (entitlement values) | the diagnosis stands — the first attempt's key-only check is a false pass. The remedy was wrong: it is an action carrying a value by `uses`, not a value alone. |
| **FT1, FT3** | the fragments in [forward-test.md](forward-test.md) are superseded by §1's shape. |

## Still open

- ~~Whether `verify` and `acceptance` may reference each other.~~ Moot: there
  is no `verify`, and `acceptance` is the only structured statement of done.
- ~~Where the non-normative `kind` list lives.~~ Moot for actions. Value kinds
  remain a **closed** set that fails closed, because a consumer must know how
  to place a value.
- **`[[r8.keep]]`'s archive-listing port**, still the one automated-core item
  that has not been re-tested against an adoption-first target.
