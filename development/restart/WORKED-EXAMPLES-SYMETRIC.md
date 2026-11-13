## Revised model and worked example

@freakboy3742 Thanks. Your cardinality point led me to restructure the proposal. As before, none of this is implemented.

Changes:

- `application_action` is now `application_requirement` — not `requirement`, which reads as a Python package requirement. The prefix makes it clear the application must satisfy the requirement.
- Acknowledgements and `revision` removed.
- The `id`, `kind` and `feature` fields are gone. A declaration's position in the table carries that information instead.
- The tables are flatter so permissions and dependencies sit at the same depth on every platform and feature. Both platforms use a `dependencies` list (Maven strings on Android; `{ url, requirement, products }` on iOS). Gradle-only config such as repositories stays in a thin `gradle` table beside those slots, not wrapped around the dependency list.

### The model

A package declares requirements, which are things that must be true of the packaged app. There are three tiers, as we discussed earlier in this thread:

- **Application requirements:** the base form, which is a name and a description. Any tool can show one to the app author. The name is only a label for the report; it does not trigger a check or a write.
- **Standard kinds:** native dependencies and permissions.
- **Tool-defined keys:** a reserved `tool.<name>` table, where a tool can try something before it is standardized.

Each requirement belongs to a platform, and may also belong to a feature:

- Directly under a platform, it applies whenever the package is in the app.
- Under a **feature**, it applies only when the app selects that feature for that platform.

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
[tool.native-integration.android]
dependencies = ["com.google.android.gms:play-services-ads:[24.0,25.0[!!24.0.0"]

[tool.native-integration.android.application_requirement]
admob-app-id = "Set the manifest meta-data com.google.android.gms.ads.APPLICATION_ID to your AdMob app ID."

[tool.native-integration.ios]
dependencies = [
    { url = "https://github.com/googleads/swift-package-manager-google-mobile-ads", requirement = { from = "12.0.0" }, products = ["GoogleMobileAds"] },
]

[tool.native-integration.ios.application_requirement]
admob-app-id = "Set GADApplicationIdentifier in Info.plist to your AdMob app ID."
```

**The app** includes both packages as ordinary Python dependencies, then selects which of plyer's features it uses on each platform:

```toml
# The app's pyproject.toml
[project]
dependencies = ["plyer~=2.1.0", "pyadmob~=1.0"]

[tool.native-integration.android.features]
plyer = ["gps"]

[tool.native-integration.ios.features]
plyer = []
```

pyadmob has no features to select, so installing it is enough to activate its requirements. `[]` means the app uses none of plyer's features on iOS. A missing entry means the app hasn't chosen yet, so the tool lists plyer's features until it does.

On an Android build, the build tool:

- passes pyadmob's dependency to Gradle unchanged
- applies the two permissions for plyer's `gps` feature
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

The author meets the requirement with settings the build tool already has, such as Briefcase's [`android_manifest_application_extra_content`] for the manifest and [`info`] for `Info.plist`. Each tool chooses when and how to show the list.

### Your questions

**What is the difference between the id and the feature?** The `id` is gone. A feature groups requirements the app may or may not need — many capabilities in a package like plyer, or one optional capability such as a scanner — much as a Python extra groups optional dependencies. A permission or dependency is identified by its native name. An application requirement keeps a name so that the tool's report can refer to it. In short, the package defines the features; the app selects them.

**How does my Android app require GPS when my iOS one doesn't?** Declarations are already per platform, so a package that needs location only on Android lists those permissions under Android and lists nothing under iOS. Feature selection is per platform too, for packages like plyer where the app chooses which capabilities it uses.

**Should permissions and dependencies follow the same rules?** Yes, and now they do. Both are lists on the same platform or feature table:

```toml
# A hypothetical package with an optional scanner
[tool.native-integration.android.feature.scanner]
permissions = ["android.permission.CAMERA"]
dependencies = ["com.example:scanner:[2.0,3.0[!!2.1.0"]
```

The app selects that feature the same way it selects plyer's:

```toml
[tool.native-integration.android.features]
pyscanner = ["scanner"]
```

The same rule covers two packages that declare the same thing. The tool combines the declarations and leaves any resolving to the platform. Gradle and SwiftPM resolve dependency versions. Permissions have no versions, so there is nothing to resolve.

**Are iOS permissions different?** No. On both platforms the package lists the platform's own permission names, and selecting a feature (or installing a package with platform-root permissions) is what brings those requirements in. On Android the build tool can apply the names itself. On iOS each permission also needs a purpose string that only the app can write, so the build tool reports any that are missing — for example:

```
plyer (gps) requires NSLocationWhenInUseUsageDescription, set in the app's pyproject.toml file.
[tool.kivy.ios.info_plist]
NSLocationWhenInUseUsageDescription = "<Your description here>"
```

**What if one package needs coarse location and another needs fine?** Both are applied. They are different permissions. On iOS, two packages that name the same key share one purpose string. Only the app writes that string, so the packages can't conflict.

v1 carries permission names only. A package that needs an attribute such as `android:maxSdkVersion` would use an application requirement for now. Two packages could ask for different attributes on the same permission, so I'd leave attributes out until a real case needs them.

### The `gradle` table

`dependencies` stays on the platform or feature table so it remains a peer of `permissions`. Gradle-only resolver config — repositories today — lives under `gradle` beside those slots, not inside the dependency list. A BOM is a platform dependency, so it would join `dependencies` later (with a way to mark the import), not `gradle`.

```toml
# An SDK that is not on Maven Central
[tool.native-integration.android]
dependencies = ["com.mapbox.mapboxsdk:mapbox-android-sdk:9.7.0"]

[[tool.native-integration.android.gradle.repositories]]
url = "https://api.mapbox.com/downloads/v2/releases/maven"
groups = ["com.mapbox"]
```

The same table can hang off a feature when only that feature needs the repository:

```toml
[tool.native-integration.android.feature.scanner]
permissions = ["android.permission.CAMERA"]
dependencies = ["com.example:scanner:[2.0,3.0[!!2.1.0"]

[[tool.native-integration.android.feature.scanner.gradle.repositories]]
url = "https://maven.example.com/scanner"
groups = ["com.example"]
```

iOS has no counterpart yet. If SwiftPM later needs resolver-only settings that are not part of a dependency entry, they would get a thin table of their own rather than stretching `dependencies`.

### Tool-defined keys

Each platform and feature table reserves a `tool.<name>` table for one tool's use. Other tools ignore it:

```toml
[tool.native-integration.android.tool.briefcase]
manifest_application_extra_content = '<meta-data android:name="com.example.sdk.FLAG" android:value="true" />'
```

### Where this grows

v1 is intentionally small. Later versions could add:

- A portable way for the app to supply a value. Today an application requirement only describes what to do (for example set the AdMob app ID); the author meets it with whatever setting their build tool already has. A later version could let the app put a named value in one place the convention defines. The build tool would write it into the manifest or `Info.plist`, and publish it under the app's `.dist-info` so the package can read it at runtime with `importlib.metadata`, without a tool-specific API — as you suggested.
- New standard kinds, starting from what tools try under `tool.<name>`.
