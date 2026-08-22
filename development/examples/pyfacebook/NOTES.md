# Meta's SDK against the current spec

Clean-sheet, from [Getting Started with the Facebook SDK for iOS](https://developers.facebook.com/documentation/ios/getting-started)
and Meta's Android Login quickstart. No `pyfacebook` distribution exists.

Chosen from [SURVEY.md](../../SURVEY.md) as the strongest case for **N1**, the
iOS application-value table §6.3's rationale predicted. It also produced two
findings the survey did not see, which is the argument for writing sidecars
rather than reading documentation.

Run after round five's Batch 0 corrections landed.

## FB1 — three account values, and nowhere to put them *(blocking, iOS)*

Meta's iOS SDK reads `FacebookAppID`, `FacebookClientToken` and
`FacebookDisplayName` from `Info.plist` at launch. The Android half of the same
integration declares the same two identifiers through §6.3 and works.

The specification cannot state the iOS requirement in any form:

- `[ios.contributes.info_plist.values]` is for producer-known constants. A
  producer cannot know an application's Meta app ID, and hard-coding its own
  would be worse than silence.
- §7.3's six prerequisite tables have no entry for *the application supplies a
  scalar*. `application_files` is a whole file, `usage_descriptions` is
  user-facing text the application authors, and `entitlements` is a key whose
  value v1 declines to model.

So the producer cannot even say what is missing. The application builds, links,
launches, and fails on the first login attempt with an SDK error about a
missing app ID — the failure mode the whole convention exists to convert into a
build-time diagnostic.

**§6.3's predicted shape fits without modification**: `id`, `reason`, and an
`info_plist_key` delivery field. Its argument for *parallel* tables rather than
one platform-neutral table is also confirmed here, in the strongest available
way: Meta issues a **different app ID per platform**, so a single answer keyed
by one `id` would be wrong for one of the two platforms.

## FB2 — `<queries>` for `com.facebook.katana`

Android 11+ package visibility means the SDK cannot see whether the Facebook
application is installed unless the manifest declares a `<queries>` entry.

This one is **less severe than the survey recorded**. The entry ships in
`facebook-common`'s own manifest and arrives through AGP's manifest merger, so
an integration that reaches the SDK through §6.5 gets it. The residual case is
a producer's own Java (§6.4) resolving an intent — and there, the failure is
silent, because `PackageManager` answers "not installed" rather than raising.

Recorded as real and narrow, which is a correction to N6's framing rather than
support for it.

## FB3 — `from_dependency` cannot name a transitive module *(new)*

`CustomTabActivity` is the class the application must register for the browser
return. It lives in `com.facebook.android:facebook-common`, which arrives
**transitively** from `facebook-login` — the artifact a producer would actually
declare.

§6.8 requires `from_dependency` to match a dependency **the same sidecar
declares**, so the sidecar has to declare `facebook-common` explicitly as well,
purely to have something to point at. That declaration is not wrong, exactly —
it does pin a version the integration depends on — but it is ceremony forced by
a rule, and it invites a producer to over-declare a vendor's internal module
layout, which is the thing most likely to change under it.

The rule itself is sound: `from_dependency` exists so a component's class has a
declared owner, and pointing at an arbitrary transitive would weaken that. The
fix is probably to permit naming any module **in the resolved graph** of a
declared dependency, checked against the record §6.5 already requires, rather
than only a direct declaration.

Not in the survey. It only appears when you try to write the entry.

## FB4 — an application value cannot be derived from another *(new)*

The login return scheme is the app ID with `fb` prepended: app ID `1234567890`
gives scheme `fb1234567890`. §6.3's inline reference substitutes a value
verbatim and has no notion of composition, so the sidecar asks the application
for the same fact twice — once as `facebook_app_id`, once as
`facebook_login_scheme` — with a `reason` explaining how to derive the second
from the first by hand.

That is a real defect in the small: two answers that must agree, with nothing
checking that they do, and a typo produces a login that returns to nowhere.

It is also **not obviously worth fixing**. A prefix field on the inline
reference would cover this case and invite the next one to ask for a suffix, a
case change, or a template. Recorded as a wart with a workaround, and as
evidence for whoever eventually proposes value templating that at least one
major vendor needs it.

## FB5, FB6 — the two carried forward

- **FB5** — `NSPrivacyTrackingDomains` in the application's privacy manifest,
  which Meta's SDK requires and which no declaration reaches (N3).
- **FB6** — the `-ObjC` linker flag. Meta's Swift package declares its own
  linker settings, so §7.4 covers it; the gap is confined to a producer linking
  the SDK some other way, which narrows N15 usefully.

## What this validated

- **`view_links` under a second vendor.** Meta's own instructions have the
  application hand-write an `<activity>` with an intent filter, three
  categories, and a `@string/fb_login_protocol_scheme` reference. §6.8 replaces
  all of it with a component entry, an export request the application approves
  by name, and one substituted value — and the stereotype removes exactly the
  bug it was designed for, since Meta's snippet is one `DEFAULT` category away
  from silent failure.
- **§6.3 on Android, twice, with a `manifest_meta_data` key each.** The second
  entry (`ClientToken`) is a value Meta added in SDK 13 and made mandatory,
  which is the version-drift case the sidecar keeps in sync and a README does
  not.
- **`LSApplicationQueriesSchemes` through `append`.** Four schemes, granting
  the application nothing — §7.6's own example, met by a real vendor.

## Verdict

**Android: clean.** **iOS: blocked on FB1**, with a wrapper that would build
and could not work. One package, both halves of N1's argument.
