# Phase 4 — the command line

Four subcommands over the registry, the reader and the corpus. Nothing new is
decided here: the CLI is a retrieval surface for material three earlier phases
put in machine-readable form, and its own documentation says it is not
normative, in the module docstring, in `--help`, and at the foot of every answer
it prints.

## What `explain` needed that did not exist

The brief calls `explain` the highest-value subcommand and says why: it "turns a
failure into a retrievable rule, so an author — human or agent — repairs against
one paragraph instead of re-reading the whole specification". Two of the three
things it emits were already there. `contract/diagnostics-v1.toml` carries the
section, the anchor, the severity and the summary for all 238 ids, and
`contract/v1.toml` carries a description and a section for all 97 declarations.

The third — "a minimal canonical fragment demonstrating correct form, generated
from the registry" — needed material the registry did not hold.

A type answers for sixteen leaves. A closed vocabulary offers its first member,
a defaulted key its default, a boolean the only value it takes. The other
fifty-five need a value nothing about the type fixes: a Maven coordinate, a
permission name, a sentence of `reason` prose. So `example` sits beside
`description`, which is where that kind of material already lives, and is
grounded on `examples/pystripe` and `development/examples/mediated-ads` wherever
those use the key.

**This is the alternative the brief's out-of-scope list already chose.** A
directory of micro-fragment examples is excluded there because "once the
registry exists, `explain` generates fragments on demand. A static directory is
one more thing that drifts." Exemplars in the registry are that, and they are
held to the schema rather than trusted.

### A required key is the easy half

The interesting half is what a fragment may **not** show. `[[constraints]]`
carries nineteen rows and three of them decide whole fragments:

- **§6.3.** `version` is required beside `module` and forbidden beside
  `coordinate`. A generator picking the first alternative alphabetically writes
  `coordinate` and then `version`, which is the one spelling §6.3 rejects. So an
  `exactly_one_of` is settled by what was asked for, not by order.
- **§6.6.** `view_links` is admitted only on a component whose `kind` is
  `activity` and which is `exported_required` — and `exported_required` then
  requires a `reason`. A fragment for `view_links.scheme` has to carry all four,
  and two of the four are values a constraint fixes rather than values the
  declaration offers.
- **§6.1.** Contributing Java or Kotlin requires owning a namespace to put it
  in. The rule is scoped to the *platform table*, which is a table this document
  defines and the registry holds no declaration for — so the generator consults
  constraints on every container down the path, declared or not.

Getting any of these wrong produces a fragment that looks right. That is what
the check is for: `check_spec.py` generates all 97, validates each against the
schema `gen_schema.py` emits, and asserts each carries the key it was asked
about. Three were invalid when the check first ran, and two of the three were
§6.1's.

### One declaration has no fragment, correctly

`android.contributes.features.required` and `android.contributes.components
.exported` are in the registry so a consumer can reject them. They are not
fields; their correct form is their absence, and a fragment showing an absence
shows nothing. `explain` says that in words instead.

## Where `validate` had to draw a line

`validate` reads one sidecar, and one sidecar cannot exercise a rule about two.
Reporting a clean build would be the overstatement §8.5's note names, so the
rules needing a closure are listed as **unchecked**: an owned namespace two
distributions claim, two values targeting one key, a packaging collision, the
§9.1 gate.

The sharper line is the other one. Run against `examples/pystripe`, the first
version reported five blocking findings — every floor unmet, a value unsupplied,
an export unapproved. All five were real requirements and none was the
producer's defect: they are the four obligations §2.2 gives the *application*,
and there is no application here. A producer checking a sidecar before
publishing would have read that output as five things to fix, and there was
nothing to fix.

So they are reported as **outstanding** and are not counted against the
producer. `obligations.ANSWERED_BY_THE_APPLICATION` names the set once;
`tests/test_examples.py` had its own copy of the same four numbers for the same
reason and now reads it from there.

## A packaging defect this phase surfaced — CLOSED

**An installed wheel could not import this package.**

```
$ pip install native_integration-0.1.0.dev0-py3-none-any.whl
$ python -c "import native_integration"
RegistryError: contract/v1.toml was not found beside the package or above it
```

`registry._candidate_directories()` looks beside the module and then in every
parent. In a checkout and in an editable install a parent is the repository
root, where `contract/` lives — which is every context this repository has ever
run in, including CI. In a real install it walks up from `site-packages` and
finds nothing, and `contract.py` calls `registry.load()` at import time, so the
failure is on `import`, not on first use.

The reader has been unusable when installed since Phase 3, and nothing noticed
because nothing installs it non-editable.

Phase 4 makes it visible rather than causing it: `[project.scripts]` puts
`native-integration` on the path, and a console script that raises on import is
plainly broken in a way a library used only from a checkout is not.

**Closed by moving the directory**, which was a decision about where the
published contract lives rather than a CLI change. setuptools includes package
data only from inside the package directory, so `contract/` is now
`src/native_integration/contract/` and `package-data` names it. The alternatives
— copying it at build time, or shipping a second copy — both leave two files
that can disagree.

The loader lost something in the move, and that is the part worth keeping.
`_candidate_directories()` used to look beside the module *and then in every
parent*, and the fallback is precisely why nobody noticed: every context this
repository ran in had a parent holding a copy. A search that succeeds in
development and fails in an install is worse than no search, so
`contract_directory()` now looks in one place.

Two tests guard it, one for each way it can come back — the directory moving out
of the package, and `package-data` ceasing to name it. Both read a fact rather
than building a wheel, which is what makes them cheap enough to keep. The wheel
itself was built and installed once, by hand: `import native_integration`
succeeds, and `native-integration explain ni.req.29` answers from it.

### The corpus is the same shape and the opposite answer

`conformance/` is not in the wheel either, and it stays out. The reason is not
size, though 432 files against a 28-member wheel is not nothing, and it is not
that the subcommand is optional. It is that `run.py` opens by saying it shares
no code with any implementation, because "a harness that shared code with an
implementation would be measuring agreement with that implementation" — and
`conformance/consumer.py` says, in the same breath, that it is deliberately not
part of the library.

Moving the corpus inside the package would make the harness importable as
`native_integration.conformance.run`, from the package whose reader it grades,
and would drag the consumer adapter into the library that must not contain it.
The registry had to move because the package cannot import without it. The
corpus must not, for a reason of the same weight pointing the other way.

What that leaves is one subcommand that needs a checkout, so `--help` says so
rather than letting the failure explain it: the corpus is found automatically
inside a checkout and named by `--corpus` otherwise.

## What Phase 4 did not build

`--explain-failures` and `authoring-guide` are Phase 5's, and are left alone.
