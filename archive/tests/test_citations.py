"""The §-citation rule `check_spec.py` holds the live examples to.

Written because the check this one replaced passed on all five citations it was
supposed to catch. Asserting that the current check is green against the current
examples would repeat that mistake exactly — a check is only worth what it
rejects, so most of this file is inputs it must reject.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import citations  # noqa: E402

SPEC = """
## 5. Requirements on the application
### 5.2 Values
### 5.5 Value kinds
### 6.6 Manifest components
### 6.8 Manifest meta-data
### 7.6 Objective-C categories
"""

SECTIONS = citations.sections(SPEC)


def complaints(text: str) -> list[tuple[str, str | None]]:
    return [(found.number, found.title) for found in citations.unnamed(text, SECTIONS)]


def test_the_headings_are_read_with_their_numbers():
    assert SECTIONS["6.6"] == "Manifest components"
    assert SECTIONS["5"] == "Requirements on the application"


# --- what it must reject ----------------------------------------------------

def test_a_citation_that_never_says_which_section_it_means():
    assert complaints("# see §6.6 for this") == [("6.6", "Manifest components")]


def test_the_bug_this_was_written_for_a_real_section_and_the_wrong_one():
    """`view_links` is §6.6. Citing §6.8 — which exists, and is meta-data — is
    what the previous check could not see."""
    assert complaints("# Chosen to test §6.8's `view_links`") == [
        ("6.8", "Manifest meta-data")
    ]


def test_a_section_that_does_not_exist_reports_no_title():
    assert complaints("# an unrecognized selector (§9.9)") == [("9.9", None)]


def test_naming_a_different_section_than_the_one_cited_does_not_excuse_it():
    assert complaints("# manifest components are governed by §6.8") == [
        ("6.8", "Manifest meta-data")
    ]


def test_a_near_miss_on_the_title_is_not_a_match():
    """Singular where the heading is plural. Tempting to normalize away, and
    not worth it: the whole value here is that the author read the title."""
    assert complaints("# an exported manifest component (§6.6)") == [
        ("6.6", "Manifest components")
    ]


# --- what it must accept ----------------------------------------------------

@pytest.mark.parametrize("line", [
    "# §6.6 (Manifest components) governs this",
    "# the manifest components of §6.6",
    "# --- approving an exported component (§6.6, Manifest components) ---",
    "# MANIFEST COMPONENTS, §6.6",
])
def test_a_citation_beside_its_title_in_any_order_or_case(line):
    assert complaints(line) == []


def test_punctuation_between_the_title_and_the_number_is_ignored():
    assert complaints("# §7.6 — Objective-C's categories — matter here") == []


def test_a_line_break_between_the_title_and_the_number_is_tolerated():
    """Prose wraps, and the pair should not have to be rewritten around that."""
    assert complaints("# the rules on Objective-C\n# categories (§7.6) apply\n") == []


def test_a_title_a_sentence_away_no_longer_vouches_for_the_number():
    """The tightening that adjacency bought. A title somewhere in three lines of
    comment is ordinary prose; a title touching the number is a claim."""
    assert complaints(
        "# Static libraries with Objective-C categories; without this the linker\n"
        "# drops them and the SDK dies on an unrecognized selector (§7.6).\n"
    ) == [("7.6", "Objective-C categories")]


def test_a_title_three_lines_away_is_far_too_far():
    """Otherwise one long comment block underwrites every number inside it."""
    assert complaints(
        "# Objective-C categories\n#\n#\n# and so §7.6 applies\n"
    ) == [("7.6", "Objective-C categories")]


def test_an_incidental_word_elsewhere_in_the_window_does_not_vouch():
    """The case adjacency exists for: §5.2 is `Values`, and a comment about
    something else entirely may say `values` in passing."""
    assert complaints(
        "# the application supplies these values in its own configuration\n"
        "# and the join is described elsewhere; see also §5.2\n"
    ) == [("5.2", "Values")]


def test_a_section_named_once_may_then_be_cited_by_number():
    assert complaints(
        "# §6.6, Manifest components, is the rule\n"
        "# ... much later ...\n"
        "# as §6.6 requires\n"
        "# and again, §6.6\n"
    ) == []


def test_naming_it_after_the_fact_still_counts():
    """The introduction does not have to come first — a file that cites §6.6
    twice and names it on the second is still a file that says what it means."""
    assert complaints("# as §6.6 requires\n# ...\n# §6.6, Manifest components\n") == []


def test_one_complaint_per_section_rather_than_per_mention():
    assert complaints("# §6.6\n# §6.6\n# §6.6\n") == [("6.6", "Manifest components")]


def test_a_file_citing_nothing_is_not_a_problem():
    assert complaints("contract = \"1\"\n") == []
