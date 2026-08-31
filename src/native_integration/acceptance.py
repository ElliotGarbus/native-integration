"""§9.1's gate: this resolution against the last one the application accepted.

§2.1 calls this the largest obligation in the document that is not about reading
a sidecar, and states the harm plainly: without it the record is a lockfile and
nothing more, and *"a transitive dependency's new permission lands in the
shipped application with a line in a report nobody had to read"*. What is
mandated is narrow — some deliberate act stands between a new native surface and
a build.

Three requirements turn on the comparison and none can be exercised in a single
run, because a delta needs a prior state. They are separated here by what the
difference *is*, not by which is noticed first: the bytes behind a coordinate
(26), a digest the stored record spells wrongly (40), and everything else (38).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .findings import Findings
from .recording import Fact, Record, RecordError, digest, read

#: §8.4, by number.
CHECKSUM = 26
UNACCEPTED = 38
MALFORMED_DIGEST = 40

#: Operands whose value is a §9.3 digest wherever they appear.
DIGEST_OPERANDS = ("sha256", "checksum")

#: Where a record pins bytes, by the fact that carries them and the operand that
#: holds the digest. §6.3 pins a resolved Maven artifact; §7.2 pins a binary
#: target, whose bytes come from a URL the package's revision does not cover.
#: The requirement over both is the same: record it, verify it on the next
#: build, fail on a mismatch.
PINNED = {"artifact": "sha256", "binary-target": "checksum"}


@dataclass(frozen=True)
class Delta:
    """What changed, in the record's own lines."""

    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.added or self.removed)


def subject_of(line: str) -> str:
    """The distribution a line concerns, or empty for an integration-wide one."""
    parts = line.split(" ", 2)
    return parts[1] if len(parts) > 1 and parts[0] == "dist" else ""


def check(
    record: Record,
    stored: str | None,
    *,
    findings: Findings,
    distributions: Sequence[str] = (),
) -> Delta:
    """Compare, report, and refuse to build through a change nobody accepted.

    A first build has nothing to compare against and is not thereby a change:
    §9.1's gate is about what the application has already seen, and an
    application seeing an integration for the first time is accepting it by
    adding the dependency.
    """
    if stored is None:
        return Delta()

    accepted = _stored_facts(stored, findings, distributions)
    if accepted is None:
        return Delta()

    # Compared as rendered lines rather than as parsed facts: the record *is*
    # its bytes, and two facts that render identically are the same fact.
    now = set(record)
    was = {fact.render() for fact in accepted}
    added = tuple(sorted(now - was))
    removed = tuple(sorted(was - now))

    # §6.3's checksum claim is a stronger statement than "something changed", so
    # it is reported as itself. A version comparison misses exactly this case: a
    # repository can serve different bytes under one version, and a moved tag
    # resolves elsewhere.
    unchanged = _checksums(added, removed, findings)
    added = tuple(line for line in added if line not in unchanged)
    removed = tuple(line for line in removed if line not in unchanged)

    delta = Delta(added=added, removed=removed)
    if delta:
        _report(delta, findings, distributions)
    return delta


def _stored_facts(
    stored: str, findings: Findings, distributions: Sequence[str]
) -> tuple[Fact, ...] | None:
    """The last accepted record, read strictly.

    §9.3 fixes one form for a digest and requires a consumer to reject a stored
    one that is not it, *rather than comparing loosely*. Comparing loosely is
    the whole point of the clause: the algorithm is already fixed, so a
    `sha256:` prefix carries nothing, and an abbreviation carries less than it
    appears to, since two records elided to different lengths cannot be compared
    at all. A consumer that accepted a twelve-character digest and matched on
    the prefix would report agreement between two records that never agreed.
    """
    try:
        facts = read(stored)
    except RecordError as problem:
        findings.requirement(
            MALFORMED_DIGEST if "hexadecimal" in str(problem) else UNACCEPTED,
            *(distributions or ("the application",)),
            message=f"the last accepted record cannot be read: {problem}",
            where="accepted.record",
        )
        return None

    malformed = False
    for fact in facts:
        keyed = dict(fact.keyed)
        for operand in DIGEST_OPERANDS:
            if operand not in keyed:
                continue
            try:
                digest(keyed[operand])
            except RecordError as problem:
                malformed = True
                findings.requirement(
                    MALFORMED_DIGEST,
                    subject_of(fact.render()) or (distributions[:1] or ("the application",))[0],
                    message=f"the last accepted record spells a digest wrongly: {problem}",
                    where=fact.render(),
                    detail=[
                        "§9.3 fixes 64 lowercase hexadecimal characters, unprefixed "
                        "and never abbreviated",
                        "comparing loosely would report agreement between two "
                        "records that never agreed",
                    ],
                )
    return None if malformed else facts


def _checksums(
    added: Sequence[str], removed: Sequence[str], findings: Findings
) -> set[str]:
    """§6.3: one coordinate, two sets of bytes. Returns the lines it claimed.

    A consumer that records a checksum and never compares has a lockfile
    documenting a guarantee it does not enforce, which is worse than not
    claiming one.
    """
    claimed: set[str] = set()
    before = _pinned_bytes(removed)
    after = _pinned_bytes(added)
    for key, (line, was) in before.items():
        if key not in after:
            continue
        now_line, now = after[key]
        claimed |= {line, now_line}
        if was == now:
            continue
        distribution, name = key
        findings.requirement(
            CHECKSUM,
            distribution,
            message=f"`{name}` resolves to different bytes than were accepted",
            where=name,
            detail=[
                f"accepted {was}",
                f"resolved {now}",
                "the version is the same, which is exactly the case a version "
                "comparison misses",
            ],
        )
    return claimed


def _pinned_bytes(lines: Sequence[str]) -> Mapping[tuple[str, str], tuple[str, str]]:
    """Every digest a record pins, keyed by the distribution and what it names."""
    found: dict[tuple[str, str], tuple[str, str]] = {}
    for line in lines:
        parts = line.split(" ")
        if len(parts) < 5 or parts[0] != "dist":
            continue
        operand = PINNED.get(parts[2])
        keyed = dict(p.split("=", 1) for p in parts[4:] if "=" in p)
        if operand and operand in keyed:
            found[(parts[1], parts[3])] = (line, keyed[operand])
    return found


def _report(delta: Delta, findings: Findings, distributions: Sequence[str]) -> None:
    """One finding for the whole delta, naming everyone it touches.

    The delta is the report §9.1 asks for, so it goes in the finding's detail
    rather than into a channel the application would have to go looking for —
    "a line in a report nobody had to read" is the failure named, not the fix.
    """
    named = sorted(
        {subject_of(line) for line in delta.added + delta.removed if subject_of(line)}
    )
    findings.requirement(
        UNACCEPTED,
        *(named or distributions or ("the application",)),
        message="the resolution differs from the last accepted record",
        where="accepted.record",
        detail=[
            *(f"+ {line}" for line in delta.added),
            *(f"- {line}" for line in delta.removed),
            "some deliberate act stands between a new native surface and a build",
        ],
    )
