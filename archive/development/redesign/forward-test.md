# Forward test: four things the first attempt cannot say

The [probe](README.md) re-expressed the five hardest sidecars that already
exist. Every one of them was a case the first attempt had been *shaped around*,
so a clean result there says the redesign loses nothing — not that it gains
anything, and not that it will stop growing.

This tests the other direction. Four requirements from
[SURVEY.md](../SURVEY.md) that the first attempt **cannot express at all**,
asked one question each: does the redesign absorb it *without inventing
vocabulary*? If a case needs a new `kind`, a new table or a new rule, the
maintenance claim is weaker than it looks.

All four land. Findings continue the probe's numbering at **V11**.

> **Superseded in part by [`review-01.md`](review-01.md).** FT1's and FT3's
> fragments put an entitlement value and an app group identifier in
> `application_value`. Both are **actions carrying a value by `uses`**: a
> consumer can write an entitlements file but cannot get an entitlement into a
> provisioning profile, so it cannot place the requirement deterministically.
> The diagnosis in FT1 — that §7.3's key-only check is a false pass — stands
> and is the reason the case matters.

Vendor facts are taken from SURVEY.md's rows and findings rather than
re-derived; anything extrapolated beyond them is marked.

---

## FT1 — Adjust: an entitlement that carries a value

**Survey rows 7 and 8, finding N17.** `com.apple.developer.associated-domains`
carries vendor-specific domains — Branch, AppsFlyer, Adjust, and passkeys'
`webcredentials:`. §7.3 models an entitlement as a `key` and nothing else, and
[P26](../PROPOSALS.md) rejected modelling the value outright, on the ground that
a consumer can neither write nor check it.

**What the first attempt can say:**

```toml
[[ios.requires.entitlements]]
key = "com.apple.developer.associated-domains"
reason = "Add applinks:<your Adjust link domain>. Ask your CSM for the domain."
```

Satisfied when *"the application configures the entitlement **key**"*. So an
application that enables Associated Domains and lists **no domains** satisfies
this requirement completely, and the build proceeds. The check passes on a
configuration that cannot work.

That is worse than manual, and it is the sharpest single result in this test: a
verification that returns *yes* for a wrong answer costs more than one that
admits it cannot tell.

**What the redesign says.** The domain is a value only the application has, and
it has a delivery site — so it is a value, not an action, and it scaffolds:

```toml
[[ios.requires.application_value]]
id = "adjust_link_domain"
kind = "entitlement"
key = "com.apple.developer.associated-domains"
placeholder = "applinks:<TODO: your Adjust link domain>"
reason = """\
Your Adjust link domain, from the dashboard. You must also enable Associated \
Domains on the App ID — the entitlement has to be in the provisioning profile \
before it can be signed."""
```

The consumer writes what the application supplies, exactly as it does for a
usage description, and blocks while the placeholder stands. Nothing is written
on the producer's authority; §2.1's rule survives intact.

> **V12 — an entitlement carrying a value is a value, and the first attempt's
> key-only check is a false pass.** This is not a new capability bolted on: it
> falls out of the value/action split, because the question *"is there somewhere
> for the consumer to write it?"* has an answer here and P26 never asked it. The
> unresolved half is provisioning, which no consumer can do and which stays in
> `reason` — the same place the first attempt put all of it.

## FT2 — WeChat: an application-owned class, with attributes

**Survey row 42, findings N20 and N5.** WeChat resolves
`${applicationId}.wxapi.WXEntryActivity` by name. It must be **exported**, must
be `singleTask`, and needs a matching `taskAffinity`.

**What the first attempt can say:** `application_classes` carries the `id`, the
`package_suffix` and the `name`, satisfied by acknowledgement. The three
attributes are unreachable — N5 examined `launchMode` and `taskAffinity` and
closed them out deliberately, on the ground that the class belongs to the
application and a producer never registers the component. Correct, and it
leaves the producer unable to state the requirement it knows.

**What the redesign says:**

```toml
[[android.requires.application_action]]
id = "wechat_entry"
kind = "application_class"
key = "${applicationId}.wxapi.WXEntryActivity"
summary = "Add WXEntryActivity under your own application ID"
reason = """\
WeChat resolves this class by name under your application ID. It must extend \
Activity, implement IWXAPIEventHandler, and forward to the SDK."""
instructions = "setup/wechat-entry-activity.md"
```

The attributes are in the instructions file, as the `<activity>` element to
paste. **The model never learns what `launchMode` is**, and does not have to:
Android can add fifty activity attributes and nothing here changes.

> **V13 — the platform's own vocabulary stays outside the model.** This is the
> maintenance argument made concrete rather than asserted. The first attempt had
> to decide, per attribute, whether to model it — and every *no* left a producer
> unable to state a real requirement, while every *yes* was a permanent
> obligation. The redesign declines the question.

## FT3 — Braze: four actions, two slots, and a shared value

**Survey row 11, findings N9 and N17.** A notification icon drawable, a
notification service extension **and** a content extension, and an app group
shared between the application and both extensions.

**What the first attempt can say:** the icon is `[[android.requires.resources]]`
(landed from N9). The service extension is `app_extensions`. The content
extension was unreachable until `kind` opened, and is reachable now. The app
group is an entitlement whose *value* — which must be identical across three
targets — is unmodelled, exactly as in FT1.

**What the redesign says** — four actions, of which two claim platform
singletons:

```toml
[[ios.requires.application_action]]
id = "braze_nse"
kind = "app_extension"
slot = "ios:extension:notification_service"
summary = "Add a Notification Service Extension"
reason = "Rich push: images, and delivery confirmation."
instructions = "setup/braze-nse.md"

[[ios.requires.application_action]]
id = "braze_nce"
kind = "app_extension"
slot = "ios:extension:notification_content"
summary = "Add a Notification Content Extension"
reason = "In-notification UI for Braze's rich push templates."
instructions = "setup/braze-nce.md"

[[ios.requires.application_value]]
id = "braze_app_group"
kind = "entitlement"
key = "com.apple.security.application-groups"
placeholder = "group.<TODO: your bundle id>.braze"
reason = """\
The same group identifier must be configured on the application and on both \
extension targets, or Braze cannot share delivery state between them."""
```

Two slots, distinct, so a second push SDK asking for `notification_service`
collides visibly and one asking for `notification_content` does not. That is
V3 doing its job under the load it was proposed for — Braze is the vendor that
wants both at once.

> **V14 — `slot` holds at four actions across two singletons.** The composition
> check does not degrade when a single package claims more than one slot, and
> the collision surface stays exactly the platform's own: one target per
> extension point.

## FT4 — AppsFlyer: a deferral becomes a stated requirement

**Survey row 7, finding N3.** `NSPrivacyTrackingDomains` in the application's
privacy manifest. N3 landed the accessed-API half as `accessed_api_types` and
**deferred tracking domains**, with a trigger: *"a producer whose own
contributed code contacts a tracking domain."*

The deferral is defensible and this test does not overturn it — for a wrapper
whose SDK arrives as a Swift package, the package carries its own manifest and
the producer's own code may contact nothing. What the deferral costs is that
today the requirement is **invisible**: an application that must list domains
learns so at upload, weeks later, from App Store Connect.

**What the redesign says**, without settling whether it should eventually be
automated:

```toml
[[ios.requires.application_action]]
id = "appsflyer_tracking_domains"
kind = "privacy_manifest"
summary = "List AppsFlyer's endpoints under NSPrivacyTrackingDomains"
reason = """\
Apple requires the application's privacy manifest to name every domain \
contacted for tracking. The upload is rejected without it, weeks after the \
build, naming a domain rather than a package."""
instructions = "setup/appsflyer-tracking-domains.md"
```

> **V15 — under the redesign a deferral degrades to *manual*, not to *silent*.**
> This is a general property, not a fact about one vendor. The first attempt has
> exactly two states for a capability: modelled, or absent — and absent means the
> producer cannot say the thing at all. A third state now exists between them, and
> it is the state most deferrals belong in: **stated, reported, acknowledged, and
> not automated.** Every deferral in [SURVEY.md](../SURVEY.md) and every exclusion
> in §11 that is a deferral rather than a principle can be re-read against this.
>
> The lifecycle deferral is the largest instance. *"Call `pyfoo.init()` early in
> your application"* is an action — honest, attributable, and reported — where
> today it is a gap the specification can only apologise for.

## What the four cases cost the model

Nothing new. The vocabulary used above is what the probe already proposed:

| Used | Introduced by |
| --- | --- |
| `application_value` + `kind = "entitlement"` | falls out of V4's delivery-site rule |
| `application_action` + `kind = "application_class"` | probe |
| `application_action` + `kind = "app_extension"` + `slot` | probe, V3 |
| `application_action` + `kind = "privacy_manifest"` | **new `kind` value, no new machinery** |
| `instructions` | probe |

`privacy_manifest` is a new *value* in an open vocabulary, which is the case
V1 exists for: a consumer that does not implement it reports the summary and
asks for acknowledgement, and the build is not blocked by a consumer's age.
No new table, no new rule, no new satisfaction mode.

> **V11 — four requirements the first attempt cannot state, absorbed with one
> new vocabulary value between them.** That is the maintenance claim tested
> rather than asserted. It is not proof — four cases chosen by one person — but
> it is the same method that changed the first attempt every round, and the
> result did not have to come out this way.

## What this did not settle

- **Whether a value can live inside an action.** FT1 and FT3 both hit it: an
  associated domain and an app group are values the application supplies
  *within* something it must separately configure and sign. Splitting them —
  a value for the string, prose in `reason` for the capability — works and is
  what is written above, but it means one requirement appears in two places and
  the consumer cannot tell they are one thing. Worth deciding deliberately
  rather than by default.
- **Whether `kind` values need a registry.** V1 says an unknown one degrades,
  which is what makes the model cheap. It also means two consumers can
  implement different sets and a producer cannot tell what will be checked. A
  non-normative list of known kinds, extended without a version bump, is
  probably the answer — but it is the seam where this design could quietly
  regrow the thing it replaced.
- **Whether the icon in FT3 is a value or an action.** A drawable the
  application supplies under a name the producer fixes has a delivery site of a
  sort — the resource name — but the consumer cannot write a drawable. It is
  written as an action here on the ground that only presence is checkable, and
  that is worth a second look.
