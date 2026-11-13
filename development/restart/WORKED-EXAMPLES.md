## Revised model and worked example

@freakboy3742 Thanks. Your cardinality point led me to restructure the proposal. As before, none of this is implemented.

Three changes first:

- `application_action` is now `application_requirement`.
- Acknowledgements and `revision` removed.
- The `id`, `kind` and `feature` fields are gone. A declaration's position in the table carries that information instead.

### The model

A package declares requirements, which are things that must be true of the packaged app. There are three tiers, as we discussed earlier in this thread:

- **Application requirements:** the base form, which is a name and a description. Any tool can show one to the app author.
- **Standard kinds:**  native dependencies and permissions.
- **Tool-defined keys:** a reserved `tool.<name>` table, where a tool can try something before it is standardized.

Permissions and dependencies are requirements too. The `application_requirement` key holds the requirements that have no standard kind.

The key is `application_requirement` and not `requirement` for two reasons. A bare `requirement` reads as a Python package requirement, which is the confusion you pointed out. The prefix also says who must satisfy it: the application.

Each requirement belongs to a platform, and may also belong to a feature:

- Directly under a platform, it applies whenever the package is in the app.
- Under a **feature**, it applies only when the app selects that feature for that platform.

A feature is a capability of the Python package, and the package names it. A feature table takes the same keys as a platform table, so dependencies, permissions and application requirements are all scoped the same way. A feature has one name across platforms, and each platform declares what the feature needs there.

As before, the package's table is copied into `.dist-info`, and the build tool reads it from each installed distribution. The tool never edits the app's `pyproject.toml`.

### Worked example

This is the same app as before, using plyer for GPS and pyadmob for ads. Both packages' declarations are hypothetical.

**plyer** has capabilities an app may not use, so it declares features:

```toml
# plyer's pyproject.toml, if it adopted this
[tool.native-integration.android.feature.gps]
permissions = [
    "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.ACCESS_FINE_LOCATION",
]

[tool.native-integration.android.feature.vibrator]
permissions = ["android.permission.VIBRATE"]

[tool.native-integration.ios.feature.gps]
permissions = ["NSLocationWhenInUseUsageDescription"]
```

**pyadmob** 

```toml
# pyadmob's pyproject.toml
[tool.native-integration.android.gradle]
dependencies = ["com.google.android.gms:play-services-ads:[24.0,25.0[!!24.0.0"]

[tool.native-integration.android.application_requirement]
admob-app-id = "Set the manifest meta-data com.google.android.gms.ads.APPLICATION_ID to your AdMob app ID."

[tool.native-integration.ios.swift_packages]
GoogleMobileAds = { url = "https://github.com/googleads/swift-package-manager-google-mobile-ads", requirement = { from = "12.0.0" }, products = ["GoogleMobileAds"] }

[tool.native-integration.ios.application_requirement]
admob-app-id = "Set GADApplicationIdentifier in Info.plist to your AdMob app ID."
```

**The app** includes both packages as ordinary Python dependencies, then selects which of plyer's features it uses on each platform:

```toml
# The app's pyproject.toml
[project]
dependencies = ["plyer", "pyadmob"]

[tool.native-integration.android.features]
plyer = ["gps"]

[tool.native-integration.ios.features]
plyer = []
```

pyadmob has no features to select, so installing it is enough to activate its requirements. `[]` means the app uses none of plyer's features on iOS. A missing entry means the app hasn't chosen yet, so the tool lists plyer's features until it does.

On an Android build, the build tool:

- passes pyadmob's dependency to Gradle unchanged
- checks that the app has declared the two permissions for plyer's `gps` feature
- ignores `vibrator`, which the app didn't select
- shows pyadmob's application requirement to the author

On an iOS build, the build tool:

- passes the GoogleMobileAds package to SwiftPM
- ignores plyer, because the app selected none of its features
- shows pyadmob's application requirement to the author

The tool shows an application requirement with the name of the package that declared it:

```
pyadmob requires:
  admob-app-id: Set the manifest meta-data com.google.android.gms.ads.APPLICATION_ID to your AdMob app ID.
```

The author meets the requirement with settings the tool already has, such as Briefcase's [`android_manifest_application_extra_content`](https://briefcase.beeware.org/en/stable/reference/platforms/android/gradle.html) for the manifest and [`info`](https://briefcase.beeware.org/en/stable/reference/platforms/iOS/xcode.html) for `Info.plist`. The tool can't tell whether a requirement has been met, so each tool chooses when and how to show the list.

### Your questions

**What is the difference between the id and the feature?** The `id` is gone. A feature groups requirements the app may or may not need: many capabilities in a package like plyer, or one optional capability such as a scanner. The app selects the features it uses, and only those requirements apply. A permission or dependency is identified by its native name. An application requirement keeps a name so that the tool's report can refer to it.

**How does my Android app require GPS when my iOS one doesn't?** Declarations are already per platform, so a package that needs location only on Android lists those permissions under Android and lists nothing under iOS. Feature selection is per platform too, for packages like plyer where the app chooses which capabilities it uses.

**Should permissions and dependencies follow the same rules?** Yes, and now they do. A dependency can belong to a feature in the same way as a permission:

```toml
# A hypothetical package with an optional scanner
[tool.native-integration.android.feature.scanner]
permissions = ["android.permission.CAMERA"]

[tool.native-integration.android.feature.scanner.gradle]
dependencies = ["com.example:scanner:[2.0,3.0[!!2.1.0"]
```

This also covers "extras that select native dependencies".

The same rule covers two packages that declare the same thing. The tool combines the declarations and leaves any resolving to the platform. Gradle and SwiftPM resolve dependency versions. Permissions have no versions, so there is nothing to resolve.

**Are iOS permissions different?** No. On both platforms the package lists the platform's own permission names, and one rule applies: the app author declares each permission in the app's configuration, and the build tool checks that against what the packages need. If one is missing, the build tool reports it and names the package that needs it.

The platforms differ only in what that declaration contains. On Android, naming the permission is enough. On iOS it also needs a purpose string, which the app author supplies through settings such as Briefcase's [`permission.fine_location`](https://briefcase.beeware.org/en/stable/reference/platforms/iOS/xcode.html) or kivyforge's `info_plist`. If this app selected `gps` on iOS without providing that string, the build tool would report:

```
plyer (gps) requires NSLocationWhenInUseUsageDescription, and the app doesn't set it.
```

The names stay native because a package's code calls specific platform APIs, so its author knows exactly which permissions it needs. A cross-platform name would need a mapping in the spec, and the platforms don't line up one to one. iOS, for example, has one key for adding to the photo library and another for reading it. A build tool can still give app authors cross-platform settings, as Briefcase does, and check the native names those settings produce.

**What if one package needs coarse location and another needs fine?** The app declares both. They are different permissions, and [Android's guidance](https://developer.android.com/develop/sensors-and-location/location/permissions) is to always declare coarse, and to add fine if the app benefits from precise location. The spec never treats one permission as implying another. On iOS, two packages that name the same key share one purpose string. Only the app writes that string, so the packages can't conflict.

v1 carries permission names only. A package that needs an attribute such as `android:maxSdkVersion` would use an application requirement for now. Two packages could ask for different attributes on the same permission, so I'd leave attributes out until a real case needs them.

### Tool-defined keys

Each platform and feature table reserves a `tool.<name>` table for one tool's use. Other tools ignore it:

```toml
[tool.native-integration.android.tool.briefcase]
manifest_application_extra_content = '<meta-data android:name="com.example.sdk.FLAG" android:value="true" />'
```

### Open points

1. Does the permission rule match what you meant? The app author declares each permission in the app's configuration, and the build tool reports any that packages need and the app hasn't declared.
2. If a library uses plyer's GPS, the library declares the location permissions itself. The app then never has to select features of a package it didn't choose. 


### Where this grows

v1 is intentionally small. Later versions could add:

- A way for a tool to check an application requirement, such as a named manifest or `Info.plist` key.
- A portable way for the app to supply a value, and your importlib-metadata idea so the package can read it.
- Attributes on permissions.
- New standard kinds, starting from what tools try under `tool.<name>`.
