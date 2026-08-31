"""The integration record, in the one serialization two consumers can diff.

§9 mandates what a record must contain and deliberately not how it is written.
`conformance/record-format.md` fixes one projection of it for comparison, and
this module emits and reads that projection. Nothing here is normative to
SPEC.md; where the two disagree, SPEC.md governs.

The file is the sorted set of its facts, so a fact is a value and a record is a
set of them. Both directions are here because §9.1's acceptance gate compares a
newly computed record against a stored one, which means reading one back.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Iterable, Iterator, Mapping, Sequence

#: A scalar that needs no quoting, from record-format.md's `bare` production.
BARE = re.compile(r"[A-Za-z0-9._:/@+~*-]+")

#: The characters that carry a short escape; everything else below 0x20, and
#: 0x7F, is written `\uXXXX` with lowercase hex.
_SHORT = {'"': '\\"', "\\": "\\\\", "\n": "\\n", "\t": "\\t", "\r": "\\r"}
_UNESCAPE = {'"': '"', "\\": "\\", "n": "\n", "t": "\t", "r": "\r"}


class RecordError(ValueError):
    """A record line this format does not admit."""


Scalar = str | int | float | bool


def render_scalar(value: Scalar) -> str:
    """One value, in the one spelling this format gives it."""
    return _quote(text_of(value))


def text_of(value: Scalar) -> str:
    """A value's text, with numbers rendered canonically.

    Without a fixed rendering `1`, `+1`, `01` and `1_000` are four spellings of
    one TOML integer, and §6.8's equality "by type as well as content" has
    nothing to compare.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        # No exponent, and always a fractional part.
        text = format(Decimal(repr(value)), "f")
        return text if "." in text else text + ".0"
    return str(value)


def _quote(text: str) -> str:
    if text and BARE.fullmatch(text):
        return text
    out = ['"']
    for character in text:
        if character in _SHORT:
            out.append(_SHORT[character])
        elif ord(character) < 0x20 or ord(character) == 0x7F:
            out.append(f"\\u{ord(character):04x}")
        else:
            out.append(character)
    out.append('"')
    return "".join(out)


def render_list(values: Iterable[Scalar]) -> str:
    """A list operand: sorted over the serialized form, de-duplicated.

    Serialized rather than decoded, because the file's own ordering is over
    serialized lines and the two disagree wherever an escape is involved.
    """
    members = sorted({render_scalar(value) for value in values})
    if not members:
        raise RecordError("there is no empty list; omit the operand instead")
    return ",".join(members)


@dataclass(frozen=True)
class Fact:
    """One line: a verb, its positional operands, then its keyed ones."""

    verb: str
    positionals: tuple[str, ...]
    keyed: tuple[tuple[str, str], ...]

    @classmethod
    def of(
        cls,
        verb: str,
        *positionals: Scalar,
        verbatim: Mapping[str, Scalar | Sequence[Scalar] | None] | None = None,
        **keyed: Scalar | Sequence[Scalar] | None,
    ) -> "Fact":
        """Build a fact, dropping any operand whose value is absent.

        An operand spelled `None` is omitted rather than written empty, which is
        what lets a caller pass an optional field through without a conditional
        at every call site. Every key this format names itself is kebab-case, so
        a Python keyword's `_` becomes `-`.

        `verbatim` is for the one place that would be wrong. A `view-link`'s
        `<data>` attributes are the sidecar's own spelling — `path_prefix`, not
        `path-prefix` — because a record must not depend on §6.6's conversion to
        an `android:` name having been performed, and re-spelling them here
        would be performing half of it.
        """
        rendered: list[tuple[str, str]] = []
        pairs = [(name.replace("_", "-"), value) for name, value in keyed.items()]
        pairs.extend((verbatim or {}).items())
        for key, value in pairs:
            if value is None:
                continue
            if isinstance(value, (list, tuple, set, frozenset)):
                members = [v for v in value if v is not None]
                if not members:
                    continue
                rendered.append((key, render_list(members)))
            else:
                rendered.append((key, render_scalar(value)))
        return cls(
            verb=verb,
            positionals=tuple(render_scalar(p) for p in positionals),
            keyed=tuple(sorted(rendered)),
        )

    def render(self) -> str:
        parts = [self.verb, *self.positionals]
        parts.extend(f"{key}={value}" for key, value in self.keyed)
        return " ".join(parts)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.render()


@dataclass
class Record:
    """A record under construction: the set of its facts."""

    facts: set[str] = field(default_factory=set)

    def add(self, verb: str, *positionals: Scalar, **keyed: Any) -> None:
        self.facts.add(Fact.of(verb, *positionals, **keyed).render())

    def extend(self, lines: Iterable[str]) -> None:
        self.facts.update(lines)

    def render(self) -> str:
        """The file: bytewise sorted, one fact per line, trailing newline."""
        if not self.facts:
            return ""
        return "".join(f"{line}\n" for line in sorted(self.facts))

    def __contains__(self, line: str) -> bool:  # pragma: no cover - convenience
        return line in self.facts

    def __iter__(self) -> Iterator[str]:
        return iter(sorted(self.facts))

    def __len__(self) -> int:
        return len(self.facts)


# -- reading one back ------------------------------------------------------


def parse(line: str) -> Fact:
    """One line back into a fact, for §9.1's comparison against a stored record."""
    tokens = _split(line, " ")
    if not tokens:
        raise RecordError("the line is empty")
    verb, *rest = tokens
    positionals: list[str] = []
    keyed: list[tuple[str, str]] = []
    for token in rest:
        if not token.startswith('"') and "=" in token:
            key, _, value = token.partition("=")
            if any(key == held for held, _ in keyed):
                raise RecordError(f"`{key}` appears twice; that is invalid, not a second value")
            keyed.append((key, value))
            continue
        if keyed:
            raise RecordError("every positional operand precedes every keyed one")
        positionals.append(token)
    return Fact(verb=verb, positionals=tuple(positionals), keyed=tuple(keyed))


def _split(text: str, separator: str) -> list[str]:
    """Split on a separator outside quotes, so a quoted value may hold one."""
    tokens: list[str] = []
    current: list[str] = []
    quoted = False
    escaped = False
    for character in text:
        if escaped:
            current.append(character)
            escaped = False
            continue
        if quoted and character == "\\":
            current.append(character)
            escaped = True
            continue
        if character == '"':
            quoted = not quoted
            current.append(character)
            continue
        if character == separator and not quoted:
            if current:
                tokens.append("".join(current))
                current = []
            continue
        current.append(character)
    if quoted:
        raise RecordError("a quoted value is not closed")
    if current:
        tokens.append("".join(current))
    return tokens


def members(value: str) -> tuple[str, ...]:
    """A keyed operand's members. A one-member list is a scalar."""
    return tuple(_split(value, ","))


def unquote(value: str) -> str:
    """A serialized scalar back to its text."""
    if not value.startswith('"'):
        return value
    if not value.endswith('"') or len(value) < 2:
        raise RecordError(f"{value} is not a closed quoted scalar")
    body = value[1:-1]
    out: list[str] = []
    index = 0
    while index < len(body):
        character = body[index]
        if character != "\\":
            out.append(character)
            index += 1
            continue
        index += 1
        if index >= len(body):
            raise RecordError("a trailing backslash is not an escape")
        marker = body[index]
        if marker in _UNESCAPE:
            out.append(_UNESCAPE[marker])
            index += 1
        elif marker == "u":
            digits = body[index + 1 : index + 5]
            if len(digits) != 4 or not re.fullmatch(r"[0-9a-f]{4}", digits):
                raise RecordError(f"\\u{digits} is not four lowercase hex digits")
            out.append(chr(int(digits, 16)))
            index += 5
        else:
            raise RecordError(f"\\{marker} is not an escape this format defines")
    return "".join(out)


def read(text: str) -> tuple[Fact, ...]:
    """A whole record, checked for the properties the file itself must have."""
    if text.startswith("\ufeff"):
        raise RecordError("a record carries no BOM")
    if text and not text.endswith("\n"):
        raise RecordError("every line ends with a newline, including the last")
    lines = text.split("\n")[:-1] if text else []
    if any(not line for line in lines):
        raise RecordError("a record holds no blank line")
    if list(lines) != sorted(lines):
        raise RecordError("a record is sorted bytewise over the whole file")
    if len(set(lines)) != len(lines):
        raise RecordError("a fact appears exactly once; a duplicate line is invalid")
    return tuple(parse(line) for line in lines)


def digest(value: str) -> str:
    """§9.3's form: 64 lowercase hex, unprefixed, never abbreviated."""
    bare = value.split(":", 1)[1] if value.startswith("sha256:") else value
    if not re.fullmatch(r"[0-9a-f]{64}", bare):
        raise RecordError(f"{value!r} is not 64 lowercase hexadecimal characters")
    return bare


def normalize_name(name: str) -> str:
    """§1's normalized distribution name — PEP 503, lowercased, runs collapsed."""
    return re.sub(r"[-_.]+", "-", name).lower()


def normalize_path(path: str) -> str:
    """Forward slashes, relative to the sidecar directory, no `./` prefix."""
    parts = [p for p in path.replace("\\", "/").split("/") if p not in (".", "")]
    if any(part == ".." for part in parts):
        raise RecordError(f"{path!r} escapes the sidecar directory")
    return "/".join(parts)
