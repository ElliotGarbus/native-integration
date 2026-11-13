# Native integration metadata for Android and iOS

Draft for review. If accepted, this replaces `SPEC.md`.

## Summary

A Python package that wraps an Android or iOS SDK declares two things: the native
dependencies the application needs, and a list of things the application author
must do. A build tool such as Briefcase or kivyforge adds the dependencies to the
native build and appends the list to the application's `pyproject.toml`, where the
author acknowledges it.

## Motivation

Today this lives in a README. The application author copies a Gradle coordinate
or a Swift package into the build configuration, and finds out what else is needed
when the build or the app fails.

Some of it only the application can do. AdMob needs the application's own ID in
the [Android manifest](https://developers.google.com/admob/android/quick-start)
and in [`Info.plist`](https://developers.google.com/admob/ios/quick-start). An app
that uses the camera [must have](https://developer.apple.com/documentation/bundleresources/information-property-list/nscamerausagedescription)
a purpose string, and only the application's author can write it.

Other things need no new metadata. An AAR's manifest
[merges into the application's](https://developer.android.com/build/manage-manifests),
and its [consumer ProGuard file](https://developer.android.com/studio/projects/android-library)
is appended to the application's. So permissions, components and keep rules for
a package's own code travel with its AAR.

## Declaring

A package declares this in its `pyproject.toml`:

```toml
[tool.native-integration.android.gradle]
dependencies = ["com.google.android.gms:play-services-ads:24.0.0"]

[[tool.native-integration.android.application_action]]
id = "admob-app-id"
description = """\
Set the manifest meta-data com.google.android.gms.ads.APPLICATION_ID to your \
AdMob app ID."""
reason = 'Without this tag the app crashes with "Missing application ID".'
acceptance = ["The app starts without that crash."]

[tool.native-integration.ios.swift_packages]
GoogleMobileAds = { url = "https://github.com/googleads/swift-package-manager-google-mobile-ads", requirement = { from = "12.0.0" }, products = ["GoogleMobileAds"] }

[[tool.native-integration.ios.application_action]]
id = "admob-app-id"
description = "Set GADApplicationIdentifier in Info.plist to your AdMob app ID."
reason = "Google's iOS setup requires this key, and only you have the ID."
acceptance = ["Info.plist has GADApplicationIdentifier set to your iOS app ID."]
```

### Dependencies

These forms follow what the tools accept today. Briefcase and kivyforge both take
`group:artifact:version` strings, and `swift_packages` follows kivyforge's table.

`android.gradle.dependencies` is a list of `group:artifact:version` strings. The
version is fixed: no `+`, ranges or `-SNAPSHOT`. It has no upper bound, because
[Gradle selects the highest version requested](https://docs.gradle.org/current/userguide/graph_resolution.html)
across the graph, so another package can move it past what this one was tested
against.

`ios.swift_packages` is a table keyed by a local name. Each entry has:

- `url`: an `https` URL. This identifies the package, so two distributions may use
  different names for it.
- `requirement`: one of `exact`, `from`, `up_to_next_minor`, `range` or `revision`.
- `products`: a non-empty list of the
  [products](https://developer.apple.com/documentation/packagedescription/product)
  to link.
- `embed` (optional, default `false`): `true` if the products are dynamic
  frameworks that must be copied into the app.

Local paths and branches are not allowed, because a path does not exist outside
the author's machine and a branch moves.

`android.gradle.repositories` is for an SDK that needs a repository the tool does
not already use:

```toml
[[tool.native-integration.android.gradle.repositories]]
url = "https://api.mapbox.com/downloads/v2/releases/maven"
groups = ["com.mapbox"]
reason = "Mapbox does not publish its Maps SDK to Maven Central."
```

`url` must be `https`. `reason` is required, and so is at least one of `groups`
or `modules`. Metadata never contains a credential. If a repository needs one, the
package asks for it with an action.

### Application actions

An action has:

- `id`: unique per distribution and platform, using only letters, digits, `-` and
  `_`, so it can name a TOML table.
- `description`: what the application author must do.
- `reason`: why the package needs it and what breaks without it, not why the
  application uses a capability. A "required only if" condition goes here.
- `acceptance` (optional): a list of end states, each checked on its own. Write
  "the activity is declared in the manifest", not "insert an `<activity>` element".

If what an action requires changes, including its `acceptance`, the package gives
it a new `id`, so it appears as a new todo.

### Acknowledging an action

A tool appends each new action to the end of the application's `pyproject.toml`,
with an empty response:

```toml
# Added by kivyforge. Requested by pyadmob.
# Set the manifest meta-data com.google.android.gms.ads.APPLICATION_ID to your AdMob app ID.
# Why: Without this tag the app crashes with "Missing application ID".
# Acceptance: The app starts without that crash.
[tool.native-integration.ack.pyadmob.android.admob-app-id]
response = ""
```

The author answers by writing a response. Any non-empty text acknowledges the action:

```toml
[tool.native-integration.ack.pyadmob.android.admob-app-id]
response = "Set in the AndroidManifest template."

[tool.native-integration.ack.pyscanner.ios.camera-usage]
response = "Not using the scanner, so no camera access is needed."
```

An acknowledgement records what the author decided, which may be not to act. That
can break the package at runtime, and it is the author's call. The table path uses
the distribution's normalized name, the platform and the `id`. Each action has its
own table because appending a second key to an existing table would need a TOML
rewrite, and repeating its header is invalid.

### In the wheel

The table's contents, except `ack`, are written to
`<name>-<version>.dist-info/native-integration.toml`, with
`metadata-version = "1.0"` added.

Build backends do not read another tool's table, so for now a small PEP 517
wrapper backend does this. If this becomes a PEP, the table moves to the top
level and backends write the file. A
[new table is safe where a new key is not](https://discuss.python.org/t/103890/70).

### Adding to this

Tools ignore keys they do not recognise, so later versions can add optional keys.
A tool trying out a key prefixes it `x-<tool>-`. A new major `metadata-version`
is for changes older tools cannot safely ignore.

## What a build tool does

For each distribution going into the application, a tool:

1. Reads `native-integration.toml`, and rejects malformed metadata or an unknown
   major version, naming the distribution.
2. Uses only the table for the target platform.
3. Gives every dependency to Gradle or SwiftPM as declared, treats Swift entries
   with the same `url` as one package, links every product any distribution lists,
   and embeds the packages marked `embed`.
4. Limits each repository to its `groups` and `modules`, matched exactly, using
   [Gradle's content filtering](https://docs.gradle.org/current/userguide/filtering_repository_content.html).
5. Appends an entry for each action not yet in `pyproject.toml`, with its
   `description`, `reason` and `acceptance` as comments attributed to the
   distribution. It never changes or removes an entry, and ignores one whose action
   no longer exists.
6. Reports every action whose `response` is empty, on every build.
7. Should name the distributions involved when resolution fails. Gradle and
   SwiftPM only know coordinates.

Everything else is the tool's choice, including how it resolves dependencies, how it
gets them into the build, and whether an empty `response` fails the build.

One approach I'd suggest is an update phase that adds each dependency to the settings
the tool already uses in the application's `pyproject.toml`, with a comment naming
the distribution. A later pass builds from there, so the full context is in one place
and a changed dependency shows in a diff.

A response is the author's word. Tools do not read it or evaluate `acceptance`, and
should report an action as acknowledged rather than as satisfied.

Adoption is not the same size everywhere. kivyforge already has these dependency
forms. Briefcase can add Gradle strings to its list, but has no Swift package
setting today, so iOS is new work there. Scoped repositories and acknowledgement
entries are new work for both.

## What stays manual

Every action is manual. The application never supplies content the build applies,
and no tool writes a value on the application's behalf. That includes things the
package knows completely, such as fixed `Info.plist` entries.

I checked this against 18 example packages ([survey](SURVEY.md)), 15 of them
hypothetical wrappers around real SDKs, and 49 items are left for the application. The largest group is 14 strings at a named key, such as
usage descriptions and API keys. The rest are entitlements, background modes, app
extensions, config files and smaller groups.

This will be tedious for some packages. Mediated ads are the obvious case: each
network adds its own SKAdNetwork entries. Two follow-up specs could help:

- An optional key that lets a tool write the application's answer to a named key.
- The insertion points Malcolm suggested, for content the package knows completely.

I would rather add these once tools have used v1.

## Security

Metadata is static, and nothing in it runs code.

A repository can serve any artifact to the build, which is why each one is limited
to named groups and modules.

`description`, `reason` and `acceptance` are third-party text that may be read by
a person or by an agent working for them. Tools display them attributed to the
distribution, and never act on them themselves. When writing them to
`pyproject.toml`, a tool comments every line, so a line break in the text cannot
add configuration.

## Why not PEP 725

In September I wrote that I would adopt PEP 725 for dependencies. I then tried
converting the examples, and changed my mind. Gradle converts well: all 17
dependencies map to `dep:maven/...`. The problems are:

- **Layer.** PEP 725's discussion covers mobile only as cross-compiling wheels
  ([64](https://discuss.python.org/t/103890/64),
  [65](https://discuss.python.org/t/103890/65)). None of the 250 posts in the PEP
  725 and PEP 804 threads mentions Maven, Gradle, Swift or CocoaPods. These
  dependencies are resolved when the application is assembled, not when a wheel is
  built.
- **Swift products.** All 15 Swift packages must name products, and in 13 no
  product matches the repository name. PURL's
  [`swift` type](https://github.com/package-url/purl-spec/blob/main/types/swift-definition.json)
  defines no qualifier or subpath for them. `cocoapods` subspecs are a precedent
  for adding one, but nothing is defined today.
- **Repository scoping.** PURL's `repository_url` says where a package is, not
  which groups a repository may serve.
- **Status.** PEP 725 is [ready but waiting](https://discuss.python.org/t/103890/98)
  for the Packaging Steering Council.

The cost is that tools reading `Requires-External-Dep` will not see these
dependencies unless they are exported.

## What this takes from PEP 725

- **Separate layers.** PEP 725 covers what a wheel is built against and needs at
  runtime. This covers what the assembled application links. A package that needs
  both declares both.
- **The metadata flow.** Static metadata goes from `pyproject.toml` into the wheel,
  as `[external]` goes to `Requires-External-Dep`. Tools read it without running
  code.
- **Absence.** As with `[external]`, no file means the package declares nothing, not
  that it needs nothing.
- **No installer obligations.** Installers do nothing with this file. Paul Moore
  [expects the same](https://discuss.python.org/t/103890/72) of pip and external
  dependencies.
- **No `OR`.** PEP 725 [decided against one](https://discuss.python.org/t/103890/33).
  A dependency here is one package, not a choice between several.
- **Markers, if needed.** No example dependency has a condition, and platform tables
  separate Android from iOS, so v1 has no markers. A later version would use PEP 508
  markers rather than a new syntax.
- **DepURL export.** A Gradle string converts mechanically, for an SBOM or
  `Requires-External-Dep`: `com.google.android.gms:play-services-ads:24.0.0` becomes
  `dep:maven/com.google.android.gms/play-services-ads@>=24.0.0`. It uses `>=` because
  Gradle may select a higher version, and `@24.0.0` would mean exactly that version.
  Swift entries could convert once products have a defined spelling.

## What changed from the last version

| Review comment | Result |
| --- | --- |
| Too broad | 46 tool requirements and a spec of about 39,000 words are now this document |
| No native source in packages | Removed. Native code ships as an AAR or Swift package |
| No entry points | Removed. Metadata goes in `.dist-info` |
| SDK floors are redundant | Removed. Wheel tags and the AAR or `Package.swift` carry them |
| Out of scope: dependency resolution | Removed. It is the tool's |
| Too much XML mapped to TOML | Removed. No manifest or plist vocabulary remains |
| Bootstrap obligations are premature | Removed |
| PEP 621 as a model | Followed: where the data lives, how it is read, and room to experiment |
| Use PEP 725 | Its layering and metadata flow are followed. Its table and DepURLs are not, for the reasons above |

## Questions for reviewers

1. Is the case against PEP 725 right? If PURL defined Swift products, would you
   still want `[external]`, and how would you scope a repository there?
2. Is a `[tool]` table with a wrapper backend acceptable until this is a PEP?
3. Is a todo list useful enough without any automation, or is the optional key
   needed in v1?
