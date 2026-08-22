# Agora against the current spec

Clean-sheet, from [Agora's video calling quickstart](https://docs.agora.io/en/video-calling/get-started/get-started-sdk)
and its [screen sharing guide](https://docs.agora.io/en/realtime-media/rtc/build/capture-and-render-video/screen-sharing).
No `pyagora` distribution exists.

Chosen from [SURVEY.md](../../SURVEY.md) as the first real-time-media
integration in the set. RTC exercises parts of the specification nothing else
has: six permissions, two hardware features, a Swift package that vends
prebuilt binaries, and a feature — screen sharing — that needs a foreground
service on Android and a separate signed executable on iOS.

## AG1 — the screen-capture service cannot be registered *(blocking)*

Android requires media projection to run inside a foreground service, and since
Android 14 that service **must** carry
`android:foregroundServiceType="mediaProjection"` and the application must hold
the matching `FOREGROUND_SERVICE_MEDIA_PROJECTION` permission. Agora's guidance
is explicit that the application creates this service; the SDK does not ship
one that can be used unmodified.

§6.8 models a component as `kind`, `name`, provenance and export. There is no
attribute, so a producer-source capture service cannot be written into a valid
manifest at all — the build fails, or worse, the service is registered without
a type and the platform kills it the moment capture starts.

**This corrects a hedge in the survey.** N5 was recorded with the caveat that
an SDK arriving as an `.aar` brings its own service declaration and dodges the
gap. Agora is the counter-example: the service is the *producer's* to declare,
because it is the producer's capture lifecycle that runs in it. The gap is not
narrow.

Note the permission half is already expressible — `FOREGROUND_SERVICE` and
`FOREGROUND_SERVICE_MEDIA_PROJECTION` are ordinary §6.7 entries. Only the
attribute that makes them meaningful is missing, which is the worst place for a
gap to sit: the declaration looks complete.

## AG2 — iOS screen capture needs a Broadcast Upload Extension *(blocking)*

Apple does not permit an application to capture its own screen from the main
process, so ReplayKit runs in a **Broadcast Upload Extension** — a separate
target, separately signed, with Agora's `AgoraReplayKitHandler` set as its
principal class and a 50 MB memory ceiling.

`kind` offers `notification_service` and `location_push`. §7.3's rationale for
the `requires` form transfers exactly — an extension is a separate signed
executable and a large thing for a transitive dependency to introduce — so the
missing piece is only the vocabulary, not the model. Adding `broadcast_upload`
costs one row and would let this sidecar state the requirement instead of
omitting the feature.

## AG3 — `libc++_shared.so`, and the composition case

Agora ships `libc++_shared.so`. So do TensorFlow Lite, OpenCV, and anything
WebRTC-derived. Two such packages in one application collide at packaging time,
and the resolution — `pickFirst`, or an equivalent — belongs to the
application's build configuration, which no producer can see or declare.

This is the one gap in the set that **should not** become a producer
declaration. No producer can know what it will be composed with, and a
declaration would be a guess. It belongs in §8 as a consumer obligation:
detect, resolve by a stated rule, and report in the record of §9 so a broken
combination is attributable rather than mysterious. Composition is what this
convention is for, so a silent failure at exactly the composition point is
worse here than it would be in a build file someone edits by hand.

## What this validated

- **§6.9's archive check, on the case its rationale describes.** Agora's
  documented rule keeps `io.agora.**` while the Maven group is `io.agora.rtc`.
  A consumer checking the pattern against the group would reject a legitimate
  rule; checking the resolved artifact accepts it. First live instance of the
  mismatch §6.9 was written for.
- **§6.7's refusal to let a producer promote a feature.** A video SDK is the
  most tempting case for `required="true"` — and it would be wrong. Whether a
  calling application refuses to install on a camera-less device is a product
  decision; the rule holds under pressure.
- **§7.4 with a binary-vending package.** Agora's Swift package distributes
  prebuilt XCFrameworks as binary targets, which is precisely the case P30
  added a checksum requirement for, and §11's "in the wheel" distinction
  handles cleanly: the binaries arrive through SwiftPM, locked and recorded,
  not smuggled inside a wheel.
- **Six permissions with real `reason` text.** The §9 report for this package
  is legible in a way a transcribed manifest is not, and `BLUETOOTH_CONNECT`
  is the entry an application would otherwise never connect to call audio
  routing.

## Verdict

**Voice and video: clean on both platforms.** **Screen sharing: blocked on
both**, for unrelated platform reasons that happen to land in the same two
gaps — a missing component attribute and a missing extension kind. A wrapper is
worth shipping without screen share, and the deficiency is nameable, which is
the outcome §12 asks a producer to be honest about.
