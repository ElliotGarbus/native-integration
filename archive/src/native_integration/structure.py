"""Structural validation, driven by `contract/v1.toml`.

Everything here is derived from the registry: what may appear where, what shape
it takes, what closed vocabulary it draws on, and the relations between keys
that `[[constraints]]` states. There is no vocabulary in this file. Adding a
declaration to the registry extends this validator without touching it.

The boundary is the one Phase 1 drew for the JSON Schema, plus the one thing a
JSON Schema cannot see: TOML distinguishes `24` from `24.0` and JSON does not,
so §5.1's "a **TOML integer** — `"24"` and `24.0` are rejected" is enforced
here and only here.

What is *not* here, because it needs more than the one file: namespace
containment and closure-wide collision, path escape, the contract version gate
against the consumer's own version, and every merge rule between distributions.
Those are §8's semantic rules.

So "adding a declaration to the registry extends this validator" is a claim
about *shape*, and it stops there. The registry also carries a `merge` value on
around twenty-five declarations — `report_together`, `union_widest`,
`coalesce_or_fail`, `must_agree` — and nothing reads them: `semantics.py`
states each of those rules in Python instead. The same goes for the vocabulary
a semantic rule needs rather than a shape check does, which is written out in
the module that uses it: `integration.FLOORS` and `integration.LANGUAGES`,
`semantics.RESERVED`, `graph.METADATA_NAMES`. A new floor in `v1.toml` is a new
line in `integration.py` too. Worth knowing before trusting a registry edit to
carry itself through.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dataclass_field
from typing import Any, Mapping, Sequence

from .findings import Findings, where as render_path
from .obligations import UnattributedCheck, for_declaration
from .registry import PLATFORMS, Node, Registry

#: §4.4's fail-closed rule, which is one rule wherever a shape is wrong.
FAIL_CLOSED = 8


@dataclass
class _Walk:
    document: Mapping[str, Any]
    platform: str
    distribution: str
    findings: Findings
    registry: Registry
    #: Every node the document actually carries, by registry id. Constraints,
    #: uniqueness and cross-references all read instances rather than re-walking.
    seen: dict[str, list[tuple[tuple[Any, ...], Any]]] = dataclass_field(
        default_factory=dict
    )

    def record(self, node: Node, path: Sequence[Any], value: Any) -> None:
        self.seen.setdefault(node.id, []).append((tuple(path), value))

    def instances(self, declaration_id: str) -> list[tuple[tuple[Any, ...], Any]]:
        return self.seen.get(declaration_id, [])

    def rule(self, identifier: str, path: Sequence[Any], **kwargs: Any) -> None:
        self.findings.rule(
            identifier, self.distribution, where=render_path(path), **kwargs
        )

    def requirement(self, number: int, path: Sequence[Any], **kwargs: Any) -> None:
        self.findings.requirement(
            number, self.distribution, where=render_path(path), **kwargs
        )

    def check(self, node: Node, name: str, path: Sequence[Any], **kwargs: Any) -> None:
        """Report a named check on a declaration, precisely where the registry
        names it and by requirement alone where it does not."""
        identifier = f"ni.decl.{node.id}.{name}"
        if identifier in self.registry.diagnostics:
            self.rule(identifier, path, **kwargs)
            return
        self.requirement(_shape_requirement(node), path, **kwargs)


def _shape_requirement(node: Node) -> int:
    """The requirement a shape failure answers to when no precise id exists.

    An implied container — `[android.contributes]`, which heads nothing of its
    own — belongs to no declaration family, so a malformed one is §4.4's: the
    consumer cannot recognize what it was given and fails closed.
    """
    try:
        return for_declaration(node.id, "shape")
    except UnattributedCheck:
        return FAIL_CLOSED


# -- type predicates -------------------------------------------------------


def _scalar_of(value: Any, kind: str) -> bool:
    if kind == "string":
        return isinstance(value, str)
    if kind == "integer":
        # TOML's `true` is a Python bool, and a bool is an int. §5.1 means a
        # TOML integer, so neither `true` nor `24.0` is one.
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "float":
        return isinstance(value, float) and not isinstance(value, bool)
    return False


def _is_reference(value: Any) -> bool:
    """§5.2's inline form: `{ application_value = "id" }` and nothing else."""
    return (
        isinstance(value, dict)
        and set(value) == {"application_value"}
        and isinstance(value["application_value"], str)
        and bool(value["application_value"])
    )


def _plist_kind(value: Any) -> str | None:
    for kind in ("boolean", "integer", "float", "string"):
        if _scalar_of(value, kind):
            return kind
    return None


# -- the walk --------------------------------------------------------------


def validate(
    document: Mapping[str, Any],
    *,
    platform: str,
    distribution: str,
    findings: Findings,
) -> None:
    """Check one parsed sidecar against the registry, for one platform."""
    walk = _Walk(
        document=document,
        platform=platform,
        distribution=distribution,
        findings=findings,
        registry=findings.registry,
    )
    root = findings.registry.tree(platform)
    _root(document, root, walk)
    _constraints(walk)
    _uniqueness(walk)
    _references(walk)


def _root(document: Mapping[str, Any], root: Node, walk: _Walk) -> None:
    if not isinstance(document, dict):
        walk.requirement(FAIL_CLOSED, (), message="the sidecar is not a table")
        return

    for key, value in document.items():
        child = root.child(key)
        if child is not None:
            _node(value, child, [key], walk)
            continue
        if key in PLATFORMS:
            # Another platform's table. §4.5's contradiction rule is a
            # constraint and is checked there; nothing else about it is this
            # build's business.
            continue
        # §4.4: an unrecognized top-level *table* is warned about, because a
        # future platform and a misspelling are indistinguishable from here. An
        # unrecognized top-level key that is not a table is rejected.
        if isinstance(value, dict):
            walk.findings.advisory(
                "S1",
                walk.distribution,
                message=f"`{key}` is a top-level table this contract does not define",
                where=key,
            )
        else:
            walk.requirement(
                FAIL_CLOSED,
                [key],
                message=f"`{key}` is a top-level key this contract does not define",
            )

    _missing_children(document, root, [], walk)


def _node(value: Any, node: Node, path: list[Any], walk: _Walk) -> None:
    if node.get("forbidden"):
        walk.check(node, "forbidden", path)
        return

    if node.node == "array_of_tables":
        if not isinstance(value, list):
            walk.check(node, "type", path, message=f"`{node.id}` is not an array of tables")
            return
        for index, entry in enumerate(value):
            if not isinstance(entry, dict):
                walk.check(node, "type", path + [index], message="entry is not a table")
                continue
            walk.record(node, path + [index], entry)
            _table(entry, node, path + [index], walk)
        return

    if node.node in ("table", "open_table"):
        if not isinstance(value, dict):
            walk.check(node, "type", path, message=f"`{node.id}` is not a table")
            return
        walk.record(node, path, value)
        if node.node == "open_table":
            _open_table(value, node, path, walk)
        else:
            _table(value, node, path, walk)
        return

    walk.record(node, path, value)
    _field(value, node, path, walk)


def _table(mapping: Mapping[str, Any], node: Node, path: list[Any], walk: _Walk) -> None:
    pattern = node.get("open_key_pattern")
    for key, value in mapping.items():
        child = node.child(key)
        if child is not None:
            _node(value, child, path + [key], walk)
            continue
        if node.open_keys:
            # §6.6's one exception to fail-closed: the attribute names are
            # Android's, and Android adds to them. What is rejected is a name
            # the mechanical conversion to an `android:` attribute is not
            # defined for.
            if pattern and not re.fullmatch(pattern, key):
                walk.check(node, "open-key-pattern", path + [key])
            elif not (isinstance(value, str) and value) and not _is_reference(value):
                walk.requirement(
                    _shape_requirement(node),
                    path + [key],
                    message=f"`{key}` is neither a string nor an application value",
                )
            continue
        walk.check(
            node,
            "unknown-key",
            path + [key],
            message=f"`{key}` is a key this contract does not define",
        )
    _missing_children(mapping, node, path, walk)
    _containers(mapping, node, path, walk)


def _open_table(mapping: Mapping[str, Any], node: Node, path: list[Any], walk: _Walk) -> None:
    """§7.4's `values` and `append`, whose key names are Apple's.

    Nothing enumerates the permitted keys — §7.4 could not — so what is checked
    is the refusals SPEC.md does name and the value shape each mode admits.
    """
    refuses = list(node.get("refuses", []))
    value_type = str(node.get("value_type", ""))
    for key, value in mapping.items():
        for register in refuses:
            if _refuses(key, register, walk.registry):
                walk.rule(
                    walk.registry.refusal_id(node.id, register),
                    path + [key],
                    detail=[f"the key is `{key}`"],
                )
        _plist_value(value, value_type, node, path + [key], walk)


def _refuses(key: str, register: str, registry: Registry) -> bool:
    if register == "usage_description_suffix":
        return key.endswith("UsageDescription")
    if register == "skadnetwork_items":
        return key == "SKAdNetworkItems"
    return key in registry.register(register)


def _plist_value(value: Any, value_type: str, node: Node, path: list[Any], walk: _Walk) -> None:
    if value_type == "plist_scalar":
        if _plist_kind(value) is None:
            walk.requirement(
                _shape_requirement(node), path, message="the value is not a plist scalar"
            )
        return
    if value_type == "plist_array":
        if not isinstance(value, list):
            walk.requirement(
                _shape_requirement(node), path, message="the value is not an array"
            )
            return
        kinds = {_plist_kind(item) for item in value}
        if None in kinds or len(kinds) > 1:
            walk.requirement(
                _shape_requirement(node),
                path,
                message="the array mixes types, or holds something that is not a plist scalar",
            )


def _missing_children(
    mapping: Mapping[str, Any], node: Node, path: list[Any], walk: _Walk
) -> None:
    for name, child in node.children.items():
        if child.get("required") and name not in mapping:
            walk.check(child, "missing", path + [name])


def _containers(mapping: Mapping[str, Any], node: Node, path: list[Any], walk: _Walk) -> None:
    if choices := node.get("exactly_one_of"):
        if sum(1 for choice in choices if choice in mapping) != 1:
            walk.check(node, "exactly-one-of", path)
    if choices := node.get("at_least_one_of"):
        if not any(choice in mapping for choice in choices):
            walk.check(node, "at-least-one-of", path)


def _field(value: Any, node: Node, path: list[Any], walk: _Walk) -> None:
    kind = node.get("type")

    if kind == "array":
        if not isinstance(value, list):
            walk.check(node, "type", path, message=f"`{node.path[-1]}` is not an array")
            return
        if (least := node.get("min_items")) and len(value) < least:
            walk.check(node, "empty", path)
        item_kind = node.get("items", "string")
        for index, item in enumerate(value):
            if item_kind == "enum":
                _closed_value(item, node, path + [index], walk)
            elif not _scalar_of(item, item_kind) or (item_kind == "string" and not item):
                walk.check(node, "type", path + [index], message="an entry is not a string")
            else:
                _pattern(item, node, path + [index], walk)
        return

    if kind == "enum":
        if not isinstance(value, str):
            walk.check(node, "type", path)
            return
        _closed_value(value, node, path, walk)
        return

    if kind == "inline_table":
        _inline_table(value, node, path, walk)
        return

    if kind == "string_or_inline_reference":
        if not ((isinstance(value, str) and value) or _is_reference(value)):
            walk.check(
                node, "type", path, message="neither a string nor an application value"
            )
        return

    if isinstance(kind, list):
        if not any(_scalar_of(value, one) for one in kind):
            walk.check(
                node, "type", path, message=f"not one of {', '.join(kind)}"
            )
        return

    if kind == "boolean":
        if not _scalar_of(value, "boolean"):
            walk.check(node, "type", path)
        elif node.get("only_true") and value is False:
            walk.check(node, "false", path)
        return

    if kind is None:
        return  # a declaration with no type states no shape

    if not _scalar_of(value, kind) or (kind == "string" and not value):
        walk.check(node, "type", path)
        return
    if kind == "string":
        _pattern(value, node, path, walk)
        _scheme(value, node, path, walk)


def _closed_value(value: Any, node: Node, path: list[Any], walk: _Walk) -> None:
    allowed = list(node.get("values", ()))
    if not isinstance(value, str):
        walk.check(node, "type", path)
        return
    if value in allowed:
        # §5.5's Platform column is normative: a kind is valid only in a table
        # for the platform its row names.
        elsewhere = node.get("value_platforms", {})
        belongs = elsewhere.get(value, "both")
        if belongs not in (walk.platform, "both"):
            walk.check(
                node,
                "wrong-platform",
                path,
                detail=[f"`{value}` belongs to the {belongs} table"],
            )
        return
    walk.check(
        node,
        "value",
        path,
        detail=[f"`{value}` is not one of {', '.join(f'`{a}`' for a in allowed)}"],
    )


def _pattern(value: str, node: Node, path: list[Any], walk: _Walk) -> None:
    pattern = node.get("pattern")
    if pattern and not re.fullmatch(pattern, value):
        walk.check(node, "pattern", path, detail=[f"`{value}` does not match `{pattern}`"])


def _scheme(value: str, node: Node, path: list[Any], walk: _Walk) -> None:
    if node.get("scheme") != "https":
        return
    # §6.4 compares the scheme case-insensitively, as RFC 3986 defines it.
    if not value.lower().startswith("https://"):
        walk.check(node, "scheme", path, detail=[f"`{value}` is not an https URL"])
        return
    if node.get("forbids_user_info"):
        authority = value[len("https://") :].split("/", 1)[0]
        if "@" in authority:
            walk.check(
                node,
                "scheme",
                path,
                message="the URL carries user-info, which is a credential in a committed file",
            )


def _inline_table(value: Any, node: Node, path: list[Any], walk: _Walk) -> None:
    keys = list(node.get("table_keys", ()))
    if not isinstance(value, dict):
        walk.check(node, "type", path, message="not an inline table")
        return
    unknown = sorted(set(value) - set(keys))
    if unknown:
        walk.check(
            node,
            "type",
            path,
            detail=[f"`{unknown[0]}` is not one of {', '.join(f'`{k}`' for k in keys)}"],
        )
        return
    if node.get("table_keys_exactly_one") and len(value) != 1:
        walk.check(
            node,
            "type",
            path,
            detail=[f"exactly one of {', '.join(f'`{k}`' for k in keys)} is required"],
        )
        return
    missing = [k for k in node.get("table_keys_required", ()) if k not in value]
    if missing:
        walk.check(node, "type", path, detail=[f"`{missing[0]}` is required here"])
        return
    member_kind = str(node.get("table_value_type", "string"))
    bound = node.get("table_value_pattern")
    for key, member in value.items():
        if not _scalar_of(member, member_kind) or (member_kind == "string" and not member):
            walk.check(node, "type", path + [key], message=f"`{key}` is not a {member_kind}")
        elif bound and not re.fullmatch(bound, str(member)):
            walk.check(node, "pattern", path + [key])


# -- rules between keys ----------------------------------------------------


def _present(mapping: Mapping[str, Any], dotted: str) -> bool:
    cursor: Any = mapping
    for step in dotted.split("."):
        if not isinstance(cursor, dict) or step not in cursor:
            return False
        cursor = cursor[step]
    return True


def _constraints(walk: _Walk) -> None:
    for rule in walk.registry.constraints:
        identifier = walk.registry.constraint_id(rule)
        scope = str(rule.get("scope", ""))
        if not scope:
            _platform_table_rule(rule, identifier, walk)
            continue
        for path, instance in walk.instances(scope):
            if isinstance(instance, dict) and _violates(rule, instance, walk):
                walk.rule(identifier, path)


def _violates(rule: Mapping[str, Any], entry: Mapping[str, Any], walk: _Walk) -> bool:
    kind = str(rule["rule"])
    name = str(rule["field"])
    other = str(rule.get("other", ""))
    expected = rule.get("value")

    if kind == "required_unless_equals":
        return entry.get(other) != expected and name not in entry
    if kind == "forbidden_if_equals":
        return entry.get(other) == expected and name in entry
    if kind == "pattern_if_equals":
        held = entry.get(name)
        return (
            entry.get(other) == expected
            and isinstance(held, str)
            and not re.fullmatch(str(rule["pattern"]), held)
        )
    if kind == "pattern_forbidden_if_equals":
        held = entry.get(name)
        return (
            entry.get(other) == expected
            and isinstance(held, str)
            and bool(re.fullmatch(str(rule["pattern"]), held))
        )
    if kind == "registers_forbidden_if_equals":
        refused = {
            member
            for register in rule["registers"]
            for member in walk.registry.register(register)
        }
        return entry.get(other) == expected and entry.get(name) in refused
    if kind == "required_if_present":
        return other in entry and name not in entry
    if kind == "forbidden_if_present":
        return name in entry and other in entry
    if kind == "requires_equals":
        return name in entry and entry.get(other) != expected
    if kind == "requires_present":
        return name in entry and not _present(entry, other)
    if kind == "required_if_any_present":
        return any(_present(entry, one) for one in rule["any_of"]) and not _present(
            entry, name
        )
    raise UnattributedCheck(f"unknown constraint rule {kind!r}")


def _platform_table_rule(rule: Mapping[str, Any], identifier: str, walk: _Walk) -> None:
    """§4.5: a platform table for a name `platforms` omits is a contradiction.

    Checked for both tables rather than the one being built. A sidecar that
    ships `[ios]` while listing only Android is contradictory whoever reads it,
    and the producer should hear so from the first consumer to look.
    """
    table, listed = str(rule["field"]), str(rule.get("other", "platforms"))
    declared = walk.document.get(listed)
    if not isinstance(declared, list) or table not in walk.document:
        return
    if table not in declared:
        walk.rule(identifier, [table], detail=[f"`{listed}` omits `{table}`"])


def _uniqueness(walk: _Walk) -> None:
    """`unique_within`, reported against the one id the generator emits per scope.

    §5 gives values and actions a single `id` space, so a duplicate between the
    two is one rule and carries one id, whichever declaration it was spelled on.
    """
    scopes: dict[str, list[str]] = {}
    for declaration_id, properties in walk.registry.declarations.items():
        if scope := properties.get("unique_within"):
            scopes.setdefault(str(scope), []).append(declaration_id)

    for scope, declaration_ids in scopes.items():
        identifier = next(
            (
                f"ni.decl.{one}.duplicate"
                for one in declaration_ids
                if f"ni.decl.{one}.duplicate" in walk.registry.diagnostics
            ),
            None,
        )
        if identifier is None:
            continue
        first: dict[str, tuple[Any, ...]] = {}
        for declaration_id in declaration_ids:
            for path, value in walk.instances(declaration_id):
                if not isinstance(value, str):
                    continue
                if value in first:
                    walk.rule(
                        identifier,
                        path,
                        detail=[f"`{value}` is already declared at {render_path(first[value])}"],
                    )
                else:
                    first[value] = path


def _references(walk: _Walk) -> None:
    """`resolves_to` — a name the same sidecar has to declare."""
    for declaration_id, properties in walk.registry.declarations.items():
        target = properties.get("resolves_to")
        if not target:
            continue
        known = _resolvable(str(target), walk)
        for path, value in walk.instances(declaration_id):
            names = value if isinstance(value, list) else [value]
            for offset, name in enumerate(names):
                if not isinstance(name, str) or name in known:
                    continue
                walk.check(
                    _node_for(declaration_id, walk),
                    "unresolved",
                    path + (offset,) if isinstance(value, list) else path,
                    detail=[f"`{name}` is not declared in this sidecar"],
                )


def _resolvable(target: str, walk: _Walk) -> set[str]:
    values = {v for _, v in walk.instances(target) if isinstance(v, str)}
    if values:
        return values
    # §6.6 and §6.7 point at a *dependency* rather than at a field: the value is
    # the `group:artifact` of one the same sidecar declares, which is `module`
    # outright or a `coordinate` with its version removed.
    names: set[str] = set()
    for _, entry in walk.instances(target):
        if not isinstance(entry, dict):
            continue
        if isinstance(module := entry.get("module"), str):
            names.add(module)
        if isinstance(coordinate := entry.get("coordinate"), str):
            names.add(coordinate.rsplit(":", 1)[0])
    return names


def _node_for(declaration_id: str, walk: _Walk) -> Node:
    properties = walk.registry.declaration(declaration_id)
    return Node(
        id=declaration_id,
        path=(),
        node=str(properties.get("node", "field")),
        properties=properties,
    )
