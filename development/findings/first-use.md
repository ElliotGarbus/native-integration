# First use, outside this repository

Everything before this was written against fixtures and worked examples inside
the repository, run from a checkout. This is what came out of the first hour of
installing the package into a clean environment and writing a sidecar by hand.

Three defects, all of which 561 tests missed for the same reason — the suite
runs from a checkout, against files it authored — and one observation about the
specification that is not a defect and is not this reader's to resolve.

## The observation: an editable install cannot be read, by design

A producer iterating on their own sidecar reaches for `pip install -e .`. Under
this convention that does not work, and the way it fails is worth setting down
because the cause is a rule rather than a bug.

```
$ pip install -e ./pyvendor
$ python build.py
[blocking] pyvendor: entry point names `pyvendor._native`, but
    …/site-packages/pyvendor/_native is not a readable directory  (§8.4, ni.req.4)
```

**The reader is correct.** [§3.2](../../SPEC.md#32-resolution) requires exactly
this: *"When a distribution's resources cannot be materialized or read, the
consumer **MUST** fail, naming the distribution, rather than skipping it."* It
fails, and it names the distribution.

**The mechanism is what cannot see the file.** §3.2 fixes two ways to reach a
sidecar — `Distribution.locate_file()` and `Distribution.files` — and under a
PEP 660 editable install neither one reaches it:

| | Under an editable install |
| --- | --- |
| `locate_file("pyvendor/_native")` | returns a `site-packages` path that does not exist |
| `Distribution.files` | lists `__editable__.pyvendor-1.0.0.pth`, `__editable___pyvendor_1_0_0_finder.py`, and `dist-info/…` — and no sidecar at all |

The real location is inside `__editable___pyvendor_1_0_0_finder.py`, in a
`MAPPING` dict. That is a setuptools implementation detail rather than an
interface, and the only supported way to consult it is to let the import system
do so — which [§3.2](../../SPEC.md#32-resolution) forbids without qualification:
*"**Nothing is imported, ever.**"*

**So the prohibition and the editable install are in tension, and the
prohibition is right.** A consumer runs on a desktop build host, and a
distribution targeting Android or iOS may not be importable there at all;
that note is why the rule exists, and it is a stronger reason than developer
convenience. The cost lands on the producer's inner loop: every sidecar edit
needs a reinstall before a consumer sees it, on exactly the workflow
[§12.2](../../SPEC.md#122-sidecar-authoring-procedure) step 8 prescribes.

**Recorded, not resolved**, under standing rule 3. Three readings are available
and this reader should not choose between them:

1. **Nothing to change.** Reinstalling is the cost of a resolution mechanism
   that never imports, and `native-integration validate <path>` already reads a
   directory directly, so the inner loop has a tool that does not need an
   install at all. The gap is only in the *consumer* loop.
2. **§3.2 could name a third mechanism** — `importlib.resources.files()`, which
   does consult the import system's finders and would resolve an editable
   install. It resolves a *package*, so using it means the consumer has imported
   the producer's package, which is the thing §3.2 forbids. Whether
   `importlib.resources` on an unimported package counts as importing is a
   question about CPython's machinery, not about this document.
3. **§3.2 could say what it expects of an editable install** — even a note
   saying a consumer is not required to support one would settle it, and would
   tell a producer to expect the reinstall rather than discover it.

The third is the cheapest and changes no obligation. It is still a specification
edit, and belongs to whoever owns the specification.

## The three defects

All three were found by using the tool, and none by the corpus. They share a
shape: the thing that broke was outside what a fixture can express.

**A finding was classified by the number it rolls up to.** §8.4 states
requirements as sentences, so one number is several rules — requirement 29
covers both an export only the application can approve and the structural
component rules a producer must satisfy. A `reason` missing beside
`exported_required` was reported as *"outstanding, for the application to
answer"*, and the run exited 0 on a sidecar with a missing required key. It is
now classified by whether a registry rule fired, which is a property of the
document rather than of the number.

No fixture pairs a structural violation with a requirement number that also
carries an application obligation, so no fixture could have caught it. Writing a
sidecar the way a producer would is a different sampling of the space.

**`authoring-guide.md` shipped in no wheel.** Phase 4 moved `contract/` into the
package and named `contract/*.toml` in `package-data`; Phase 5 put a `.md` file
beside the registry and no glob named it. The command worked from a checkout and
failed from an install — *the same shape as the defect Phase 4 existed to fix,
one file extension later.* The guard now matches the glob against what is
actually in the directory; the version that asserted the glob's shape passed
while the file was unshipped.

**Findings printed their message and dropped their detail.** *"the application's
`min_sdk` is below the declared floor"* reads as though a configured value were
too low; the detail said `declared 36` and `the application configures none`,
which is a different problem with a different fix. A reader had to open the JSON
to tell which one they had.

## And one in the worked consumer

`build.py`, the toy build tool written for the playground, did this:

```python
sources = discover(closure=closure, findings=findings)
if not sources:
    return 0        # nothing to do
```

Discovery had produced a blocking finding naming the distribution. Returning
early discarded it and exited 0 — turning a producer's entire native surface
into silence, which is the failure §3.2's *fail, do not skip* rule exists to
prevent. **An empty result is not the same as no problem**, and the early return
is the natural way to write it.

It is not in this repository, and it is recorded here because it is the mistake
a consumer author is most likely to repeat: the reader reports the finding
correctly, and a consumer can still throw it away.
