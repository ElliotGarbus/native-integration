@freakboy3742 You asked about VERS, the version range format from the Package URL project. PEP 725 doesn't use it, and that's where the limit comes from:

- [Versioning](https://peps.python.org/pep-0725/#versioning): considers `vers` URIs and chooses a subset of PEP 440 instead, because `vers` isn't ergonomic.
- [DepURL](https://peps.python.org/pep-0725/#depurl): `version` MUST use that subset.
- [Rejected ideas](https://peps.python.org/pep-0725/#allowing-use-of-ecosystem-specific-version-comparison-semantics): rejects ecosystem-specific version comparison, and suggests a comment or qualifier for those cases.

Guava shows the effect. It [specifies its flavor in the Maven version](https://github.com/google/guava/blob/master/README.md), so an Android app needs `33.8.0-android`. I tested that with [`pyproject-external`](https://github.com/jaimergp/pyproject-external) 0.1.17, the PEP's reference implementation:

```
dep:maven/com.google.guava/guava@33.8.0-android     UnsupportedSpecError: not PEP440 compatible
dep:maven/com.google.guava/guava@>=33.8.0-android   UnsupportedSpecError: not PEP440 compatible
dep:maven/com.google.guava/guava@>=33.8.0           accepted
```

The last one is accepted but no longer says Android, and [Maven Central has no plain `33.8.0`](https://repo1.maven.org/maven2/com/google/guava/guava/maven-metadata.xml).

PURL isn't the limit: `packageurl-python` accepts `pkg:maven/com.google.guava/guava@33.8.0-android`.

So writing this dependency as a DepURL needs a change to PEP 725.
