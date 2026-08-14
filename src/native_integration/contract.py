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

_CONTRACT = re.compile(r"\A(\d+)(?:\.(\d+))?\Z")

#: The specification revision this library implements.
SPEC_MAJOR = 1
SPEC_MINOR = 0

#: The entry-point group, which carries the major version (§10).
ENTRY_POINT_GROUP = f"native_integration.v{SPEC_MAJOR}"


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
        match = _CONTRACT.match(text.strip())
        if not match:
            raise ValueError(
                f"contract {text!r} is not a major, optionally with a minor — e.g. \"1\" or \"1.1\""
            )
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
