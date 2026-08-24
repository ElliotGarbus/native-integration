# Mediated ads against the current spec

Clean-sheet, from [AdMob's Android](https://developers.google.com/admob/android/quick-start)
and iOS quick starts and the mediation adapter guides. Three hypothetical
distributions: `pyadmob`, `pyadmob-applovin`, `pyadmob-mintegral`.

**This is the first composition example.** Every other sidecar in this directory
is one producer as a direct dependency, which leaves the rules whose entire
justification is cross-distribution — §6.1's exclusivity, §6.6's scope overlap,
§6.7's merge, §6.10 and §6.3 sharing one key space, §7.6's de-duplication,
§7.8's union, §9.1's collisions — evidenced only by unit tests written beside
the rules they test. Mediated ads is the case where a real application routinely
holds three to six such packages at once, so the collisions are ordinary rather
than contrived.

Gap identifiers are `MA*`. Versions and SKAdNetwork identifiers were read in
August 2026 and are illustrative.

## MA1 — the composition is clean, and that is the finding *(a validation)*

Three packages, two platforms, no conflict and no unanswered prerequisite. The
whole set produces **nothing louder than a note**: a contributed repository
reported with the prominence §6.6 demands, and a requested-versus-resolved line
per dependency. Both are things a reviewer should see; neither is a problem.
That is §8's third outcome doing its job, and it is worth stating because a
composition example that produced silence would mean the disclosure rules were
not firing.

What actually merged:

| Rule | In this set |
| --- | --- |
| §7.6 de-duplication | five distinct SKAdNetwork identifiers from seven declarations; `cstr6suwn9` and `ludvb6z3bs` each declared twice, each present once |
| §7.8 union | all three ask for Objective-C category loading; §9 names all three |
| §6.10 coalescing | `OPTIMIZE_INITIALIZATION` set by two packages to the same value — the coalescing path, with both provenance records kept |
| §6.7 union | `INTERNET` declared three times, one entry in the merged manifest, three distributions in its provenance |
| §6.3 scoping | three vendor keys, three distributions, three separate answers |

## MA2 — two predicted stresses did not materialize *(a correction)*

This example was chosen partly to test two hypotheses about where composition
would hurt. Neither held, and the reasons are more useful than the guesses:

**§6.6's overlap rule was not stressed, and structurally cannot be by
mediation.** The prediction was that several adapters each contributing a vendor
repository would contest coordinates, forcing the relaxation §6.6 says it would
accept "if a real package demonstrates a need". They cannot: each vendor's
repository serves that vendor's own Maven group, so the scopes are disjoint by
construction. Two repositories contest coordinates only when two distributions
mirror *the same* artifacts, which is a different situation — a vendor's
repository and a corporate proxy of it, say. **§6.6's blunt rule stands, and
this example is evidence that the case it forbids is rarer than it looks.**

**§6.3's per-distribution scoping was not stressed either.** The prediction was
that several packages would want one vendor's key and the application would
answer it repeatedly. They do not: the mediation SDK needs the AdMob ID, and
each adapter needs *its own* vendor's key. One value per vendor, one vendor per
distribution. The duplication §6.3's rationale defends against would need two
distributions wrapping one vendor — which §12 already tells producers not to do.

## MA3 — the plist half of a mediated set is where the record gets long

Five identifiers here; a real mediated application carries somewhere between
fifty and a few hundred, because each adapter ships its network's full list. The
merge is correct and the *record* is where that lands: §9's per-line entry
format means an ads-heavy application's record gains one line per identifier per
declaring distribution.

Nothing here is wrong, and no rule needs changing. It is recorded because §9's
own argument for one line per contributed thing — "a set difference over
`entries` *is* the delta a reviewer reads" — is made against integrations an
order of magnitude smaller than this one, and whether that holds at four hundred
lines is a question for whoever writes the first consumer's report, not for the
specification.

## MA4 — an adapter is a thin sidecar, which is what the split predicts

Each adapter is one dependency, one or two vendor keys, one Swift package and a
short identifier list. §12 tells a producer to split a family into distributions
an application opts into, and the mediation ecosystem is that shape already:
nobody wants every adapter. The example is evidence that the guidance describes
something real rather than a hypothetical — and that a thin sidecar stays
legible, which is the property that makes reviewing six of them feasible.

## MA5 — the join is scoped by platform, and §2.2 did not say so *(a correction)*

The set has an [`app-pyproject.toml`](app-pyproject.toml) beside it — the second
worked application half in the repository, after `examples/pystripe/`, and the
first answering more than one package. Writing it produced the finding that a
sidecar could not.

`pyadmob` declares `admob_app_id` in **both** §6.3 and §7.3, because the SDK
needs one on each platform and the AdMob console issues a *different* ID for
each. §2.2 said the join key for a producer-local `id` is the pair
*(declaring distribution, `id`)*. Under that reading the two declarations are
one requirement, and an application answering it once satisfies both builds
while shipping the wrong identifier on one of them — silently, because the value
is well-formed and the wrong account's.

In practice a consumer builds one platform at a time and reads answers for that
build, which is what `examples/pystripe/` already does by nesting under
`.android` and `.ios`. So the behaviour was right and the **statement** was
wrong. §2.2 now says the join is additionally scoped by platform, and gives the
reason §6.3's rationale already had: an AdMob, Firebase or Meta application ID
differs between platforms, which is why a single platform-neutral table was
declined in the first place.

Two smaller things came with it. §2.2's join table had gone **stale** — it was
missing §7.3's application values, all four of §6.11's tables, and §9.1's
packaging choice — and is now current. And the application's half turns out to
be short: three ad packages ask for account credentials and one sentence, where
one payment package asked for an exported component and a forwarded callback.
The size of what an application answers tracks what its packages *do*, not how
many of them there are.

## MA6 — the record, generated rather than illustrated

[`record-android.json`](record-android.json) and
[`record-ios.json`](record-ios.json) are the §9 records this set produces,
written by `tools/record_example.py` and checked in CI. Appendix E shows the
*shape* of a record and says so — hand-written, non-normative. These are the
thing itself.

The closure they are generated from is the ordinary one for this ecosystem: the
application depends on the two **adapters** it wants, and each adapter depends
on the mediation SDK, so `pyadmob` arrives underneath. The record says so:

```json
"name": "pyadmob",
"origin": "via pyadmob-applovin, pyadmob-mintegral",
```

and the entries under it include

```
meta-data com.google.android.gms.ads.APPLICATION_ID = ca-app-pub-…
```

An account identifier, demanded by a package the application never named,
attributed to the two packages that brought it in. That is the README's opening
paragraph as an artifact rather than a claim, and it is what §3.2's closure rule
and §9's `origin` field exist to produce.

Two smaller things the pair shows that no single-platform record could:

- **The same `id`, two values.** `GADApplicationIdentifier` in the iOS record
  carries a different identifier from `com.google.android.gms.ads.APPLICATION_ID`
  in the Android one — MA5, visible in the output rather than argued in prose.
- **MA3's prediction, confirmed.** The record keeps one `skadnetwork` line per
  identifier *per declaring distribution*, so `cstr6suwn9` appears under both
  `pyadmob` and `pyadmob-mintegral` while the merged plist carries it once.
  Provenance is per-package and de-duplication is per-application, which is the
  right split and also why an ads-heavy record grows the way MA3 predicted.

## What this did not exercise

Recorded so the next composition example is chosen against the gap rather than
by hunch:

- **§9.1's packaging collisions.** Ad adapters do not collide on packaged
  paths; that needs two SDKs each bundling a C++ runtime — Agora with
  TensorFlow Lite is the case.
- **§6.7's least-restrictive attribute merge.** All three declare `INTERNET`
  without attributes, so the union is trivial. Producing a genuine
  `max_sdk_version` disagreement would have meant inventing one, which is worth
  less than leaving the rule unexercised and saying so.
- **§6.1's namespace exclusivity.** No adapter contributes Java, so nothing
  claims a namespace. The rule's only live evidence remains PyGMA's round-one
  finding.
