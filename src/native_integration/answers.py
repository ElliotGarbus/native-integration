"""The application's side of the contract (§2.2, requirement 8.26).

Every ``requires`` in the specification is answered by the *application*,
through the *consumer's own configuration*. This module defines the capability
a consumer must provide and deliberately not the spelling: :class:`AnswerSource`
is the shape a build tool adapts its own configuration to, and
:class:`MappingAnswers` is a working implementation for tools that have no
opinion yet, and for tests.

What is not the consumer's to choose is the **join key**. Every method below
that answers a producer-local ``id`` takes the declaring distribution as well,
because identity is the pair *(distribution, id)*: two distributions may each
declare ``client_id`` without collision, and an answer keyed on ``client_id``
alone would not say which it meant.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Mapping, Protocol, Sequence, runtime_checkable


class CredentialKind(str, enum.Enum):
    ENVIRONMENT = "env"
    FILE = "file"
    SECRET_STORE = "secret"
    LITERAL = "literal"


@dataclass(frozen=True)
class CredentialReference:
    """How the application supplies a build-time credential (§2.2, §6.6).

    §2.2 requires a consumer to accept a *reference* — an environment variable,
    an external secret store, a file outside the project — and forbids
    requiring the value to be written into a file the consumer directs the
    application to commit. A literal is permitted (a developer experimenting
    should not be blocked) and is never the only option.

    The value never reaches the integration record: §9 forbids writing an
    application-supplied credential into the record, a report, or a diagnostic,
    so this object redacts itself and :meth:`describe` names the *requirement*.
    """

    kind: CredentialKind
    username: str | None = None
    #: For ENVIRONMENT/FILE/SECRET_STORE this is a locator, not a secret. For
    #: LITERAL it is the secret itself, and nothing here ever prints it.
    locator: str | None = None
    _value: str | None = field(default=None, repr=False, compare=False)

    @classmethod
    def from_env(cls, variable: str, *, username: str | None = None) -> "CredentialReference":
        return cls(CredentialKind.ENVIRONMENT, username=username, locator=variable)

    @classmethod
    def from_file(cls, path: str, *, username: str | None = None) -> "CredentialReference":
        return cls(CredentialKind.FILE, username=username, locator=path)

    @classmethod
    def from_secret_store(cls, key: str, *, username: str | None = None) -> "CredentialReference":
        return cls(CredentialKind.SECRET_STORE, username=username, locator=key)

    @classmethod
    def literal(cls, value: str, *, username: str | None = None) -> "CredentialReference":
        return cls(CredentialKind.LITERAL, username=username, _value=value)

    @property
    def by_indirection(self) -> bool:
        return self.kind is not CredentialKind.LITERAL

    def describe(self) -> str:
        """A record-safe description: how the credential arrives, never what it is."""
        if self.kind is CredentialKind.LITERAL:
            return "configured (literal, withheld from the record)"
        return f"configured (by {self.kind.value}: {self.locator})"

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"CredentialReference({self.kind.value}, locator={self.locator!r})"


@runtime_checkable
class AnswerSource(Protocol):
    """What a consumer must be able to ask its own configuration.

    One method per row of §2.2's table. A consumer implements this over
    whatever spelling it offers; the library never sees the syntax.
    """

    # §6.3 — joined by (distribution, id)
    def application_value(self, distribution: str, value_id: str) -> str | None: ...

    # §6.7 — joined by permission name; suppression is global per permission
    def permission_suppressed(self, name: str) -> bool: ...

    # §6.8 — joined by (distribution, component name)
    def export_approved(self, distribution: str, component: str) -> bool: ...

    # §6.6 — joined by repository url
    def repository_credentials(self, url: str) -> CredentialReference | None: ...

    # §7.3 — entitlements, joined by key; presence is what v1 verifies
    def entitlement_configured(self, key: str) -> bool: ...

    # §7.3 — usage descriptions, joined by key; a non-empty value satisfies
    def usage_description(self, key: str) -> str | None: ...

    # §7.3 — application files, joined by name
    def application_file_configured(self, name: str) -> bool: ...

    # §7.3 — an extension target of that kind exists (half of app_extensions)
    def extension_target_exists(self, kind: str) -> bool: ...

    # §7.3 — acknowledgement, joined by (distribution, id)
    def acknowledged(self, distribution: str, entry_id: str) -> bool: ...

    # §7.3 — a capability key, joined by (key, value). Not distribution-scoped:
    # one application declaring `remote-notification` satisfies every producer
    # that needed it.
    def plist_capability_configured(self, key: str, value: str) -> bool: ...


def _norm(name: str) -> str:
    return name.lower().replace("_", "-")


@dataclass(frozen=True)
class MappingAnswers:
    """An :class:`AnswerSource` over plain mappings.

    Distribution keys are compared in PEP 503 normalized form, so an answer
    filed under ``Py_Stripe`` still meets a declaration from ``py-stripe``.
    """

    application_values: Mapping[str, Mapping[str, str]] = field(default_factory=dict)
    suppressed_permissions: Sequence[str] = ()
    allow_exported: Mapping[str, Sequence[str]] = field(default_factory=dict)
    #: Keyed by repository url — the join §2.2 names for a credential.
    credentials: Mapping[str, CredentialReference] = field(default_factory=dict)
    entitlements: Sequence[str] = ()
    usage_descriptions: Mapping[str, str] = field(default_factory=dict)
    application_files: Sequence[str] = ()
    extension_targets: Sequence[str] = ()
    acknowledged_ids: Mapping[str, Sequence[str]] = field(default_factory=dict)
    #: The application's own capability keys, e.g.
    #: ``{"UIBackgroundModes": ["remote-notification"]}``.
    plist_capabilities: Mapping[str, Sequence[str]] = field(default_factory=dict)

    def _per_distribution(self, table: Mapping[str, object], distribution: str):
        for key, value in table.items():
            if _norm(key) == _norm(distribution):
                return value
        return None

    def application_value(self, distribution: str, value_id: str) -> str | None:
        values = self._per_distribution(self.application_values, distribution) or {}
        supplied = values.get(value_id)  # type: ignore[union-attr]
        if supplied is None:
            return None
        # §6.3 — the supplied value is a non-empty string, and only that.
        return supplied if isinstance(supplied, str) and supplied.strip() else None

    def permission_suppressed(self, name: str) -> bool:
        return name in self.suppressed_permissions

    def export_approved(self, distribution: str, component: str) -> bool:
        approved = self._per_distribution(self.allow_exported, distribution) or ()
        return component in approved  # type: ignore[operator]

    def repository_credentials(self, url: str) -> CredentialReference | None:
        return self.credentials.get(url)

    def entitlement_configured(self, key: str) -> bool:
        return key in self.entitlements

    def usage_description(self, key: str) -> str | None:
        text = self.usage_descriptions.get(key)
        return text if isinstance(text, str) and text.strip() else None

    def application_file_configured(self, name: str) -> bool:
        return name in self.application_files

    def extension_target_exists(self, kind: str) -> bool:
        return kind in self.extension_targets

    def acknowledged(self, distribution: str, entry_id: str) -> bool:
        acked = self._per_distribution(self.acknowledged_ids, distribution) or ()
        return entry_id in acked  # type: ignore[operator]

    def plist_capability_configured(self, key: str, value: str) -> bool:
        return value in self.plist_capabilities.get(key, ())


class NoAnswers(MappingAnswers):
    """An application that has answered nothing.

    Useful for the first run of a report, where the point is to list what the
    application will have to supply.
    """
