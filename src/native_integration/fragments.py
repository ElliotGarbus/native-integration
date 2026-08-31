"""A minimal sidecar in correct form, generated from the registry.

This is the third thing `explain` emits, and the reason the brief puts a
directory of micro-fragment examples out of scope: once the vocabulary is
machine-readable a fragment is a function of it, and a static directory is one
more artifact to drift.

**Minimal means minimal.** The fragment carries the declaration asked about, the
containers it sits inside, and nothing else except what those containers cannot
be written without. An author reading it should be able to tell which parts are
the answer and which are the frame, and a fragment padded with optional keys
makes that judgement for them, wrongly.

**Correct means the constraints too.** A required key is the easy half. The
`[[constraints]]` rows are the half that decides what a fragment may *not* show:
§6.3 wants `version` beside `module` and forbids it beside `coordinate`, and
§6.6 admits `view_links` only on an `activity` that is `exported_required`. A
generator that picked the first alternative alphabetically would demonstrate the
one form the section rejects, which is worse than showing nothing.

**And it is valid.** `check_spec.py` validates every generated fragment against
the schema `gen_schema.py` emits, so a stale exemplar in `contract/v1.toml` is a
failed build rather than a plausible-looking lie in a help message.
"""

from __future__ import annotations

from typing import Any, Iterator, Mapping, Sequence

from .registry import PLATFORMS, Registry, RegistryError

#: Values a type fixes on its own, so the registry carries no exemplar for them.
_BY_TYPE: Mapping[str, Any] = {"boolean": True, "integer": 26}


class Inline(dict):
    """A mapping that is a *value* rather than a table.

    `version = { at_least = "4.0.0", below = "5.0.0" }` and `[android.owns]` are
    both mappings, and TOML spells them differently. The registry knows which is
    which — an `inline_table` type — so the distinction is carried from where it
    is known to where it is rendered rather than guessed at either end.
    """


class Unwritable(Exception):
    """A declaration no fragment can demonstrate, and why."""


def _value_for(properties: Mapping[str, Any]) -> Any:
    """One leaf's canonical value.

    The registry answers wherever it can: a closed vocabulary offers its first
    member, a defaulted key its default, a `true`-only flag the only value it
    takes. `example` covers what a type cannot — a permission name, a
    coordinate, a sentence of `reason` prose — and every one of those is held to
    the schema.
    """
    if properties.get("only_true"):
        return True
    if properties.get("default") is not None:
        return properties["default"]
    if properties.get("values"):
        chosen = properties["values"][0]
        # A closed vocabulary on an `array` constrains its *members*, so one
        # member is not the value — a list holding it is.
        return [chosen] if properties.get("type") == "array" else chosen
    if "example" in properties:
        example = properties["example"]
        return Inline(example) if properties.get("type") == "inline_table" else example
    kind = properties.get("type")
    if isinstance(kind, str) and kind in _BY_TYPE:
        return _BY_TYPE[kind]
    raise Unwritable(
        "the registry carries no example for this declaration, and its type "
        "does not fix one"
    )


def _path_of(declaration_id: str, platform: str) -> tuple[str, ...]:
    return tuple(declaration_id.replace("<platform>", platform).split("."))


def _owners(declaration_id: str) -> Iterator[str]:
    """Every container on the way down to a declaration, outermost first."""
    segments = declaration_id.split(".")
    for depth in range(1, len(segments)):
        yield ".".join(segments[:depth])


def _needed(
    registry: Registry, scope: str, wanted: str
) -> tuple[dict[str, Any], set[str]]:
    """What one container needs beside `wanted`, and what it must not carry.

    Returns the declarations to write with the value each must take — `None`
    where the registry's own value will do — and the set a constraint forbids.
    """
    prefix = scope + "."
    children = {
        identifier: properties
        for identifier, properties in registry.declarations.items()
        if identifier.startswith(prefix) and "." not in identifier[len(prefix):]
    }
    needed: dict[str, Any] = {
        identifier: None
        for identifier, properties in children.items()
        if properties.get("required") and not properties.get("forbidden")
    }
    forbidden: set[str] = set()

    # `wanted` may be this container's child or something further inside it;
    # either way the constraints on the child that holds it apply.
    inside = wanted[len(prefix):] if wanted.startswith(prefix) else ""
    held = inside.split(".")[0] if inside else ""

    rules = registry.constraints_for(scope)
    for rule in rules:
        # §6.1's rule names its trigger in `any_of` and its field by a dotted
        # path from the platform table: contributing Java or Kotlin source
        # requires owning a namespace to put it in.
        triggers = rule.get("any_of")
        if triggers and any(f"{scope}.{name}" == wanted or wanted.startswith(f"{scope}.{name}.")
                            for name in triggers):
            needed.setdefault(f"{scope}.{rule['field']}", None)
            continue
        if rule["field"] != held:
            continue
        other = f"{scope}.{rule.get('other', '')}"
        if rule["rule"] in ("required_if_present", "requires_present"):
            needed.setdefault(other, None)
        elif rule["rule"] == "requires_equals":
            needed[other] = rule.get("value")
        elif rule["rule"] == "forbidden_if_present":
            forbidden.add(other)

    # An alternative is chosen by what has already been asked for, not by order.
    container = registry.declarations.get(scope, {})
    for alternatives in (container.get("exactly_one_of"), container.get("at_least_one_of")):
        if not alternatives:
            continue
        offered = [f"{scope}.{name}" for name in alternatives]
        chosen = next(
            (name for name in offered if name in needed or name == wanted),
            next((name for name in offered if name not in forbidden), offered[0]),
        )
        needed.setdefault(chosen, None)
        forbidden.update(name for name in offered if name != chosen)

    # And what the keys now present drag in after them.
    for rule in rules:
        other = f"{scope}.{rule.get('other', '')}"
        field = f"{scope}.{rule['field']}"
        if other not in needed and other != wanted:
            continue
        if rule["rule"] == "required_if_present":
            needed.setdefault(field, None)
        elif rule["rule"] == "required_unless_equals":
            settled = needed.get(other) or _value_for(registry.declaration(other))
            if settled != rule.get("value"):
                needed.setdefault(field, None)
        elif rule["rule"] == "forbidden_if_present":
            forbidden.add(field)

    for name in forbidden:
        needed.pop(name, None)
    needed.pop(wanted, None)
    return needed, forbidden


def _build(registry: Registry, declaration_id: str, platform: str) -> dict:
    properties = registry.declaration(declaration_id)
    if properties.get("forbidden"):
        raise Unwritable(
            "this key is not a field. Its correct form is its absence, which no "
            "fragment can show"
        )

    settled: dict[str, Any] = {}
    if properties.get("node") == "field":
        settled[declaration_id] = _value_for(properties)
    else:
        for child, forced in _needed(registry, declaration_id, "")[0].items():
            settled[child] = forced if forced is not None else _value_for(
                registry.declaration(child)
            )

    # Every container on the way down, declared or not: §6.1's rule is scoped to
    # the platform table, which is a table this document defines and the
    # registry holds no declaration for.
    for owner in _owners(declaration_id):
        for sibling, forced in _needed(registry, owner, declaration_id)[0].items():
            if sibling in settled:
                continue
            settled[sibling] = (
                forced if forced is not None else _value_for(registry.declaration(sibling))
            )

    # Registry order, which is Appendix B's order, so a fragment reads the way
    # the reference table does rather than in the order the rules were resolved.
    order = list(registry.declarations)
    document: dict = {"contract": registry.contract.split(".")[0]}
    for identifier in sorted(settled, key=order.index):
        holder = document
        path = _path_of(identifier, platform)
        for segment in path[:-1]:
            holder = holder.setdefault(segment, {})
        holder[path[-1]] = settled[identifier]
    if len(document) == 1:
        holder = document
        for segment in _path_of(declaration_id, platform):
            holder = holder.setdefault(segment, {})
    return document


# -- rendering ---------------------------------------------------------------


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_scalar(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{k} = {_scalar(v)}" for k, v in value.items()) + " }"
    return str(value)


def _render(document: Mapping[str, Any], arrays: frozenset[tuple[str, ...]]) -> str:
    lines: list[str] = []

    def emit(mapping: Mapping[str, Any], prefix: tuple[str, ...]) -> None:
        scalars = {
            k: v for k, v in mapping.items()
            if not isinstance(v, dict) or isinstance(v, Inline)
        }
        tables = {
            k: v for k, v in mapping.items()
            if isinstance(v, dict) and not isinstance(v, Inline)
        }
        if prefix and (scalars or not tables):
            header = ".".join(prefix)
            lines.append(f"[[{header}]]" if prefix in arrays else f"[{header}]")
        for key, value in scalars.items():
            lines.append(f"{key} = {_scalar(value)}")
        if prefix and (scalars or not tables):
            lines.append("")
        elif scalars:
            lines.append("")
        for key, value in tables.items():
            emit(value, prefix + (key,))

    emit(document, ())
    return "\n".join(lines).rstrip("\n") + "\n"


def fragment(registry: Registry, declaration_id: str, platform: str = "android") -> str:
    """A minimal `native.toml` demonstrating one declaration in correct form."""
    if platform not in PLATFORMS:
        raise RegistryError(f"{platform!r} is not a platform this document defines")
    properties = registry.declaration(declaration_id)
    declared_for = properties.get("platform")
    if declared_for in PLATFORMS:
        platform = str(declared_for)

    arrays = frozenset(
        _path_of(identifier, platform)
        for identifier, entry in registry.declarations.items()
        if entry.get("node") == "array_of_tables"
    )
    return _render(_build(registry, declaration_id, platform), arrays)
