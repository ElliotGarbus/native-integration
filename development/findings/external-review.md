# The first external review

The first reading of this repository by someone who did not write it, after
Phase 5. Its defect findings are acted on below; its design comments are
recorded so that freeze review does not treat them as settled because they were
written down once.

## Defects, and what was done

| Finding | Held? | Action |
| --- | --- | --- |
| The one sentence an implementer quotes — "forty-six requirements in a core profile plus one per platform" — reads as though the platforms each add one. §8.1 splits them 29 / 11 / 6. | Yes. The registry says so; three documents said the other thing. | The split is stated in words wherever the sentence appeared: an Android-only tool owes forty |
| Zip-slip in `_from_wheel`: a member named `pkg/_native/../../x` passes the prefix check and writes outside the unpack directory. The authoring path. | Yes. Proven with a crafted wheel before fixing: `inspect` wrote a file into the system temp directory and exited 0. | Each target is resolved and must stay inside the unpack directory; a wheel naming one that does not is refused whole, naming the member |
| `Credential.__repr__` prints the locator — the secret, when `kind = "literal"`. `REDACTED` was defined and never used. | Yes, and worse: the repr carried a comment claiming it kept the value out of a trace, and the requirements table repeated the claim. | The locator is withheld for every kind; the kind is shown |
| `read()` defaults `closure=` to isolated-environment; `discover()` requires one. As a default it is the easy way to break requirement 1 on a fat build host. | Yes. | `closure` is required. A caller meaning §3.2's allowance spells `Closure.isolated_environment()` |
| The public example is not the one the schema check watches, and the two current-model copies of `pystripe` have drifted. | Yes. `examples/pystripe` was on the rules checks and off the schema loop, on a comment that still called it the first attempt. | One copy, the public one, on every check; `CONVERSION.md` no longer says the converted set is waiting for a reader that already exists |
| CI tests a checkout, not the artifact, and never on Windows. | Yes. Two shipped defects of exactly that class are already in `first-use.md`. | A job builds the wheel, installs it with no checkout above it, and runs every subcommand; the reader matrix runs on windows-latest |
| Application repositories that commit `accepted.record` will not pin line endings unless the consumer guide puts the snippet beside the first-build gate. | Yes. | The `.gitattributes` lines sit in `src/README.md`'s paragraph on persisting the record |

Three of the seven were security-shaped, and two of those were in the library's
*edges* — the CLI's unpack and a repr — rather than in the sidecar path, which
had been careful. That is the pattern worth keeping: the code that was written
against §8 was reviewed against §8, and the code around it was not reviewed
against anything.

## Design comments, held open for freeze review

None of these is a defect, and none was reversed. Each is a decision the
specification made; the review's point is that freeze review should re-decide
them rather than inherit them.

**Lifecycle composition is the load-bearing deferral.** Push and payments stay
manual on iOS. Version 1 can state "call this early" as an action; it cannot
generate the dispatcher that would make it a contribution. §11 defers this with
a trigger — several vendors initialize from a manifest entry naming a class a
package can contribute — and that trigger is the freeze-time question.

**Acknowledgement without verification is the honest v1 choice, and the report
should say so louder.** An acknowledged action is not a verified one. §5.4
makes satisfaction an acknowledgement because a check that cannot satisfy an
action buys only a better error message, and one that can reports *done* for a
requirement that is half met. The report should not let "acknowledged" read as
"verified". Worth a wording pass on the reader's report before a freeze.

**Record content is specified; format is not.** §9.6 says what a record must
contain and `conformance/record-format.md` fixes a canonical form for the
corpus — but the specification does not make that form interchange. Two
conforming tools cannot share `accepted.record`. Fine while there is one
consumer; it becomes the interoperability defect the moment there are two.
Decide before a freeze whether the corpus's format is the format.

**The named target tools collide with the permanent exclusions.** The README
names python-for-android, Chaquopy and kivy-ios as the audience. p4a and
Chaquopy vendor `.aar` files, which §11 excludes permanently; kivy-ios is
recipe-shaped rather than SwiftPM-shaped. Before asking those maintainers to
read this, tell them up front what still applies to a recipe-and-AAR toolchain
and what does not.

**`credentials_required` on Swift packages entered from symmetry, not from a
case.** No converted sidecar needed a private Swift package; the key mirrors
Maven's. `CONVERSION.md` already names the trigger: a private-package case
arrives, or the key goes. Decide it, rather than freezing a key no sidecar has
used.

## The follow-up

A second pass found eight more, and rejected four late claims -- a permissive
closure default, missing Windows and wheel CI, hyphenated wheel filenames,
conditional actions -- that the current code or the specification disproves.
Every one of the eight held on verification.

| Finding | What was done |
| --- | --- |
| **High.** An empty `outputs/payload/` passed every payload-exclusion assertion: nothing was excluded because nothing was included, and the harness asked only the second question | The harness first requires the payload to carry each closure distribution's own package, outside `_native/`; the three payload cases ship a file there. Shown to fail on an empty payload before being trusted |
| A malformed artifact or binary-target digest in the injected graph raised `RecordError` out of `read()` | Reported as requirement 26, attributed to the distribution that declared the artifact; the fact is not written |
| A case needing `resolved.toml` returned *unverified* for a consumer that cannot take one, before looking at the wrong outcome that consumer had already reported | A known failure fails; the capability note is appended to it |
| The conformance JSON example omitted `outputs` | Shown, and stated as optional -- the harness type-checks it if present and never requires it, which the review had overstated |
| The unverified pin captured one assertion per case and never noticed a stale pin | Every assertion line under every unverified case, both directions. It found that R01 had carried a second unverified assertion, unpinned, since the list was written |
| The schema's `$id` returned 404 | Points at the raw file on `main`, which resolves; the freeze-time answer is a tag-pinned URL or a real host |
| `development/README.md` said all development sidecars are kept current; most are deliberately held to the frozen first attempt | Says which are frozen and which are current, and names the list that decides it |
| `README.md` counted twenty-six checks; the script runs twenty-seven | No number: the script prints one line per check |

**And one of my own.** Six of these were pushed with four tests failing. The
chain gated the commit on `pytest | tail`, whose exit status is `tail`'s, and
the commits were not joined to the proof step that raised. That is the failure
[`AGENTS.md`](../../AGENTS.md) was written to name, the same week it was
written, by the same hand. It is recorded rather than amended away, and every
gate since runs the checked command alone and tests its own exit status.

## What the review said to keep

> Using the library does not make a tool conforming.

The sentence the reviewer would keep quoting, from `src/README.md`. A first
consumer still owns generation, the §9.1 gate, a target-platform `Closure`,
the adaptation of its configuration into the application's answers, payload
exclusion, native graph locking, and the bootstrap requirements 45 and 46. The
library is the reading half; the corpus is how a tool finds out whether it did
the rest.
