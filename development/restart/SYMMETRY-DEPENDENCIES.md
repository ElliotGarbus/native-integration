# Symmetry sketch: same depth, one `dependencies` slot

Applies two changes to the examples in [`WORKED-EXAMPLES.md`](WORKED-EXAMPLES.md):

1. **Same key depth** — `permissions`, `dependencies`, `application_requirement`, and `tool.<name>` are direct children of every platform and feature table. No `.gradle` nest.
2. **One slot name** — both platforms use `dependencies` as a list. Android entries are Maven coordinate strings; iOS entries are tables with `url`, `requirement`, and `products`. No local package name key.

App feature selection is unchanged. Nothing here is a commitment to ship this shape.

## Examples

### plyer

Unchanged. It only declares permissions, which were already at the right depth.

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

### pyadmob

**Current** ([`WORKED-EXAMPLES.md`](WORKED-EXAMPLES.md)):

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

**With (1) and (2):**

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

The old `GoogleMobileAds = { … }` key was only a local table name (from the kivyforge-shaped `swift_packages` table). SwiftPM identifies the package by `url` and links `products`; it does not need that extra name. `GoogleMobileAds` remains where it belongs — in `products`.

### Optional scanner

**Current:**

```toml
# A hypothetical package with an optional scanner
[tool.native-integration.android.feature.scanner]
permissions = ["android.permission.CAMERA"]

[tool.native-integration.android.feature.scanner.gradle]
dependencies = ["com.example:scanner:[2.0,3.0[!!2.1.0"]
```

**With (1) and (2):**

```toml
# A hypothetical package with an optional scanner
[tool.native-integration.android.feature.scanner]
permissions = ["android.permission.CAMERA"]
dependencies = ["com.example:scanner:[2.0,3.0[!!2.1.0"]
```

### Tool-defined keys

Unchanged depth. Still a sibling of the standard keys under the platform (or feature) table:

```toml
[tool.native-integration.android.tool.briefcase]
manifest_application_extra_content = '<meta-data android:name="com.example.sdk.FLAG" android:value="true" />'
```

### App selection

Unchanged:

```toml
# The app's pyproject.toml
[project]
dependencies = ["plyer", "pyadmob"]

[tool.native-integration.android.features]
plyer = ["gps"]

[tool.native-integration.ios.features]
plyer = []
```

## Comparison

| Axis | Current | After (1) and (2) |
| --- | --- | --- |
| Where permissions live | Directly under platform / feature | Same |
| Where Android deps live | Under `android.gradle.dependencies` (and `feature.*.gradle`) | Under `android.dependencies` / `feature.*.dependencies` |
| Where iOS deps live | Under `ios.swift_packages` (keyed by local name) | Under `ios.dependencies` as a list of `{ url, requirement, products }` |
| Slot name across platforms | `gradle` + `swift_packages` | `dependencies` on both |
| Value shape | Android list of strings; iOS named table | Both lists; entry shape still platform-native |
| iOS local name | Required as the table key | Dropped; merge/identity uses `url` |
| Feature-bound permission + dep | Two tables (`feature.scanner` and `feature.scanner.gradle`) | One table; both keys as siblings |
| `application_requirement` | Sibling of platform / of `.gradle` | Sibling of `dependencies` and `permissions` |
| App feature selection | Per-platform lists | Same |

## Analysis

**What improves.** The scanner example is the clearest win: one feature table holds the permission and the dependency as peers, which is exactly the “same rules” claim in the reply. pyadmob’s Android side loses a nesting level that only existed to namespace Gradle, so a reader scanning `android` sees the same kind of slots as under `android.feature.gps`. Renaming `swift_packages` to `dependencies` makes the cross-platform story one sentence: every scope may declare `permissions` and `dependencies`; the platform decides how each value is written.

**What does not become symmetric.** Both platforms now write `dependencies = [ … ]` on the platform table. Entry *contents* still differ: Android is a coordinate string; iOS is a small table because SwiftPM needs `url`, a version `requirement`, and `products` — Maven folds identity and version into one string. That is real platform variation, not an extra naming axis. `application_requirement` also remains a different shape (name → prose), which is intentional for the uncheckable escape hatch.

**Cost of dropping `.gradle`.** Today `.gradle` is a place for more than dependencies (repositories, and later perhaps BOM / plugin concerns). Flattening `dependencies` to the platform table means those other Gradle-only keys need a home: either more top-level Android keys (`repositories = ...`), a thinner residual `gradle` table for non-dependency Gradle config, or tool-defined keys until standardized. The worked examples do not show repositories, so this sketch does not choose; it is the main structural question this change opens.

**Cost of the shared name.** `dependencies` under `[project]` already means Python requirements. Here it is always under `[tool.native-integration.<platform>…]`, so the path disambiguates, but authors and docs must say “native dependencies” when speaking loosely. `swift_packages` was more self-describing for iOS readers copying from vendor docs; `dependencies` is better for the model, slightly worse as a label for Swift-only authors.

**Reader / tool impact.** Tools already branch on platform; they would key off `dependencies` and interpret by platform instead of looking for `gradle.dependencies` vs `swift_packages`. Validation and `explain` paths get one structural rule (“scope may have dependencies”) and two value schemas. Conformance cases that name the old keys would move with the rename.

**Verdict.** For Russell’s symmetry point, (1) and (2) are worth it: they make the cardinality story visible in the TOML, especially for feature-bound deps. The remaining asymmetries (value shapes, prose requirements, any Gradle-only leftovers) are platform or tier differences he already allowed, not parallel fields that recreate the old mismatch. The open design choice is where non-dependency Gradle configuration lives once `.gradle` is no longer the dependency nest.
