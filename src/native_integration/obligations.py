"""Which §8 requirement each registry check discharges.

`contract/v1.toml` carries mechanical properties only — that was Phase 1's whole
discipline — so it does not say which numbered requirement a failed check
answers to. §8.4 is prose, and this table is read out of it by hand. It is the
one place in the reader where a mapping is written rather than derived, and
`tests/test_obligations.py` holds it total: every id any generator emits
resolves to exactly one requirement, and that requirement's §8.1 profile agrees
with the platform the declaration belongs to.

The corpus needs this because a finding carries both ids — the precise one for
the rule and `ni.req.<n>` for the obligation — and `run.py` compares the set
exactly.
"""

from __future__ import annotations

from typing import Mapping

from .registry import PLATFORM_TOKEN, Registry

#: A check that answers to the same requirement wherever it fires. §4.4's
#: fail-closed rule is one rule, not one per container.
BY_CHECK: Mapping[str, int] = {
    "unknown-key": 8,
}

#: Otherwise the declaration family decides, longest prefix first. §8.4 is
#: organized this way — one requirement per kind of declared material — which is
#: why a prefix is the right grain and a section is not: §6.6 carries two
#: requirements and §5.2 carries three.
BY_FAMILY: Mapping[str, int] = {
    "contract": 7,
    "platforms": 9,
    "android.requires": 12,
    "ios.requires": 12,
    f"{PLATFORM_TOKEN}.requires.application_value": 13,
    f"{PLATFORM_TOKEN}.requires.application_action": 14,
    "android.owns": 23,
    "android.contributes.src": 23,
    "android.contributes.gradle_dependencies": 25,
    "android.contributes.gradle_repositories": 27,
    "android.contributes.permissions": 28,
    "android.contributes.features": 28,
    "android.contributes.components": 29,
    # §6.6 splits: requirement 29 rejects a `view_links` in an invalid
    # *combination*, requirement 30 validates the link's own attributes. The
    # combination rules are `[[constraints]]` scoped to `components`, so they
    # resolve above; what reaches this prefix is the content.
    "android.contributes.components.view_links": 30,
    "android.contributes.r8": 31,
    "android.contributes.meta_data": 32,
    "android.contributes.queries": 32,
    "ios.contributes.swift_packages": 33,
    "ios.contributes.src": 34,
    "ios.contributes.accessed_api_types": 34,
    "ios.contributes.info_plist": 35,
    "ios.contributes.python_modules": 36,
    "ios.contributes.objc_categories": 37,
}

#: Where the family's requirement is not the one that owns a particular rule.
BY_DECLARATION_CHECK: Mapping[tuple[str, str], int] = {
    # §5 gives values and actions one `id` space, so uniqueness is one rule and
    # the generator emits one id for it, against the value's declaration. §8.4
    # puts that rule in requirement 22 rather than with the value keys.
    (f"{PLATFORM_TOKEN}.requires.application_value.id", "duplicate"): 22,
    # §5.3's `uses` naming no value the same sidecar declares, and §5.7's slot,
    # are both requirement 22's rather than requirement 14's.
    (f"{PLATFORM_TOKEN}.requires.application_action.uses", "unresolved"): 22,
    (f"{PLATFORM_TOKEN}.requires.application_action.slot", "type"): 22,
}

#: Every `[[constraints]]` row, attributed one at a time. A constraint states a
#: relation between two keys, and §8.4 does not always give that relation to the
#: requirement that owns either key: §6.6's placement rules for `view_links` are
#: requirement 29's, while the attributes of the link itself are requirement
#: 30's, and both hang off the same declarations. Nineteen rows are few enough
#: to read out of §8.4 rather than infer.
BY_CONSTRAINT: Mapping[str, int] = {
    # §5.2 and §5.5 — `key` against `kind`. Requirement 13 owns the value keys.
    "ni.constraint.<platform>.requires.application_value.key"
    ".required-unless-equals.kind": 13,
    "ni.constraint.<platform>.requires.application_value.key"
    ".forbidden-if-equals.kind": 13,
    "ni.constraint.<platform>.requires.application_value.key"
    ".pattern-if-equals.kind": 13,
    "ni.constraint.<platform>.requires.application_value.key"
    ".pattern-forbidden-if-equals.kind": 13,
    # Except this one: requirement 35 refuses a capability, external-reach or
    # consumer-managed key "wherever it arrives, in those three channels alike",
    # and a `kind = "info_plist"` value is the third channel.
    "ni.constraint.<platform>.requires.application_value.key"
    ".registers-forbidden-if-equals.kind": 35,
    # §6.3 — `version` against the two dependency shapes.
    "ni.constraint.android.contributes.gradle_dependencies.version"
    ".required-if-present.module": 25,
    "ni.constraint.android.contributes.gradle_dependencies.version"
    ".forbidden-if-present.coordinate": 25,
    # §6.6 — requirement 29 rejects "`view_links` or `intent_filters` in an
    # invalid combination", and every one of these is such a combination.
    "ni.constraint.android.contributes.components.reason"
    ".required-if-present.exported_required": 29,
    "ni.constraint.android.contributes.components.foreground_service_type"
    ".requires-equals.kind": 29,
    "ni.constraint.android.contributes.components.view_links"
    ".requires-equals.kind": 29,
    "ni.constraint.android.contributes.components.view_links"
    ".requires-equals.exported_required": 29,
    "ni.constraint.android.contributes.components.intent_filters"
    ".forbidden-if-present.exported_required": 29,
    "ni.constraint.android.contributes.components.intent_filters"
    ".forbidden-if-present.view_links": 29,
    # §7.2 — requirement 33 imports §6.4's credential rules for a package.
    "ni.constraint.ios.contributes.swift_packages.reason"
    ".required-if-present.credentials_required": 33,
    # §7.1 and §7.3 — requirement 34 rejects both "from a sidecar contributing
    # no Swift source", which is the one rule stated twice.
    "ni.constraint.ios.contributes.src.symbol_prefixes.requires-present.swift": 34,
    "ni.constraint.ios.contributes.accessed_api_types.requires-present.src.swift": 34,
    # §6.1 — requirement 23 enforces every ownership rule.
    "ni.constraint.android.owns.java_namespaces.required-if-any-present": 23,
    # §4.5 — requirement 9 enforces `platforms` entirely.
    "ni.constraint.android.platform-table-requires-listing.platforms": 9,
    "ni.constraint.ios.platform-table-requires-listing.platforms": 9,
}


class UnattributedCheck(RuntimeError):
    """A generated id this table does not answer for.

    Raised rather than defaulted. A diagnostic attributed to the wrong
    requirement is worse than one attributed to none: the corpus compares the
    id set exactly, and a wrong `ni.req.<n>` makes a passing consumer look
    non-conforming for a rule it satisfied.
    """


def _family(owner: str) -> int | None:
    best: tuple[int, int] | None = None
    for prefix, number in BY_FAMILY.items():
        if owner == prefix or owner.startswith(f"{prefix}."):
            if best is None or len(prefix) > best[0]:
                best = (len(prefix), number)
    return None if best is None else best[1]


def for_declaration(declaration_id: str, check: str) -> int:
    """The §8.4 requirement a declaration check discharges."""
    if (declaration_id, check) in BY_DECLARATION_CHECK:
        return BY_DECLARATION_CHECK[(declaration_id, check)]
    if check in BY_CHECK:
        return BY_CHECK[check]
    number = _family(declaration_id)
    if number is None:
        raise UnattributedCheck(
            f"no §8 requirement is recorded for {declaration_id}.{check}; "
            "add it to obligations.BY_FAMILY, from §8.4's own text"
        )
    return number


def for_constraint(identifier: str) -> int:
    """The §8.4 requirement a `[[constraints]]` row discharges."""
    try:
        return BY_CONSTRAINT[identifier]
    except KeyError:
        raise UnattributedCheck(
            f"no §8 requirement is recorded for {identifier}; "
            "add it to obligations.BY_CONSTRAINT, from §8.4's own text"
        ) from None


def for_identifier(identifier: str, registry: Registry) -> int:
    """The requirement behind any generated declaration or constraint id."""
    if identifier.startswith("ni.constraint."):
        return for_constraint(identifier)
    if identifier.startswith("ni.decl."):
        declaration = str(registry.about(identifier)["declaration"])
        check = identifier[len("ni.decl.") + len(declaration) + 1 :]
        return for_declaration(declaration, check)
    raise UnattributedCheck(f"{identifier} is not a declaration or constraint id")
