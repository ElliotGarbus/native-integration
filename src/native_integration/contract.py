"""The contract version gate (§4.3).

Three checks, not one. A consumer implementing *X.Y* rejects a different major,
rejects a greater minor, **and** rejects a sidecar that under-declares — one
using a capability introduced later than the contract it names, even when the
consumer implements both. The third is the one that is easy to leave out and
the one that keeps a producer's mis-declaration from becoming an older
consumer's problem later.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import registry

_REGISTRY = registry.load()

#: The form a `contract` value takes, as `contract/v1.toml` fixes it rather than
#: as this module remembers it. The registry's pattern refuses a leading zero;
#: a second regex here would be free to disagree, and eventually would.
_CONTRACT = re.compile(rf"\A(?:{_REGISTRY.declaration('contract')['pattern']})\Z")
_PARTS = re.compile(r"\A(\d+)(?:\.(\d+))?\Z")

#: The specification revision this library implements, from `[meta]`.
SPEC_MAJOR, SPEC_MINOR = (int(part) for part in _REGISTRY.contract.split("."))

#: The entry-point group, which carries the major version (§10).
ENTRY_POINT_GROUP = _REGISTRY.entry_point_group


@dataclass(frozen=True, order=True)
class ContractVersion:
    """A contract version: a major, and a minor that defaults to 0."""

    major: int
    minor: int = 0

    @classmethod
    def parse(cls, text: object) -> "ContractVersion":
        """Parse ``"1"`` or ``"1.1"``. Raises :class:`ValueError` otherwise."""
        if not isinstance(text, str):
            raise ValueError("contract must be a string")
        stripped = text.strip()
        if not _CONTRACT.match(stripped):
            raise ValueError(
                f"contract {text!r} is not a major, optionally with a minor — e.g. \"1\" or \"1.1\""
            )
        match = _PARTS.match(stripped)
        assert match is not None  # the registry's pattern admits nothing else
        return cls(int(match.group(1)), int(match.group(2) or 0))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"

    @property
    def canonical(self) -> str:
        """How a producer should spell it: ``"1"`` for a zero minor."""
        return str(self.major) if self.minor == 0 else f"{self.major}.{self.minor}"


#: The version this library implements, as a value.
IMPLEMENTED = ContractVersion(SPEC_MAJOR, SPEC_MINOR)

#: Every version 1 capability is 1.0: no minor revision has been issued. The
#: mechanism is here so that adding one is a `since=` on a schema field rather
#: than a new pass over the validator.
V1_0 = ContractVersion(1, 0)
