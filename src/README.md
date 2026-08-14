# The reference reader

`native_integration` is a reader for [the specification](../SPEC.md): discovery,
parsing, validation, and rule enforcement, so that a build tool gets the
consumer obligations of §8 as code paths rather than as prose it has to
remember to implement.

It is **not** a build tool. It never writes a Gradle or Xcode project, never
resolves a Maven coordinate, and never runs anything. It tells a consumer what
the application's dependency closure declares, what the application still has
to answer, and what changed since the last time anyone accepted it.

```bash
python3 -m pip install -e ".[test]"
python3 -m pytest -q
```

## A read, end to end

```python
from native_integration import Application, Closure, MappingAnswers, Platform, read

integration = read(
    platform=Platform.ANDROID,
    closure=Closure.direct("pystripe"),          # your resolver's answer, for the target platform
    application=Application(
        android_sdk={"min_sdk": 24, "compile_sdk": 35},
        answers=MappingAnswers(                  # your own configuration, adapted
            application_values={"pystripe": {"stripe_return_scheme": "trailmap-pay"}},
            allow_exported={"pystripe": ["org.pystripe.PaymentReturnActivity"]},
        ),
    ),
    resolvers=my_ports,                          # see "Ports" below
    record_path="native-integration.lock.json",
)

print(integration.report())
integration.raise_for_errors()                   # blocking diagnostics stop the build
for permission in integration.effective.permissions():
    ...                                          # stage it; the library computed it
```

`integration.effective` is what the **sidecars** contribute, after the
application's answers — permissions after suppression, components with their
export decisions, generated intent filters with application values already
substituted, the merged `Info.plist`, and the paths that must never reach the
device.

It is not the whole native surface. What a *resolved artifact* brings in on its
own — an `.aar`'s permissions, its exported components, a `required="true"`
feature this library overrides — lives in `integration.resolution.artifact_findings`
and in the record, because §9 attributes those to the artifact rather than to
the distribution that named the coordinate. A consumer staging a manifest needs
both.

## Where the obligations live

[`docs/REQUIREMENTS.md`](../docs/REQUIREMENTS.md) maps every §8 requirement to
the code path that discharges it. It is generated from `rules.py` and from
SPEC.md itself, and CI fails if it drifts.

| Module | What it holds |
| --- | --- |
| `discovery` | §3 — the closure, entry-point iteration, and reaching a distribution's files without importing it |
| `sidecar`, `schema`, `contract` | §4 — the contract gate, the fail-closed key walk, and §§6–7's per-sidecar rules |
| `crossrules` | the rules that are not properties of one sidecar: namespaces, component classes, module names, contested repository scopes |
| `answers`, `context` | §2.2 — the application's side, joined on `(distribution, key)` |
| `effective` | declarations become contributions: suppression, approval, substitution, satisfaction |
| `native`, `ports` | §6.5/§7.4/§6.9/§9 — everything that needs a resolved graph |
| `record` | §9 — the durable, diffable record, the delta, and the acceptance gate |

## Two design decisions worth knowing before you adopt it

**A diagnostic cannot be built without naming a distribution.** Requirement 8.15
is enforced by `Diagnostic.__post_init__`, not by discipline. If you find
yourself with a finding that belongs to no distribution, it is a finding about
your own configuration and does not go here.

**A missing port raises rather than passing.** Four obligations need something
only a build tool has — a locked dependency graph with checksums, an archive
listing, the manifest inside a resolved `.aar`. Those are `Protocol`s in
`ports.py`. If a sidecar declares material that needs one and you supplied
none, the read raises `UnimplementedObligation` naming the requirement. A tool
must not be able to pass validation by leaving a check unimplemented — that is
the "silently ignored" failure §4.4 exists to prevent, one level up.

`native_integration.testing` has stub ports that echo declarations back. They
resolve nothing and exist for tests; do not ship them.

## Status

The specification is a draft and so is this. The version here tracks the
specification revision it implements, and the two are amended together.
