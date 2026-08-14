"""What the consumer and the application bring to the read.

The specification is careful about which party each fact belongs to, and these
two objects keep that split visible in the API: a :class:`ConsumerProfile`
describes the build tool, an :class:`Application` describes the app being
built. Nothing in a sidecar can change either.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from .answers import AnswerSource, MappingAnswers
from .contract import IMPLEMENTED, ContractVersion


@dataclass(frozen=True)
class ConsumerProfile:
    """The consuming build tool's own facts."""

    name: str = "consumer"
    #: The contract this consumer implements (§4.3). A sidecar declaring a
    #: different major, or a greater minor, is rejected with a message naming
    #: the contract that would work.
    contract: ContractVersion = IMPLEMENTED
    #: Namespaces the consumer's own generated bootstrap occupies, added to
    #: §6.1 rule 4's consumer-independent list.
    reserved_namespaces: tuple[str, ...] = ()
    #: ``Info.plist`` keys the consumer manages itself; a producer setting one
    #: is an error rather than a silent overwrite (§7.6).
    managed_plist_keys: frozenset[str] = frozenset()
    #: Gradle configurations this consumer implements. Version 1 defines only
    #: ``implementation``; a consumer must reject a value it does not
    #: implement rather than treat it as the default (§6.5).
    gradle_configurations: frozenset[str] = frozenset({"implementation"})
    #: Whether declared resources are read from disk. A real build **must**
    #: leave this on: §4.1's containment and symlink rules, §6.1 rule 1's check
    #: that contributed source declares a package under an owned namespace, and
    #: §9's per-file hashes all need the files. Turn it off only to validate a
    #: sidecar whose package data is not present — a documented example, a
    #: review of a `native.toml` on its own.
    verify_resources: bool = True


@dataclass(frozen=True)
class Application:
    """The application being built: its configuration, and its answers.

    The floors here are the application's *configured* values, which §6.2 and
    §7.2 compare a producer's requirement against. A consumer never raises them
    to satisfy a producer, so this object is read-only to the library.
    """

    #: ``compile_sdk`` / ``min_sdk`` / ``target_sdk`` as the application sets them.
    android_sdk: Mapping[str, int] = field(default_factory=dict)
    #: The application's iOS deployment target, e.g. ``"15.0"``.
    deployment_target: str | None = None
    #: Whether the application has enabled shrinking. §6.9's keeps apply only
    #: when it has.
    shrinking_enabled: bool = False
    #: Features the application *itself* declares required. §9 lets a resolved
    #: artifact's ``required="true"`` stand only for these.
    required_features: frozenset[str] = frozenset()
    #: ``<meta-data>`` keys the application sets itself. §6.3: a key the
    #: application also sets is the application's — the consumer keeps its
    #: value and reports the override.
    manifest_meta_data: Mapping[str, str] = field(default_factory=dict)
    #: ``Info.plist`` keys the application sets itself, whose ``append`` entries
    #: come first in the deterministic merge order of §7.6.
    info_plist_append: Mapping[str, Sequence[object]] = field(default_factory=dict)
    #: How the application answers every ``requires`` (§2.2).
    answers: AnswerSource = field(default_factory=MappingAnswers)

    def floor_met(self, key: str, required: int) -> bool:
        configured = self.android_sdk.get(key)
        return configured is not None and configured >= required

    def configured(self, key: str) -> int | None:
        return self.android_sdk.get(key)
