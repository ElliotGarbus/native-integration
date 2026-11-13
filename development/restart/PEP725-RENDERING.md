@freakboy3742 @mhsmith Here are the renderings I promised, using PEP 725 DepURLs.

**Gradle coordinates fit, except BOMs (below).** All 17 in the examples convert:

```
com.google.android.gms:play-services-ads:24.0.0
dep:maven/com.google.android.gms/play-services-ads@>=24.0.0?type=aar
```

I use `>=` because [Gradle may select a higher version](https://docs.gradle.org/current/userguide/graph_resolution.html), and `@24.0.0` would mean exactly that version. Android SDKs are usually AARs, and PURL's default type is `jar`, so the DepURL needs `?type=aar`. The native coordinate doesn't.

**Swift dependencies do not.** The URL and version convert, but SwiftPM links products, and PURL's `swift` type defines no way to name them. All 15 Swift packages in the examples name products, and in 13 none is named after the repository. The subpath below is only my convention:

```
url = "https://github.com/firebase/firebase-ios-sdk", requirement = { from = "11.0.0" }, products = ["FirebaseMessaging"]
dep:swift/github.com/firebase/firebase-ios-sdk@>=11.0.0,<12#FirebaseMessaging
```

## What would need to change

Through DepURL changes or a native expression in PEP 725:

- **Swift products:** a defined way to name them, one or several per package. [purl-spec#400](https://github.com/package-url/purl-spec/issues/400) is open on a related naming problem, with disagreement over subpaths.
- **Swift embedding:** a way to say a product must be embedded in the app.
- **Maven versions:** a way to write versions that aren't PEP 440. [116 of Guava's 162 versions](https://repo1.maven.org/maven2/com/google/guava/guava/maven-metadata.xml) fail, including `33.8.0-android`.
- **Maven BOMs:** a way to import a BOM as a [Gradle platform](https://docs.gradle.org/current/userguide/platforms.html), so dependencies can omit their versions. A DepURL can name the BOM's file with `?type=pom`, but can't say to import it.
- **Maven repositories:** a way to limit a repository to named groups. `repository_url` only says where one package is.
- **Registry:** tools may warn or error on names missing from the PEP 804 registry, which doesn't mention Maven or Swift.

I'd prefer a native expression. Authors can copy coordinates from the vendor's documentation and tools can pass them on unchanged, whereas converting by hand only adds chances for error.

PEP 725 lets later PEPs add fields to `[external]`. Malcolm, do you think its authors would accept a native table such as `[external.native]`? Until this is a PEP, it would stay in `[tool.native-integration]`.
