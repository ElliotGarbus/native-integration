"""Requirement 42: a supplied credential is never persisted, anywhere.

`Credential.__repr__` was documented -- in a code comment and in
docs/REQUIREMENTS.md's structural claim for 42 -- as keeping the locator out of
a traceback. It printed it. For `kind = "literal"` the locator is the secret,
so a stack trace in a CI log was the persistence the requirement forbids.
"""

from __future__ import annotations

from native_integration import Credential
from native_integration.application import REDACTED


def test_a_literal_credential_never_appears_in_its_repr():
    secret = "sk_live_4f2c19THISISTHESECRET"
    held = Credential(kind="literal", locator=secret)
    for rendered in (repr(held), str(held), f"{held}", f"{held!r}"):
        assert secret not in rendered
        assert REDACTED in rendered


def test_an_indirect_locator_is_withheld_too():
    """An environment variable's name is harmless; a rule with an exception is
    a rule that gets the exception wrong."""
    assert "VENDOR_TOKEN" not in repr(Credential(kind="env", locator="VENDOR_TOKEN"))


def test_the_kind_is_still_visible():
    """What a trace needs is *how* the credential arrives, which is the whole
    of what §2.2 makes a consumer accept."""
    assert "'literal'" in repr(Credential(kind="literal", locator="x"))
    assert Credential(kind="literal", locator="x").by_indirection is False
