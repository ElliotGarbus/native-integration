# Converting the worked sidecars

Seven sidecars re-expressed against the finished specification rather than
against the probe's sketch: [`examples/`](examples/) beside this file. The
first attempt's versions stay frozen where they are, so the two can be read
side by side.

This is the first time the new model has been applied to whole integrations
rather than to fragments in an argument. Findings continue at **V22**.

| Case | What it exercises | Result |
| --- | --- | --- |
| [pystripe](examples/pystripe/) | the worked pair — sidecar and the application's reply | clean; **fixed a defect the frozen version still has** |
| [pyonesignal](examples/pyonesignal/) | four actions, a slot, a value inside an action | clean |
| [pyhealthconnect](examples/pyhealthconnect/) | an application-owned class Play policy requires | clean; the case the redesign was for |
| [mediated-ads](examples/mediated-ads/) ×3 | composition — coalescing, de-duplication, repository scope | clean; **caught a misuse the first attempt could not** |
| [pyairship](examples/pyairship/) | a vendor offering two paths to one fact | clean |

**No conversion needed a capability the specification lacks.** That is the
headline, and it is worth stating plainly because it could have gone otherwise:
these are the same integrations that produced thirteen tables the first time
through.

## V22 — the conversion found a real defect in a frozen example

`examples/pystripe/native.toml` registers `org.pystripe.PaymentReturnActivity`
as a producer-sourced component and contributes no source. §6.6 requires a
producer-source component's `name` to refer to a class the distribution
contributes; the reference reader checks only the owned namespace, so nothing
caught it. The converted sidecar declares `[android.contributes.src]`.

That defect predates the redesign and would have survived it. What surfaced it
was re-reading a sidecar against the rules with the rules in hand — which is
the argument for doing this conversion at all, and an argument for a reader
that enforces the clause.

## V23 — a predicted misuse, demonstrated

[review-01](review-01.md) §2 argued that requiring a delivery site would turn a
§6.3 SHOULD into a schema error, and used `pyadmob-mintegral` as the example:
two application values with no `manifest_meta_data`, so the application supplies
two strings that reach nothing. Mintegral takes both at runtime.

Converting it, the rule bites exactly as predicted — the values will not
validate, and the honest form is an action telling the author to pass the keys
to `init()`. A prediction is cheap; the same prediction surviving contact with
the file it was made about is not.

## V24 — `uses` earned its place twice, independently

OneSignal and Airship both need an App Group identifier: a string the
application supplies, inside an outcome only the application can reach —
enabling the capability on two targets and getting the entitlement into a
provisioning profile. Both split into a value and an action tied by `uses`.

Two unrelated vendors reaching the same shape is the evidence `uses` did not
have when it was proposed, where it rested on one case seen twice in one
review.

## V25 — the probe's own artifacts went stale, and nothing noticed

The Airship sidecar written during the probe still carried `kind`, `key` and
`value` on its actions — the verification fields removed from the model weeks
earlier. It had been correct when written and wrong since, and no check covered
it, because it lived in a directory nothing validated.

Converting it fixed that file. The general lesson is the reason the new
`development/redesign/examples/` set is now checked against
[Appendix B](../../SPEC.md#appendix-b-declaration-reference) by
`tools/check_spec.py`: an example that is not validated is a claim about the
specification that nobody is testing.

## What the conversion cost

Three checks, exactly the ones [review-01](review-01.md) §3 predicted when
verification was dropped:

| Case | The first attempt checked | Version 1 |
| --- | --- | --- |
| OneSignal `aps-environment` | the entitlement key is present | acknowledged |
| Airship `AirshipConfig.plist` | a file of that name is in the bundle | acknowledged |
| OneSignal `UIBackgroundModes` | the key holds the declared value | acknowledged |

Each is now an action with acceptance criteria, so what was a silent
key-presence test is a stated list a person or an agent can walk. Whether that
is a fair trade is the thing support evidence has to answer; the point here is
that the cost is three cases across seven integrations, not a general loss.

## What stayed exactly the same

Everything in the automated core. Gradle coordinates and ranges, the Maven
repository and its bounded scope, permissions with their reasons, `meta_data`
coalescing across pyadmob and its AppLovin adapter, SKAdNetwork identifiers
de-duplicating across three packages, Swift packages, `objc_categories`, the
shrinker keeps and their `from_dependency` form, ownership. Those sections were
ported nearly verbatim from the first attempt and the conversion did not
disturb them, which is the other half of the evidence: the restructure took the
prerequisite taxonomy and left the part eighteen examples had already
validated.

## Where these live, and why not `examples/`

`examples/` and `development/examples/` hold the first attempt's eighteen
sidecars, which the reference reader's test suite validates against the first
attempt's rules. Those keep working. The converted set lives here until the
reader implements this specification, at which point it graduates and the
frozen set moves under `development/` with the document it belongs to.
