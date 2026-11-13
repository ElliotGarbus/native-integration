# Worked example

One integration, both halves.

| File | What it is |
| --- | --- |
| [`pystripe/native.toml`](pystripe/native.toml) | the **sidecar** — what the package declares |
| [`pystripe/app-pyproject.toml`](pystripe/app-pyproject.toml) | the **application's reply** — what its author writes |

Stripe was chosen because it exercises three different answer paths in one
SDK most people recognise:

- a **value the application supplies** — the 3D Secure return scheme, which the
  package cannot know because it is registered per application in Stripe's
  dashboard;
- an **exported component the application approves** — without which the build
  fails rather than quietly registering an activity that cannot receive the
  redirect;
- a **conditional action the application acknowledges** — needed only if the
  webview fallback is reached.

Each answer is filed under the **declaring distribution plus the key the
declaration named**. The spelling of the application's file is illustrative —
[§2.2](../SPEC.md#22-how-the-application-answers) defines the capability a build
tool must offer and deliberately not the syntax — but that join is not.

The most useful thing in the pair may be what is *absent*: the Stripe
publishable key. It is per-application and looks like it belongs beside the
return scheme, and it does not, because the SDK takes it at runtime and §5.2 is
only for values the build must embed. It goes in the application's Python. The
scheme differs in kind because it is baked into a manifest intent filter, where
no runtime call can reach it.

Two things keep the pair honest. `python3 tools/check_spec.py` keeps the halves
in step — a requirement added to the sidecar with no answer fails, and so does
an answer removed from the application — and `tests/test_examples.py` runs the
reader in [`src/`](../src/) over the sidecar itself, so a declaration that is
spelled correctly and still wrong fails too.

---

**Seventeen further integrations** — PyOneSignal, PyCoreLocation, PyWebViews,
PyGMA, Firebase, Sentry, Mapbox, Meta, Airship, Agora, Health Connect,
TensorFlow Lite and a three-package mediated-ads set — were expressed against
the specification while it was being written, and are what shaped it. They live
in [`development/examples/`](../development/examples/) with the findings beside
each, and the decisions they produced are in
[`development/PROPOSALS.md`](../development/PROPOSALS.md).
