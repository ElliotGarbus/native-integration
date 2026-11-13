# TensorFlow Lite, and the collision with Agora

Clean-sheet, from [TensorFlow Lite's Android quickstart](https://ai.google.dev/edge/litert/android/quickstart).
No `pytflite` distribution exists.

**Written to be composed, not read alone.** [Mediated ads](../mediated-ads/)
covered composition where the overlaps are ordinary — identifier lists,
permissions, a shared meta-data key — and its NOTES record what it could not
reach. §9.1's packaging collisions was the first item on that list, because ad
adapters do not ship native code that collides. This pair does: a video-calling
application that also runs on-device vision is an ordinary product, and both
SDKs bundle a C++ runtime.

Gap identifiers are `TF*`. Composed with [pyagora](../pyagora/) in
`tests/test_examples.py`.

## TF1 — §9.1 fires, and names both packages *(first evidence)*

Agora's `.aar` and TensorFlow Lite's both carry
`lib/arm64-v8a/libc++_shared.so`. Neither producer can see the other, and
neither declaration mentions the file — it is inside a resolved artifact, which
is exactly why §9.1 makes this the consumer's obligation rather than something a
sidecar declares.

The build fails, naming the path and **both distributions**:

```
`lib/arm64-v8a/libc++_shared.so` is carried by more than one artifact
(pyagora → io.agora.rtc:full-sdk:4.5.0, pytflite → org.tensorflow:tensorflow-lite:2.16.1);
choosing one silently would decide at random which native code the application
runs, so the application must choose
```

Two properties of that are the whole point of the rule:

- **Gradle would already have failed here**, with a duplicate-path error naming
  two Maven coordinates. What it cannot say is which *Python distributions*
  asked for them, and that mapping is the only thing the consumer holds and the
  build system does not.
- **`META-INF/LICENSE` collides too, and is resolved silently**, recorded and
  not reported as a problem. Treating both the same way would either fail every
  realistic build or pick between two C++ runtimes by declaration order. The
  split is what makes the rule usable.

The application chooses which artifact supplies the library, and the choice is
recorded. Only it can know whether the two SDKs tolerate one runtime — a
question neither vendor documents, because neither knows about the other.

**A caveat worth stating plainly:** the file listings in the test are stubbed,
because the reader resolves nothing from the network. What the example
demonstrates is the rule and its diagnostic, not that these two releases collide
today — which is a property of the artifacts and precisely why §9.1 inspects the
resolved archive rather than the declaration.

## TF2 — packaging *options* are not packaging collisions *(a new gap)*

TensorFlow Lite memory-maps the model straight out of the APK, which works only
if AAPT stored it uncompressed. Every integration guide says the same thing:

```gradle
aaptOptions { noCompress "tflite" }
```

§9.1 was landed as the answer to "two artifacts, one path". This is the other
half of the same area and the rule does not reach it: one artifact, one path,
and a **packaging setting** the producer knows and the application does not.
Nothing in the specification can say it.

It is not the arbitrary-build-mutation case §11 excludes, for the same reason
§7.8's `objc_categories` is not: a producer would be naming *one behaviour it
depends on* — leave assets with this extension uncompressed — rather than
passing a flag. The failure it prevents is the shape this convention exists for,
too: the model loads on a build where AAPT happened not to compress it and fails
on the next with an mmap error that names no package.

Recorded as a finding rather than proposed as a table. One vendor is a
hypothesis, and the survey's own rule is that a second is what makes it a
finding — though `.tflite`, `.lite` and ML model formats generally all share the
constraint, so the second may not be far away.

## TF3 — the iOS half is out of reach, and §11 now says so *(a validation)*

TensorFlow Lite for Apple platforms is published to CocoaPods and not to Swift
Package Manager; the request has been open upstream for years and was carried
into LiteRT. §7.4 resolves Swift packages and nothing here resolves podspecs.

Until this round that was a silence. §11 now carries a **CocoaPods-only** row,
and this is the first example to land on it — ML Kit is the row's stated
example, and this is a second vendor for the same exclusion. What a producer
does about it is what §4.5 is for: `platforms = ["android"]` says the
distribution does not work on iOS, and a build for iOS fails naming it rather
than producing an application that links nothing.

## TF4 — §6.11's `application_files`, outside a test *(a validation)*

The model is the application's — a binding cannot ship the weights its user
trained — and TensorFlow Lite reads it from assets by name. §6.11's table was
landed on Airship's evidence and this is its second vendor, on a different
platform mechanism (an asset the interpreter mmaps, rather than a config file a
push SDK parses). The rule that the consumer checks only that a file of that
name is wired in, and never creates one, needs no adjustment for it.
