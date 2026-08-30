#!/usr/bin/env python3
"""Run the conformance corpus against an external consumer.

    python3 conformance/run.py --profile android -- mytool build --conformance-record

For each case in the profile this invokes the consumer once, with the case's
`input/` directory as the application's resolved dependency closure, and
compares what came back against what the case says the specification requires.

**This is not a consumer.** It imports none, implements none, and knows nothing
about sidecars beyond how to compare two records. The reference reader under
`src/` is a separate thing and is not used here — a harness that shared code
with an implementation would be measuring agreement with that implementation,
which is the failure `README.md` opens by naming.

Three axes are checked, per `conformance/README.md`:

* `outcome`     — accept or blocking, the build's fate;
* `diagnostics` — the findings, each with the distributions it names;
* `assertions`  — postconditions on what the consumer produced.

**The JSON is the only authority on the outcome.** A consumer whose exit status
disagrees with what it reported has contradicted itself, and that is a failure
rather than something to resolve by preferring one of the two.

**An assertion is verified here where it can be.** The consumer is handed an
output directory and writes what it produced into it; the payload assertions are
then checked against those files rather than taken on the consumer's word.
Assertions with no adapter are marked *attested* in `README.md` and remain the
consumer's claim — labelled, so that nobody mistakes testimony for evidence.

Two things short of a pass are reported differently, because they mean opposite
things:

* **unverified** — the consumer cannot observe an assertion, so a *numbered*
  requirement went unchecked. Conformance was not demonstrated, and the run
  exits non-zero. §8.5's note names the failure: an obligation quietly skipped
  is how a conformance claim overstates itself.
* **unsupported** — the consumer does not claim an advisory the case names.
  §8.5 makes an advisory reported and never blocking, so this is a conforming
  consumer declining an optional obligation, and the run still exits 0.

Exit status is 0 when every case passed or was unsupported, and 1 when any
failed or went unverified.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROFILES = ("core", "android", "ios")

PASS, FAIL = "pass", "fail"
#: A numbered requirement the consumer could not be checked on, and an advisory
#: it declines. The first is a gap in the evidence; the second is not.
UNVERIFIED, UNSUPPORTED = "unverified", "unsupported"


#: Which platforms a profile's cases are exercised for. §8.1 makes conformance
#: "the core plus at least one platform profile", so a **core** case binds a
#: consumer whichever platform it builds — and a corpus that ran core only
#: against Android could not establish iOS conformance at all.
PROFILE_PLATFORMS = {"core": ("android", "ios"), "android": ("android",), "ios": ("ios",)}


@dataclass
class Case:
    name: str
    profile: str
    platform: str
    directory: Path
    spec: dict

    @property
    def label(self) -> str:
        return f"{self.profile}/{self.name}" + (
            f" [{self.platform}]" if len(PROFILE_PLATFORMS[self.profile]) > 1 else ""
        )

    @property
    def requirement(self) -> str:
        return str(self.spec.get("requirement", "?"))

    @property
    def outcome(self) -> str:
        return self.spec.get("outcome", "accept")

    @property
    def input_directory(self) -> Path:
        """The case's input for this platform, or its single platform-free one."""
        per_platform = self.directory / "input" / self.platform
        return per_platform if per_platform.is_dir() else self.directory / "input"

    @property
    def expected_record(self) -> Path | None:
        named = self.spec.get("record")
        candidate = (
            self.directory / "expected" / named
            if named
            else self.directory / "expected" / f"{self.platform}.record"
        )
        return candidate if candidate.exists() else None


@dataclass
class Result:
    case: Case
    status: str
    detail: list[str] = field(default_factory=list)


def load_cases(profile: str, platforms: set[str]) -> list[Case]:
    cases: list[Case] = []
    for path in sorted((ROOT / profile).glob("*/case.toml")):
        spec = tomllib.loads(path.read_text(encoding="utf-8"))
        for platform in PROFILE_PLATFORMS[profile]:
            if platform not in platforms:
                continue
            cases.append(
                Case(
                    name=path.parent.name,
                    profile=profile,
                    platform=platform,
                    directory=path.parent,
                    spec=spec,
                )
            )
    return cases


FACTS = tomllib.loads((ROOT / "record-facts.toml").read_text(encoding="utf-8"))["facts"]

DIGEST = re.compile(r"[0-9a-f]{64}")
DIGEST_KEYS = ("sha256", "checksum")

FORMATS = tomllib.loads((ROOT / "record-facts.toml").read_text(encoding="utf-8"))["formats"]


def well_formed(kind: str, value: str) -> str | None:
    """Whether `value` is in the normalized form `kind` names, or why not.

    §2 of record-format.md borrows every one of these from SPEC.md rather than
    inventing any — a distribution name is §1's normalized form, a date is
    §9.6's RFC 3339 full-date, a path is §9.3's forward-slash relative form.
    Left unchecked they are documentation; two consumers that normalize
    differently produce records that never compare.
    """
    if kind == "date":
        # A pattern accepts 2026-02-30. The calendar does not.
        try:
            year, month, day = (int(part) for part in value.split("-"))
            date(year, month, day)
        except (ValueError, TypeError):
            return "is not an RFC 3339 full-date"
        if value != f"{year:04d}-{month:02d}-{day:02d}":
            return "is not an RFC 3339 full-date"
        return None
    if kind == "path":
        # A drive letter is absolute too, and `C:/x` slips past a leading-slash
        # test while naming a location no wheel can contain.
        if value.startswith("/") or "\\" in value or re.match(r"[A-Za-z]:", value):
            return "is not a relative forward-slash path"
        if any(part in ("", ".", "..") for part in value.split("/")):
            return "is not a normalized relative path"
        return None
    if kind == "integer":
        return None if re.fullmatch(r"0|-?[1-9][0-9]*", value) else "is not an integer"
    pattern = FORMATS.get(kind)
    if pattern and not re.fullmatch(pattern, value):
        return f"is not a well-formed {kind}"
    return None


def read_record(raw: bytes) -> tuple[list[str], list[str]]:
    """The file rules of record-format.md §1, checked rather than assumed.

    A harness that silently repaired CRLF, blank lines or a missing final
    newline would let two consumers disagree about the bytes while agreeing
    about the facts — which is the one thing a byte-comparable format exists to
    prevent.
    """
    problems: list[str] = []
    if raw.startswith(b"\xef\xbb\xbf"):
        problems.append("the record starts with a BOM")
        raw = raw[3:]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return [], [f"the record is not valid UTF-8: {exc}"]
    if "\r" in text:
        problems.append("the record contains a carriage return; lines end with a bare newline")
    if text and not text.endswith("\n"):
        problems.append("the record has no final newline")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            problems.append(f"line {index} is blank; the file is facts and nothing else")
    return lines, problems


BARE = re.compile(r"[A-Za-z0-9._:/@+~*-]+")
KEY = re.compile(r"[a-z0-9_-]+")
ESCAPES = {'"': '"', "\\": "\\", "n": "\n", "t": "\t", "r": "\r"}

#: The characters `\uXXXX` exists for: those with no literal form and no short
#: escape of their own.
NEEDS_UNICODE_ESCAPE = frozenset(
    {chr(c) for c in range(0x20)} - {"\n", "\t", "\r"} | {chr(0x7F)}
)


#: Operand names whose normalized form is the same wherever they appear. A
#: fact may add or override with its own `formats` table.
FORMAT_BY_NAME = {
    "contract": "contract",
    "date": "date",
    "distribution": "distribution",
    "distributions": "distribution",
    "max-sdk": "integer",
    "path": "path",
    "via": "distribution",
    "withdrew": "distribution",
}


class LexError(Exception):
    pass


def scan_scalar(line: str, i: int) -> tuple[str, str, int]:
    """One scalar from `line` at `i`. Returns (decoded, raw, next index).

    Canonicalization is checked here rather than after the fact: the format's
    claim is that one value has one spelling, and a lexer that accepted two
    would let two consumers emit files that differ in bytes and agree in facts.
    """
    if i >= len(line):
        raise LexError("a value is missing where one is required")
    if line[i] == '"':
        out: list[str] = []
        j = i + 1
        while True:
            if j >= len(line):
                raise LexError("a quoted value is never closed")
            char = line[j]
            if char == '"':
                j += 1
                break
            if char == "\\":
                if j + 1 >= len(line):
                    raise LexError("a quoted value ends inside an escape")
                marker = line[j + 1]
                if marker in ESCAPES:
                    out.append(ESCAPES[marker])
                    j += 2
                    continue
                if marker == "u":
                    digits = line[j + 2 : j + 6]
                    if len(digits) != 4 or any(d not in "0123456789abcdef" for d in digits):
                        raise LexError(
                            f"`\\u{digits}` is not four lowercase hexadecimal digits"
                        )
                    point = chr(int(digits, 16))
                    # `\uXXXX` is for the characters that have no other
                    # representation. A printable character written this way,
                    # or a control that has a short escape, would give one
                    # value two spellings and defeat the byte comparison.
                    if point not in NEEDS_UNICODE_ESCAPE:
                        raise LexError(
                            f"`\\u{digits}` is written literally, or with its short escape"
                        )
                    out.append(point)
                    j += 6
                    continue
                raise LexError(f"`\\{marker}` is not an escape this format defines")
            if ord(char) < 0x20 or ord(char) == 0x7F:
                raise LexError("a control character is written as an escape, never literally")
            out.append(char)
            j += 1
        decoded = "".join(out)
        if decoded and BARE.fullmatch(decoded):
            raise LexError(f'`{decoded}` is bare, so it is never quoted')
        return decoded, line[i:j], j

    match = BARE.match(line, i)
    if not match:
        raise LexError(f"`{line[i]}` begins no value this format defines")
    return match.group(0), match.group(0), match.end()


def scan_value(line: str, i: int) -> tuple[list[str], str, int]:
    """A scalar, or a list of two or more. Returns (decoded members, raw, next).

    Members are ordered by their **serialized** bytes, not their decoded ones.
    The two disagree wherever an escape is involved — `"a b"` sorts before
    `"a\\nb"` written out, and after it decoded — and the file's own ordering is
    over serialized lines, so a member ordering defined any other way would put
    the two sorts in conflict.
    """
    members: list[str] = []
    raws: list[str] = []
    start = i
    while True:
        decoded, raw, i = scan_scalar(line, i)
        members.append(decoded)
        raws.append(raw)
        if i < len(line) and line[i] == ",":
            i += 1
            if i >= len(line) or line[i] in ", ":
                raise LexError("a list has a value between every pair of commas")
            continue
        break
    if len(members) > 1:
        if raws != sorted(raws):
            raise LexError("a list is sorted bytewise over its serialized members")
        if len(set(raws)) != len(raws):
            raise LexError("a list is de-duplicated")
    return members, line[start:i], i


def lex(line: str) -> tuple[list[str], dict[str, list[str]], dict[str, str]]:
    """A fact as its positional operands, its keyed ones, and their raw text."""
    positional: list[str] = []
    keyed: dict[str, list[str]] = {}
    raw: dict[str, str] = {}
    order: list[str] = []
    i = 0
    while i < len(line):
        if line[i] == " ":
            raise LexError("operands are separated by exactly one space")
        key_match = KEY.match(line, i)
        if key_match and line[key_match.end() : key_match.end() + 1] == "=":
            key = key_match.group(0)
            if key in keyed:
                raise LexError(f"`{key}` appears more than once")
            values, spelling, i = scan_value(line, key_match.end() + 1)
            keyed[key] = values
            raw[key] = spelling
            order.append(key)
        else:
            if keyed:
                raise LexError("a positional operand follows a keyed one")
            decoded, _, i = scan_scalar(line, i)
            positional.append(decoded)
        if i < len(line):
            if line[i] != " ":
                raise LexError("operands are separated by exactly one space")
            i += 1
            if i >= len(line):
                raise LexError("the fact ends in a space")
    if order != sorted(order):
        raise LexError("keyed operands are sorted bytewise by key")
    return positional, keyed, raw


def match_template(positional: list[str]) -> tuple[str, dict, dict[str, str]] | None:
    """The fact type these positionals satisfy, and its placeholder bindings."""
    for name, spec in FACTS.items():
        tokens = spec["template"].split(" ")
        if len(tokens) != len(positional):
            continue
        bindings = {}
        for want, got in zip(tokens, positional):
            if want.startswith("<"):
                bindings[want.strip("<>")] = got
            elif want != got:
                break
        else:
            return name, spec, bindings
    return None


def satisfied(condition: dict, bound: dict[str, list[str]]) -> bool:
    """Whether a conditional rule's `if` half holds for this fact."""
    present = bound.get(condition["key"])
    if present is None:
        return False
    if "values" in condition:
        return any(v in condition["values"] for v in present)
    if "not_values" in condition:
        return all(v not in condition["not_values"] for v in present)
    return True


def validate_fact(line: str) -> list[str]:
    try:
        positional, keyed, _raw = lex(line)
    except LexError as problem:
        return [f"{problem}: {line}"]

    matched = match_template(positional)
    if matched is None:
        return [f"no fact type in record-facts.toml has this form: {line}"]
    name, spec, bindings = matched

    problems: list[str] = []
    # Placeholder bindings and keyed operands share one namespace, so a
    # conditional rule may test either.
    bound: dict[str, list[str]] = {k: [v] for k, v in bindings.items()}
    bound.update(keyed)

    allowed = set(spec.get("required", [])) | set(spec.get("optional", []))
    if spec.get("open_keys"):
        # §6.6 fixes the shape of a `<data>` attribute name even though the set
        # is open: the conversion to an `android:` attribute is defined only
        # for that shape, so a key outside it names nothing a consumer can
        # write.
        shape = re.compile(spec["open_key_pattern"])
        for key in sorted(set(keyed) - allowed):
            if not shape.fullmatch(key):
                problems.append(
                    f"{name} takes keys matching `{spec['open_key_pattern']}`, "
                    f"and `{key}` does not: {line}"
                )
    else:
        for key in sorted(set(keyed) - allowed):
            problems.append(f"{name} does not take `{key}`: {line}")
    for key in sorted(set(spec.get("required", [])) - set(keyed)):
        problems.append(f"{name} requires `{key}`: {line}")

    # A keyed operand is scalar unless the fact says otherwise. Without this,
    # `kind=activity,service` and `sha256=<a>,<b>` are well-formed facts.
    lists = set(spec.get("lists", []))
    for key in sorted(set(keyed) - lists):
        if len(keyed[key]) > 1:
            problems.append(f"{name} takes one value for `{key}`, not a list: {line}")

    for key, allowed_values in spec.get("values", {}).items():
        for value in bound.get(key, []):
            if value not in allowed_values:
                problems.append(
                    f"{name} takes {key}={'|'.join(allowed_values)}, not {value}: {line}"
                )

    for rule in spec.get("rules", []):
        field = rule["field"]
        if "required_if" in rule and satisfied(rule["required_if"], bound) and field not in keyed:
            problems.append(f"{name} requires `{field}` here: {line}")
        if "forbidden_if" in rule and satisfied(rule["forbidden_if"], bound) and field in keyed:
            problems.append(f"{name} does not take `{field}` here: {line}")

    for key in DIGEST_KEYS:
        for value in keyed.get(key, []):
            if not DIGEST.fullmatch(value):
                problems.append(
                    f"{key} is not 64 lowercase hexadecimal characters, "
                    f"which §9.3 requires: {line}"
                )

    formats = dict(FORMAT_BY_NAME)
    formats.update(spec.get("formats", {}))
    # §6.8's and §7.4's `value`, whose form its own `type` operand chooses.
    typed = spec.get("typed_value")
    if typed:
        chosen = bound.get(typed["key"], [])
        if chosen and chosen[0] in typed["formats"]:
            formats[typed["operand"]] = typed["formats"][chosen[0]]
    for operand, kind in formats.items():
        for value in bound.get(operand, []):
            problem = well_formed(kind, value)
            if problem:
                problems.append(f"`{operand}` {problem}: {line}")
    return problems


def drop_unclaimed_advisories(lines: list[str], claimed: set[str]) -> list[str]:
    """Remove operands an advisory obligation governs, unless the case claims it.

    §6.5's permission `reason` is RECOMMENDED and carrying it into the record is
    advisory S7. A fixed expected record cannot hold it unconditionally without
    failing every consumer that does not implement S7 — and §8.5 is explicit
    that an advisory is reported, never blocking. So the operand is compared
    only in a case that asks for the advisory, and is dropped from both sides
    everywhere else.
    """
    out = []
    for line in lines:
        try:
            positional, _keyed, raw = lex(line)
        except LexError:
            out.append(line)
            continue
        matched = match_template(positional)
        governed = {} if matched is None else matched[1].get("advisory_operands", {})
        operands = [
            f"{key}={raw[key]}"
            for key in sorted(raw)
            if governed.get(key) is None or governed[key] in claimed
        ]
        out.append(" ".join(positional + operands))
    return out


def elide_digests(lines: list[str]) -> list[str]:
    """Drop digest *content*, never digest syntax.

    `ignore_digests` exists so that a case about namespace collision is not also
    a test of file hashing. It is not a licence to emit `sha256=garbage`, so the
    syntax is validated in `validate_fact` before anything is elided here.

    Eliding goes through the lexer rather than over the raw text. Splitting on
    spaces would reach inside a quoted value, so a `reason` that happens to
    quote a digest would be rewritten — and two different reasons quoting two
    different digests would then compare equal, which is the opposite of what
    this is for.

    It reaches **input** hashes only. A Maven artifact's SHA-256 and a Swift
    binary target's checksum are the integrity §6.3 and §7.2 require a consumer
    to verify, and eliding those would suppress the behaviour a resolved-graph
    case exists to test.
    """
    out = []
    for line in lines:
        try:
            positional, _keyed, raw = lex(line)
        except LexError:
            out.append(line)  # invalid, and already reported as such
            continue
        elidable = len(positional) > 2 and positional[2] == "input"
        operands = [
            f"{key}=<digest>" if elidable and key in DIGEST_KEYS else f"{key}={raw[key]}"
            for key in sorted(raw)
        ]
        out.append(" ".join(positional + operands))
    return out


def compare_records(
    expected: bytes, actual: bytes, *, ignore_digests: bool, advisories: set[str]
) -> list[str]:
    """The whole comparison: two sorted sets of valid facts, diffed."""
    want, problems = read_record(expected)
    if problems:
        return [f"the case's own expected record is malformed: {p}" for p in problems]
    got, problems = read_record(actual)
    if problems:
        return problems

    for line in got:
        problems.extend(validate_fact(line))
    if problems:
        return problems

    if got != sorted(got):
        return ["the record is not in sorted order, which record-format.md §1 requires"]
    if len(set(got)) != len(got):
        return ["the record repeats a fact; each is stated exactly once"]

    want = drop_unclaimed_advisories(want, advisories)
    got = drop_unclaimed_advisories(got, advisories)
    if ignore_digests:
        want, got = elide_digests(want), elide_digests(got)

    for line in sorted(set(want) - set(got)):
        problems.append(f"missing: {line}")
    for line in sorted(set(got) - set(want)):
        problems.append(f"unexpected: {line}")
    return problems


def run_consumer(command: list[str], case: Case, outputs: Path) -> tuple[int, dict]:
    """Invoke the consumer for one case, and read what it reported.

    Two arguments: the case's `input/`, and an output directory to write what it
    produced into. The second is what lets an assertion be checked rather than
    believed — a consumer that writes its assembled payload to
    `<outputs>/payload/` has the payload assertions verified against the files
    themselves.
    """
    outputs.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [*command, str(case.input_directory), str(outputs)],
        capture_output=True,
        timeout=300,
    )
    # Strictly, not `errors="replace"`. Replacing turns invalid UTF-8 into
    # U+FFFD before the JSON is parsed, so a consumer could ship bytes this
    # interface says are UTF-8 and never hear about it — most easily in a field
    # nothing reads.
    try:
        stdout = completed.stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        return completed.returncode, {"_malformed": f"stdout is not valid UTF-8: {exc}"}
    try:
        return completed.returncode, json.loads(stdout or "{}")
    except json.JSONDecodeError:
        fallback = completed.stderr.decode("utf-8", errors="replace")
        return completed.returncode, {"_malformed": (stdout or fallback)[:400]}


def diagnostic_ids(entries: object) -> set[str]:
    return {entry["id"] for entry in entries}  # type: ignore[index]


def malformed(reported: object) -> str | None:
    """Whether the consumer's answer has the shape this interface documents.

    A response is untrusted input like any other. Reaching into it and letting
    an AttributeError escape would turn a consumer's bad output into a crash of
    the harness, where it belongs as a failed case naming what was wrong.
    """
    if not isinstance(reported, dict):
        return "the answer is not a JSON object"
    if not isinstance(reported.get("outcome", ""), str):
        return "`outcome` is not a string"
    for key in ("diagnostics", "advisories"):
        value = reported.get(key, [])
        if not isinstance(value, list):
            return f"`{key}` is not an array"
        for entry in value:
            if not isinstance(entry, dict):
                return f"`{key}` holds something that is not a finding object"
            if not isinstance(entry.get("id"), str):
                return f"a {key[:-1]} has no `id`"
            named = entry.get("distributions", [])
            if not isinstance(named, list) or any(not isinstance(d, str) for d in named):
                return f"`{entry.get('id')}` has no array of distributions"
    capabilities = reported.get("capabilities", {})
    if not isinstance(capabilities, dict) or any(
        not isinstance(v, bool) for v in capabilities.values()
    ):
        return "`capabilities` is not an object of booleans"
    if not isinstance(reported.get("outputs", ""), str):
        return "`outputs` is not a string"
    assertions = reported.get("assertions", {})
    if not isinstance(assertions, dict) or any(
        not isinstance(v, bool) for v in assertions.values()
    ):
        return "`assertions` is not an object of booleans"
    if not isinstance(reported.get("record", ""), str):
        return "`record` is not a string"
    return None


#: Assertions the harness verifies itself, against the payload a consumer wrote
#: into its output directory. Everything else in README.md's table is *attested*
#: — the consumer's own claim, which is evidence of intent and not of behaviour.
PAYLOAD_SOURCE_SUFFIXES = (".java", ".kt", ".swift")


def payload_files(outputs: Path) -> list[Path] | None:
    payload = outputs / "payload"
    if not payload.is_dir():
        return None
    return [p for p in payload.rglob("*") if p.is_file()]


def verify_sidecar_excluded(case: Case, files: list[Path]) -> str | None:
    """§4.1 requirement 6: the sidecar directory reaches no device payload."""
    offenders = [
        f for f in files if f.name == "native.toml" or "_native" in f.parts
    ]
    return None if not offenders else f"the payload carries {offenders[0].name}"


def verify_source_excluded(case: Case, files: list[Path]) -> str | None:
    """Requirement 24: contributed source is compiled, never shipped."""
    offenders = [f for f in files if f.suffix in PAYLOAD_SOURCE_SUFFIXES]
    return None if not offenders else f"the payload carries {offenders[0].name}"


def verify_module_stubs_excluded(case: Case, files: list[Path]) -> str | None:
    """§7.5: `<name>.py` and `<name>.pyi` are excluded for every registered module."""
    registered = set()
    for sidecar in case.input_directory.glob("*/*/_native/native.toml"):
        document = tomllib.loads(sidecar.read_text(encoding="utf-8"))
        for module in document.get("ios", {}).get("contributes", {}).get(
            "python_modules", []
        ):
            registered.add(module["name"])
    offenders = [
        f for f in files if f.stem in registered and f.suffix in (".py", ".pyi")
    ]
    return None if not offenders else f"the payload carries {offenders[0].name}"


VERIFIED_ASSERTIONS = {
    "sidecar_excluded_from_payload": verify_sidecar_excluded,
    "contributed_source_excluded_from_payload": verify_source_excluded,
    "python_module_stubs_excluded": verify_module_stubs_excluded,
}


def check(case: Case, exit_code: int, reported: dict, outputs: Path) -> Result:
    problems: list[str] = []
    unverified: list[str] = []
    unsupported: list[str] = []

    if isinstance(reported, dict) and "_malformed" in reported:
        return Result(case, FAIL, [f"the consumer did not answer in JSON: {reported['_malformed']}"])
    problem = malformed(reported)
    if problem:
        return Result(case, FAIL, [f"the consumer's answer is malformed: {problem}"])

    # Axis 1 — the build's fate. The JSON says; the exit status must agree.
    actual_outcome = reported.get("outcome", "")
    if actual_outcome not in ("accept", "blocking"):
        problems.append(f"outcome: {actual_outcome!r} is neither accept nor blocking")
    elif actual_outcome != case.outcome:
        problems.append(f"outcome: expected {case.outcome}, got {actual_outcome}")
    elif (exit_code != 0) != (actual_outcome == "blocking"):
        problems.append(
            f"the consumer reported {actual_outcome} and exited {exit_code}, "
            "which contradicts it"
        )

    # A case needing a stated resolution cannot be run against a consumer that
    # cannot be told one. README.md says so; this is where it takes effect.
    if (case.input_directory / "resolved.toml").exists() and not reported.get(
        "capabilities", {}
    ).get("injected_resolution", False):
        return Result(
            case,
            UNVERIFIED,
            ["the consumer cannot accept a stated resolution, which this case needs"],
        )

    # Axis 2 — findings.
    for key in ("diagnostics", "advisories"):
        expected = {entry["id"]: set(entry.get("distributions", [])) for entry in case.spec.get(key, [])}
        actual = {entry["id"]: set(entry.get("distributions", [])) for entry in reported.get(key, [])}
        for missing in sorted(set(expected) - set(actual)):
            if key == "advisories":
                unsupported.append(f"advisory {missing}: the consumer does not claim it")
            else:
                problems.append(f"{key}: expected {missing}, not reported")
        # Requirement 18: every diagnostic about declared material names the
        # contributing distribution. Naming the wrong one, or none, is the
        # failure that requirement exists to prevent — a finding nobody can act
        # on — so the corpus checks the names and not only the ids.
        for identifier, want in sorted(expected.items()):
            if identifier in actual and want and actual[identifier] != want:
                problems.append(
                    f"{identifier} names {sorted(actual[identifier]) or 'no distribution'}, "
                    f"and this case requires {sorted(want)}"
                )
        if key == "diagnostics":
            # An unexpected advisory is a consumer being more helpful than the
            # case asked for; an unexpected blocking diagnostic is not.
            for extra in sorted(set(actual) - set(expected)):
                problems.append(f"{key}: reported {extra}, which this case does not expect")

    # Axis 3 — postconditions.
    vouched = reported.get("assertions", {})
    files = payload_files(outputs)
    for assertion in case.spec.get("assertions", []):
        state = vouched.get(assertion)
        adapter = VERIFIED_ASSERTIONS.get(assertion)
        if adapter is not None:
            if files is None:
                unverified.append(
                    f"assertion {assertion}: the consumer wrote no payload to inspect"
                )
                continue
            failure = adapter(case, files)
            if failure:
                problems.append(f"assertion {assertion}: {failure}")
            elif state is False:
                problems.append(
                    f"assertion {assertion}: the consumer reports it unmet, and the "
                    "payload it wrote satisfies it"
                )
            continue
        if state is True:
            continue
        if state is None:
            unverified.append(f"assertion {assertion}: the consumer cannot observe it")
        else:
            problems.append(f"assertion {assertion}: the consumer reports it unmet")

    expected_record = case.expected_record
    if expected_record is not None:
        problems.extend(
            compare_records(
                expected_record.read_bytes(),
                reported.get("record", "").encode("utf-8"),
                ignore_digests=bool(case.spec.get("ignore_digests")),
                # The advisories the consumer actually claims, not the ones
                # the case names. An advisory operand is compared only against
                # a consumer that says it implements the obligation; §8.5 makes
                # an advisory reported and never blocking, so a consumer that
                # does not claim it leaves the case unsupported rather than
                # failing it on a record difference the advisory caused.
                advisories={
                    identifier.rsplit(".", 1)[-1]
                    for identifier in diagnostic_ids(case.spec.get("advisories", []))
                    & diagnostic_ids(reported.get("advisories", []))
                },
            )
        )

    if problems:
        return Result(case, FAIL, problems + unverified + unsupported)
    if unverified:
        return Result(case, UNVERIFIED, unverified + unsupported)
    if unsupported:
        return Result(case, UNSUPPORTED, unsupported)
    return Result(case, PASS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, action="append", required=True)
    parser.add_argument("--list", action="store_true", help="list cases and exit")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    # §8.1: conformance is "the core plus at least one platform profile". The
    # platform profiles selected are what the consumer builds, and the core
    # cases are exercised for exactly those — a core case run only against
    # Android would leave an `core + ios` claim resting on nothing.
    platforms = {p for p in args.profile if p in ("android", "ios")}
    if not platforms:
        print(
            "note: no platform profile selected, so the core cases run for both."
            "\n      §8.1 makes conformance the core plus at least one platform"
            " profile, so this is a development run rather than a claim.\n"
        )
        platforms = {"android", "ios"}
    cases = [
        case for profile in args.profile for case in load_cases(profile, platforms)
    ]
    if not cases:
        print("no cases found for the selected profile(s)")
        return 1

    if args.list:
        for case in cases:
            print(f"{case.label}  §{case.spec.get('section', '?')}  "
                  f"requirement {case.requirement}  {case.outcome}")
        return 0

    command = [part for part in args.command if part != "--"]
    if not command:
        parser.error("a consumer command is required: … -- mytool build …")

    results = []
    with tempfile.TemporaryDirectory(prefix="native-integration-conformance-") as workspace:
        for case in cases:
            outputs = Path(workspace) / case.profile / case.name / case.platform
            results.append(check(case, *run_consumer(command, case, outputs), outputs))

    for result in results:
        print(f"{result.status.upper():12} {result.case.label}"
              f"  (requirement {result.case.requirement})")
        for line in result.detail:
            print(f"             {line}")

    failed = [r for r in results if r.status == FAIL]
    unverified = [r for r in results if r.status == UNVERIFIED]
    unsupported = [r for r in results if r.status == UNSUPPORTED]
    passed = len(results) - len(failed) - len(unverified) - len(unsupported)
    print(
        f"\n{passed} passed, {len(failed)} failed, "
        f"{len(unverified)} unverified, {len(unsupported)} unsupported"
    )
    # An unverified case is a requirement nobody checked, which is not a green
    # run. An unsupported one is an advisory declined, which §8.5 says is.
    return 1 if failed or unverified else 0


if __name__ == "__main__":
    raise SystemExit(main())
