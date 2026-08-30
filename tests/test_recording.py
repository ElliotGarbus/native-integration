"""The conformance record's serialization.

The corpus already holds forty-odd records the harness accepts, so the strongest
available check is that this module reads every one of them and writes it back
byte for byte. A serializer that agreed with the format's prose but not with the
files would pass a prose-only test and fail every case.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from native_integration import recording
from native_integration.recording import Fact, Record, RecordError

ROOT = Path(__file__).resolve().parent.parent
CONFORMANCE = ROOT / "conformance"


def _records() -> list[Path]:
    return sorted(CONFORMANCE.glob("*/*/**/*.record"))


def test_the_corpus_ships_records_to_check():
    """Most cases are blocking and carry a note instead of a record, so the set
    is small. It has to hold both kinds: an expected record is what a consumer
    must produce, and an `accepted.record` is a stored one it must read back."""
    found = _records()
    assert sum(1 for p in found if p.parent.name == "expected") >= 8
    assert sum(1 for p in found if p.name == "accepted.record") >= 6


@pytest.mark.parametrize("path", _records(), ids=lambda p: str(p.relative_to(CONFORMANCE)))
def test_every_corpus_record_round_trips_byte_for_byte(path):
    text = path.read_text(encoding="utf-8", newline="")
    facts = recording.read(text)
    assert "".join(f"{fact.render()}\n" for fact in facts) == text


@pytest.mark.parametrize("path", _records(), ids=lambda p: str(p.relative_to(CONFORMANCE)))
def test_every_corpus_record_is_a_sorted_set(path):
    """`read` enforces the file's own properties, so this is what it rejects."""
    recording.read(path.read_text(encoding="utf-8", newline=""))


# -- the lexical rules -----------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        ("plain", "plain"),
        ("com.example:sdk:1.0.0", "com.example:sdk:1.0.0"),
        ("https://maven.example.com/releases", "https://maven.example.com/releases"),
        ("has space", '"has space"'),
        ("", '""'),
        ('quote"inside', '"quote\\"inside"'),
        ("back\\slash", '"back\\\\slash"'),
        ("line\nbreak", '"line\\nbreak"'),
        ("tab\there", '"tab\\there"'),
        ("bell\x07", '"bell\\u0007"'),
        ("delete\x7f", '"delete\\u007f"'),
        ("café", "\"café\""),
    ],
)
def test_a_value_has_one_spelling(value, expected):
    """"A value that can be written bare **is** written bare; one that cannot
    **is** quoted. One spelling per value, or the sort is not deterministic"."""
    assert recording.render_scalar(value) == expected


def test_non_ascii_is_kept_rather_than_escaped():
    """"Nothing is dropped and nothing is folded — a `reason` §6.4 requires to be
    kept and attributed is kept exactly"."""
    text = "Héberge le SDK — non publié"
    assert recording.unquote(recording.render_scalar(text)) == text


@pytest.mark.parametrize(
    "value, expected",
    [
        (True, "true"),
        (False, "false"),
        (0, "0"),
        (-7, "-7"),
        (1000, "1000"),
        (1.5, "1.5"),
        (1.0, "1.0"),
        (1e30, "1000000000000000000000000000000.0"),
        (-0.25, "-0.25"),
    ],
)
def test_numbers_are_rendered_one_way(value, expected):
    """No exponent, no leading zero, and a float always carries a fraction."""
    assert recording.text_of(value) == expected


def test_a_one_member_list_is_a_scalar():
    assert Fact.of("dist", "x", groups=["com.vendor"]).render() == "dist x groups=com.vendor"
    assert (
        Fact.of("dist", "x", groups=["com.b", "com.a"]).render()
        == "dist x groups=com.a,com.b"
    )


def test_a_list_is_sorted_and_de_duplicated_over_its_serialized_form():
    rendered = Fact.of("decision", "x", withdrew=["b", "a", "b"]).render()
    assert rendered == "decision x withdrew=a,b"


def test_there_is_no_empty_list():
    with pytest.raises(RecordError):
        recording.render_list([])
    # Through `Fact.of` the operand is dropped instead, which is what the format
    # says to do where a list would be empty.
    assert Fact.of("dist", "x", groups=[]).render() == "dist x"


def test_an_absent_operand_is_omitted_rather_than_written_empty():
    assert Fact.of("dist", "x", reason=None).render() == "dist x"


def test_keyed_operands_are_sorted_and_follow_the_positionals():
    fact = Fact.of("dist", "map-sdk", "floor", "min_sdk", state="met", declared=24,
                   configured=26)
    assert fact.render() == "dist map-sdk floor min_sdk configured=26 declared=24 state=met"


def test_a_python_keyword_operand_reaches_the_format_as_kebab_case():
    fact = Fact.of("dist", "x", "contributes", "component", "C", kind="activity",
                   exported_required=True)
    assert fact.render() == "dist x contributes component C exported-required=true kind=activity"


# -- reading -----------------------------------------------------------------


def test_a_quoted_value_may_hold_a_separator():
    fact = recording.parse('dist x contributes query q kind=package reason="a, b and c"')
    assert dict(fact.keyed)["reason"] == '"a, b and c"'
    assert recording.members(dict(fact.keyed)["reason"]) == ('"a, b and c"',)


def test_a_list_splits_outside_quotes_only():
    assert recording.members('a,"b,c",d') == ("a", '"b,c"', "d")


def test_a_repeated_key_is_invalid_rather_than_a_second_value():
    with pytest.raises(RecordError):
        recording.parse("dist x kind=a kind=b")


def test_a_positional_after_a_keyed_operand_is_invalid():
    with pytest.raises(RecordError):
        recording.parse("dist x kind=a stray")


@pytest.mark.parametrize(
    "text",
    [
        "\ufeffbuild contract 1.0\n",
        "build contract 1.0",
        "build platform android\nbuild contract 1.0\n",
        "build contract 1.0\nbuild contract 1.0\n",
        "build contract 1.0\n\n",
    ],
    ids=["bom", "no-trailing-newline", "unsorted", "duplicate", "blank-line"],
)
def test_the_file_itself_has_properties_a_reader_enforces(text):
    with pytest.raises(RecordError):
        recording.read(text)


def test_a_record_is_written_as_a_sorted_set():
    record = Record()
    record.add("build", "platform", "android")
    record.add("build", "contract", "1.0")
    record.add("build", "contract", "1.0")
    assert record.render() == "build contract 1.0\nbuild platform android\n"
    assert len(record) == 2


def test_an_empty_record_is_empty_rather_than_a_blank_line():
    assert Record().render() == ""


# -- normalization -----------------------------------------------------------


@pytest.mark.parametrize(
    "name, expected",
    [("Py_Stripe", "py-stripe"), ("py.stripe", "py-stripe"), ("PY--STRIPE", "py-stripe")],
)
def test_a_distribution_name_is_normalized(name, expected):
    assert recording.normalize_name(name) == expected


def test_a_digest_is_unprefixed_and_never_abbreviated():
    full = "3de10e32e5acdc2e46c4a3b55a1263a3a0547188407fb799d39df73e5e2b0a5a"
    assert recording.digest(f"sha256:{full}") == full
    assert recording.digest(full) == full
    with pytest.raises(RecordError):
        recording.digest(full[:16])
    with pytest.raises(RecordError):
        recording.digest(full.upper())


def test_a_malformed_digest_survives_the_read_and_fails_the_interpretation():
    """`core/R40_stored_digest_malformed` ships an abbreviated digest on purpose.
    The line is well-formed, so reading the file must not reject it; §9.3's rule
    is about what the operand means, and bites when the fact is interpreted."""
    path = (
        CONFORMANCE / "core" / "R40_stored_digest_malformed" / "input" / "android"
        / "accepted.record"
    )
    facts = recording.read(path.read_text(encoding="utf-8", newline=""))
    abbreviated = [
        value
        for fact in facts
        for key, value in fact.keyed
        if key == "sha256" and len(value) != 64
    ]
    assert abbreviated
    for value in abbreviated:
        with pytest.raises(RecordError):
            recording.digest(value)


def test_a_path_is_normalized_and_may_not_escape():
    assert recording.normalize_path("./java/com/Example.java") == "java/com/Example.java"
    assert recording.normalize_path("java\\com\\Example.java") == "java/com/Example.java"
    with pytest.raises(RecordError):
        recording.normalize_path("../elsewhere.java")


def test_the_worked_example_is_reproduced_from_facts():
    """record-format.md §5's example, built through the API rather than quoted."""
    record = Record()
    record.add("build", "contract", "1.0")
    record.add("build", "platform", "android")
    record.add("dist", "examplytics", "contract", "1")
    record.add("dist", "examplytics", "version", "1.0.0")
    record.add("dist", "examplytics", "origin", "direct")
    record.add("dist", "examplytics", "owns", "java-namespace", "org.example.analytics")
    record.add(
        "dist", "examplytics", "floor", "min_sdk", configured=26, declared=24, state="met"
    )
    record.add(
        "dist", "examplytics", "floor", "compile_sdk", configured=35, declared=35,
        state="met",
    )
    record.add(
        "dist", "examplytics", "value", "analytics_key",
        key="com.example.analytics.API_KEY", kind="manifest_meta_data", state="supplied",
    )
    record.add(
        "dist", "examplytics", "contributes", "permission",
        "android.permission.INTERNET", reason="Event delivery",
    )
    record.add(
        "dist", "examplytics", "contributes", "source",
        "java/org/example/analytics/Bridge.java",
    )
    record.add(
        "dist", "examplytics", "input", "java/org/example/analytics/Bridge.java",
        sha256="22ea0ee0c3006cac66f6d0240d32ac4c3dc6828179de7084d34c6ba3adce2836",
    )
    record.add(
        "dist", "examplytics", "input", "native.toml",
        sha256="3de10e32e5acdc2e46c4a3b55a1263a3a0547188407fb799d39df73e5e2b0a5a",
    )

    expected = (
        CONFORMANCE / "core" / "R01_dependency_closure" / "expected" / "android.record"
    ).read_text(encoding="utf-8", newline="")
    assert record.render() == expected
