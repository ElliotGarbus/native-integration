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

from .application import Application
from .findings import Findings
from .recording import Fact, Record, RecordError, digest, parse, read

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

#: §9.1's answers, by the `decision` they are recorded as. Every one is a row of
#: §2.2's table: the application deciding something about its own build.
ANSWERED = ("approve-export", "suppress-permission", "artifact-feature", "collision")

#: The operands of a requirement fact that hold the application's answer to it.
#: The rest of the line is the producer's: that a value is declared, its `kind`,
#: the `key` it lands in, an action's `slot` and what it `uses`.
ANSWER_OPERANDS = ("state", "date", "version")


def resolution_only(line: str) -> str | None:
    """One record line reduced to what §9.1 gates, or None where it gates none.

    §9.1 splits the record in two and passes only the first half through steps
    2 to 4. The accepted resolution is *"every contribution, the hashed inputs,
    the resolved native graphs with their checksums and revisions, and the
    material resolved artifacts bring with them"*. The application's answers —
    *"supplied values, acknowledgements, dismissals, permission suppressions,
    export approvals, required-feature decisions, colliding-path choices"* — are
    *"recorded as they change"* and **MUST NOT** require acceptance of
    themselves.

    Three kinds of line come out differently:

    * a `decision` the application made is dropped. §9.1's note says why in
      terms: *"the application is the accepting party, so requiring it to accept
      its own decision would be a confirmation dialog"*, and the click-through
      §9.6 warns about is bought exactly that way. `decision credential-required`
      is not dropped — that a repository needs a credential is a fact about a
      producer's declaration (§9.5), not something the application decided.
    * an `effective` merge is dropped, because every input to it is gated
      already. A producer widening a permission moves the `contributes` line
      too, so nothing escapes the gate; a *suppression* moves only this one, and
      gating it would gate the answer a second time.
    * a value or an action keeps everything except its `state`, `date` and
      `version`. The split runs through the middle of these lines rather than
      around them: that a producer newly demands a value is a change to the
      resolution and must be accepted, and whether the application has answered
      it yet is the application's own business.

    The projection is deliberately not the identity on any answer-bearing line,
    so a record that gains an answer compares equal to the one that lacked it.
    """
    fact = parse(line)
    if fact.verb == "effective":
        return None
    if fact.verb == "decision" and fact.positionals[:1] and fact.positionals[0] in ANSWERED:
        return None
    if fact.verb == "dist" and fact.positionals[1:2] and fact.positionals[1] in ("value", "action"):
        kept = tuple((key, value) for key, value in fact.keyed if key not in ANSWER_OPERANDS)
        return Fact(fact.verb, fact.positionals, kept).render()
    return line


def gated(lines) -> set[str]:
    """The half of a record §9.1 compares, projected line by line."""
    return {kept for line in lines if (kept := resolution_only(line)) is not None}


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
    application: Application | None = None,
    distributions: Sequence[str] = (),
) -> Delta:
    """Compare, report, and refuse to build through a change nobody accepted."""
    if stored is None:
        return _first_build(record, findings, application or Application(), distributions)

    accepted = _stored_facts(stored, findings, distributions)
    if accepted is None:
        return Delta()

    # Compared as rendered lines rather than as parsed facts: the record *is*
    # its bytes, and two facts that render identically are the same fact. Both
    # sides are projected first, so what is compared is the accepted resolution
    # and not the answers §9.1 keeps out of the gate.
    now = gated(record)
    was = gated(fact.render() for fact in accepted)
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


def _first_build(
    record: Record,
    findings: Findings,
    application: Application,
    distributions: Sequence[str],
) -> Delta:
    """No stored record, which §9.1 makes step 4 rather than an exemption.

    The tempting reading is that a first build has nothing to compare against
    and so is not a change. §9.1 forecloses it: *"treating 'no record yet' as
    implicit approval does not [satisfy this], because the first build is the
    one where an application acquires all of its inherited native surface at
    once."* An exemption here is the largest one available — every permission,
    every repository, every contributed class, waved through together.

    So everything is the delta, and the application must have performed the
    bootstrap action §9.1 allows: *"a single bootstrap action covering the
    initial set satisfies this"*.

    "Everything" is the same half every other build compares. §9.1 asks for
    *"the whole effective set"* to be reported, and an application's own answers
    are not something it is being asked to accept on the first build either.
    """
    everything = Delta(added=tuple(sorted(gated(record))))
    if application.initial_acceptance is not None:
        return Delta()
    # A resolution that failed to compute is not one an application can accept.
    # §9.1's lifecycle begins by computing the resolution and the gate is step
    # 4 of it, so a build already failing validation is not "silently writing a
    # record and proceeding" — it is not proceeding at all, and a second
    # diagnostic saying so would bury the one the author can act on.
    if not findings.ok:
        return everything
    findings.requirement(
        UNACCEPTED,
        *(sorted({subject_of(line) for line in everything.added if subject_of(line)})
          or distributions or ("the application",)),
        message="this integration has never been accepted, and there is no stored record",
        where="accepted.record",
        detail=[
            *(f"+ {line}" for line in everything.added),
            "the first build is the one where an application acquires all of its "
            "inherited native surface at once",
        ],
    )
    return everything


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
