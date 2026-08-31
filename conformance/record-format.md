# The conformance record

**The normalized form a consumer emits so that two consumers can be compared.**

[§9](../SPEC.md#9-recording-and-review) mandates what an integration record must
contain and deliberately not how it is written: "A lockfile entry, a checksum
file beside the generated project, or any other durable artifact satisfies the
record." That freedom is right for a build tool and useless for a test suite —
two conforming consumers can produce records that agree on every fact and share
no bytes.

This file defines one serialization, for that comparison and nothing else.

| | |
| --- | --- |
| **What it is** | a projection of the integration record onto a fixed, diffable form |
| **What it is not** | a required record format. A consumer's own record stays whatever [§9.6](../SPEC.md#96-what-a-record-must-contain) leaves it |
| **Who emits it** | a consumer being tested, on request — a `--conformance-record` flag or equivalent |
| **Status** | non-normative to [SPEC.md](../SPEC.md); binding only on a conformance claim made through this corpus |

**Where this file and SPEC.md disagree, SPEC.md governs and this file is the
defect** ([conformance/README.md](README.md)).

---

## 1. The shape

A conformance record is a UTF-8 text file. Every line is one **fact**. The file
is the **sorted set** of its facts:

- lines are sorted **bytewise**, ascending, over the whole file;
- a fact appears **exactly once** — a duplicate line is invalid, not a repeat;
- lines end with `\n`, including the last; there is no BOM and no blank line.

Sorting the whole file is what makes two consumers comparable without agreeing
on anything else. It also means `diff` is the entire comparison algorithm, which
is what [run.py](run.py) does.

> Bytewise sort groups the file usefully on its own, because every fact begins
> with its verb and then its subject: all `build` facts, then `decision`, then
> each distribution's block together in normalized-name order. That is a
> consequence, not a rule — nothing may depend on the grouping.

## 2. Lexical rules

```abnf
fact       = verb SP operand *( SP operand )
operand    = positional / keyed
positional = scalar
keyed      = key "=" value
key        = dockey / openkey
dockey     = 1*( %x61-7A / DIGIT / "-" )
openkey    = 1*( %x61-7A / DIGIT / "-" / "_" )
value      = scalar / list
list       = scalar 1*( "," scalar )
scalar     = bare / quoted
bare       = 1*( ALPHA / DIGIT / "." / "_" / "-" / ":" / "/" / "@" / "+" / "~" / "*" )
quoted     = DQUOTE *qchar DQUOTE
qchar      = %x20-21 / %x23-5B / %x5D-7E / %x80-10FFFF / escape
escape     = "\" ( DQUOTE / "\" / "n" / "t" / "r" / "u" 4LOWHEX )
LOWHEX     = DIGIT / %x61-66
```

- Every **positional** operand precedes every **keyed** one, and a positional
  operand is always a scalar.
- A keyed operand is **scalar unless its fact says otherwise**.
  [`record-facts.toml`](record-facts.toml) names the operands that may carry a
  list — `via`, `uses`, `groups`, `modules`, `products`, `reasons`, `withdrew`,
  `artifacts`, `distributions` — and a list anywhere else is invalid.
- `dockey` is every key this format names itself; `openkey` is a `view-link`
  attribute, which is the sidecar's own spelling and so may contain `_`.
- A keyed operand appears **at most once** in a fact. Repeating one is invalid,
  not a second value.
- A value that can be written `bare` **is** written bare; one that cannot **is**
  quoted. One spelling per value, or the sort is not deterministic.
- A **one-member list is a scalar**. `list` therefore takes two or more members,
  which is what keeps it distinguishable. A reader expecting a list treats a
  scalar as a list of one.
- There is **no empty list**. Where a list would be empty the keyed operand is
  omitted, and where its absence would lose a claim the claim gets a fact of its
  own — `plist-array-key` is the case that needed one.
- List members are sorted bytewise **over their serialized form**, and
  de-duplicated. Keyed operands within one fact are sorted bytewise by key.
  Serialized rather than decoded, because the file's own ordering is over
  serialized lines and the two disagree wherever an escape is involved: `"a b"`
  sorts before `"a\nb"` as written and after it once decoded.

**Escaping is JSON's**, so that any string a TOML sidecar can hold has exactly
one serialization here. `\n`, `\t`, `\r`, `\"` and `\\` are literal; every other
character below `%x20`, and `%x7F`, is written `\uXXXX` with lowercase hex
digits. Nothing is dropped and nothing is folded — a `reason` §6.4 requires to be
kept and attributed is kept exactly.

### Normalization, before anything is written

| | |
| --- | --- |
| distribution name | [§1](../SPEC.md#1-terminology)'s normalized form — lowercased, runs of `-`, `_`, `.` collapsed to one `-` |
| path | forward slashes, relative to the sidecar directory, no `./` prefix ([§9.3](../SPEC.md#93-hashed-inputs)) |
| digest | 64 lowercase hexadecimal characters, unprefixed, never abbreviated ([§9.3](../SPEC.md#93-hashed-inputs)) |
| date | [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339) full-date in UTC — `2026-08-24` ([§9.6](../SPEC.md#96-what-a-record-must-contain)) |
| boolean | `true` / `false` |
| version | as the ecosystem spells it; never re-rendered |

A record covers **one platform's build** ([§9.2](../SPEC.md#92-the-report)). The
iOS half of an application lives in its own file.

## 3. Facts

**[`record-facts.toml`](record-facts.toml) is the authoritative list**, and
[run.py](run.py) enforces exactly what is in it. Each entry gives a fact's
template, its required and optional keyed operands, and any closed vocabulary
they take. A fact matching no template, or carrying a key its template does not
allow, makes the record invalid — the line is rejected, never ignored, on
[§4.4](../SPEC.md#44-unknown-declarations-fail-closed)'s reasoning one level up.

The examples below are illustrations of forms defined there. They are not the
definition: a format whose only specification is its examples is one two
implementers can satisfy differently, which is the failure this file exists to
prevent.

Three verbs, and the set is closed.

### 3.1 `build`

```
build contract 1.0
build platform android
```

`contract` is the contract the **consumer** implements
([§4.3](../SPEC.md#43-contract-version)); `platform` is what the resolution was
computed for.

### 3.2 `dist`

Subject is the normalized distribution name. Every fact a distribution
contributes is one line.

**Identity and provenance** ([§9.6](../SPEC.md#96-what-a-record-must-contain),
[§3.2](../SPEC.md#32-resolution))

```
dist map-sdk version 4.1.0
dist map-sdk contract 1
dist map-sdk origin direct
dist analytics-shim origin transitive via=some-ui-lib
```

`origin` is `direct` or `transitive`; `via` names the producer's immediate
dependents, sorted. Where several paths exist a consumer reports at least the
immediate dependents, and what it reports is deterministic across runs.

**Inputs** ([§9.3](../SPEC.md#93-hashed-inputs))

```
dist map-sdk input java/com/example/maps/MapBridge.java sha256=9f2c17b40ae83d6512cc0947fa2b81d35e07c6a94b1f28d0e35ba7c61804df92
dist map-sdk input native.toml sha256=71ff3ac8250b91e7d4a6c03fb8215de9074c1a6b39f52840cbe7d1904a63f28c
```

**Ownership** ([§6.1](../SPEC.md#61-ownership))

```
dist map-sdk owns java-namespace org.example.maps
```

**Requirements** ([§5](../SPEC.md#5-requirements-on-the-application),
[§5.4](../SPEC.md#54-how-a-requirement-is-satisfied))

```
dist map-sdk floor min_sdk configured=26 declared=24 state=met
dist map-sdk value maps_api_key key=com.example.maps.API_KEY kind=manifest_meta_data state=supplied
dist map-sdk value maps_optional conditional=true date=2026-08-24 kind=inline state=dismissed version=4.1.0
dist map-sdk action map_deep_links date=2026-08-24 state=acknowledged version=4.1.0
dist map-sdk action map_offline_cache conditional=true state=unresolved
dist map-sdk action airship_nse conditional=true slot=com.apple.usernotifications.service state=unresolved
dist map-sdk action app_group_entitlement state=unresolved uses=app_group_id
```

`state` is one of `met` / `unmet` (floors), or `supplied` / `unresolved` /
`dismissed` (values), or `acknowledged` / `unresolved` / `dismissed` (actions).
`conditional=true` appears only where the sidecar declares it. `date` and
`version` appear on an acknowledgement or a dismissal and nowhere else, because
[§9.6](../SPEC.md#96-what-a-record-must-contain) requires them there.

**Contributions** ([§6](../SPEC.md#6-android-declarations),
[§7](../SPEC.md#7-ios-declarations)). One verb-phrase per contribution kind, so
that a set difference over these lines *is* the delta a reviewer reads.

```
dist map-sdk contributes source java/com/example/maps/MapBridge.java
dist map-sdk contributes gradle-dependency com.example.maps:android configuration=implementation requested=exact:4.1.0 resolved=4.1.0
dist map-sdk contributes gradle-repository https://maven.example.com/releases authenticated=true groups=com.example.maps reason="Hosts the maps SDK, which is not on Maven Central"
dist map-sdk contributes permission android.permission.INTERNET reason="Map tile delivery"
dist map-sdk contributes permission android.permission.ACCESS_FINE_LOCATION max-sdk=30 never-for-location=false
dist map-sdk contributes feature android.hardware.location.gps required=false
dist map-sdk contributes component org.example.maps.RedirectActivity exported-required=true kind=activity
dist map-sdk contributes component com.vendor.sdk.Receiver from-dependency=com.vendor:sdk kind=receiver
dist map-sdk contributes view-link org.example.maps.RedirectActivity host=oauth2redirect path_prefix=/callback scheme=myapp-oauth
dist map-sdk contributes intent-filter org.example.maps.Messaging action=com.google.firebase.MESSAGING_EVENT
dist map-sdk contributes keep org.example.maps.**
dist map-sdk contributes keep okhttp3.** from-dependency=com.squareup.okhttp3:okhttp
dist map-sdk contributes meta-data com.example.maps.MODE type=string value=fast
dist map-sdk contributes query com.google.android.apps.healthdata kind=package reason="Availability check"
dist pycharting contributes swift-package Charting products=Charting requirement=from:2.4.0 url=https://github.com/example/charting
dist pycharting contributes swift-source swift/Shim.swift
dist pycharting contributes symbol-prefix PyChart
dist pycharting contributes accessed-api NSPrivacyAccessedAPICategoryUserDefaults reasons=CA92.1
dist pycharting contributes plist-value CADisableMinimumFrameDurationOnPhone type=boolean value=true
dist pycharting contributes plist-append LSApplicationQueriesSchemes value=examplescheme
dist pycharting contributes plist-array-key LSApplicationQueriesSchemes
dist pycharting contributes skadnetwork su67r6k2v3.skadnetwork
dist pycharting contributes python-module web_views init=PyInit_WebViews swift-package=PyWebViews
dist pycharting contributes objc-categories
```

**A component records what the producer requested, never what the application
answered.** [§9.1](../SPEC.md#91-the-lifecycle) splits the record in two: the
accepted resolution is producer-originated and **gated**, while an export
approval is one of the application's own answers and is explicitly *not*. So the
contribution carries `exported-required`, and whether it was approved lives in a
`decision approve-export` fact and nowhere else. Recording the outcome here
would make an application answer read as a changed resolution and trip a gate
§9.1 says must not apply to it.

A `view-link`'s `<data>` attributes are written in the **sidecar's spelling,
verbatim** — `path_prefix`, not `pathPrefix` and not `path-prefix`. A record must
not depend on [§6.6](../SPEC.md#66-manifest-components)'s conversion to an
`android:` attribute name having been performed, and re-spelling them here would
be performing half of it. They are the one place `key` admits `_`; every key
this format names itself is kebab-case.

`plist-append` emits one fact per array member, which is what makes a
de-duplicated union comparable — and `plist-array-key` states the key's mode
separately, because an empty `append` declaration still claims that key as
array-valued for [§7.4](../SPEC.md#74-infoplist)'s one-mode rule and would
otherwise vanish from the record entirely.

**A request is spelled one way.** [§6.3](../SPEC.md#63-gradle-dependencies)
gives a dependency two forms and [§7.2](../SPEC.md#72-swift-packages) gives a
package three. A record that wrote them freely would let two consumers describe
one declaration differently, so each has a single encoding:

| Declared | Recorded |
| --- | --- |
| `coordinate = "g:a:4.1.0"` | `requested=exact:4.1.0` |
| `version = { at_least = "5.6.1", below = "6.0.0" }` | `requested=range:5.6.1:6.0.0` |
| `requirement = { exact = "1.2.3" }` | `requirement=exact:1.2.3` |
| `requirement = { from = "1.2.0" }` | `requirement=from:1.2.0` |
| `requirement = { revision = "8a1f0c9e" }` | `requirement=revision:8a1f0c9e` |

Both bounds appear in the `range` form because §6.3 requires both within
`version`. `branch` has no spelling here, because §7.2 excludes it there.

**Numbers are rendered one way too.** A `value` whose `type` is `integer` is
canonical decimal — `0`, or an optional sign and no leading zero — and a `float`
carries a fractional part and no exponent. Without that, `1`, `+1`, `01` and
`1_000` are four spellings of one TOML integer, and
[§6.8](../SPEC.md#68-manifest-meta-data)'s equality "by type as well as content"
has nothing to compare.

**The resolved native graph** ([§6.3](../SPEC.md#63-gradle-dependencies),
[§7.2](../SPEC.md#72-swift-packages))

```
dist map-sdk artifact com.example.maps:android:4.1.0 sha256=0d3e4f9a17c2b85e6dd0341fbb9a72c5e08d41a6f3c7b2905ea18d43f6c07b21
dist map-sdk artifact com.squareup.okhttp3:okhttp:4.12.0 sha256=5b81c0f2d7a3946e18bb52c07f9d3a6418e2c5b09fa471d38c62e0ab7451f9d0 transitive=true
dist pycharting package https://github.com/example/charting requested=from:2.4.0 revision=8a1f0c9e4b2d7f36a05c1e8b9d4427fa3c60e15b version=2.4.0
dist pycharting package https://github.com/example/charting-core revision=b73c2ad91e604f8ab5d0c7e21f9836540ac1de77 transitive=true version=1.2.0
dist pycharting binary-target ChartingRenderer.xcframework checksum=e11d5b0c93a726f4180dc35ba9f27e64108c3d95b2af7016e5c48d3b9207fa14
```

**What resolved artifacts brought with them**
([§9.4](../SPEC.md#94-what-resolved-artifacts-bring-with-them))

```
dist map-sdk artifact-declares com.example.maps:android:4.1.0 permission com.example.permission.MAPS_ID
dist map-sdk artifact-declares com.example.maps:android:4.1.0 feature android.hardware.location.gps required=true
dist map-sdk artifact-declares com.example.maps:android:4.1.0 component com.example.maps.PublicActivity exported=true
```

These are attributed to the **artifact**, not to the sidecar, which is the whole
point of §9.4. The `dist` subject says which distribution pulled it in.

### 3.3 `decision`

The answers [§2.2](../SPEC.md#22-how-the-application-answers) joins by something
other than `(distribution, id)`, plus the credential facts
[§9.5](../SPEC.md#95-secrets-are-never-recorded) allows. These are
integration-wide, so they carry no `dist` subject — each names the distributions
it affected instead.

```
decision approve-export org.example.maps.RedirectActivity date=2026-08-24 distribution=map-sdk state=approved
decision approve-export org.example.maps.PendingActivity distribution=map-sdk state=pending
decision artifact-feature android.hardware.location.gps artifact=com.example.maps:android:4.1.0 date=2026-08-24 distribution=map-sdk keep=optional
decision collision lib/arm64-v8a/libc++_shared.so artifacts=com.example.maps:android:4.1.0,com.vendor:sdk:2.0.0 chosen=com.example.maps:android:4.1.0 date=2026-08-24 decided=application distributions=analytics-shim,map-sdk
decision credential-required https://git.example.com/vendor/vendorkit kind=package
decision credential-required https://maven.example.com/releases kind=repository
decision suppress-permission android.permission.ACCESS_FINE_LOCATION date=2026-08-24 withdrew=analytics-shim,map-sdk
```

A component still awaiting approval is `state=pending` with no `date`, which is
how [§9.6](../SPEC.md#96-what-a-record-must-contain)'s "the approval's absence
where a component is still pending" stays recoverable.

**No credential value ever appears.** A `credential-required` fact states that a
repository or package needs one; that is a fact about the integration, and the
credential is not ([§9.5](../SPEC.md#95-secrets-are-never-recorded)).

### 3.4 `effective`

What the application will actually register, where
[§6.5](../SPEC.md#65-permissions-and-features) computes it from more than one
declaration. Integration-wide like a `decision`, so no `dist` subject; the
contributors are named instead.

```
effective permission android.permission.ACCESS_FINE_LOCATION distributions=analytics-shim,map-sdk never-for-location=true
effective permission android.permission.BLUETOOTH_SCAN distributions=analytics-shim,map-sdk max-sdk=33
```

This does not duplicate the `contributes permission` facts above it. Those
record who asked for what; this records the result, which §6.5 **requires** to
appear "in the record and report with the distributions that produced it".
Both are needed because the merge is lossy in the direction that matters: an
entry with no `max_sdk_version` defeats one that has it, a lower ceiling gives
way to a higher, and `never_for_location` holds only where every declaration
asserts it. In each case the narrower declaration is the one that looks
careful, and a record holding only the requests leaves a reviewer to derive
what was actually registered.

`max-sdk` is absent where any declaration stated no ceiling, because unbounded
is the widest need. `never-for-location` appears only where it holds, since its
absence and `false` say the same thing.

A **suppressed** permission has no `effective` fact at all, which is how §6.5's
"absent from the effective merged manifest" stays visible in the record.

The two shared key spaces settle the same way.
[§6.8](../SPEC.md#68-manifest-meta-data) and
[§7.4](../SPEC.md#74-infoplist) both put the application's own entry above every
contribution, and both require it to be kept and reported:

```
effective meta-data com.example.MODE distributions=analytics-shim,map-sdk source=application type=string value=balanced
effective plist-value ExampleAdsMode distributions=map-sdk type=string value=fast
```

`source=application` says the application set the key itself and won. The
contributions it overrode stay in the record beside it — an application removing
its own entry later needs to see the disagreement it was standing on top of.

A key whose only claimant is a [§5.2](../SPEC.md#52-values) value the
application *supplied* has no `effective` fact, and the supplied string never
appears. Its state is already recorded against the requirement that asked for
it, and [§9.5](../SPEC.md#95-secrets-are-never-recorded) is the reason the
content is not: an `api_key` delivered through `manifest_meta_data` is exactly
what §5.2 is used for. A producer's own declaration is public by construction
and is recorded in full.

## 4. What is deliberately not in it

| | Why |
| --- | --- |
| An action's `summary`, `instructions` and `acceptance` | Inline in `native.toml`, so the `input` digest already pins them ([§9.3](../SPEC.md#93-hashed-inputs)). Restating prose would make the comparison sensitive to line wrapping |
| The report's rendering | [§9.2](../SPEC.md#92-the-report) mandates distinctions, not a format. A corpus that fixed the rendering would be testing a spelling the specification refuses to fix |
| Anything the consumer generated | The manifest, the Gradle files, the Xcode project. Those are the consumer's, and two conforming consumers differ |
| Timestamps other than a decision's date | A record diffed between runs must not change because time passed |

A `reason` **is** included, on two different footings.
[§6.4](../SPEC.md#64-maven-repositories) and
[§6.9](../SPEC.md#69-package-visibility) **require** one to be kept and
attributed — a repository's, and a `queries` entry's — and
[§7.2](../SPEC.md#72-swift-packages) imports §6.4's rule for a package.
[§6.5](../SPEC.md#65-permissions-and-features)'s permission `reason` is
**RECOMMENDED**, and carrying it into the record is advisory
[S7](../SPEC.md#85-advisory-obligations) rather than a requirement. This format
carries it so that a consumer claiming S7 can be checked on it; a consumer that
does not claim S7 omits the operand, which is why it is optional on the fact
rather than required.

## 5. Worked example

This is [`core/R01_dependency_closure/expected/android.record`](core/R01_dependency_closure/expected/android.record)
verbatim — the corpus's shortest complete case, and its digests are the real
SHA-256 of the bytes in that case's `input/`:

```
build contract 1.0
build platform android
dist examplytics contract 1
dist examplytics contributes permission android.permission.INTERNET reason="Event delivery"
dist examplytics contributes source java/org/example/analytics/Bridge.java
dist examplytics floor compile_sdk configured=35 declared=35 state=met
dist examplytics floor min_sdk configured=26 declared=24 state=met
dist examplytics input java/org/example/analytics/Bridge.java sha256=22ea0ee0c3006cac66f6d0240d32ac4c3dc6828179de7084d34c6ba3adce2836
dist examplytics input native.toml sha256=3de10e32e5acdc2e46c4a3b55a1263a3a0547188407fb799d39df73e5e2b0a5a
dist examplytics origin direct
dist examplytics owns java-namespace org.example.analytics
dist examplytics value analytics_key key=com.example.analytics.API_KEY kind=manifest_meta_data state=supplied
dist examplytics version 1.0.0
effective permission android.permission.INTERNET distributions=examplytics
```

Every line is a fact [§9.6](../SPEC.md#96-what-a-record-must-contain) requires
to be recoverable, and the file is its own sorted order.

## 6. Digests in a fixture

A fixture's `input` digests are the SHA-256 of the bytes in its own `input/`
directory, so they are real and a consumer computes the same ones.

Where a fixture is not about hashing, `ignore_digests = true` makes `run.py`
compare digest **content** loosely — so a case about namespace collision is not
also a test of file hashing. It does not relax the **syntax**: every `sha256`
and `checksum` is 64 lowercase hexadecimal characters
([§9.3](../SPEC.md#93-hashed-inputs)) whatever the case sets, and `run.py`
rejects a record that abbreviates one before any comparison happens.

## 7. What a fixture cannot pin

One operand is elided from both sides of every comparison, always:
`chosen` on a `decision collision` line that says `decided=consumer`.

[§9.7](../SPEC.md#97-packaging-collisions) lets a consumer resolve a
packaging-metadata collision itself, "by a rule that does not depend on
resolution order", and fixes no rule. Two conforming consumers may therefore
keep different copies of `META-INF/LICENSE`, and a fixture that pinned the
winner would fail one of them for making a choice the section hands it. What
[§9.6](../SPEC.md#96-what-a-record-must-contain) requires recorded is the row —
the path, the artifacts that collided, the distributions responsible, the date,
and that the consumer decided — so that is what is compared.

`decided=application` is compared in full. There the answer is the
application's, joined by the packaged path, and choosing differently means
shipping the copy the application refused.
