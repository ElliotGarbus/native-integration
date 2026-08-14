"""Namespace containment, reserved prefixes, coordinates, and R8 patterns.

§6.1 states the containment rule once and references it everywhere, calling it
"the most likely point of divergence between two conforming implementations".
It is implemented once here for the same reason.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: §6.1 rule 4 — the bootstrap/runtime namespaces of the known Python-mobile
#: toolchains. Deliberately consumer-independent: a distribution must not be
#: able to clobber one toolchain's runtime because a different toolchain built
#: the application. A consumer adds the namespaces its own generated bootstrap
#: occupies through :class:`~native_integration.context.ConsumerProfile`.
RESERVED_NAMESPACES: tuple[str, ...] = (
    "org.kivy.android",
    "org.libsdl.app",
    "org.jnius",
    "org.renpy.android",
    "com.chaquo.python",
    "org.beeware.android",
)


def segments(namespace: str) -> tuple[str, ...]:
    return tuple(part for part in namespace.split(".") if part != "")


def contains(outer: str, inner: str) -> bool:
    """True when namespace ``outer`` contains ``inner``, per §6.1.

    Computed on dot-separated segments, never on raw strings, so
    ``org.kivy.android`` contains ``org.kivy.android.helpers`` and does not
    contain ``org.kivy.androidx``; ``PyGMA`` does not contain ``PyGMAKit``.
    """
    a, b = segments(outer), segments(inner)
    return len(b) >= len(a) and b[: len(a)] == a


def overlaps(a: str, b: str) -> bool:
    """True when either namespace contains the other — §6.1 rule 5's test."""
    return contains(a, b) or contains(b, a)


def reserved_prefix(namespace: str, extra: tuple[str, ...] = ()) -> str | None:
    """The reserved prefix ``namespace`` falls under, if any (§6.1 rule 4)."""
    for prefix in (*RESERVED_NAMESPACES, *extra):
        if contains(prefix, namespace) or contains(namespace, prefix):
            return prefix
    return None


def is_single_label(namespace: str) -> bool:
    return len(segments(namespace)) == 1


# --- Maven coordinates ------------------------------------------------------

_CHANGING = re.compile(r"-SNAPSHOT\Z", re.I)
_DYNAMIC = re.compile(r"(\+\Z|\Alatest\.|\[|\]|\(|\)|,)")


@dataclass(frozen=True)
class Module:
    """A Maven ``group:artifact`` pair."""

    group: str
    artifact: str

    @classmethod
    def parse(cls, text: str) -> "Module":
        parts = text.split(":")
        if len(parts) != 2 or not all(parts):
            raise ValueError(f"{text!r} is not group:artifact")
        return cls(*parts)

    def __str__(self) -> str:
        return f"{self.group}:{self.artifact}"


def split_coordinate(text: str) -> tuple[Module, str]:
    """``group:artifact:version`` → (module, version)."""
    parts = text.split(":")
    if len(parts) != 3 or not all(parts):
        raise ValueError(f"{text!r} is not group:artifact:version")
    return Module(parts[0], parts[1]), parts[2]


def is_changing_version(version: str) -> bool:
    """A version whose content can change under a fixed spelling (§6.5)."""
    return bool(_CHANGING.search(version.strip()))


def is_dynamic_version(version: str) -> bool:
    """``+``, ``latest.release``, or a range spelled inside a coordinate (§6.5)."""
    return bool(_DYNAMIC.search(version.strip()))


# --- R8 class patterns ------------------------------------------------------


def keep_pattern_base(pattern: str) -> str:
    """The fixed namespace prefix of a keep pattern, for containment tests.

    ``org.example.mypkg.**`` → ``org.example.mypkg``. A pattern whose wildcard
    is not at the end (``org.*.mypkg``) has no fixed base beyond the first
    wildcard, and everything after it is dropped.
    """
    out: list[str] = []
    for part in pattern.split("."):
        if "*" in part or "?" in part:
            break
        out.append(part)
    return ".".join(out)


def compile_keep_pattern(pattern: str) -> re.Pattern[str]:
    """Compile an R8 class pattern to a regex over fully qualified class names.

    ``**`` matches any characters including ``.``; ``*`` matches any characters
    except ``.``; ``?`` matches one character except ``.``. This is enough for
    §6.9, which admits class patterns only — not R8's rule grammar.
    """
    out: list[str] = []
    i = 0
    while i < len(pattern):
        char = pattern[i]
        if char == "*":
            if pattern.startswith("**", i):
                out.append(".*")
                i += 2
                continue
            out.append("[^.]*")
        elif char == "?":
            out.append("[^.]")
        else:
            out.append(re.escape(char))
        i += 1
    return re.compile("\\A" + "".join(out) + "\\Z")
