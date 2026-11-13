# Native integration: proposed v1 scope

@mhsmith @freakboy3742 Before I put more effort into the full proposal, I'd like
to know whether this direction looks right to you.

## Objective

Let a Python package that wraps an Android or iOS SDK tell the tool building the
application which native dependencies it needs and what the application author must do.

## Proposal

A package that wraps an Android or iOS SDK declares two things in the
`[tool.native-integration]` table of its own `pyproject.toml`, which a small wrapper
backend copies into `.dist-info` (until this is a PEP):

- **Native dependencies:** Gradle Maven coordinates, Swift package URLs, and any Maven
  repository an SDK needs.
- **Application actions:** a todo list of what only the application author can do.

```toml
# pyadmob's pyproject.toml
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

A build tool (Briefcase, kivyforge) reads this from each installed package and passes
the dependencies to Gradle or SwiftPM, much as an installer handles `Requires-Dist`.
How it does that is its choice, including whether it records them in `pyproject.toml`
or a lock file.

The tool also appends each new action to the application's `pyproject.toml`, with an
empty `response`. The author answers it:

```toml
# Added by kivyforge. Requested by pyadmob.
# Set the manifest meta-data com.google.android.gms.ads.APPLICATION_ID to your AdMob app ID.
# Why: Without this tag the app crashes with "Missing application ID".
# Acceptance: The app starts without that crash.
[tool.native-integration.ack.pyadmob.android.admob-app-id]
response = "Set in the AndroidManifest template."
```

The response is an acknowledgement, not a claim that the action was taken. "Not using
the scanner, so no camera access is needed" is a valid answer. The tool reports
every empty response on every build. Whether an empty response fails the build
is the tool's choice.

Every action is manual in v1. No tool writes on an `application_action` to the manifest or `Info.plist`.
The author will use what the build tool already provides, such as Briefcase's
`android_manifest_extra_content`.

Permissions are not in this metadata. If a package needs one its SDK doesn't declare,
it uses an `application_action` to ask the author to declare it. Similarly, on iOS an
`application_action` asks the author to write a purpose string.

This proposal follows Russell's PEP 621 suggestion: it defines where the data lives
and how it is read, and keeps the initial metadata small.

## A change on PEP 725

Previously, I wrote "Agreed and adopted" about PEP 725. I'm walking that back. I tried
converting the 18 example packages, 15 of them hypothetical wrappers around real SDKs,
and it is better to leave these mobile dependencies in their native format.

DepURLs are meant to be portable across packaging ecosystems, and virtual packages let each ecosystem choose a provider. That fits system dependencies. Here each platform has one resolver, and a Gradle coordinate or Swift URL names exactly one artifact. A tool would only convert the DepURL back again.

All 17 Gradle dependencies convert, but gain nothing. A Swift dependency has no complete
DepURL: SwiftPM links products, and PURL's `swift` type defines no way to name them. All 15
Swift packages in the examples name products, and in 13 none is named after the
repository.

I take PEP 725's flow from `pyproject.toml` into the wheel, like PEP 725,  this puts no
obligations on installers. A package can use both: PEP 725 for what a wheel is built
against, and this proposal for what the application links.

## Where I'd like your view

1. Are dependencies plus a todo list the right scope for v1?
2. Malcolm, you asked me to leave these dependencies to PEP 725. Is there value in
   `[external]` here that I'm missing?
3. Russell, you suggested permissions as possible first metadata. Would you recommend
   adding metadata for permissions?

And of course any other feedback is welcomed.  None of this has been built.