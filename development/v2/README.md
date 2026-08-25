# Round seven: a probe against a successor model

**Status: a design probe, not a specification, and not part of the version 1
example set.** Nothing here is normative and nothing here has been decided. The
five sidecars below were re-expressed *on paper* against a proposed successor
model, before any specification text was written, because that is the order
that has changed this design every round: the examples first, the prose after.

The question being tested is whether a much smaller model can carry what
version 1 carries. The concerns behind it are adoption (a specification too
complicated to implement is not implemented), coverage (a missing capability
that only surfaces after a producer needs it), and **maintenance** — every one
of `app_extensions`, `app_links`, `plist_capabilities` and
`application_classes` exists because a platform vendor shipped a construct and
[SPEC.md](../../SPEC.md) needed a table for it. That is an unbounded obligation
against two vendors who ship annually.

Gap identifiers are `V1`–`V10`, continuing the per-round scheme of
[PROPOSALS.md](../PROPOSALS.md) and [SURVEY.md](../SURVEY.md).

## The model under test

The target changes. Version 1's is *the sidecar contains everything necessary
for a consumer to correctly integrate the package*. The successor's is **the
sidecar automates the portable, repeatable parts of integration and tells the
application author exactly what remains** — with *manual* as a first-class
outcome rather than a gap in the specification.

Automate where all three are true: the producer knows exactly what is required,
the consumer can do it deterministically, and little or no application-specific
policy is involved. Everything else becomes something the application is told
to do.

That leaves two prerequisite tables where version 1 has thirteen:

```toml
[[<platform>.requires.application_value]]
id          # the join key, scoped by (distribution, id, platform)
kind        # where the consumer delivers it: manifest_meta_data,
            # manifest_placeholder, info_plist, usage_description, inline
key         # the platform key it is delivered to
reason      # what it is and where to obtain it
placeholder # what the consumer scaffolds, and blocks on until it is replaced
conditional

[[<platform>.requires.application_action]]
id          # the join key
kind        # OPTIONAL verification hint: entitlement, plist_capability,
slot        #   bundle_file, asset_file, resource, app_extension, url_scheme,
key         #   app_link, application_class — or absent, meaning opaque
value       # OPTIONAL, kind-dependent
summary     # one line, shown to the application author
reason      # why it is needed, and what breaks without it
instructions # OPTIONAL path to prose in the wheel
conditional
```

The contributions half of version 1 — `owns`, source, Gradle dependencies and
repositories, Swift packages, permissions, features, components, `meta_data`,
`queries`, `r8`, `info_plist`, `python_modules`, `objc_categories`, the SDK
floors — is **unchanged**. So is discovery (§3), the sidecar and contract
rules (§4), locking (§6.5, §7.4), and the record and review lifecycle (§9).
Roughly three quarters of the current document is untouched by this proposal.

## Method

Five sidecars, chosen as the hardest cases in the existing set:

| Case | Chosen because | Result |
| --- | --- | --- |
| [Meta](../examples/pyfacebook/) | three account values, a derived value, a browser return | **clean** — one table collapses for free |
| [OneSignal](../examples/pyonesignal/) | an extension target, two entitlements, a capability key | **clean, with V2 and V3 applied** |
| [Health Connect](../examples/pyhealthconnect/) | an application-owned class Play policy requires | **better than version 1** |
| [Mediated ads](../examples/mediated-ads/) ×3 | composition: three packages in one application | **clean** — and it exposed a version 1 misuse |
| [Airship](pyairship/) | the vendor offers **two paths to one fact** | **clean** — and the model chooses between them |

Airship is the only one written out in full, as [`pyairship/native.toml`](pyairship/native.toml);
it is the case the other four could not ask.

## What the thirteen tables become

| Version 1 | Successor | Loss |
| --- | --- | --- |
| `ios.url_schemes` | action | **none** — already acknowledgement-only |
| `android.application_classes` | action | **none** — already acknowledgement-only |
| `android.app_links` | action | **none** — already acknowledgement-only |
| `ios.app_extensions` | action + `slot` | the target-of-kind half; contention needs V3 |
| `ios.entitlements` | action + `kind` | key presence, unless V2 |
| `ios.plist_capabilities` | action + `kind` | key/value presence, unless V2 |
| `ios.application_files` | action + `kind` | file-wired-in check, unless V2 |
| `android.application_files` | action + `kind` | same |
| `android.resources` | action + `kind` | breaks §6.10's pairing check, unless V2 |
| `ios.usage_descriptions` | **value** (`kind = "usage_description"`) | **none** — placeholder is equal or better |
| `android.application_values` | **value** (`kind = "manifest_meta_data"`) | none |
| `ios.application_values` | **value** (`kind = "info_plist"`) | none |
| `android.manifest_placeholder` | **value** (`kind = "manifest_placeholder"`) | none |

Thirteen tables to two. Four collapse with nothing lost, four are value
delivery and keep their structure, five lose an inspectable check unless the
action carries an optional `kind` (V2).

## Findings

### V1 — actions must fail *open*, where version 1 fails closed

The load-bearing decision. §4.4 makes a consumer reject any value it does not
implement, and that rule is precisely why each new platform construct needs a
new table: an unknown `kind` is a build failure, so the specification has to
enumerate the world in advance.

An action has to invert it: **an unrecognized `kind` degrades to a manual
instruction rather than failing the build.** That is safe here and nowhere else
in the document, for a reason worth stating in the text: an action is a
`requires`, so it grants the producer nothing. The worst case of a consumer not
understanding `kind = "app_clip"` is that a person reads a sentence and does
the work by hand — which is the baseline this convention improves on, not a
regression from it.

This single inversion is what stops the specification growing whenever Apple or
Google ships something new, and it is the whole reason the model is cheaper to
maintain. It should be argued for explicitly rather than left as a default.

### V2 — an opaque action blinds five checks; `kind` is the cheap fix

An entitlement key's presence, a capability key's value, a bundle file being
wired in — a consumer that generates the project can check all three today. A
missing `aps-environment` currently **fails the build** instead of producing a
`codesign` error with no path back to the package that needed it. Collapsing
those to a tick-box is the one place the successor is genuinely worse than
version 1.

An optional `kind` recovers all of it and costs nothing, because V1 already
established that an unknown one degrades:

```toml
[[ios.requires.application_action]]
id = "aps_environment"
kind = "entitlement"          # a hint, not a contract
key = "aps-environment"
summary = "Enable the Push Notifications capability"
reason = "APNs delivery. Without the entitlement the build fails at codesign."
```

The taxonomy does not disappear — **it moves from a normative table to an
optional verification hint.** That is the difference between "the specification
must grow when a vendor ships something" and "a consumer may grow if it wants
to", and it is the actual content of this proposal.

### V3 — singleton contention needs a `slot`

iOS permits one extension target per extension point. §7.3 spends three
paragraphs on what happens when two packages both need a
`notification_service`, and the answer — the application merges both vendors'
code into the one target iOS allows — depends on the consumer *noticing* that
two packages asked for the same thing.

Two opaque actions are indistinguishable strings. A `slot` restores the check:

```toml
slot = "ios:extension:notification_service"
```

This is the only composition check that lives in action space. Everything else
the mediated-ads trio exercises — `meta_data` coalescing, SKAdNetwork
de-duplication, repository scope overlap, one `id` meaning different values per
platform — is in the automated core and survives untouched.

### V4 — a value requires a delivery site; without one it is an action

Make it a schema rule, and the value/action line becomes crisp: **if there is
nowhere for the consumer to write it, it is not a value.**

Version 1 cannot state that, because its delivery field is optional — and the
trio shows the cost. `pyadmob-mintegral` declares two application values with
no `manifest_meta_data` and no inline reference:

```toml
[[android.requires.application_values]]
id = "mintegral_app_id"
reason = "Your Mintegral application ID, from the Mintegral dashboard"
```

The application supplies those and they reach **nothing** — Mintegral takes
them at runtime. §6.3 has a SHOULD against exactly this (*"a producer SHOULD
NOT route one through build configuration merely because it can"*) and no way
to enforce it. Under the successor it is a schema error, and the honest form is
an action: *obtain your Mintegral keys and pass them to `init()`*.

One consequence: §6.10's `resources` pairing needs the resource declaration to
keep structure (`kind = "resource"`), or a consumer can no longer tell that
`@drawable/ic_stat_notify` names something the sidecar actually asked for.

### V5 — Health Connect is the case that vindicates the change

HC2 needs a permissions-rationale activity the application owns, **plus** an
activity-alias guarded by `START_VIEW_PERMISSION_USAGE` with an intent filter
carrying both an action and a category. Google Play requires the whole thing of
a health application.

Version 1 expresses **half**: `application_classes` covers the class, and the
alias, the attribute and the two-part filter are recorded as inexpressible. The
successor expresses all of it — one action, with an `instructions` file
carrying the exact XML to paste.

§2.1 already argues this is the better outcome: *"A contribution that writes
half of a two-part requirement is worse than a prerequisite naming both,
because it looks finished."* Version 1 landed on the wrong side of its own
principle here, because a table was the only instrument it had.

### V6 — three tables collapse with nothing lost at all

`url_schemes`, `application_classes` and `app_links` are already
acknowledgement-only in version 1: the consumer cannot inspect what was asked
for, so it asks the application to state that it did the work. That is exactly
what a generic action does. Three tables, three sets of satisfaction rules, and
three §8 requirements, for nothing.

Meta's iOS half is the demonstration — everything version 1 says, the successor
says, and `url_schemes` disappears.

### V7 — placeholders verify values; actions have three tiers

The scaffolded placeholder is stronger than it first looks, because it makes
verification **platform-agnostic**: `"<TODO: explain why your app uses
location>"` is checkable by string comparison, without the consumer knowing
what `NSLocationWhenInUseUsageDescription` means. It cannot be satisfied by
inattention, which acknowledgement can.

It does not extend to actions — *"add a Notification Service Extension"* has no
placeholder to leave unedited. So verification has three tiers:

| Form | Check | Strength |
| --- | --- | --- |
| value + `placeholder` | the placeholder is gone | strong |
| action + known `kind` | kind-specific inspection | medium |
| opaque action | acknowledgement | weak |

A producer's choice of form decides which tier it gets, which is a useful
incentive against reaching for manual first.

### V8 — where a vendor offers two paths, the producer picks one *(Airship)*

Airship's Android app key can be supplied two ways:

- **(A)** `airshipconfig.properties` in the application's assets — the author
  downloads a file from the dashboard and wires it in;
- **(B)** an Autopilot subclass supplying `AirshipConfigOptions`, which Airship
  loads from one `<meta-data>` line naming the class.

(A) is an action: manual, and the consumer can check only that a file of that
name is present. (B) is two application values plus a contributed class — the
consumer writes both values into the manifest, the producer's own code reads
them at takeOff, and **no manual step remains on Android at all.**

Two things follow. First, the three-part test *chooses*, and it chooses (B):
the producer writes the Autopilot subclass once so that no application author
transcribes anything, which is the trade this whole convention exists to make.
Second, the model should have **no way to say "either A or B"**, and adding one
would be a mistake — it would hand the application author two TODOs for one
fact and no way to know that doing either is enough. The producer decides; the
sidecar states one path.

Version 1 has the same property and never had to face it, because when Airship
was first written both paths were blocked (AS1, AS2). Both are expressible
today, so the choice is now real.

### V9 — the residual manual set is the lifecycle gap, exactly

Airship's iOS half cannot take path (B), and the reason is precise:
(B) works on Android **because the vendor provides a load hook** — one manifest
line naming a producer class that runs before any component receives an intent.
iOS has no counterpart. `Airship.takeOff` is a runtime call that comes too late
for a push received at launch, and nothing lets a producer register code to run
before the interpreter starts.

So the same fact stays a manual action on iOS while being fully automated on
Android. That asymmetry is the platform's, not the model's — but it lands
exactly on the deferred lifecycle question, and it is the clearest measurement
of what that deferral costs: **one manual step per push SDK per application, on
iOS only.** Anything that closes the lifecycle gap converts those actions into
values.

### V10 — the §8 saving is smaller than the table saving

Six to eight of §8's forty-one requirements go — 8.8, 8.21, 8.22, 8.23, parts
of 8.6, 8.26, 8.31 and 8.35. The expensive obligations are all in the automated
core and all survive: locked resolution with per-artifact checksums (8.12),
packaging collisions (8.30), reading resolved `.aar` manifests (8.19), and the
record and acceptance lifecycle (8.9).

Worth being accurate about in the new document. The win is comprehension and
maintenance, which is the stated concern; the implementation win is real but
modest, and a build-tool author who reads "much simpler" and then meets 8.12
will feel misled.

## What this probe does not settle

- **The `instructions` channel needs a rule.** Nothing executes it, so §2.1
  holds — but an arbitrary markdown file in a wheel is *socially* executable
  ("run this", "paste that") where a `reason` string a reviewer reads in a
  report is not. At minimum: instructions are data shown to a human, a consumer
  never acts on them, and the file is a declared resource so §9's per-file
  hashing surfaces a change between versions.
- **Manual must not become the default.** If an action is free it is the path
  of least resistance for every hard case, and the convention degrades into a
  README with checkboxes. The document needs an explicit norm — a producer
  SHOULD NOT declare an action for something the automated core covers — and
  probably a report that counts them, so fourteen manual actions look as bad as
  they are.
- **Three policy hooks survive inside the "no application policy" core**:
  permission suppression (the `AD_ID` and children's-category case),
  export approval, and repository scope bounding. The three-part test decides
  what to automate; it does not make the automated things policy-free, and the
  new text should say so rather than imply otherwise.
- **Whether this is `native_integration.v2` or version 1 amended.** §10 requires
  a new major and a new group name for a change that alters meaning, binding
  from the moment the draft marker comes off — which it has not. Amending in
  place is legitimate; a new group is clearer, and costs one string.
