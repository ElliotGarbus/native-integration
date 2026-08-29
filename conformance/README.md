# The conformance corpus

Cases a consuming tool is run against, so that "conforming" means something
checkable rather than claimed.

## Precedence

**Where a fixture and the specification disagree, [SPEC.md](../SPEC.md) wins and
the fixture is a defect.** File it as one.

This is stated first because the alternative is how a corpus quietly becomes the
contract: a fixture asserts something the specification never said, two
implementations are held to it, and the specification is the thing that gets
edited to match. Nothing here is normative. The corpus is evidence about
conformance, not a source of it.

## Fixtures are authored from the specification, never from a run

**No `expected/` file in this corpus was produced by executing an
implementation**, and none may be. If an expected output cannot be derived from
the specification's text alone, that is an ambiguity finding — record it under
[`development/findings/`](../development/findings/) with its section anchors and
stop.

The reason is the whole point of the exercise. A corpus derived from consumer #1
cannot establish that consumer #2 agrees with the specification; it establishes
only that consumer #2 agrees with consumer #1. Two consumers reading one sidecar
and agreeing is the bar [the README](../README.md#before-a-freeze) sets before a
freeze, and a corpus that bakes in one implementation cannot measure it.

## Layout

```
conformance/
  record-format.md          the normalized output two consumers are compared on
  run.py                    the harness
  core/                     requirements every consumer implements (§8.1)
  android/
  ios/
    <Rnn>_<slug>/
      case.toml             what this case asserts
      input/                the sidecars, and the application's answers
      expected/             the conformance record, or the diagnostics
```

### `input/`

```
input/
  closure.toml        the resolved dependency closure for the target platform
  application.toml    the application's own configuration and answers
  <distribution>/     one tree per distribution, as installed
    <package>/_native/native.toml
```

`closure.toml` is what a consumer's own resolver would have produced —
distribution name, version, how it entered ([§3.2](../SPEC.md#32-resolution)),
and the entry-point value. A distribution marked `origin = "not-in-closure"` is
installed alongside and outside the closure, which is the only way to exercise
requirement 1.

`application.toml` is a **neutral spelling**.
[§2.2](../SPEC.md#22-how-the-application-answers) fixes the capability a consumer
must offer and deliberately not its syntax, so a consumer under test adapts this
into whatever it actually reads. The corpus cannot mandate a spelling the
specification refuses to.

Profiles follow [§8.1](../SPEC.md#81-conformance-is-per-platform). Advisory
obligations carry no profile there, so each sits with the section it enforces:
S1–S4 are core, S5–S9 and S11–S13 Android, S10, S14 and S15 iOS.

## `case.toml`

Two axes, deliberately. [§8.2](../SPEC.md#82-dispositions-and-what-recording-is-not)
classifies **findings**; a numbered requirement that defines no finding is a
conformance obligation, checked by inspecting what the consumer produced. One
field cannot carry both, and collapsing them would invent a disposition the
specification declines to define.

```toml
requirement = 23           # the §8.4 number, or "S13" for an advisory
profile     = "android"    # core | android | ios
section     = "6.1"        # what it enforces, for `explain`

# Axis 1 — what happens to the build.
outcome = "blocking"       # accept | blocking

# Axis 2 — findings expected while exercising it.
diagnostics = ["ni.req.23"]
advisories  = []

# Axis 3 — observable postconditions, for obligations with no finding.
assertions = []
```

| Field | Meaning |
| --- | --- |
| `outcome` | `blocking` — the build **MUST NOT** proceed. `accept` — it proceeds |
| `diagnostics` | diagnostic IDs ([`contract/diagnostics-v1.toml`](../contract/diagnostics-v1.toml)) the consumer must report. Every one names the distribution responsible ([§8.4](../SPEC.md#84-requirements) requirement 18) |
| `advisories` | advisory IDs expected. Reported, never blocking ([§8.5](../SPEC.md#85-advisory-obligations)) |
| `assertions` | named postconditions on what the consumer produced — the record, the payload, the generated project |
| `record` | the `expected/` file to compare against, when the case has one |
| `ignore_digests` | the case is not about hashing, so `input` digests compare loosely |

An unsatisfied conditional requirement is neither blocking nor advisory
([§8.2](../SPEC.md#82-dispositions-and-what-recording-is-not)), and says so on
the axes rather than in a disposition:

```toml
outcome = "accept"
state    = "unresolved"
reported = true
```

### Assertions

An assertion names something observable about the consumer's own output. It is
not a diagnostic, and it may accompany an accepted build, a blocked one, or an
advisory — which is why it is a separate axis rather than a third disposition.

| Assertion | Requirement |
| --- | --- |
| `no_producer_import` | 3 — no producing distribution is imported, ever |
| `sidecar_excluded_from_payload` | 6 — the sidecar directory reaches no device payload |
| `contributed_source_excluded_from_payload` | 24 |
| `python_module_stubs_excluded` | 36 — `<name>.py` and `<name>.pyi` |
| `every_diagnostic_names_a_distribution` | 18 |
| `instructions_attributed_to_producer` | 21 |
| `no_credential_in_record` | 42 |
| `record_contains` / `record_omits` | 43, and any row of [§9.6](../SPEC.md#96-what-a-record-must-contain) |
| `activity_extends_component_activity` | 45 |
| `url_callback_observable` | 46 |

A consumer that cannot observe an assertion reports it **unsupported** rather
than passing it. An assertion silently skipped is how a conformance claim
overstates itself — the failure [§8.5](../SPEC.md#85-advisory-obligations)'s
note already names for advisory obligations.

## Running it

```
python3 conformance/run.py --profile android -- mytool build --conformance-record
```

`run.py` invokes the consumer once per case, with the case's `input/` as the
application's dependency closure, and compares what comes back. It reports
pass, fail or unsupported per case, and exits non-zero on any fail.

The consumer under test supplies the command. Nothing here imports a consumer,
and nothing here is a consumer.
