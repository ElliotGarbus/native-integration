# What the examples leave for the application

The 18 contract-1 sidecars in `development/examples/` and `examples/pystripe/`
(14 integrations), re-read under [SCOPE.md](SCOPE.md). Fifteen are hypothetical
wrappers around real SDKs; `pycorelocation`, `pygma` and `pyonesignal` are not
marked that way. Under the restart:

- Native dependencies stay in the forms build tools already accept.
- The package ships no source. Its glue code is its own AAR or Swift package,
  and that AAR's manifest merges into the application's.
- SDK floors are gone.

Whatever is left is an application action. Counts are items / packages.

## Where each declaration goes

| Declaration | Items | Goes to |
| --- | --- | --- |
| `gradle_dependencies` | 17 / 16 | Kept as `group:artifact:version` strings; 14 ranges lose their upper bound |
| `swift_packages` | 15 / 15 | Kept, in kivyforge's table form |
| `gradle_repositories` | 2 / 2 | Kept |
| `min_sdk`, `compile_sdk`, `target_sdk`, `deployment_target` | 48 / 18 | Wheel tags, and the AAR or `Package.swift` |
| `src.java`, `owns`, `r8.keep_classes`, `swift_symbol_prefixes` | 21 / 8 | The package's own AAR |
| `components`, `features` | 5 / 3 | The package's own AAR manifest |
| `r8.keep` for a dependency, in a package with its own AAR | 6 / 6 | That AAR's consumer rules |

Six packages ship Java today: `core`, `messaging`, `pyagora`, `pyairship`,
`pygma` and `pystripe`. Each would now publish an AAR, which is the cost
mhsmith accepted on their behalf.

## Would DepURLs work?

Dependencies do not use DepURLs, but reviewers will ask, so this was tested.
The counts are these 18 sidecars only. Of the 115 `native.toml` files in the
repository, 91 are conformance fixtures and 6 are redesign copies. Gradle
`configuration` appears only in fixtures.

All 17 Gradle dependencies convert. The three single-version `coordinate`s
become floors (`>=`), which drops the version they were tested against.

No Swift dependency converts completely. SwiftPM links products, and in 13 of
the 15 packages no product is named after the repository, so a tool cannot infer
one. PURL's `swift` type defines no qualifiers and no subpath, so any spelling
of a product is a convention until PURL defines it.

The closest precedent is PURL's `cocoapods` type, which uses the subpath for a
subspec. Applied here, each product is its own entry:

```
dep:swift/github.com/firebase/firebase-ios-sdk@>=11.0.0,<12#FirebaseMessaging; sys_platform == 'ios'
```

That gives 17 entries for the 14 packages with a version requirement. They parse
with `packageurl-python`, but that shows syntax only: the same parser accepted a
`swift` PURL missing its required namespace. `pycorelocation` pins a git
revision, which is not a PEP 440 specifier, and does not convert.

## Left for the application

| What the application must do | Items | Packages | Conditional |
| --- | --- | --- | --- |
| Supply a string at a named key | **14** | **7** | 5 |
| iOS entitlement | 5 | 3 | 1 |
| iOS `UIBackgroundModes` value | 5 | 5 | 1 |
| iOS app extension | 4 | 4 | 3 |
| Copy fixed values into `Info.plist` (SKAdNetwork, `LSApplicationQueriesSchemes`) | 4 | 4 | 0 |
| Supply a value used in code or a manifest placeholder, not at a key | 4 | 3 | 0 |
| Add a file (`GoogleService-Info.plist`, `AirshipConfig.plist`, a model) | 3 | 3 | 0 |
| Fixed Android `<meta-data>` (`OPTIMIZE_INITIALIZATION`) | 2 | 2 | 0 |
| Register a return URL scheme and handle the callback (Facebook on both platforms, Stripe on iOS) | 3 | 2 | 1 |
| Call an initializer (Mintegral) | 1 | 1 | 0 |
| Supply `NSLocationTemporaryUsageDescriptionDictionary` | 1 | 1 | 1 |
| Add R8 keep rules for SDK classes Python reaches reflectively (`pymapbox`, `pyonesignal`, `pytflite`) | 3 | 3 | 0 |

The 14 strings at a key are five Android `<meta-data>` values (Facebook ×2,
Sentry, AdMob, AppLovin) and nine iOS `Info.plist` strings (eight usage
descriptions and `GADApplicationIdentifier`). Facebook's Android activity
moved from `components` to the URL-scheme row, because Meta's instructions have
the application write it. A vendor's consumer rules cover what the vendor's SDK
needs, not what a Python wrapper reaches by reflection, so a package with no AAR
of its own has nowhere else to put those keep rules. No example declares
`core_library_desugaring`; a package that needed it would also use an action.

The examples' `NOTES.md` record items contract 1 could not express. Under the
restart, each one is a prose action:

- the Firebase and Crashlytics Gradle plugins and build scripts (firebase F1, F4)
- Airship Autopilot (AS1)
- OneSignal's `Application` subclass (A2)
- Agora's Broadcast Upload Extension (AG2)
- Health Connect's `<queries>` entry and its rationale activity (HC1, HC2)
- Facebook's privacy-manifest tracking domains (FB5)

Nothing in the set is inexpressible any more. The cost is that more of it is
manual.

M2 and `SPEC.md` §6.6 say Mapbox's repository needs a token. It no longer does:
[Mapbox's install guide](https://docs.mapbox.com/android/maps/guides/install/)
shows no repository credential, and on 2026-11-01 the 11.0.0 and 11.34.1 POMs and
AARs downloaded anonymously.

## Unverified

These need the vendor's own artifacts, per the evidence standard in
`AGENTS.md`, before they are counted either way. They change how many actions a
package declares, not the shape of an action, so they do not block v1:

- **Android permissions: 26 items in 12 packages.** Five of the packages ship
  their own AAR and declare permissions there. For the other seven (`pyadmob`,
  `pyadmob-applovin`, `pyadmob-mintegral`, `pyfacebook`, `pyhealthconnect`,
  `pymapbox`, `pyonesignal`), the permission is free only if the vendor's AAR
  manifest declares it. Otherwise it is an action.
- **`-ObjC` (`objc_categories`), 3 packages.** FB6 says Meta's Swift package
  sets its own linker flags. Google's mediation packages are unchecked.

## Not covered

`pycorelocation` and `pywebviews` are Swift packages that carry a CPython
extension module, which the build tool must link and register (L2, W1).
Neither PEP 725 nor an action automates that. It is a contract between build
tool and package, not between package and application, and is out of scope.

## What this means for v1

v1 actions are prose, with no structured kinds, so that Briefcase and
kivyforge can adopt the spec with small changes. A tool reports each action and
the application author does the work.

If adopters find that tedious, the 14 strings at a key are the first candidate
for an optional key, since a tool could then write the application's answer for
it. The 4 fixed `Info.plist` rows and the 2 fixed `<meta-data>` items come next,
but the package knows those values completely, so they are contributions rather
than requests.

12 of the 49 items are "required only if", all on iOS.
