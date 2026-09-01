# Phase 5 — the authoring procedure, and getting it to travel

## What the gate is for

The review on this phase asks one question: does §12.2 introduce normative
content that was not already in the specification? The section is guidance about
guidance, and a procedure is the shape in which a new rule is easiest to smuggle
— a step reads naturally as an instruction, and "do this first" is one word away
from "you must do this first".

Two answers to that question, one for a reader and one for CI.

### Every step, and where it comes from

| Step | Decides | Stated in |
| --- | --- | --- |
| 1. Inventory | What the vendor's documentation asks for, per platform | [Goals](../SPEC.md#goals) — "the things an application author would otherwise transcribe out of a README" |
| 2. Classify | `owns` / `requires` / `contributes` | [§2.1](../SPEC.md#21-design-principles)'s table, and its own worked examples of each |
| 3. Test a contribution | Whether material may be automated at all | [Goals](../SPEC.md#goals)'s three-part test; [§2.1](../SPEC.md#21-design-principles) makes it the decision between the last two categories |
| 4. Choose a shape | Floor, value or action | [§5](../SPEC.md#5-requirements-on-the-application)'s table and its boundary rule — "what the consumer can place deterministically" |
| 5. Fall back to an action | What to do when nothing fits | [Non-goals](../SPEC.md#non-goals) (this document models no platform exhaustively); [§2.1](../SPEC.md#21-design-principles) — "state it as an action rather than forcing it into a shape the consumer cannot honor" |
| 6. Decide conditionality | Separate distribution, or `conditional = true` | [§12](../SPEC.md#12-guidance-for-package-authors) for a facade with a seam; [§12.1](../SPEC.md#121-framework-bindings-where-this-guidance-does-not-apply) for a binding without one |
| 7. Check the declarations | That every key exists and is spelled right | [Appendix B](../SPEC.md#appendix-b-declaration-reference); [§4.4](../SPEC.md#44-unknown-declarations-fail-closed) is why a misspelling is fatal rather than ignored |
| 8. Confirm what shipped | That the artifact carries what the source tree does | [§4.1](../SPEC.md#41-location-and-name), [§4.2](../SPEC.md#42-one-file-for-all-platforms), [§3.2](../SPEC.md#32-resolution), [§3.4](../SPEC.md#34-one-entry-per-distribution) |

Nothing in the table is new. What is new is the **order**, and the claim that
the order is worth writing down: the guidance is complete and lives in five
sections, so an author meets it as a set of principles and has to invent the
sequence themselves. The place they invent it wrong is step 3 — the
contribution-versus-requirement boundary — which is decided by a test stated
under Goals and applied in §2.1, two sections away from §12 where an author
looking for authoring advice starts.

### And the property CI holds it to

**§12.2 uses no RFC 2119 keyword in its own voice.** 1,024 words, fifteen
distinct section anchors, and every obligation it mentions is a citation or a
quotation. That is mechanically checkable, so `check_spec.py` checks it: quoted
spans are stripped first, since quoting an obligation is attribution rather than
assertion, and a section that stops citing fails too.

An edit that adds `**MUST**` or `**SHOULD**` to §12.2 now fails the build.

**The check was written twice, and the second one is the finding.** The first
version's `\b` had been mangled into a literal backspace on the way into the
file, so its pattern matched nothing and it passed everything, including a
deliberately injected `**MUST**`. It reported `ok` for two runs before the
injection test caught it. A checker that cannot fail is worse than no checker,
because the green line is read as evidence — which is exactly what
`tools/citations.py` was written to say about its own predecessor, one phase
earlier, and it happened again anyway.

## Getting it out of this repository

§12.2 is useless where it sits. The author who needs it is in *another*
package's repository, and will have neither `SPEC.md` nor this checkout.

- `native-integration authoring-guide` prints it. The text is copied into
  package data by `tools/gen_authoring_guide.py`, byte for byte, with a
  `--check` in CI — the same generate-and-guard pattern as Appendix B, the
  schema and the diagnostic ids, and for the same reason. Reading `SPEC.md` off
  disk would have worked here and nowhere else, which is precisely the mistake
  `contract/` was making until Phase 4 found it.
- `--template` prints a commented `native.toml` skeleton. Everything but
  `contract` is commented out, so what it emits is a valid sidecar rather than a
  valid-looking one, and its header carries the specification's URL: a file
  copied into another repository has nothing else to say where its rules are.
- `validate --explain-failures` pairs each finding with the step that decides
  it.

### The pairing is derived twice before it is looked up

A finding carries the section its rule comes from, and every step of §12.2 says
which sections it draws on, so the first match is exact and needs no table.

It is also almost never the one that fires. A numbered requirement's diagnostic
carries **§8.4** — where the requirement is *indexed*, not where its rule is
*stated* — so the sections cited in the requirement's own summary are tried
next, and that is what resolves most findings. `BY_SECTION` is the last resort
and the only hand-written table in this phase; it maps the document's structure
onto the procedure's (§5 is a requirement, so step 4; §6 and §7 are
contributions, so step 3) rather than listing requirements one by one.

## The template found a defect in `validate`

A sidecar with nothing but `contract = "1"` was reported as blocking, on
requirement 38: *this integration has never been accepted, and there is no
stored record.* In the same output, `validate`'s own note said the §9.1
acceptance gate had gone unchecked. Both cannot be true.

§9.1 makes acceptance the **application's** act, and `validate` reads one
sidecar with no application and no stored record. A producer has nothing to
accept, so requirement 38 belongs with the four obligations already reported as
outstanding rather than as the producer's defects, and the note no longer claims
a rule it does in fact evaluate.

`examples/pystripe` never showed this, because `_first_build` suppresses the
gate when other findings already block — and the example raises four. A *clean*
sidecar was needed to surface it, and the template is the first one this
repository has ever produced.

## What Phase 5 did not do

- **`AGENTS.md` is the minor half, and is one page.** Two playbooks that point
  at the validator and the corpus rather than restating a rule, plus three
  notes on changing this repository. Anything longer would become a second
  specification that nobody regenerates.
- **§12.2 stops where the specification does.** It cannot tell an author whether
  a vendor's SDK needs a permission, and it does not decide the
  contribution-versus-action boundary — the three-part test does. What it
  removes is the guessing about which question to ask next.
