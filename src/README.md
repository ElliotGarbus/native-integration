# The reference reader

`native_integration` is a reader for [the specification](../SPEC.md): discovery,
parsing, validation, resolution and recording, so that a build tool gets §8's
consumer obligations as code paths rather than as prose it has to remember to
implement.

It is **not** a build tool. It never writes a Gradle or Xcode project, never
resolves a Maven coordinate, and never runs anything. It tells a consumer what
the application's dependency closure declares, what the application still has
to answer, and what changed since the last time anyone accepted it.

Two audiences, and they use different halves of it. If you are **writing a
sidecar**, you want [the producer's workflow](#the-producers-workflow) and
[the command reference](#the-command-line); the library never comes into it. If
you are **writing a build tool**, you want
[the consumer's workflow](#the-consumers-workflow) and [the API](#the-api)
after it, and the command line only to test what you built. Either way,
[for a coding agent](#for-a-coding-agent) is what changes when an agent is doing
the work rather than a person — which is less than you might expect.

## Why this exists

The specification is forty-six numbered requirements across twelve sections. Two
people have to act on it, and without something executable both act on it from
memory.

**A producer** — the maintainer of a Python package that binds a native SDK —
has to turn a vendor's integration README into declarations. The failure mode is
not misreading a rule; it is *inventing a shape*: forcing an item into a
contribution the consumer cannot honor, because that is the declaration that
looked closest. [§2.1](../SPEC.md#21-design-principles) calls the result "a
partial automation that looks complete", and it is worse than a clear task,
because the build succeeds.

**A consumer** — the author of a build tool — has to implement §8. The failure
mode there is claiming a requirement whose second clause was never written: a
requirement is a sentence, not a bullet list, and "report the merge" sits inside
requirement 28 beside two rules that are structural. Twice during this
repository's own development a requirement was claimed and not satisfied while
every test passed.

This package answers both from the same material. **The library** turns §8's
obligations into code paths a build tool calls, rather than prose it has to
remember to implement. **The command line** turns the specification into
something you can query: a failure resolves to the one paragraph that decides
it, and a draft sidecar can be held to the document before it ships.

## The producer's workflow

You maintain a Python package that binds a native SDK, and you are adding a
sidecar to it. **This half is the command line** — you are writing TOML, not
Python, and nothing here imports the library. The loop is **draft, validate,
explain, fix**, and it ends against the built artifact rather than the source
tree.

**1. Start from the procedure, not the reference.**

```bash
native-integration authoring-guide             # §12.2's eight ordered steps
native-integration authoring-guide --template  # a skeleton to fill in
```

The step that matters most is the three-part test, which decides whether an
item is something you *contribute* or something you *require* of the
application. Getting it wrong produces a sidecar that validates.

**2. Validate the draft.** Point it at the directory holding `native.toml`:

```
$ native-integration validate src/pyvendor/_native
pyvendor  —  src/pyvendor/_native
  [blocking] (android) ni.decl.android.contributes.features.required.forbidden
      `android.contributes.features.required` must not be declared by a producer
      at android.contributes.features[0].required
      native-integration explain ni.decl.android.contributes.features.required.forbidden
```

Every finding carries the command that explains it. The location is the path
into your document, not a line number, because that is what you search for.

**3. Explain what you do not recognize.**

```
$ native-integration explain ni.decl.android.contributes.features.required.forbidden
ni.decl.android.contributes.features.required.forbidden   [blocking]

  §6.5   SPEC.md#65-permissions-and-features

  `android.contributes.features.required` must not be declared by a producer

  no fragment: this key is not a field. Its correct form is its absence, which
  no fragment can show
```

One paragraph, not a re-read of §6. Where the answer *is* a declaration rather
than a refusal, it comes with a minimal fragment in correct form — which is
usually faster to copy than to derive from the reference.

**4. Fix and repeat** until the producer's half is clean:

```
$ native-integration validate src/pyvendor/_native
pyvendor  —  src/pyvendor/_native
  no finding, for the rules one sidecar can be held to

  not checked here: one distribution was read, so every rule that needs the
  whole dependency closure went unchecked …
```

**Read the `not checked here` lines before believing the first one.** A clean
result means clean *for the rules one sidecar can be held to*. Whether your
namespace collides with another package's, and whether the application can
answer what you ask, are questions this cannot reach.

Findings that *are* the application's — a floor its configuration must meet, a
value only the developer knows — appear under `outstanding, for the application
to answer`. They are real requirements and none of them is your defect, so they
never fail the run. `--explain-failures` names the step of §12.2 behind each
one.

**5. Validate the artifact, not the source tree.**

```bash
python3 -m build
native-integration validate dist/pyvendor-1.0.0-py3-none-any.whl
```

This is the step worth the discipline. A sidecar that is correct in `src/` and
missing from the wheel is the one failure this convention cannot report — a
consumer finds no sidecar, concludes the distribution declares nothing, and
builds an application without it.

## The consumer's workflow

You are making a build tool honor sidecars. **This half is the API, not the
command line** — the CLI is how you test what you built, and nothing in it is
something a build tool would shell out to.

**1. Read [§8](../SPEC.md#8-conformance)** — forty-six numbered requirements, a
core profile plus one per platform. §8.1 makes conformance per-platform, so an
Android-only tool can conform without implementing anything for Xcode.

**2. Call `discover()`, then `read()`.** `discover()` is §3's discovery step —
it walks the entry-point group across installed distributions and returns the
sidecars whose distribution is in your `closure`, ignoring everything else in
the environment. `read()` is the reading half that follows — validation,
resolution, the record and the delta. [The API](#the-api) below is the whole
of it: what it returns, what it is worth, and where it stops.

Two pieces are yours and cannot be otherwise:

| | |
| --- | --- |
| The **closure** | `read()` takes one rather than computing it, because the dependency closure is resolved for the *target* platform and only your build tool knows what that is. Requirement 1 forbids evaluating markers for the build host |
| The **application's answers** | [§2.2](../SPEC.md#22-how-the-application-answers) fixes the capability a consumer must offer and deliberately not the syntax, so adapting your own configuration into `Application` is your work. A library that chose the spelling would be choosing what the specification refuses to fix |

[`conformance/consumer.py`](../conformance/consumer.py) is that adapter written
out — about 150 lines, and the smallest thing that turns a closure and a
configuration into a verdict.

Using the library is a **choice**. A consumer may implement §8 independently and
still be tested by everything below; the corpus drives a command, not an import.

**3. Then the command line, to test what you built.** Run the corpus rather than
writing your own cases.

```bash
native-integration conformance --profile android -- yourtool build --record
```

The cases were authored from the specification's prose, never by running an
implementation — a corpus derived from consumer #1 cannot establish that
consumer #2 agrees with the specification, only that it agrees with consumer #1.

**4. Take a failure to `explain`.** Each case names the requirement it
exercises, and `native-integration explain ni.req.38` is the rule that decides
it.

**5. Read `unverified` as the failure it is.** The harness reports three things
that are not passes, and they mean different things:

| | |
| --- | --- |
| `failed` | the consumer did the wrong thing |
| `unverified` | an assertion about a *numbered* requirement could not be checked — the run exits non-zero, because an obligation quietly skipped is how a conformance claim overstates itself |
| `unsupported` | the consumer declined an **advisory**, which [§8.5](../SPEC.md#85-advisory-obligations) permits. A pass |

The requirement implementers miss is §9.1's acceptance gate: comparing the
resolution against the last accepted record and refusing to build through a
change nobody accepted. It is the largest obligation in the document that is not
about reading a sidecar, and three cases turn on it.

## The API

**Add one call to your build tool, at one seam, and refuse the build when it
says to.**

```python
integration = read(sources, platform="android", closure=your_closure,
                   application=your_application, accepted=last_record)

if not integration.ok:                 # <- this line is the whole point
    print(integration.report())
    raise SystemExit(1)
```

`your_closure` and `your_application` are a `Closure` and an `Application` —
[building one](#building-a-closure) and [the other](#building-an-application)
below show constructing both from data your build tool already has. `read()`
does not take your resolver's or your config's own types directly; adapting
into these two shapes is the one piece of work this section assumes you have
already done.

Everything under [What it is worth](#what-it-is-worth) comes from those two
lines: the ninety-seven declarations validated, the collisions that only appear
once an application has two sidecars, the merge directions, and diagnostics with
ids your users can look up themselves. You get all of it by calling `read()` and
honoring the answer.

Then three pieces of work, in this order:

| | |
| --- | --- |
| **1. Adapt your configuration** into `Application` — your build tool's own spec file mapped onto [§2.2](../SPEC.md#22-how-the-application-answers)'s answers. [`conformance/consumer.py`](../conformance/consumer.py) is that adapter written out, in about 150 lines |
| **2. Emit what it resolved** into the project writer you already have. `integration.resolved` is what each distribution declared, validated; `integration.effective(...)` is what the merges decided. You loop the first for dependencies and source, the second for permissions and keys — [what comes back](#what-comes-back-and-what-to-do-with-it) says which is which, and why it matters |
| **3. Persist `integration.record`** and pass it back as `accepted=` on the next build. That is [§9.1](../SPEC.md#91-the-lifecycle)'s gate — worth doing last, and worth not skipping |

Then find out where you stand. The corpus runs *your* command and names every
requirement you are missing:

```bash
native-integration conformance --profile android -- yourtool build
```

The library is about thirty of §8's forty-six requirements. Step 2 is most of
the other fifteen, and it is work you already do — you are feeding it from a
validated source instead of from nothing.

### What the call takes and returns

`read()` writes no file, resolves no coordinate, reaches no network, and imports
nothing a producer shipped. Everything it concluded is in the object it hands
back.

| You supply | It returns |
| --- | --- |
| the sidecars discovery found | `findings` — every diagnostic, each naming a distribution, the §8 obligation it discharges, and the rule that produced it |
| the **closure**, resolved for the target platform | `record` — [§9](../SPEC.md#9-recording-and-review)'s durable, diffable record of what was resolved |
| the **application's answers**, adapted from your own configuration | `resolved` — per sidecar, what each distribution declared after those answers |
| optionally, a resolution you performed and the last accepted record | `delta` — what changed since the application last accepted anything |

### What it is worth

§8 is forty-six numbered requirements, and about thirty of them are about
*reading*: what a sidecar may say, what two of them may say together, what the
application still owes, and what changed since it last agreed to anything. This
library is those thirty as code paths you call, rather than paragraphs you have
to remember to implement.

The value is not that it saves typing. It is that **a rule you never wrote can
still fire.** A producer declares `required = true` on a feature; §6.5 forbids
it; you did not write that check and your build fails anyway, naming the
distribution and the rule. Multiply by thirty, and by every clause inside each
one — §8 states requirements as sentences, and the clause an implementer misses
is almost never the first one in the sentence.

### Where it stops, and what that means for conformance

**The library does not make your build tool conforming, and cannot.** Three
things it does not do, worth being plain about before you adopt it:

- **It computes a verdict; honoring it is your act.** `integration.ok` can be
  `false` and your tool can write a Gradle file anyway. Refusing to build
  through an unaccepted change is [§9.1](../SPEC.md#91-the-lifecycle)'s
  obligation and only a build tool can discharge it. A library that could force
  it would have to *be* the build tool.
- **It never sees what you generate.** It can tell you a producer contributed
  `android.permission.CAMERA`. Whether that permission reached your merged
  manifest is a question about an artifact it does not look at.
  [`docs/REQUIREMENTS.md`](../docs/REQUIREMENTS.md) marks fifteen of §8's
  requirements *beyond this reader* for exactly this reason.
- **Two of its inputs are yours, and it cannot check them.** Hand it a closure
  computed for the build host rather than the target platform and it will
  validate that closure quite happily — while you have broken requirement 1.

What establishes conformance is the corpus, and it is built to be independent of
this library on purpose: `native-integration conformance` runs **your command**
as a subprocess, imports nothing of yours or ours, and compares what comes back
against cases written from the specification's prose. Six of its assertions come
back *unverified* against this library, because they are about generated output
and a reader produces none — scoring full marks here would have proved nothing.

So: the library is how you avoid re-deriving §8 from prose. The corpus is how
you find out whether you got it right.

### Building a `Closure`

`Closure` and `Application` are imported from here because this is where their
*shape* is fixed — `read()` has to accept something, and §2.2 deliberately does
not fix a spelling for the application's answers, so this library fixes a
neutral one. What is never the library's is the *data* inside: every field below
is read off something your build tool already has.

| `Closure` | |
| --- | --- |
| `members: Mapping[str, Origin]` | every distribution's normalized name, and how it entered |
| `isolated: bool` | §3.2's allowance: treat every installed distribution as a candidate |
| `Origin.direct: bool`, `Origin.via: tuple[str, ...]` | a direct dependency, or the sorted chain of dependents it came in through |
| `Closure.direct(*names)`, `Closure.of(members)`, `Closure.isolated_environment()` | the three ways to build one |

```python
# Your resolver already produced this — every distribution it settled on for
# this platform, however it got there. Building a Closure is relabeling that
# result, not asking the library to resolve anything.
closure = Closure.of({
    "pystripe": Origin(direct=True),
    "protobuf": Origin(via=("pystripe",)),
})
```

`via` is what §3.2 calls provenance: the record attributes every contribution to
the smallest unit that brought it in, so a transitive dependency's new
permission is reported as *arriving through* `pystripe` rather than as
something the application asked for.

### Building an `Application`

Bigger, because [§2.2](../SPEC.md#22-how-the-application-answers)'s table is:
one field per row, joined the way requirement 10 fixes.

| Answers | Field | Joined by |
| --- | --- | --- |
| a build floor | `android: Mapping[str, int]`, `deployment_target: str`, `core_library_desugaring: bool` | the key itself — `min_sdk`, `compile_sdk`, `target_sdk`, or the one iOS and one boolean floor |
| a value | `values: Mapping[tuple[str, str], str]` | `(distribution, id)` |
| an acknowledged action | `acknowledged: Mapping[tuple[str, str], Answer]` | `(distribution, id)` |
| a dismissed conditional requirement | `dismissed: Mapping[tuple[str, str], Answer]` | `(distribution, id)` |
| a suppressed permission | `suppressed_permissions: Mapping[str, Answer]` | the permission's name, applying to every contributor of it |
| an approved export | `exported_components: Mapping[str, Approval]` | the component's class |
| a repository or package credential | `credentials: Mapping[str, Credential]` | the `url`, on §6.4's identity rather than the raw string |
| a resolved artifact's feature decision | `artifact_features: Mapping[str, FeatureDecision]` | the feature `name` |
| a colliding path's choice | `packaging_choices: Mapping[str, PackagingChoice]` | the packaged `path` |

`Answer` is just a `date`; `Approval`, `FeatureDecision` and `PackagingChoice`
each add the one field their row needs — `approved`, `keep`, `artifact`.
`manifest_meta_data` and `info_plist` are not answers at all: the application
sets these itself, for its own reasons, and a producer contributing the same
key loses ([§6.8](../SPEC.md#68-manifest-meta-data),
[§7.4](../SPEC.md#74-infoplist)). `initial_acceptance` is
[§9.1](../SPEC.md#91-the-lifecycle)'s first-build bootstrap, and `date` is the
build's own date, told rather than read off the clock so that gate does not
report a change that is not one.

Your own config file is where these come from. Say `examplebuild` scaffolds the
placeholder [the top-level README](../README.md#a-sidecar-and-the-applications-reply)
shows, and the author filled it in:

```toml
[tool.examplebuild.android]
min_sdk = 24
compile_sdk = 35

# Added by examplebuild. Required by pystripe.
[tool.examplebuild.native.pystripe.android.values]
stripe_return_scheme = "trailmap-pay"
```

```python
config = tomllib.loads(Path("pyproject.toml").read_text())
own = config.get("tool", {}).get("examplebuild", {})
native = own.get("native", {})
application = Application(
    android=own.get("android", {}),
    values={
        (distribution, key): value
        for distribution, by_platform in native.items()
        for key, value in by_platform.get("android", {}).get("values", {}).items()
    },
)
```

The spelling is yours. [`conformance/consumer.py`](../conformance/consumer.py)'s
`application_of` is the same adaptation done against the corpus's neutral
spelling instead of a real `pyproject.toml`, and covers every row of the table.

### Finding the sidecars

`discover()` is §3's discovery step: it walks the entry-point group across
installed distributions and returns a `SidecarSource` for every one whose
distribution `closure` contains, skipping the rest in silence (§3.2). It
imports nothing — a distribution targeting Android may not be importable on
the build host at all — and reaches the files through
`Distribution.locate_file()`, which is why an editable install cannot be read
([§12.2](../SPEC.md#122-sidecar-authoring-procedure), step 8).

```python
findings = Findings(load_registry())
sources = discover(closure=closure, findings=findings)
```

It takes a `Findings` because requirements 2 and 4 are found *here*, before any
sidecar is read: a distribution registering two entry points, or an entry
point naming a directory that is not there. **Read those findings even when
`sources` is empty.** An empty list with a blocking finding beside it is a
distribution whose whole native surface just went silent, which is the failure
§3.2's *fail, do not skip* rule exists to prevent — and `if not sources:
return` is the natural way to write exactly that bug.

`source_from_path(root, distribution=...)` builds one source by naming a
directory. It is for a test, a fixture, or a producer checking their own
sidecar; a build tool does not know its dependencies' sidecar directories up
front.

### The call

```python
record_path = Path("native-integration.record")   # wherever you keep §9's record

integration = read(
    sources,
    platform="android",
    closure=closure,
    application=application,
    accepted=record_path.read_text() if record_path.exists() else None,
    findings=findings,                  # discover()'s findings come first
    profiles=("android",),              # what this tool implements — see below
)

if not integration.ok:                  # <- the line only a build tool can write
    print(integration.report())
    raise SystemExit(1)
```

`read()` writes no file, resolves no coordinate, reaches no network, and imports
nothing a producer shipped. It raises in one case only: `UnimplementedProfile`,
when `platform` is not in `profiles`. That is requirement 9 —
[§8.1](../SPEC.md#81-conformance-is-per-platform) makes conformance per-platform, so an
Android-only tool is a conforming consumer, and the way it stays one is by
refusing an iOS build outright rather than producing part of one. Pass the
profiles you actually implement; the default claims both.

`contract` (default `"1.0"`) is the specification revision you implement, and
decides which sidecars are rejected as too new (§4.3).

### What comes back, and what to do with it

`Integration` holds `findings`, `resolved`, `record` and `delta`, and one method
that is not any of those. In the order a build tool uses them:

**`findings` — decide.** Every diagnostic, blocking and advisory, in the order
they happened. `integration.ok` is false when any is blocking;
`raise_for_errors()` throws an `IntegrationError` carrying `.findings` for the
tool that would rather catch than check. Each `Finding` has `obligation` (the
`ni.req.N` it discharges), `rule` (the finer registry id, where one fired),
`distributions`, `severity`, `section`, `message`, `where` and `detail`.
`findings.blocking`, `findings.advisories`, `findings.for_distribution(name)`
are the views; `as_diagnostics()` and `as_advisories()` are the JSON shape the
corpus reads. `report()` renders all of it for a terminal.

**`resolved` — read what each distribution declared.** One `Resolved` per
sidecar, after the application's answers:

| | |
| --- | --- |
| `sidecar` | the parsed document. `sidecar.entries("contributes", "gradle_dependencies")` is the tuple of tables under that path for this platform; `sidecar.section("requires")` a single table; `sidecar.table` the platform's whole table |
| `distribution` | its normalized name |
| `owns` | the Java namespaces it claims (§6.1) |
| `sources`, `staged` | every contributed source file, and each with the root it was staged from |
| `values` | each declared value's `id` mapped to its §5.4 state: `supplied`, `unresolved` or `dismissed` |

This is what you loop for the things a build tool copies through unchanged —
Gradle coordinates, Swift packages, contributed source, components:

```python
for entry in integration.resolved:
    for dep in entry.sidecar.entries("contributes", "gradle_dependencies"):
        gradle.add(dep.get("coordinate") or dep["module"], dep.get("configuration", "implementation"))
```

**`effective(kind)` — read what the merge decided.** `resolved` says what each
distribution *asked for*. Three things in §6 and §7 are not copied through but
**merged**, and the merge is directional: §6.5 registers a permission with the
widest `max_sdk_version` any contributor stated, and omits it entirely if the
application suppressed it; §6.8 and §7.4 let the application's own value win a
key. Those results live in the record as `effective` facts, and
`integration.effective("permission")`, `effective("meta-data")` and
`effective("plist-value")` return them parsed:

```python
for fact in integration.effective("permission"):
    name, merged = fact.positionals[1], dict(fact.keyed)
    manifest.add_permission(name, max_sdk=merged.get("max-sdk"))
```

**Do not write permissions from `resolved`.** A suppressed permission is still
in `resolved` — it was contributed — and has no `effective` fact, which is how
§6.5's *absent from the effective merged manifest* is spelled. The operand
names are [record-format.md §3.4](../conformance/record-format.md#34-effective)'s.

**`record` — persist, and hand back.** `integration.record.render()` is
[§9](../SPEC.md#9-recording-and-review)'s record: bytewise sorted, one fact per
line, diffable. Write it when the application *accepts* the resolution — behind
a flag or a review, never on every build, because a tool that rewrote it each
run would have a record and no gate. Pass its text back as `accepted=` next
time.

**`delta` — show what changed.** `added` and `removed` record lines against
`accepted`, already projected to the half §9.1 gates: a producer's new
permission is in it, the application's own answers are not. It is the content
of the `ni.req.38` finding, and the thing a reviewer reads.

### What each omitted argument switches off

Four arguments are optional, and each one omitted narrows what can be checked
rather than silently weakening a check that still claims to run:

| Omitted | What stops being checkable |
| --- | --- |
| `application` | every requirement is unanswered, so §5.4's satisfaction rules report against an application that answered nothing |
| `closure` | §3.2's origin is unknown, so nothing is attributed to the dependency that brought it in |
| `graph` | §9.4 and §9.7 — what a *resolved* artifact declares, and which artifacts collide on a packaged path |
| `accepted` | §9.1's gate has no prior record to compare against, and does not fire |

`graph` is the one to look at twice. §9.4's obligations are about the manifest
inside a resolved `.aar` and the files inside a resolved archive — things only a
tool that has done the resolving can see. `graph_of(raw)` builds a `Graph` from
a mapping in the corpus's `resolved.toml` shape: an `artifact` list of tables
with `coordinate`, `sha256`, `declared_by`, `transitive`, `files`, `classes`,
and `permission` / `feature` / `component` sub-tables carrying what the
artifact's own manifest declares; a `package` list for Swift, with `url`,
`revision`, and `binary_targets`. Passing one is what turns those obligations
on; without one they are not guessed at.

### What it cannot tell you

Against the [conformance corpus](../conformance/README.md) this reader passes
every case it can and reports six runs as **unverified**, which is a worse
outcome than a pass and a better one than a false pass. Each is an assertion
about *generated output*: that the sidecar stayed out of the payload, that a
view-link's attributes reached the manifest, that a feature decision was
applied, that the Python module stubs were excluded, that the Objective-C
categories were linked. The harness asks for a manifest or a payload to inspect
and there is none. Closing them takes a build tool, not a better reader.

## The command line

```bash
python3 -m pip install -e ".[test]"     # not on PyPI yet — a checkout is how you get it
```

Installing the package puts `native-integration` on the path. It is **not
normative** — `SPEC.md` is, and every answer the tool gives says so.

| Command | Answers |
| --- | --- |
| [`explain`](#explain) | what one rule says, and what correct form looks like |
| [`inspect`](#inspect) | what a sidecar declares |
| [`validate`](#validate) | whether a sidecar obeys the specification |
| [`conformance`](#conformance) | whether a build tool does |
| [`authoring-guide`](#authoring-guide) | how to write a sidecar in the first place |

Every command takes `-h`. `--json` is for a script or an agent; without it the
output is written to be read.

### `explain`

```
native-integration explain <identifier> [--json] [--platform android|ios]
```

The one to reach for. An id in — from a build log, from a diagnostic, or the
key you are writing — and one rule out.

| | |
| --- | --- |
| `<identifier>` | a diagnostic id (`ni.req.29`, `ni.decl.contract.pattern`, `ni.adv.S7`) or a declaration's dotted path (`android.contributes.r8`) |
| `--platform` | which platform table to write a fragment into, for a declaration that exists on both. Default `android` |
| `--json` | emit the answer as JSON |

It resolves **every** id the generators emit and every declaration the contract
defines — 238 and 97 respectively — so an id printed by a failing build always
leads somewhere. A declaration may be spelled as the author has it
(`android.requires.application_value.kind`) or as the registry stores it
(`<platform>.requires.application_value.kind`).

The answer carries the section and its anchor, the rule's own text, the severity
where the id is a diagnostic, the §8.1 profile where it is a numbered
requirement, and — for anything keyed to a declaration — a **minimal fragment in
correct form**, generated from the registry and validated against the JSON
schema. Two declarations have no fragment and say why: `exported` and a
feature's `required` are not fields, so their correct form is their absence.

**Exit status.** `0` when the id resolves, `2` when it does not — with near
matches suggested.

**`--json` keys.** `id`, `kind`, `contract`, `section`, `anchor`,
`specification`, `rule`. Then, depending on what was asked for: `severity`,
`declaration`, `requirement` and `profile` for a diagnostic; `node`, `category`,
`platform`, `required`, `since` and `values` for a declaration; `fragment` and
`related` wherever a declaration is involved, and `no_fragment` in place of the
first where none can be written.

### `inspect`

```
native-integration inspect <target> [--json] [--platform android|ios] [--distribution NAME]
```

What a sidecar declares, reported and not judged. Use it on someone else's
package to see what installing it would bring.

| | |
| --- | --- |
| `<target>` | a wheel, or a directory holding a `native.toml` |
| `--platform` | platforms to read for. Default: every platform the sidecar supports |
| `--distribution` | the distribution's name, where the path does not give it |
| `--json` | emit the answer as JSON |

A wheel is read as the zip it is. [§3.2](../SPEC.md#32-resolution) forbids
importing a producing distribution, and unpacking an archive imports nothing —
which is what makes it safe to inspect a package you have not installed.

**Exit status.** `0` when the sidecar is readable; `2` when the target holds
none, or holds more than one.

**`--json` keys.** `distribution`, `origin`, `contract`, `platforms`,
`declares` — the last a map of platform to the `owns` / `requires` /
`contributes` keys present.

### `validate`

```
native-integration validate <target> [--json] [--explain-failures]
                                     [--platform android|ios] [--distribution NAME]
```

One sidecar, held to the specification. Run it on the built artifact before
publishing: a sidecar correct in `src/` and missing from the wheel is the one
failure this convention cannot report.

| | |
| --- | --- |
| `<target>` | a wheel, or a directory holding a `native.toml` |
| `--explain-failures` | pair each finding with the step of [§12.2](../SPEC.md#122-sidecar-authoring-procedure) that decides it |
| `--platform` | platforms to read for. Default: every platform the sidecar supports |
| `--distribution` | the distribution's name, where the path does not give it |
| `--json` | emit the answer as JSON |

**What it cannot say matters as much as what it can**, and the output separates
three things rather than one:

| | |
| --- | --- |
| **findings** | the producer's, and what a failing exit status means |
| **outstanding** | obligations [§2.2](../SPEC.md#22-how-the-application-answers) gives the *application* — a value only the developer knows, an action only they can acknowledge, a floor only their configuration meets, an export only they can approve, an integration only they can accept. Real requirements, three of which block a real build, and none of them the sidecar's defect |
| **unchecked** | rules one sidecar cannot exercise at all, one entry per rule: an owned namespace two distributions claim, two values targeting one key, one module declared twice, a packaging collision, and everything that needs an application's answers |

**Exit status.** `0` when nothing the producer can fix is blocking; `1` when
something is. An outstanding obligation never fails the run.

**`--json` keys.** `distribution`, `contract`, `outcome`, `findings`,
`outstanding`, `unchecked`, `normative` (always `false`), and `steps` with
`--explain-failures`. Each finding carries `id`, `requirement`,
`distributions`, `section`, `severity`, `message`, `where` and `detail`.

### `conformance`

```
native-integration conformance --profile core|android|ios [--corpus DIR] -- <consumer command>
```

The corpus, run against someone else's consumer. This only invokes the harness;
[`conformance/run.py`](../conformance/README.md) is the authority on the result.

| | |
| --- | --- |
| `--profile` | §8.1 profiles to claim. Repeatable, and naming a platform profile brings the core with it, because conformance is the core plus at least one platform profile |
| `--corpus` | the `conformance/` directory of a checkout. Found automatically when you are inside one |
| `<consumer>` | everything after `--` is the consumer command, run once per case |

The corpus is **not** in the installed package, so this needs a checkout. It
belongs to the specification rather than to this library, and its harness is
deliberately kept out of the implementation it measures.

**Exit status.** The harness's: non-zero if any case failed *or* went
unverified. `unverified` is not a pass — it means an assertion about a numbered
requirement could not be checked. `unsupported` is a pass: a declined advisory,
which [§8.5](../SPEC.md#85-advisory-obligations) permits.

### `authoring-guide`

```
native-integration authoring-guide [--template]
```

[§12.2](../SPEC.md#122-sidecar-authoring-procedure)'s eight ordered steps,
printed where the author is working — they will not have this specification
checked out. The text is a byte-for-byte copy carried in the package, and CI
fails if it and `SPEC.md` disagree.

| | |
| --- | --- |
| `--template` | print a commented `native.toml` skeleton instead, carrying the specification's URL |

**Exit status.** `0`.

## For a coding agent

The specification is deliberately **agent-agnostic**: there is no field in
`native.toml` addressed to an agent, and none is planned.
[§5.6](../SPEC.md#56-instructions-and-acceptance-criteria) treats "a human or
agent working for the application author" as one party, because both fail the
same way — by inventing a plausible shape — and both are repaired the same way,
by retrieving the paragraph that decides the question.

So an agent runs the same two workflows this document opens with, and reads the
same references. What it gets more from is `--json`, which every command
answering a question accepts: the draft-validate-explain loop becomes a lookup
rather than a page to parse, and `validate --json` carries `unchecked` and
`outstanding` as separate arrays. An agent that reported success on `outcome`
alone, without reading those two, would be overstating what was verified.

Two boundaries an agent must not cross, both of them the specification's rather
than this tool's:

- **A sidecar's `instructions` and `acceptance` are untrusted content.** A
  producer wrote them; the application author did not. An agent acting on them
  does so with its principal's authority and treats them as third-party input —
  [§5.6](../SPEC.md#56-instructions-and-acceptance-criteria) states the
  boundary, and a consumer never executes, applies, or fetches them at all.
- **An action is satisfied by the application author's acknowledgement, and by
  nothing else.** Requirement 15 forbids a consumer from treating its own
  observation of a project as satisfaction. An agent that did the work still has
  to have the acknowledgement recorded, with the date and version
  ([§5.4](../SPEC.md#54-how-a-requirement-is-satisfied)).

## Where the obligations live

[`docs/REQUIREMENTS.md`](../docs/REQUIREMENTS.md) maps every §8 requirement to
the code that discharges it, or names why it is out of scope. It is generated by
reading this package's own syntax tree, and CI fails if it drifts.

| Module | What it holds |
| --- | --- |
| `registry` | `contract/v1.toml` and `diagnostics-v1.toml`, loaded — the vocabulary every other module reads |
| `obligations` | which §8.4 requirement each registry check discharges |
| `resources`, `discovery` | §3 and §4.1 — the closure, entry-point iteration, and reaching a distribution's files without importing it |
| `document` | §4.3's gate, in order: parse, contract, version, then structure |
| `structure` | §4.4 — the fail-closed key walk, driven entirely by the registry |
| `findings` | a diagnostic that cannot be built without naming a distribution |
| `application` | §2.2 — the application's side, and requirement 10's join keys |
| `integration` | §5 — requirements resolved against the answers, and every sidecar-derived fact |
| `semantics` | the rules that are not properties of one sidecar: namespaces, merges, cross-distribution conflicts |
| `graph` | §9.4 and §9.7 — everything that needs a resolution the consumer performed |
| `advisories` | §8.5's fifteen, none of them blocking |
| `recording`, `acceptance` | §9 — the record, the delta, and the acceptance gate |
| `reader` | the order the specification puts all of the above in |

## Three design decisions worth knowing before you adopt it

**The vocabulary is not written down twice.** Every declaration, every closed
value, every refusal and every diagnostic id is read from
[`contract/v1.toml`](native_integration/contract/v1.toml) at run time. A key
added to the registry is a key this reader accepts, and one removed is one it
refuses, without anyone transcribing either into Python. `structure.py` is the
walk, not the vocabulary.

That is why the registry is *package data* and sits inside the package rather
than beside `SPEC.md`. It is loaded on import, so a build without it is a build
that cannot be imported — which is what shipped, undetected, for as long as the
loader also searched parent directories and every checkout had a copy in one.

**A diagnostic cannot be built without naming a distribution.** Requirement 18
is enforced by `Finding.__post_init__`, which raises, rather than by discipline.
A finding that belongs to no distribution is a finding about your own
configuration, and does not go here.

**An invalid sidecar produces one finding, not a cascade.** A document that
fails §4.4 is never resolved, so it cannot go on to report the values it did not
supply and the actions nobody acknowledged. Those would be true statements about
a file the reader has already refused to interpret, and the one thing the
application can act on is the refusal.

## Status

```bash
python3 -m pip install -e ".[test]"
python3 -m pytest -q
```

The specification is a draft and so is this. The version here tracks the
specification revision it implements, and the two are amended together.
