"""The v1 declaration registry, loaded rather than restated.

`contract/v1.toml` is the source of truth for the declaration vocabulary and
`contract/diagnostics-v1.toml` for the diagnostic identifiers. This module is
the only place either is parsed, and the only place an identifier is formed, so
adding a declaration is a registry edit and not a reader edit.

Nothing here validates a sidecar. It answers three questions and no others:
what may appear where, what shape it takes, and which identifier names the
check that failed.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator, Mapping

#: An id spelled with this token is declared identically under both platform
#: tables. Diagnostic ids keep the token; document paths resolve it.
PLATFORM_TOKEN = "<platform>"

PLATFORMS = ("android", "ios")

CONTAINERS = ("table", "array_of_tables", "open_table")


class RegistryError(RuntimeError):
    """The registry is missing, malformed, or was asked for an id it lacks.

    Always raised rather than warned about. A check the registry cannot name is
    a reader defect, and a reader that fell back to a hand-written string would
    be the second source of truth this module exists to prevent.
    """


def _candidate_directories() -> Iterator[Path]:
    """Where `contract/` may sit, nearest first.

    Packaged beside the module when installed; at the repository root in a
    source checkout or an editable install.
    """
    here = Path(__file__).resolve()
    yield here.parent / "contract"
    for parent in here.parents:
        yield parent / "contract"


def contract_directory() -> Path:
    for candidate in _candidate_directories():
        if (candidate / "v1.toml").is_file():
            return candidate
    raise RegistryError(
        "contract/v1.toml was not found beside the package or above it; "
        "the reader cannot validate without the registry it is driven by"
    )


@dataclass(frozen=True)
class Node:
    """One position in a sidecar document, as the registry describes it.

    `id` is the registry's own spelling, `<platform>` token included, because
    that is what a diagnostic id is built from. `path` is where the node sits in
    a document for one concrete platform. The two differ for every declaration
    shared between Android and iOS.
    """

    id: str
    path: tuple[str, ...]
    node: str
    properties: Mapping[str, Any] = field(default_factory=dict)
    children: Mapping[str, "Node"] = field(default_factory=dict)

    @property
    def declared(self) -> bool:
        """Whether the registry names this node, or it is an implied container.

        `[android.contributes]` carries no properties of its own and has no row;
        `[ios.contributes]` does, because `objc_categories` hangs directly off
        it. A walker needs both to exist and needs to tell them apart.
        """
        return bool(self.properties)

    @property
    def is_container(self) -> bool:
        return self.node in CONTAINERS

    @property
    def open_keys(self) -> bool:
        """Whether the key *names* here belong to the platform, not to us.

        The one place §4.4's fail-closed rule does not apply.
        """
        return bool(self.properties.get("open_keys"))

    def get(self, name: str, default: Any = None) -> Any:
        return self.properties.get(name, default)

    def child(self, name: str) -> "Node | None":
        return self.children.get(name)

    def walk(self) -> Iterator["Node"]:
        for child in self.children.values():
            yield child
            yield from child.walk()


def _applies_to(declaration_id: str, platform: str) -> bool:
    head = declaration_id.split(".", 1)[0]
    if head == PLATFORM_TOKEN:
        return True
    if head in PLATFORMS:
        return head == platform
    return True  # a top-level key, which belongs to no platform table


def _document_path(declaration_id: str, platform: str) -> tuple[str, ...]:
    segments = declaration_id.split(".")
    if segments[0] == PLATFORM_TOKEN:
        segments[0] = platform
    return tuple(segments)


@dataclass(frozen=True)
class Registry:
    """`contract/v1.toml` and `contract/diagnostics-v1.toml`, in memory."""

    meta: Mapping[str, Any]
    declarations: Mapping[str, Mapping[str, Any]]
    registers: Mapping[str, Mapping[str, Any]]
    constraints: tuple[Mapping[str, Any], ...]
    diagnostics: Mapping[str, Mapping[str, Any]]

    @property
    def contract(self) -> str:
        return str(self.meta["contract"])

    @property
    def entry_point_group(self) -> str:
        return str(self.meta["entry_point_group"])

    # -- the vocabulary ----------------------------------------------------

    def tree(self, platform: str) -> Node:
        """The document shape for one platform, as a tree of nodes.

        The root's children are the top-level keys and the one platform table
        this build is for. The other platform's table is absent rather than
        empty: §4.5 makes declaring a table for an unlisted platform a
        contradiction, and that is a rule, not a shape.
        """
        if platform not in PLATFORMS:
            raise RegistryError(f"{platform!r} is not a platform this document defines")
        return _tree(self, platform)

    def declaration(self, declaration_id: str) -> Mapping[str, Any]:
        try:
            return self.declarations[declaration_id]
        except KeyError:
            raise RegistryError(f"the registry declares no {declaration_id!r}") from None

    def register(self, name: str) -> tuple[str, ...]:
        """The members of a refusal register, as §7.4 and §6.1 fix them."""
        try:
            return tuple(self.registers[name]["members"])
        except KeyError:
            raise RegistryError(f"the registry holds no register {name!r}") from None

    def constraints_for(self, scope: str) -> tuple[Mapping[str, Any], ...]:
        return tuple(rule for rule in self.constraints if rule.get("scope", "") == scope)

    # -- the identifiers ---------------------------------------------------

    def _known(self, identifier: str) -> str:
        if identifier not in self.diagnostics:
            raise RegistryError(
                f"{identifier} is not an id any generator emits; "
                "run tools/gen_error_ids.py, or the check is misnamed"
            )
        return identifier

    def declaration_id(self, declaration_id: str, check: str) -> str:
        """The id for a check that is a property of one declaration."""
        return self._known(f"ni.decl.{declaration_id}.{check}")

    def refusal_id(self, declaration_id: str, register: str) -> str:
        """The id for a key a declaration's refusal register turns away."""
        return self._known(f"ni.decl.{declaration_id}.refuses.{register.replace('_', '-')}")

    def constraint_id(self, rule: Mapping[str, Any]) -> str:
        """The id for a `[[constraints]]` row, formed as its generator forms it."""
        parts = (
            rule.get("scope", ""),
            rule["field"],
            rule["rule"].replace("_", "-"),
            rule.get("other", ""),
        )
        return self._known("ni.constraint." + ".".join(p for p in parts if p))

    def requirement_id(self, number: int | str) -> str:
        """The id for a §8.4 numbered requirement."""
        return self._known(f"ni.req.{number}")

    def advisory_id(self, number: str) -> str:
        """The id for a §8.5 advisory obligation, `S7` and the like."""
        return self._known(f"ni.adv.{number}")

    def about(self, identifier: str) -> Mapping[str, Any]:
        """Section, anchor, severity and summary for an id, for a diagnostic."""
        return self.diagnostics[self._known(identifier)]

    def profile_of(self, number: int | str) -> str:
        """§8.1's profile for a numbered requirement — core, android or ios."""
        return str(self.about(f"ni.req.{number}")["profile"])

    def requirements(self) -> tuple[int, ...]:
        return tuple(
            sorted(
                int(identifier.rsplit(".", 1)[1])
                for identifier in self.diagnostics
                if identifier.startswith("ni.req.")
            )
        )

    def advisories(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                identifier.rsplit(".", 1)[1]
                for identifier in self.diagnostics
                if identifier.startswith("ni.adv.")
            )
        )


def _tree(registry: Registry, platform: str) -> Node:
    located: dict[tuple[str, ...], tuple[str, Mapping[str, Any]]] = {}
    for declaration_id, properties in registry.declarations.items():
        if not _applies_to(declaration_id, platform):
            continue
        path = _document_path(declaration_id, platform)
        if path in located:
            raise RegistryError(
                f"{declaration_id!r} and {located[path][0]!r} both describe "
                f"{'.'.join(path)} on {platform}"
            )
        located[path] = (declaration_id, properties)

    def children_of(prefix: tuple[str, ...]) -> Mapping[str, Node]:
        depth = len(prefix)
        names = sorted(
            {path[depth] for path in located if len(path) > depth and path[:depth] == prefix}
        )
        built = {}
        for name in names:
            path = prefix + (name,)
            declaration_id, properties = located.get(path, ("", {}))
            built[name] = Node(
                id=declaration_id or ".".join(path),
                path=path,
                node=str(properties.get("node", "table")),
                properties=properties,
                children=children_of(path),
            )
        return built

    return Node(id="", path=(), node="table", children=children_of(()))


@lru_cache(maxsize=None)
def load() -> Registry:
    """Parse the registry once, and hand out the same one thereafter."""
    directory = contract_directory()
    contract = tomllib.loads((directory / "v1.toml").read_text(encoding="utf-8"))
    diagnostics_path = directory / "diagnostics-v1.toml"
    if not diagnostics_path.is_file():
        raise RegistryError(
            f"{diagnostics_path} is missing; run: python3 tools/gen_error_ids.py"
        )
    diagnostics = tomllib.loads(diagnostics_path.read_text(encoding="utf-8"))
    return Registry(
        meta=contract["meta"],
        declarations=contract["declarations"],
        registers=contract.get("registers", {}),
        constraints=tuple(contract.get("constraints", ())),
        diagnostics=diagnostics["diagnostics"],
    )
