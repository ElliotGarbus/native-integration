# PyWebViews against contract 1

Source: [PyPlatformPackages/PyWebViews](https://github.com/PyPlatformPackages/PyWebViews).

Selected as the "substantial package-owned Swift" case. It is that — four Swift
files, two `@PyClass` types, `WKWebView` wrapped and rendered into a Kivy
texture. But the finding that matters arrives before any of it.

## W1 — there is no Python distribution *(blocking, and categorical)*

PyWebViews has **no `pyproject.toml`, no wheel, and no `dist-info`**. The
repository is a SwiftPM package. Its Python file,
`Sources/PyWebViews/wrappers/web_views.py`, is not an importable module — it is
Swiftonize code-generation input:

```python
from swift_tools.swift_types import *  # type: ignore

@wrapper()
class WebViewer:
    def load_url(self, url: str): ...
```

§3.2 discovers producers by enumerating the application's **resolved dependency
closure** and reading entry points via `importlib.metadata`. There is nothing
here for that to find. PyWebViews cannot participate in this convention in any
form — not because a key is missing, but because the carrier is.

The remedy is real and known: ship a thin wheel, which is exactly PyCoreLocation's
shape. But the specification should **say** that the Python distribution is the
carrier and that a native-only package has to acquire one to participate. §3.2
assumes it silently, and the assumption is not free — it is a packaging
obligation on projects that currently have no reason to have a wheel at all.

This is also the more interesting half of the question the exercise was meant to
answer. Two of the four packages are Swift packages first and Python packages
second; one of them has not bothered with the Python half yet.

## W3 — Swift package versions encode the CPython ABI *(new, and sharp)*

PyWebViews' git tags are `311.0.0`, `311.1.0`, `311.1.1`, `311.1.2`, `311.1.3`.
Its `Package.swift` depends on:

```swift
.package(url: "https://github.com/py-swift/PythonCore", .upToNextMajor(from: .init(311, 0, 0)))
.package(url: "https://github.com/py-swift/PySwiftKit", from: .init(311, 0, 0))
```

PyCoreLocation depends on PySwiftKit `from: .init(313, 0, 0)`.

**The major version is the Python version.** 311 is CPython 3.11; 313 is 3.13.
Three consequences:

**An application depending on both packages cannot resolve.** PySwiftKit 311.x
and 313.x are different majors; SwiftPM will fail. That failure is correct — the
two packages genuinely target different interpreters — but the *diagnostic* is a
SwiftPM resolver error naming `PySwiftKit`. Nothing connects it back to
`py_core_location` and `py_web_views`. Requirement 8.15 — *"Name the
contributing distribution in every diagnostic"* — cannot be met, because the
diagnostic is not the consumer's to write.

**The specification never says what happens when producers' native dependencies
are mutually unsatisfiable.** §6.5 and §7.4 lock resolution and §9 records it,
but both assume resolution *succeeds*. Two producers declaring incompatible
Gradle coordinates is the identical case on Android, and the text is silent
there too. A consumer must be required to report, on native resolution failure,
the full set of declared coordinates and packages **with their declaring
distributions** — the one thing it knows that the underlying resolver does not.

**It also breaks the fix proposed for PyCoreLocation.** P13 suggested a SHOULD
that a self-declared Swift package pin the distribution's own version. Here that
is unimplementable: the wheel version would track the package's features while
the tag tracks the Python ABI. The two version lines mean different things and
cannot be made to agree.

There is a mitigating truth worth stating: this constraint is *already*
expressible one layer down, as `requires-python` in the wheel. A correctly
resolved dependency closure for CPython 3.13 would never contain a 3.11-only
distribution. That is an argument for the specification saying plainly that the
**closure's Python version governs** and the sidecar does not restate it — and
another argument for W1, since a package with no wheel has no `requires-python`
either.

## W2 — module name, module struct, target, and repository are four names

| Layer | Name |
| --- | --- |
| Python import | `web_views` (`from web_views import JavaViewer, WebViewer`) |
| `@PyModule` struct | `WebViews` |
| SwiftPM target and product | `PyWebViews` |
| Repository / distribution | `PyWebViews` |

P8's draft spells the Python module name and the Swift package separately, which
this confirms is necessary rather than merely tidy:

```toml
[[ios.contributes.python_modules]]
name = "web_views"
swift_package = "PyWebViews"
```

A single Swift package can also vend more than one `@PyModule`, so the
list-of-tables shape is right. Nothing here changes P8 — it is the second
independent example of the same need, which promotes it from PyCoreLocation's
single case.

## W4 — §7.5's "SHOULD NOT be used for a library", demonstrated

`WebViews.swift` declares, at file scope:

```swift
fileprivate let retinaScale = 1.0 / UIScreen.main.nativeScale
fileprivate let screen_size  = UIScreen.main.nativeBounds
let ui_scale = UIScreen.main.scale
func invertedHeight(_ v: Double) -> Double { … }
public protocol WKBase { … }
extension Double { var retinaScaled: Self { … } }
```

If this were staged into the application target via §7.5 rather than resolved as
a SwiftPM module, `ui_scale` and `invertedHeight` are prime collision
candidates, and `extension Double { var retinaScaled }` becomes visible to
everything the target compiles, including the application's own code.

Two things follow, and they point in opposite directions from the current text:

- **§7.1's prefix guidance would not have helped.** It asks producers to prefix
  "contributed type names, and in particular `@objc` runtime names." Nothing in
  that reaches file-scope functions, global constants, or extension members —
  which is exactly what collides here. §7.1 should say what its guidance does
  **not** cover.
- **§7.1's anticipated hardening already exists, and it is §7.4.** The text
  defers per-producer Swift modules to §10 as future work. A SwiftPM package
  *is* a separate module, so every producer that follows §7.4's own
  RECOMMENDED-for-anything-larger advice gets the hardening today. The
  interesting move is therefore not to build module separation for §7.5, but to
  ask whether §7.5 should exist for anything beyond a genuinely small shim — and
  to make its discouragement concrete by naming this failure mode.

Both PyCoreLocation and PyWebViews reached for §7.4 rather than §7.5 without
being told to. That is the specification's own recommendation being confirmed by
practice, which is a real if unglamorous result.

## W6 — the dictionary Info.plist cases keep resolving themselves

A `WKWebView` binding needs no permission, no entitlement, and no Info.plist key
of its own. The keys that *might* be needed are all conditional on what the
**application** loads:

| Key | Needed when | Shape |
| --- | --- | --- |
| `NSAppTransportSecurity` | the app loads cleartext URLs | **dictionary** |
| `NSCameraUsageDescription` | page calls `getUserMedia` | usage description |
| `NSMicrophoneUsageDescription` | page calls `getUserMedia` | usage description |

None belong to the producer. A web view binding cannot know what the application
will load, so declaring any of them would be §12's facade problem in its purest
form — the union of every page's needs, imposed on every application.

This is the third example in a row where a **dictionary-valued Info.plist key**
appeared, and the third where the right answer was to move it out of
`contributes` rather than to add dictionary support:

- PyOneSignal: `NSExtension` → generated by the consumer from `kind` (P4).
- PyCoreLocation: `NSLocationTemporaryUsageDescriptionDictionary` → a `requires`
  the application supplies (P9).
- PyWebViews: `NSAppTransportSecurity` → not the producer's at all.

§7.6 says typed contributions for dictionary structures "may be added in a minor
revision." On this evidence they should not be. Every case so far dissolves
under a narrower primitive, and the general form would hand producers the
ability to write arbitrary structured application configuration.

## W5 — third-party chain, `upToNextMajor` throughout

`UIViewRender` and `KivyTexture` (KivySwiftPackages) both come in as
`.upToNextMajor(from: 311.0.0)` — §7.4's `{ from = … }`, correctly handled — and
resolve transitively, so only PyWebViews itself is declared. Same asymmetry as
PyCoreLocation: §6.5 records the Android graph "including transitives," §7.4
records only "the version actually resolved." Nothing new; P10 already covers it,
now with a second example.

## Not a specification matter, but worth recording

The Swift reaches into the host application's view hierarchy directly —
`UIApplication.shared.windows.first`, then `rootViewController`, then
`addSubview` — with a `fatalError()` when it is not found. A producer that
manipulates the consumer-generated app's UIKit hierarchy is outside anything
this specification governs or could govern. It is a reminder that the
declaration surface is not the trust boundary: contributed Swift is compiled
into the application target and can do anything the application can. §9's
disclosure is the only control, which is what §9 already says.

## Verdict

PyWebViews contributed one new blocking finding and one sharp one, and confirmed
three existing ones.

**W1 is categorical**: the convention requires a Python distribution as the
carrier, and this project does not have one. That is a legitimate boundary, but
the specification states it nowhere.

**W3 is the sharpest technical finding of the four examples so far**, because it
is the first case where two producers are mutually **unsatisfiable** rather than
merely awkward — and where the resulting diagnostic provably cannot meet
requirement 8.15.

Confirmations: P8 gains a second independent example and its
name-versus-package split is validated (W2). P10 gains a second example (W5).
And §7.5/§7.1 receive concrete evidence (W4) that the discouragement is right,
the prefix guidance is narrower than the problem, and the deferred hardening is
already available through §7.4.

One correction propagated backward: the PyCoreLocation sidecar originally
declared `{ exact = "0.1.0" }` for its own Swift package. That repository has no
tags, so it could never have resolved; it now pins a revision. W3 explains why
the obvious fix — pin the wheel's version — is not available in this ecosystem.

**PyGMA next**, which is the only remaining cross-platform case and the only one
that should exercise §6.3 and Android/iOS symmetry.
