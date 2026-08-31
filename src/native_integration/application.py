"""The application's side of the contract (§2.2, requirement 10).

Every `requires` in the specification is answered by the *application*, through
the consumer's own configuration. §2.2 fixes the capability a consumer must
offer and deliberately not its syntax, so this is a neutral model a build tool
adapts its own spelling into. Nothing here reads a file.

What is not the consumer's to choose is the **join key**. Requirement 10 names
one per row of §2.2's table, and four of them are joined by something other than
`(distribution, id)` — a permission by its name, an export by the component
class, a credential by the URL, a colliding path by the path — and those "apply
to every contributor of the name or path they address". Keeping the join in the
lookup rather than at each call site is what makes that hold.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Mapping

#: §9.5: a credential's value never reaches a record, a report or a diagnostic.
#: What is recordable is that one is *required*, which is a fact about the
#: integration rather than a secret.
REDACTED = "«withheld»"


def normalize_name(name: str) -> str:
    """§1's normalized distribution name — PEP 503, lowercased, runs collapsed."""
    return re.sub(r"[-_.]+", "-", name).lower()


def url_identity(url: str) -> tuple[str, str]:
    """What makes two repository or package URLs the same one (§6.4).

    "Repository identity is the `url`, compared with its scheme
    case-insensitively and the rest byte-for-byte; a consumer **MUST NOT**
    normalize further, since a trailing path segment is a different
    repository." §7.2 imports the rule for a Swift package: its `url` is an
    https URL "on §6.4's terms", and every rule §6.4 states about an
    authenticated repository holds there too.

    Both halves matter. Folding case across the whole URL would merge two
    repositories that differ only in a path segment's case, which §6.4 says are
    different repositories; comparing raw strings splits one repository into
    two over a scheme nobody types consistently.
    """
    scheme, separator, rest = url.partition("://")
    return (scheme.lower(), rest) if separator else ("", url)


@dataclass(frozen=True)
class Answer:
    """An answer the application gave, and the date §9.6 records it against."""

    date: str = ""


@dataclass(frozen=True)
class Approval(Answer):
    """§6.6's export approval. Absent approval is pending, not refusal."""

    approved: bool = False


@dataclass(frozen=True)
class FeatureDecision(Answer):
    """§9.4's decision on a resolved artifact's `required="true"` feature."""

    keep: str = ""


@dataclass(frozen=True)
class PackagingChoice(Answer):
    """§9.7's choice of which artifact supplies a colliding packaged path."""

    artifact: str = ""


@dataclass(frozen=True)
class Credential:
    """How a build-time credential arrives, never what it is.

    §2.2 requires a consumer to accept a *reference* — an environment variable,
    a secret store, a file outside the project — and forbids requiring the value
    to be written into a file it directs the application to commit. A literal is
    permitted, and is never the only option.
    """

    kind: str = "env"
    locator: str = ""
    username: str = ""

    @property
    def by_indirection(self) -> bool:
        return self.kind != "literal"

    def __repr__(self) -> str:  # pragma: no cover - keeps a value out of a trace
        return f"Credential(kind={self.kind!r}, locator={self.locator!r})"


@dataclass(frozen=True)
class Application:
    """The application's configuration, and every answer it has given."""

    #: §5.1's Android floors, by key — `min_sdk`, `compile_sdk`, `target_sdk`.
    android: Mapping[str, int] = field(default_factory=dict)
    #: §5.1's iOS floor, as the application configures it.
    deployment_target: str = ""
    #: The date the build is being made on, for a decision the consumer makes
    #: itself (§9.7's packaging metadata). Told rather than read off the clock:
    #: a record carrying today's date differs from yesterday's for no reason,
    #: and §9.1's gate would report a change that is not one.
    date: str = ""
    core_library_desugaring: bool = False

    #: What the application sets itself in the two key spaces it shares with
    #: producers: §6.8's `<meta-data>` and §7.4's `Info.plist`. Not answers —
    #: the application configures these for its own reasons and owes nobody a
    #: justification — but a producer contributing the same key is a conflict
    #: only the consumer can see, and §6.8 and §7.4 both resolve it the same
    #: way: "the application's own value always wins".
    manifest_meta_data: Mapping[str, object] = field(default_factory=dict)
    info_plist: Mapping[str, object] = field(default_factory=dict)

    #: §9.1's bootstrap action: the application has accepted an integration it
    #: has no stored record for. Absent means it has not, which is a first build
    #: and blocks — "the first build is step 4, not an exemption". This is an
    #: answer rather than a fact about the integration, so it never reaches the
    #: record: a record that changed on being accepted could not be compared
    #: against the thing that was accepted.
    initial_acceptance: Answer | None = None

    # -- joined by (distribution, id) --------------------------------------
    values: Mapping[tuple[str, str], str] = field(default_factory=dict)
    acknowledged: Mapping[tuple[str, str], Answer] = field(default_factory=dict)
    dismissed: Mapping[tuple[str, str], Answer] = field(default_factory=dict)

    # -- joined by something else, and applying to every contributor -------
    suppressed_permissions: Mapping[str, Answer] = field(default_factory=dict)
    exported_components: Mapping[str, Approval] = field(default_factory=dict)
    credentials: Mapping[str, Credential] = field(default_factory=dict)
    artifact_features: Mapping[str, FeatureDecision] = field(default_factory=dict)
    packaging_choices: Mapping[str, PackagingChoice] = field(default_factory=dict)

    # -- lookups -----------------------------------------------------------

    def value(self, distribution: str, identifier: str) -> str | None:
        """A supplied value, or `None`. An empty string is not an answer."""
        held = self.values.get((normalize_name(distribution), identifier))
        return held if isinstance(held, str) and held.strip() else None

    def acknowledgement(self, distribution: str, identifier: str) -> Answer | None:
        return self.acknowledged.get((normalize_name(distribution), identifier))

    def dismissal(self, distribution: str, identifier: str) -> Answer | None:
        return self.dismissed.get((normalize_name(distribution), identifier))

    def suppression(self, permission: str) -> Answer | None:
        return self.suppressed_permissions.get(permission)

    def export(self, component: str) -> Approval:
        """§6.6, joined by the component class and applying to every contributor."""
        return self.exported_components.get(component, Approval())

    def credential(self, url: str) -> Credential | None:
        """§2.2's join, on §6.4's identity rather than on the raw string.

        The answer is keyed by the repository or package `url`, and §6.4 fixes
        what makes two of those the same one: the scheme compared
        case-insensitively, the rest byte for byte. An application answering
        `https://` for a sidecar that wrote `HTTPS://` has answered — matching
        the strings would tell it otherwise, and the diagnostic it would then
        read says its credentials are not configured when they are.
        """
        wanted = url_identity(url)
        for offered, credential in self.credentials.items():
            if url_identity(offered) == wanted:
                return credential
        return None

    def artifact_feature(self, name: str) -> FeatureDecision | None:
        return self.artifact_features.get(name)

    def packaging_choice(self, path: str) -> PackagingChoice | None:
        return self.packaging_choices.get(path)

    # -- floors ------------------------------------------------------------

    def configured_floor(self, key: str) -> int | str | bool | None:
        """What the application configures for one floor key, or `None`."""
        if key == "deployment_target":
            return self.deployment_target or None
        if key == "core_library_desugaring":
            return self.core_library_desugaring
        return self.android.get(key)


def version_parts(text: str) -> tuple[int, ...]:
    """§5.1's `deployment_target`, compared component-wise and numerically.

    Absent components read as zero, so `16` and `16.0.0` are the same floor.
    """
    return tuple(int(part) for part in text.split(".") if part != "")


def meets(declared: object, configured: object, key: str) -> bool:
    """Whether a configuration satisfies a declared floor.

    A consumer never raises the application's configuration to satisfy a floor
    (requirement 12), so this only answers the question.
    """
    if configured is None:
        return False
    if key == "deployment_target":
        want = version_parts(str(declared))
        have = version_parts(str(configured))
        width = max(len(want), len(have))
        return have + (0,) * (width - len(have)) >= want + (0,) * (width - len(want))
    if isinstance(declared, bool):
        return bool(configured) is declared
    return isinstance(configured, int) and not isinstance(configured, bool) and (
        configured >= int(declared)  # type: ignore[arg-type]
    )
