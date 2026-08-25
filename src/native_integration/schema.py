"""The sidecar schema, and the fail-closed walk over it (§4.4, §5).

Every key version 1 defines is declared here once, with its type and the
contract minor that introduced it. Two obligations fall out of that rather than
out of hand-written checks:

* **unknown keys fail closed** — inside a platform table the consumer is
  building, anything not declared here is an error, not a shrug;
* **under-declaration is caught** — a key whose ``since`` exceeds the contract
  the sidecar names is rejected even when this library implements both (§4.3).

Tables for a platform the consumer is *not* building are skipped entirely, per
§4.4, and an unrecognized top-level table is a warning because a future
platform and a misspelling are indistinguishable from here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from . import rules
from .contract import V1_0, ContractVersion
from .diagnostics import DiagnosticBag, Rule

Check = Callable[[Any], str | None]


# --- value checks -----------------------------------------------------------


def a_string(value: Any) -> str | None:
    return None if isinstance(value, str) else "must be a string"


def nonempty_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return "must be a string"
    return None if value.strip() else "must not be empty"


def an_int(value: Any) -> str | None:
    # bool is an int in Python; a boolean SDK level is a mistake worth naming.
    if isinstance(value, bool) or not isinstance(value, int):
        return "must be an integer"
    return None


def a_bool(value: Any) -> str | None:
    return None if isinstance(value, bool) else "must be a boolean"


def string_list(value: Any) -> str | None:
    if not isinstance(value, list):
        return "must be a list of strings"
    if any(not isinstance(v, str) or not v.strip() for v in value):
        return "must contain only non-empty strings"
    return None


def nonempty_string_list(value: Any) -> str | None:
    problem = string_list(value)
    if problem:
        return problem
    return None if value else "must not be empty"


def meta_data_value(value: Any) -> str | None:
    """§6.10 — a string, integer or boolean, and never a resource reference."""
    if isinstance(value, bool) or isinstance(value, int):
        return None
    if isinstance(value, str):
        return None if value.strip() else "must not be empty"
    return "must be a string, an integer or a boolean"


def one_of(*allowed: str) -> Check:
    def check(value: Any) -> str | None:
        if not isinstance(value, str):
            return "must be a string"
        if value not in allowed:
            return "must be one of " + ", ".join(repr(a) for a in allowed)
        return None

    return check


def version_range(value: Any) -> str | None:
    """§6.5's ``{ at_least, below }`` — both required, a range open at either end invalid."""
    if not isinstance(value, dict):
        return "must be a table with `at_least` and `below`"
    keys = set(value)
    if keys != {"at_least", "below"}:
        missing = {"at_least", "below"} - keys
        extra = keys - {"at_least", "below"}
        parts = []
        if missing:
            parts.append("missing " + ", ".join(sorted(missing)))
        if extra:
            parts.append("unknown " + ", ".join(sorted(extra)))
        return "needs exactly `at_least` and `below` (" + "; ".join(parts) + ")"
    if any(not isinstance(v, str) or not v.strip() for v in value.values()):
        return "bounds must be non-empty strings"
    return None


SWIFT_REQUIREMENT_KEYS = ("exact", "from", "revision", "branch")


def swift_requirement(value: Any) -> str | None:
    """§7.4's ``requirement`` — exactly one form. ``branch`` parses, then is rejected."""
    if not isinstance(value, dict):
        return "must be a table: { exact = … }, { from = … } or { revision = … }"
    keys = set(value)
    unknown = keys - set(SWIFT_REQUIREMENT_KEYS)
    if unknown:
        return "unknown requirement form(s): " + ", ".join(sorted(unknown))
    if len(keys) != 1:
        return "must declare exactly one of exact, from, revision"
    if any(not isinstance(v, str) or not v.strip() for v in value.values()):
        return "requirement value must be a non-empty string"
    return None


def value_or_reference(value: Any) -> str | None:
    """A literal string, or §6.3's inline ``{ application_value = "<id>" }``."""
    if isinstance(value, str):
        return None if value.strip() else "must not be empty"
    if isinstance(value, dict):
        if set(value) != {"application_value"}:
            return 'an inline reference takes exactly { application_value = "<id>" }'
        return nonempty_string(value["application_value"])
    return "must be a string or { application_value = \"<id>\" }"


#: §7.6 — plist keys that grant a capability or restrict installation, which a
#: producer declares as a §7.3 prerequisite and never contributes. Closed, and
#: extensible by a minor revision. What puts a key here is not that it is
#: array-valued but that a producer's entry changes what the application may do,
#: or who may install it.
CAPABILITY_KEYS: tuple[str, ...] = ("UIBackgroundModes", "UIRequiredDeviceCapabilities")

_PLIST_SCALARS = (str, int, float, bool)


def plist_value(value: Any) -> str | None:
    """§7.6's fixed TOML-to-plist mapping, for ``values`` entries."""
    if isinstance(value, bool) or isinstance(value, (str, int, float)):
        return None
    if isinstance(value, list):
        return plist_array(value)
    return (
        "has no plist form: only strings, integers, floats, booleans and "
        "homogeneous arrays of those (dates and tables are rejected by design)"
    )


def plist_array(value: Any) -> str | None:
    if not isinstance(value, list):
        return "must be an array"
    if not value:
        return None
    kinds = {bool if isinstance(v, bool) else type(v) for v in value}
    if not all(isinstance(v, _PLIST_SCALARS) for v in value):
        return "arrays may contain only strings, integers, floats and booleans"
    if len(kinds) > 1:
        return "must be homogeneous: a mixed-type array has no unambiguous plist form"
    return None


# --- schema nodes -----------------------------------------------------------


@dataclass(frozen=True)
class Field:
    check: Check
    required: bool = False
    since: ContractVersion = V1_0


@dataclass(frozen=True)
class Table:
    fields: Mapping[str, Field] = field(default_factory=dict)
    tables: Mapping[str, "Table"] = field(default_factory=dict)
    arrays: Mapping[str, "Table"] = field(default_factory=dict)
    #: Arbitrary keys whose *values* are checked — the application's own plist
    #: keys, which are not schema.
    open_values: Check | None = None
    #: Keys a producer must not spell at all, each with the rule that says so.
    forbidden: Mapping[str, Rule] = field(default_factory=dict)
    since: ContractVersion = V1_0


def _prerequisite(**extra: Field) -> Table:
    """The §7.3 common rules as a table: ``reason`` required, ``conditional`` optional."""
    return Table(
        fields={
            "reason": Field(nonempty_string, required=True),
            "conditional": Field(a_bool),
            **extra,
        }
    )


ANDROID = Table(
    tables={
        "owns": Table(fields={"java_namespaces": Field(nonempty_string_list)}),
        "requires": Table(
            fields={
                "compile_sdk": Field(an_int),
                "min_sdk": Field(an_int),
                "target_sdk": Field(an_int),
                "core_library_desugaring": Field(a_bool),
            },
            arrays={
                "application_values": Table(
                    fields={
                        "id": Field(nonempty_string, required=True),
                        "reason": Field(nonempty_string, required=True),
                        "manifest_meta_data": Field(nonempty_string),
                        "manifest_placeholder": Field(nonempty_string),
                    }
                ),
                # §6.11 — the Android prerequisite family, on §7.3's rules.
                "application_files": _prerequisite(
                    name=Field(nonempty_string, required=True)
                ),
                "resources": _prerequisite(
                    # `type` is the platform's vocabulary, open per §4.4.
                    type=Field(nonempty_string, required=True),
                    name=Field(nonempty_string, required=True),
                ),
                "application_classes": _prerequisite(
                    id=Field(nonempty_string, required=True),
                    package_suffix=Field(nonempty_string),
                    name=Field(nonempty_string),
                ),
                "app_links": _prerequisite(id=Field(nonempty_string, required=True))
            },
        ),
        "contributes": Table(
            tables={
                "src": Table(fields={"java": Field(string_list), "kotlin": Field(string_list)}),
                "r8": Table(
                    fields={"keep_classes": Field(string_list)},
                    arrays={
                        "keep": Table(
                            fields={
                                "pattern": Field(nonempty_string, required=True),
                                "from_dependency": Field(nonempty_string, required=True),
                            }
                        )
                    },
                ),
            },
            arrays={
                "gradle_dependencies": Table(
                    fields={
                        "coordinate": Field(nonempty_string),
                        "module": Field(nonempty_string),
                        "version": Field(version_range),
                        "configuration": Field(nonempty_string),
                    }
                ),
                "gradle_repositories": Table(
                    fields={
                        "url": Field(nonempty_string, required=True),
                        "reason": Field(nonempty_string, required=True),
                        "groups": Field(string_list),
                        "modules": Field(string_list),
                        "credentials_required": Field(a_bool),
                    }
                ),
                "queries": Table(
                    fields={
                        # §6.12 — exactly one target; the pairing is checked in
                        # sidecar.py, where the diagnostic can name both fields.
                        "package": Field(nonempty_string),
                        "provider_authority": Field(nonempty_string),
                        "reason": Field(nonempty_string, required=True),
                    }
                ),
                "meta_data": Table(
                    fields={
                        "key": Field(nonempty_string, required=True),
                        "value": Field(meta_data_value, required=True),
                        "reason": Field(nonempty_string, required=True),
                    }
                ),
                "permissions": Table(
                    fields={
                        "name": Field(nonempty_string, required=True),
                        "reason": Field(nonempty_string),
                        "max_sdk_version": Field(an_int),
                        "never_for_location": Field(a_bool),
                    }
                ),
                "features": Table(
                    fields={"name": Field(nonempty_string, required=True)},
                    forbidden={"required": rules.FEATURE_REQUIRED_FORBIDDEN},
                ),
                "components": Table(
                    fields={
                        "kind": Field(one_of("service", "activity", "receiver", "provider"), required=True),
                        "name": Field(nonempty_string, required=True),
                        "from_dependency": Field(nonempty_string),
                        "exported_required": Field(a_bool),
                        "reason": Field(nonempty_string),
                        # §6.8 — Android's own vocabulary, open per §4.4.
                        "foreground_service_type": Field(nonempty_string),
                    },
                    arrays={
                        "view_links": Table(
                            # §6.8 — Android's own <data> attributes, snake-cased.
                            # The set is open per §4.4: a consumer rejects an
                            # attribute it does not implement rather than
                            # dropping it, which is what UNIMPLEMENTED_DATA
                            # below turns into a diagnostic.
                            fields={
                                "scheme": Field(value_or_reference, required=True),
                                "host": Field(value_or_reference),
                                "path_prefix": Field(value_or_reference),
                                "port": Field(value_or_reference),
                                "mime_type": Field(value_or_reference),
                                "path": Field(value_or_reference),
                                "path_pattern": Field(value_or_reference),
                                "path_suffix": Field(value_or_reference),
                            }
                        ),
                        "intent_filters": Table(
                            fields={"action": Field(nonempty_string, required=True)}
                        ),
                    },
                    forbidden={"exported": rules.COMPONENT_EXPORT_FORBIDDEN_KEY},
                ),
            },
        ),
    }
)


IOS = Table(
    fields={"swift_symbol_prefixes": Field(string_list)},
    tables={
        "requires": Table(
            fields={"deployment_target": Field(nonempty_string)},
            arrays={
                "entitlements": _prerequisite(key=Field(nonempty_string, required=True)),
                "usage_descriptions": _prerequisite(key=Field(nonempty_string, required=True)),
                "app_extensions": _prerequisite(
                    id=Field(nonempty_string, required=True),
                    # §7.3 — an Apple extension point identifier, snake-cased.
                    # Open per §4.4; the consumer profile decides which it
                    # implements, so the schema only requires a value.
                    kind=Field(nonempty_string, required=True),
                ),
                "application_files": _prerequisite(name=Field(nonempty_string, required=True)),
                "url_schemes": _prerequisite(id=Field(nonempty_string, required=True)),
                "plist_capabilities": _prerequisite(
                    key=Field(one_of(*CAPABILITY_KEYS), required=True),
                    value=Field(nonempty_string, required=True),
                ),
                # §7.3 — the iOS counterpart to §6.3. `info_plist_key` is
                # required, unlike §6.3's optional manifest_meta_data: iOS has
                # no inline reference site, so a value naming no key is inert.
                "application_values": _prerequisite(
                    id=Field(nonempty_string, required=True),
                    info_plist_key=Field(nonempty_string, required=True),
                ),
            },
        ),
        "contributes": Table(
            # §7.8 — one boolean naming one behaviour. A key taking flag
            # strings would be the escape hatch §11 closes.
            fields={"objc_categories": Field(a_bool)},
            tables={
                "src": Table(fields={"swift": Field(string_list)}),
                "info_plist": Table(
                    fields={"skadnetwork_identifiers": Field(string_list)},
                    tables={
                        "values": Table(open_values=plist_value),
                        "append": Table(open_values=plist_array),
                    },
                ),
            },
            arrays={
                # §7.5 — Apple's canonical strings, verbatim. No expansion is
                # defined: the vocabulary is the platform's and changes on
                # Apple's schedule, not this specification's (§6.7's rule).
                "accessed_api_types": Table(
                    fields={
                        "type": Field(nonempty_string, required=True),
                        "reasons": Field(nonempty_string_list, required=True),
                        "reason": Field(nonempty_string),
                    }
                ),
                "swift_packages": Table(
                    fields={
                        "name": Field(nonempty_string, required=True),
                        "url": Field(nonempty_string, required=True),
                        "requirement": Field(swift_requirement, required=True),
                        "products": Field(nonempty_string_list, required=True),
                    }
                ),
                "python_modules": Table(
                    fields={
                        "name": Field(nonempty_string, required=True),
                        "swift_package": Field(nonempty_string, required=True),
                        "init": Field(nonempty_string),
                    }
                ),
            },
        ),
    },
)

PLATFORMS: dict[str, Table] = {"android": ANDROID, "ios": IOS}

TOP_LEVEL_FIELDS: dict[str, Field] = {
    "contract": Field(nonempty_string, required=True),
    "platforms": Field(nonempty_string_list),
}


# --- the walk ---------------------------------------------------------------


@dataclass
class _Context:
    bag: DiagnosticBag
    distribution: str
    declared: ContractVersion
    implemented: ContractVersion


def _walk(node: Table, doc: Mapping[str, Any], path: str, ctx: _Context) -> None:
    prefix = f"{path}." if path else ""

    for key, rule in node.forbidden.items():
        if key in doc:
            ctx.bag.add(
                rule,
                f"`{prefix}{key}` must not be declared by a producer",
                ctx.distribution,
            )

    for key, spec in node.fields.items():
        if spec.required and key not in doc:
            ctx.bag.add(rules.KEY_REQUIRED, f"`{prefix}{key}` is required", ctx.distribution)

    for key, value in doc.items():
        where = f"{prefix}{key}"
        if key in node.forbidden:
            continue  # already reported, with a rule that says why
        if key in node.fields:
            spec = node.fields[key]
            _check_since(spec.since, where, ctx)
            problem = spec.check(value)
            if problem:
                ctx.bag.add(rules.TYPE_INVALID, f"`{where}` {problem}", ctx.distribution)
        elif key in node.tables:
            child = node.tables[key]
            _check_since(child.since, where, ctx)
            if not isinstance(value, dict):
                ctx.bag.add(rules.TYPE_INVALID, f"`{where}` must be a table", ctx.distribution)
                continue
            _walk(child, value, where, ctx)
        elif key in node.arrays:
            child = node.arrays[key]
            _check_since(child.since, where, ctx)
            if not isinstance(value, list) or not all(isinstance(v, dict) for v in value):
                ctx.bag.add(
                    rules.TYPE_INVALID,
                    f"`{where}` must be an array of tables — [[{where}]]",
                    ctx.distribution,
                )
                continue
            for index, entry in enumerate(value):
                _walk(child, entry, f"{where}[{index}]", ctx)
        elif node.open_values is not None:
            problem = node.open_values(value)
            if problem:
                ctx.bag.add(rules.TYPE_INVALID, f"`{where}` {problem}", ctx.distribution)
        else:
            ctx.bag.add(
                rules.UNKNOWN_KEY,
                f"`{where}` is not a key this specification defines",
                ctx.distribution,
            )


def _check_since(since: ContractVersion, where: str, ctx: _Context) -> None:
    if since > ctx.declared:
        ctx.bag.add(
            rules.CONTRACT_UNDER_DECLARED,
            f"`{where}` was introduced in contract {since.canonical}, "
            f"but this sidecar declares contract {ctx.declared.canonical}",
            ctx.distribution,
        )


def validate_document(
    doc: Mapping[str, Any],
    *,
    distribution: str,
    platform: str,
    declared: ContractVersion,
    implemented: ContractVersion,
    bag: DiagnosticBag,
) -> None:
    """Walk ``doc`` for ``platform``, filling ``bag``.

    The top level and the platform table being built are validated; a platform
    table for another platform is skipped, and an unrecognized top-level table
    is warned about rather than rejected (§4.4).
    """
    ctx = _Context(bag=bag, distribution=distribution, declared=declared, implemented=implemented)

    for key, spec in TOP_LEVEL_FIELDS.items():
        if spec.required and key not in doc:
            bag.add(rules.KEY_REQUIRED, f"`{key}` is required", distribution)

    for key, value in doc.items():
        if key in TOP_LEVEL_FIELDS:
            problem = TOP_LEVEL_FIELDS[key].check(value)
            if problem:
                bag.add(rules.TYPE_INVALID, f"`{key}` {problem}", distribution)
        elif key == platform:
            if not isinstance(value, dict):
                bag.add(rules.TYPE_INVALID, f"`{key}` must be a table", distribution)
                continue
            _walk(PLATFORMS[key], value, key, ctx)
        elif key in PLATFORMS:
            continue  # another platform's table: legitimately not our concern
        elif isinstance(value, dict):
            bag.add(
                rules.UNKNOWN_TOP_LEVEL,
                f"`{key}` is not a table this specification defines — a future platform "
                "and a misspelling are indistinguishable from here",
                distribution,
            )
        else:
            # §4.4 — the warning above exists because a future platform is
            # indistinguishable from a typo. A future platform is a *table*, so
            # a scalar cannot be one, and the key likeliest to be misspelled is
            # `platforms`, whose whole point is a claim that otherwise fails
            # silently (§4.5).
            bag.add(
                rules.UNKNOWN_KEY,
                f"`{key}` is not a top-level key this specification defines, and is not "
                "a table, so it cannot be a platform a later revision adds",
                distribution,
            )
