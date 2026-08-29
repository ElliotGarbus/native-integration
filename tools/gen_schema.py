#!/usr/bin/env python3
"""Generate schema/native-integration-v1.schema.json from contract/v1.toml.

**What this schema is for.** A producer wants to know their sidecar is
well-formed before they ship a wheel, and a consumer wants the cheap half of
validation off its own plate. This covers what a schema can cover: presence,
types, closed vocabularies, array item shapes, `oneOf` forms, and
integer-versus-string.

**What it deliberately does not cover**, because a schema cannot see past one
file: namespace containment and closure-wide collision (§6.1), cross-reference
resolution (§5.3's `uses`, §6.6's `from_dependency`, §7.5's `swift_package`),
path escape and symlinks (§4.1), and every merge rule between distributions.
Those need the dependency closure or the wheel's own files. They are code, and
a schema stretched to reach them would be a schema that lies about its scope.

So **passing this schema is not conformance**. It is the structural floor, and
§8 is the rest.

Two shapes in the registry drive everything conditional:

* a declaration's own fields — `required`, `type`, `values`, `pattern`,
  `min_items`, `only_true`, `exactly_one_of`, `at_least_one_of`;
* the `[[constraints]]` block, whose five rule names are exactly the relations
  a JSON Schema `if`/`then` can state.

    python3 tools/gen_schema.py          # write the schema
    python3 tools/gen_schema.py --check  # fail if it is out of date
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "contract" / "v1.toml"
OUTPUT = ROOT / "schema" / "native-integration-v1.schema.json"

SCHEMA_ID = "https://elliotgarbus.github.io/native-integration/native-integration-v1.schema.json"

PLATFORMS = ("android", "ios")

#: TOML types as JSON Schema names. TOML has no null and no distinct float type
#: name, so the mapping is total and unsurprising.
JSON_TYPE = {
    "string": "string",
    "integer": "integer",
    "boolean": "boolean",
    "float": "number",
}


def expand(declaration_id: str, platform: str) -> str | None:
    """Resolve a registry id against one platform, or None if it is another's."""
    if declaration_id.startswith("<platform>."):
        return declaration_id.replace("<platform>", platform, 1)
    if declaration_id.split(".", maxsplit=1)[0] in PLATFORMS:
        return declaration_id if declaration_id.startswith(f"{platform}.") else None
    return declaration_id


def leaf_schema(entry: dict) -> dict[str, Any]:
    """The schema for one field, from its declared type alone."""
    kind = entry.get("type")

    if kind == "enum":
        return {"enum": list(entry["values"])}

    if kind == "array":
        items: dict[str, Any]
        if entry.get("items") == "enum":
            items = {"enum": list(entry["values"])}
        else:
            items = {"type": JSON_TYPE[entry.get("items", "string")]}
            if entry.get("items", "string") == "string":
                items["minLength"] = 1
                if pattern := entry.get("pattern"):
                    items["pattern"] = f"^{pattern}$"
        node: dict[str, Any] = {"type": "array", "items": items}
        if min_items := entry.get("min_items"):
            node["minItems"] = min_items
        return node

    if kind == "inline_table":
        keys = list(entry["table_keys"])
        value_type = JSON_TYPE[entry.get("table_value_type", "string")]
        node = {
            "type": "object",
            "additionalProperties": False,
            "properties": {k: {"type": value_type, "minLength": 1} for k in keys},
        }
        if entry.get("table_keys_exactly_one"):
            # §7.2's requirement forms. `additionalProperties: false` is what
            # refuses `branch`; the bounds are what refuse two at once.
            node["minProperties"] = 1
            node["maxProperties"] = 1
        for required in entry.get("table_keys_required", []):
            node.setdefault("required", []).append(required)
        return node

    if kind == "string_or_inline_reference":
        return {"$ref": "#/$defs/stringOrInlineValue"}

    if isinstance(kind, list):
        return {"type": [JSON_TYPE[t] for t in kind]}

    if kind == "boolean":
        # §5.1's boolean floor, and §7.6's. Only `true` says anything, so
        # `false` is a declaration that requires nothing.
        return {"const": True} if entry.get("only_true") else {"type": "boolean"}

    node = {"type": JSON_TYPE[kind]}
    if kind == "string":
        node["minLength"] = 1
        if pattern := entry.get("pattern"):
            node["pattern"] = f"^{pattern}$"
        elif entry.get("scheme") == "https":
            # §6.4 compares the scheme case-insensitively, as RFC 3986 defines
            # it, so `HTTPS://` is the same scheme and is valid. Nothing else
            # about the URL is normalized.
            node["pattern"] = "^[Hh][Tt][Tt][Pp][Ss]://"
    return node


def constraint_schema(rule: dict) -> dict[str, Any]:
    """One `[[constraints]]` entry as a JSON Schema `if`/`then`."""
    field, other = rule["field"], rule["other"]

    if rule["rule"] == "required_unless_equals":
        return {
            "if": {"properties": {other: {"const": rule["value"]}}, "required": [other]},
            "then": True,
            "else": {"required": [field]},
        }
    if rule["rule"] == "forbidden_if_equals":
        return {
            "if": {"properties": {other: {"const": rule["value"]}}, "required": [other]},
            "then": {"not": {"required": [field]}},
        }
    if rule["rule"] == "required_if_present":
        return {"if": {"required": [other]}, "then": {"required": [field]}}
    if rule["rule"] == "forbidden_if_present":
        return {"if": {"required": [field]}, "then": {"not": {"required": [other]}}}
    if rule["rule"] == "requires_equals":
        return {
            "if": {"required": [field]},
            "then": {"properties": {other: {"const": rule["value"]}}, "required": [other]},
        }
    raise SystemExit(f"unknown constraint rule {rule['rule']!r} in contract/v1.toml")


def container_schema(entry: dict) -> dict[str, Any]:
    """The object a table or array-of-tables holds, before its children land."""
    obj: dict[str, Any] = {"type": "object", "additionalProperties": False, "properties": {}}

    if entry.get("open_keys"):
        # §6.6's `view_links`: the one place an unrecognized key is written
        # through rather than rejected, because the `<data>` attribute names
        # are Android's and Android adds to them.
        obj["additionalProperties"] = {"$ref": "#/$defs/stringOrInlineValue"}
        if pattern := entry.get("open_key_pattern"):
            obj["propertyNames"] = {"pattern": f"^{pattern}$"}

    if choices := entry.get("exactly_one_of"):
        obj["oneOf"] = [{"required": [c]} for c in choices]
    if choices := entry.get("at_least_one_of"):
        obj["anyOf"] = [{"required": [c]} for c in choices]

    if entry["node"] == "array_of_tables":
        return {"type": "array", "items": obj}
    return obj


def open_table_schema(entry: dict, registers: dict) -> dict[str, Any]:
    """§7.4's `values` and `append`, whose key names are Apple's.

    The key names are open by design — §7.4 enumerates no permitted key and
    could not — so what the schema states is the refusals SPEC.md does name,
    and the value shape each mode admits.
    """
    refused: list[str] = []
    for register in entry.get("refuses", []):
        if register == "usage_description_suffix":
            continue
        if register == "skadnetwork_items":
            refused.append("SKAdNetworkItems")
            continue
        refused.extend(registers[register]["members"])

    forbidden: list[dict[str, Any]] = [{"enum": sorted(set(refused))}]
    if "usage_description_suffix" in entry.get("refuses", []):
        forbidden.append({"pattern": "UsageDescription$"})

    value = {"$ref": "#/$defs/plistValue"}
    if entry.get("value_type") == "plist_array":
        value = {"$ref": "#/$defs/plistArray"}

    return {
        "type": "object",
        "propertyNames": {"not": {"anyOf": forbidden}},
        "additionalProperties": value,
    }


def walk(tree: dict[str, Any], path: list[str]) -> dict[str, Any]:
    """The object at `path`, creating plain containers on the way.

    `[android.contributes]` has no row in Appendix B — nothing is declared
    directly on it — so it has no registry entry either. The schema still needs
    the level, so a missing intermediate becomes an ordinary closed object.
    """
    cursor = tree
    for step in path:
        properties = cursor.setdefault("properties", {})
        cursor = properties.setdefault(
            step, {"type": "object", "additionalProperties": False, "properties": {}}
        )
        if cursor.get("type") == "array":
            cursor = cursor["items"]
    return cursor


def insert(tree: dict[str, Any], path: list[str], node: dict[str, Any]) -> None:
    """Attach `node`, keeping anything a child already auto-created at the path.

    Registry order is document order, so a child can land before the container
    it belongs to — `ios.contributes.swift_packages` precedes `ios.contributes`,
    which exists only to head `objc_categories`. Replacing outright would drop
    every sibling declared above it.
    """
    parent = walk(tree, path[:-1])["properties"]
    existing = parent.get(path[-1])
    if existing is not None:
        target = node["items"] if node.get("type") == "array" else node
        source = existing["items"] if existing.get("type") == "array" else existing
        target.setdefault("properties", {}).update(source.get("properties", {}))
        for key in ("required", "allOf", "oneOf", "anyOf"):
            if key in source:
                target.setdefault(key, []).extend(source[key])
    parent[path[-1]] = node


def mark_required(tree: dict[str, Any], path: list[str]) -> None:
    walk(tree, path[:-1]).setdefault("required", []).append(path[-1])


def platform_schema(registry: dict, platform: str) -> dict[str, Any]:
    declarations, registers = registry["declarations"], registry["registers"]
    root: dict[str, Any] = {"type": "object", "additionalProperties": False, "properties": {}}

    for declaration_id, entry in declarations.items():
        resolved = expand(declaration_id, platform)
        if resolved is None or "." not in resolved:
            continue  # another platform's, or a top-level key
        if entry.get("forbidden"):
            continue  # `additionalProperties: false` already refuses it
        path = resolved.split(".")[1:]

        if entry["node"] in ("table", "array_of_tables"):
            insert(root, path, container_schema(entry))
        elif entry["node"] == "open_table":
            insert(root, path, open_table_schema(entry, registers))
        else:
            node = leaf_schema(entry)
            if entry["node"] == "field" and entry.get("type") == "enum":
                # §5.5's Platform column: a kind is valid only in a table for
                # the platform its row names.
                if mapping := entry.get("value_platforms"):
                    node = {
                        "enum": [
                            v for v in entry["values"] if mapping[v] in (platform, "both")
                        ]
                    }
            insert(root, path, node)
            if entry.get("required"):
                mark_required(root, path)

    for rule in registry["constraints"]:
        scope = expand(rule["scope"], platform)
        if scope is None:
            continue
        walk(root, scope.split(".")[1:]).setdefault("allOf", []).append(
            constraint_schema(rule)
        )

    return root


def build(registry: dict) -> dict[str, Any]:
    declarations = registry["declarations"]

    schema: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": SCHEMA_ID,
        "title": "native-integration sidecar, contract 1",
        "description": (
            "Structural validation only. Namespace containment, cross-reference "
            "resolution, closure-wide collision detection and path escape are "
            "SPEC.md §8's and are not expressible here; passing this schema is "
            "not conformance."
        ),
        "type": "object",
        "required": ["contract"],
        # §4.4: an unrecognized top-level *table* is warned about, because a
        # future platform and a misspelling are indistinguishable from here. An
        # unrecognized top-level key that is not a table is rejected.
        "additionalProperties": {"type": "object"},
        "properties": {},
        "$defs": {
            "stringOrInlineValue": {
                "oneOf": [
                    {"type": "string", "minLength": 1},
                    {
                        "type": "object",
                        "required": ["application_value"],
                        "additionalProperties": False,
                        "properties": {
                            "application_value": {"type": "string", "minLength": 1}
                        },
                    },
                ]
            },
            # §7.4's TOML-to-plist mapping. `anyOf` rather than `oneOf` because
            # an array of integers satisfies both the integer and the number
            # branch, which `oneOf` would count as a failure.
            "plistArray": {
                "anyOf": [
                    {"type": "array", "items": {"type": t}}
                    for t in ("string", "integer", "number", "boolean")
                ]
            },
            "plistValue": {
                "anyOf": [
                    {"type": ["string", "integer", "number", "boolean"]},
                    {"$ref": "#/$defs/plistArray"},
                ]
            },
        },
    }

    for declaration_id, entry in declarations.items():
        if "." in declaration_id or entry["node"] != "field":
            continue
        schema["properties"][declaration_id] = leaf_schema(entry)

    for platform in PLATFORMS:
        schema["properties"][platform] = platform_schema(registry, platform)

    return schema


def main() -> int:
    registry = tomllib.loads(REGISTRY.read_text(encoding="utf-8"))
    content = json.dumps(build(registry), indent=2, sort_keys=False) + "\n"

    if "--check" in sys.argv:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != content:
            print(f"FAIL  {OUTPUT.relative_to(ROOT)} is out of date")
            print("      run: python3 tools/gen_schema.py")
            return 1
        print(f"ok    {OUTPUT.relative_to(ROOT)} is current")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n" explicitly: this repository pins LF (.gitattributes), and a
    # generator that emitted CRLF on Windows would fail its own --check against
    # an LF checkout while passing on Linux.
    OUTPUT.write_text(content, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
