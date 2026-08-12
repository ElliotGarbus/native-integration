# Mapbox against the current spec

Clean-sheet, from [Mapbox's Android install guide](https://docs.mapbox.com/android/maps/guides/install/)
and [Navigation SDK installation](https://docs.mapbox.com/android/navigation/guides/install/).
No `pymapbox` distribution exists.

Mapbox was chosen from a coverage gap rather than a hunch. After nine sidecars,
exactly one declarable table had never been used:
`[[android.contributes.gradle_repositories]]` — §6.6 — which carries the
strongest language in the specification:

> *"A repository contribution changes where artifacts in the application's build
> can resolve from, which makes it a supply-chain concern of a different order
> than any other contribution — an unconstrained repository added by a
> transitive dependency is a dependency-confusion vector."*

The most safety-critical section in the document was completely untested.
Mapbox is the canonical custom-repository case. It exercises §6.6, validates the
part that matters, and then hits a wall the section does not know about.

## M1 — §6.6 works, and the group restriction earns itself *(a validation)*

```toml
[[android.contributes.gradle_repositories]]
url = "https://api.mapbox.com/downloads/v2/releases/maven"
reason = "Mapbox does not publish its Maps SDK artifacts to Maven Central"
groups = ["com.mapbox"]
```

Every requirement §6.6 imposes is satisfiable and none of it is ceremony:

- **`reason` is REQUIRED** and there is a real one — Mapbox genuinely does not
  publish to Maven Central, which is the only defensible ground for asking an
  application to widen its resolution surface.
- **`groups` or `modules` is REQUIRED**, and `["com.mapbox"]` is exactly right.
  The endpoint serves Mapbox artifacts and nothing else, so constraining it
  costs the producer nothing and reduces the repository from "may shadow
  anything" to "may serve what it named."
- **Distinct prominence in the §9 report** is proportionate here. A mapping SDK
  arriving transitively and quietly adding a resolution source is precisely the
  case the rule was written for.

This is the section behaving as designed on its first real contact.

## M2 — the credential, and why it is not a missing field *(the finding)*

The repository is **not anonymous**. Mapbox requires HTTP basic authentication:
username `mapbox`, password a **secret** token scoped `DOWNLOADS:READ`, which
Mapbox's documentation says to store in `~/.gradle/gradle.properties` and keep
out of source control.

§6.6 has `url`, `reason`, `groups`, `modules`. Nothing else. **A consumer that
reads this sidecar and does exactly what it says gets `401` on every
`com.mapbox` artifact.**

The reflex is to add a credential field. That reflex is wrong, and the reason it
is wrong is the interesting part:

- A sidecar is **package data inside a wheel**. Anything written there is
  readable by everyone who installs the distribution, and by anyone browsing
  the sdist on PyPI. A secret cannot live there under any spelling.
- Worse, §9 requires the integration record to hash `native.toml` and every
  resource it references, and to be *durable and diffable* — typically
  committed. A credential in a sidecar would be laundered into the
  application's version control by a rule written to improve auditability.

So the specification is **right to have no field** and **wrong to have nothing**:
the declaration is incomplete by necessity, and a producer has no way to say
"this repository needs an application-supplied credential."

**The shape that fits** is the one §7.3 has converged on four times already — a
prerequisite, with an inline reference mirroring §6.3's `application_value`:

```toml
[[android.contributes.gradle_repositories]]
url = "https://api.mapbox.com/downloads/v2/releases/maven"
reason = "…"
groups = ["com.mapbox"]
credential = { username = "mapbox", password = { application_secret = "mapbox_downloads_token" } }
```

with rules that fall straight out of the problem: the application supplies the
secret through the consumer's own configuration; the consumer **MUST NOT**
write it into the generated project, the integration record, or any diagnostic;
and an unsatisfied secret is a reported prerequisite like any other.

Two things make this more than a convenience. Without it a consumer cannot
resolve the dependency at all, so the sidecar is not merely terse but
non-functional. And the §9 interaction means a naive implementer *will* leak the
secret into a committed artifact unless the specification says not to — which it
currently has no occasion to say, because it does not know credentials exist.

Recorded as **P27**.

> **Decided since.** §6.6 gained `credentials_required = true` — the flag and
> nothing more — plus an explicit prohibition on a sidecar containing a
> credential in any field. The structured `credential = { username, password }`
> form sketched above was **rejected**: the username and the secret reference
> are things a consumer passes through rather than acts on, so `reason` carries
> them better, and every field added there is somewhere a producer could put a
> token by mistake. A boolean cannot hold a secret.
>
> §9 gained the rule against recording secrets, and that was the more important
> half — it fixes a defect that existed before this proposal and would have
> outlived its rejection.

## M3 — two tokens, and only one of them is a build concern

Mapbox uses two different tokens, which the install documentation itself
conflates and which are worth separating:

| Token | When | Where |
| --- | --- | --- |
| Secret, `DOWNLOADS:READ` | build time | Gradle repository credential (M2) |
| Public, `pk.` | runtime | string resource, `Info.plist`, or programmatic |

The public token is per-application and genuinely needed, but both platforms
accept `MapboxOptions.accessToken` programmatically, so a Python wrapper passes
it in and neither the Android string resource (excluded by §11) nor iOS's
`MBXAccessToken` is required.

That matters for a claim made earlier in this repository. When P2 was revisited,
the note read: *"The genuine iOS counterpart would be this same shape aimed at
an `Info.plist` key an SDK reads at launch. No example has needed one."* Mapbox
**does** read one — `MBXAccessToken` — so the claim was too strong. It survives
only on the escape-hatch test: the programmatic path exists, so no new primitive
is forced. That is a weaker position than "no example has needed one," and the
distinction is the one this repository keeps having to relearn.

## M4 — §12's guidance applies cleanly, for once

`ACCESS_FINE_LOCATION` is needed only for the location puck — one feature among
many. §12 says feature-conditional native surface belongs in an optional
distribution, and unlike PyCoreLocation (§12.1, a framework binding with no seam
to split along) **a Mapbox wrapper genuinely has the seam**: `pymapbox` and
`pymapbox[location]` are different Python API surfaces, not one class carved in
half.

So the sidecar declares no location permission, and §12's advice is followed
rather than excused. It is the first example where that guidance is both
applicable and free.

## M5 — a real instance of §10's deferred conditional contribution

Mapbox ships two artifacts for the same SDK: `com.mapbox.maps:android-ndk27` for
applications targeting 16 KB memory pages, and `com.mapbox.maps:android`
otherwise. Which one is correct depends on a property of the application's
build, not of the package.

§10 anticipates exactly this — *"conditional contributions (a `when` key with a
**closed vocabulary** of conditions such as ABI or simulator/device — not an
expression language)"* — and this is the first concrete instance in the example
set. One instance, deferred work, no proposal. Recorded so the anticipated
feature has evidence attached when it is next considered.

## Verdict

§6.6 passes its first test on everything it models and fails on the one thing it
does not know exists. That is a good failure: the rules that were written to be
strict — required `reason`, mandatory content filtering, distinct reporting —
all hold up under a real vendor, and the gap is a category the section never
contemplated rather than a rule that turned out wrong.

**M2 is the finding**, and its interest is not "add a credential field" — it is
that credentials cannot go in a sidecar at all, that §9's own auditability rules
would make a naive implementation leak them into version control, and that the
specification currently has nowhere to say so.

**M3 is a correction** to a claim made two commits ago, and a reminder that
"no example needs this" is a much stronger statement than "every example has an
escape hatch."
