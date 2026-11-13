"""Whether a §-citation says which section it points at.

Split out of `check_spec.py` so it can be tested directly. A checker nobody
tests is a checker that quietly stops catching things — which is the exact
failure it was written to prevent, one level up: `check_spec.py` verified that
every key an example used appeared *somewhere* in the specification, and five
stale citations survived it because appearing somewhere is not the claim.

A bare `§6.8` asserts only that a section numbered 6.8 exists, so that is all a
checker can verify from it. The rule here is therefore that a citation names its
section, and the pair is then verifiable exactly.

Deriving the subject instead was tried and abandoned: `contract/v1.toml` maps
every declaration to its anchor, but the leaf names are ordinary words —
`value`, `action`, `package`, `requirement` — so "this line mentions a
declaration" fired on 10 of 22 lines that were correct. A check that cries wolf
on correct input teaches people to write around it.

The real mechanism is not the checker. Writing the title beside the number makes
the author read the title, which is where a wrong number becomes obvious.
"""

from __future__ import annotations

import re
from typing import Iterator, Mapping, NamedTuple

CITATION = re.compile(r"§(\d+(?:\.\d+)*)")
HEADING = re.compile(r"^#{2,4} (\d+(?:\.\d+)*)\.? (.+)$", re.M)

#: Characters of slack allowed between a citation and its section's title.
#:
#: The title has to sit *beside* the number rather than merely near it. A word
#: like "values" turning up somewhere in three lines of comment is ordinary
#: prose; the same word touching `§5.2` is a deliberate claim, and only the
#: second is evidence that the author checked.
#:
#: Twenty is measured rather than chosen: it leaves 32 of the 35 citations in
#: the live examples untouched, and the three it rejects read better reworded.
NEARBY = 20


class Problem(NamedTuple):
    line: int
    number: str
    #: The heading the citation should have named, or `None` when the section
    #: does not exist at all.
    title: str | None

    def render(self, where: str) -> str:
        if self.title is None:
            return f"{where}:{self.line} cites §{self.number}, which SPEC.md does not have"
        return (
            f"{where}:{self.line} cites §{self.number} and the file never says which "
            f"section that is — write `{self.title}` beside the first mention, or "
            f"fix the number"
        )


def sections(document: str) -> dict[str, str]:
    """Every numbered heading, as `{"6.6": "Manifest components"}`."""
    return {m.group(1): m.group(2).strip() for m in HEADING.finditer(document)}


def spelled(text: str) -> str:
    """Fold the differences between a heading and the same words in a sentence.

    Punctuation goes, so `Objective-C` survives being written `Objective C`. So
    do possessives, because `Objective-C's categories` is a natural way to name
    the section and refusing it would be the checker dictating prose for no
    gain — the author still had to read the title to write it.
    """
    return re.sub(r"[^a-z0-9]+", " ", re.sub(r"['\u2019]s\b", "", text.lower())).strip()


def names_it(context: str, marker: str, title: str) -> bool:
    """Whether `title` sits beside `marker` in `context`, within `NEARBY`."""
    at = context.find(marker)
    if at < 0:
        return False
    # The title's own length is added to the reach so that a long heading is not
    # penalized for being long — the slack is the gap between the two, not the
    # span they occupy together.
    reach = NEARBY + len(title)
    beside = context[max(0, at - reach) : at + len(marker) + reach]
    return spelled(title) in spelled(beside)


def unnamed(text: str, known: Mapping[str, str]) -> Iterator[Problem]:
    """Citations in `text` that never say which section they mean.

    Once per file, not once per citation. A file that has already said which
    section §5.5 is may go on referring to it by number, and requiring the title
    at every mention would only produce prose written for the checker. What this
    buys is that every section a file points at is introduced by name exactly
    once, which is the point at which a stale number is visible.
    """
    lines = text.splitlines()
    introduced: set[str] = set()
    pending: dict[str, Problem] = {}

    for index, line in enumerate(lines):
        for number in CITATION.findall(line):
            if number not in known:
                yield Problem(index + 1, number, None)
                continue
            if number in introduced:
                continue
            # Three lines rather than one, so that a title and a number split
            # by a line break still count. `names_it` then requires them to be
            # adjacent within those lines, so the extra lines buy tolerance for
            # wrapping and nothing else.
            context = " ".join(lines[max(0, index - 1) : index + 2])
            if names_it(context, f"§{number}", known[number]):
                introduced.add(number)
                pending.pop(number, None)
            else:
                pending.setdefault(number, Problem(index + 1, number, known[number]))

    yield from (pending[number] for number in sorted(pending))
