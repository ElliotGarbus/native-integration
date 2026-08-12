# Discussion post — first call for review

Draft for the repository's **Ideas** discussion, and the anchor every other
venue should point at. Not part of the specification; nothing here is normative.

> **Using it elsewhere.** Trim hard. The p4a issue and a Discord message should
> be three sentences and a link *to the discussion* — not this text again. One
> place to reply beats four.
>
> For Briefcase and Chaquopy, lead with question 3 and the argument that two
> tools reading one convention beats each growing its own. The KivMob story is
> Kivy-specific and reads as someone else's problem.
>
> Keep the failure rate in. A specification that reports where it broke reads as
> tested; one that lists only capabilities reads as unreviewed. The failures are
> the credibility.

---

**Title:** A convention for Python packages to declare their Android/iOS integration — looking for holes

---

`pip install` faithfully installs what a wheel contains, but there's no
convention for translating a Python dependency's Android or iOS integration
requirements into the host app's Gradle or Xcode configuration. So the package
knows what it needs, and the app author is the one obliged to say it — hand-copied
out of a README, repeated per app, silently drifting on every version bump. When
the package is a *transitive* dependency, the person on the hook may not know
it's in the tree at all.

**[native-integration](https://github.com/ElliotGarbus/native-integration)** is a
draft convention for closing that: a package ships a small TOML sidecar declaring
its native requirements, a build tool discovers it through an entry point, reads
it **without importing the package**, and stages it into the generated project.
No new artifact type, no build-backend plugin, no change to any packaging
standard.

It's a draft, nothing is implemented, and it's deliberately not one tool's
feature — a convention only one tool reads isn't worth defining.

## What I'd genuinely like torn apart

**1. Is the declaration set right — what's missing, what's unnecessary?**

Ten integration cases have been written as sidecars: four existing packages from
PyPlatformPackages, plus clean-sheet ones for Firebase, Sentry, Stripe and
Mapbox. They're all in
[`examples/`](https://github.com/ElliotGarbus/native-integration/tree/main/examples)
with the findings beside them.

**Every one was written by the same hand.** A sidecar written by someone who
didn't write the spec is worth more than another written by someone who did, and
that's the reading the examples can't give themselves.

**2. Does the "app keeps authority" split land in the right place?**

A package may *request* a permission or register a component, but only the app
may mark a feature `required` or a component `exported`, and the app can suppress
any contributed permission. A package can never write an entitlement, and never
writes an iOS purpose string — that text is App Store reviewed and the app
answers for it.

**3. If you maintain a build tool: is this something you'd plausibly read?**

There are 26 numbered obligations on a consuming tool in §8. If one of them is
unimplementable in your architecture, that's the most valuable thing you could
tell me.

## What already came out of trying it

One of the four original packages fit without a workaround. The rest changed the
spec:

- **A Swift package can now *be* the Python extension module.** Most of
  PyPlatformPackages' iOS packages are SwiftPM libraries implementing a Python
  module directly — nothing could make one importable, so the build succeeded and
  `import` failed.
- **Purpose strings and app extensions moved to the app.** The spec's own example
  had a library writing the sentence App Store review reads.
- **The hardest failures turned out to be correct refusals.** Firebase's Gradle
  plugin and Crashlytics' symbol upload are unreachable because the spec declines
  build-time execution — not because something's missing. That's a different and
  better position than "we haven't got to it yet."

## Reading order

Don't start with the spec — it's ~17k words.
**[README](https://github.com/ElliotGarbus/native-integration)** first, then
**one** example:
[Firebase](https://github.com/ElliotGarbus/native-integration/tree/main/examples/firebase)
to watch it hit real boundaries, or
[PyGMA](https://github.com/ElliotGarbus/native-integration/tree/main/examples/pygma)
to see it work end to end.
[Appendix D](https://github.com/ElliotGarbus/native-integration/blob/main/SPEC.md#appendix-d-declaration-reference)
is a one-line description of every key if you'd rather scan the surface.

Disagreement is more useful than agreement. Two rounds of external review both
changed it substantially — the places it's wrong now are the places nobody has
looked yet.
