#!/usr/bin/env python3
"""Consistency checks for SPEC.md, README.md and the worked examples.

These catch the failure mode this repository keeps hitting: a change that is
locally correct invalidates its immediate neighbour, and the neighbour is the
last thing anyone re-reads. Every check here corresponds to a defect that
actually shipped at least once.

Mechanical only. Nothing here can tell you a section contradicts itself; that
still needs reading.

    python3 tools/check_spec.py

Exits non-zero on the first failing category, listing every failure in it.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = (ROOT / "SPEC.md").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
EXAMPLES = sorted(
    [*ROOT.glob("examples/**/native.toml"), *ROOT.glob("development/examples/**/native.toml")]
)

RFC2119 = r"MUST NOT|MUST|SHOULD NOT|SHOULD|MAY"
failures: list[str] = []


def check(name: str, problems: list[str]) -> None:
    print(f"{'FAIL' if problems else 'ok  '}  {name}")
    for p in problems:
        print(f"        {p}")
    failures.extend(problems)


def toml_blocks(text: str) -> list[tuple[int, str]]:
    """Fenced ```toml blocks, with the 1-based line each starts on."""
    return [
        (text[: m.start()].count("\n") + 1, m.group(1))
        for m in re.finditer(r"```toml\n(.*?)```", text, re.S)
    ]


def keys_of(obj: dict) -> set[str]:
    out: set[str] = set()
    for k, v in obj.items():
        out.add(k)
        if isinstance(v, dict):
            out |= keys_of(v)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    out |= keys_of(item)
    return out


# --- 1. every § reference resolves ------------------------------------------
sections = {
    m.group(1) for m in re.finditer(r"^#{2,3}\s+(\d+(?:\.\d+)?)[.\s]", SPEC, re.M)
}
check(
    "§ references resolve",
    [f"§{r} referenced but no such section" for r in sorted(set(re.findall(r"§(\d+(?:\.\d+)?)", SPEC)) - sections)],
)

# --- 2. consumer requirements are sequential, and the index matches ----------
problems = []
try:
    block = SPEC.split("A conforming consumer **MUST**:")[1].split(
        "A conforming consumer **SHOULD**:"
    )[0]
    nums = [int(n) for n in re.findall(r"^(\d+)\.", block, re.M)]
    if nums != list(range(1, len(nums) + 1)):
        problems.append(f"requirement numbering is not 1..N: {nums}")
    index = SPEC.split("| Theme | Requirements |")[1].split("A conforming consumer")[0]
    listed = {int(n) for n in re.findall(r"\b(\d+)\b", index)}
    for missing in sorted(set(nums) - listed):
        problems.append(f"requirement {missing} is in no index theme")
    for phantom in sorted(listed - set(nums)):
        problems.append(f"index names requirement {phantom}, which does not exist")
    # The SHOULD list carries its own identifiers, referenced as 8.S1 and so on.
    advisory = SPEC.split("A conforming consumer **SHOULD**:")[1].split("\n## ")[0]
    letters = [int(n) for n in re.findall(r"^- \*\*S(\d+)\.\*\*", advisory, re.M)]
    if letters != list(range(1, len(letters) + 1)):
        problems.append(f"advisory numbering is not S1..SN: {letters}")
    for referenced in sorted(set(re.findall(r"requirement 8\.S(\d+)", SPEC))):
        if int(referenced) not in letters:
            problems.append(f"text references requirement 8.S{referenced}, which does not exist")
except IndexError:
    problems.append("could not locate the §8 requirement list or its index table")
check("§8 requirements sequential and fully indexed", problems)

# --- 3. every TOML block parses ---------------------------------------------
problems = []
for label, text in (("SPEC.md", SPEC), ("README.md", README)):
    for line, body in toml_blocks(text):
        try:
            tomllib.loads(body)
        except tomllib.TOMLDecodeError as exc:
            problems.append(f"{label}:{line} does not parse: {exc}")
check("TOML blocks parse", problems)

# --- 4. documented keys exist in the spec -----------------------------------
# Catches an example or a README block drifting after a schema change.
problems = []
for path in EXAMPLES:
    for key in keys_of(tomllib.loads(path.read_text(encoding="utf-8"))):
        if key not in SPEC:
            problems.append(f"{path.relative_to(ROOT)} uses `{key}`, absent from SPEC.md")
for line, body in toml_blocks(README):
    for key in keys_of(tomllib.loads(body)):
        # pyproject.toml fragments legitimately name the producer's own package
        if key not in SPEC and not key.startswith(("project", "tool")) and key != "kivmob":
            problems.append(f"README.md:{line} uses `{key}`, absent from SPEC.md")
check("keys used in examples and README exist in SPEC", problems)

# --- 5. RFC 2119 keywords are marked ----------------------------------------
# Bolded topic sentences (**… MUST …**) and prose about a keyword ("an
# unsatisfiable MUST") are both legitimate; anything else should carry its own
# emphasis. Code is masked first: R8 glob patterns such as `"okhttp3.**"` are
# not markdown, and a keyword inside an example is not a normative use.
def mask_code(text: str) -> str:
    out = list(text)
    for m in re.finditer(r"```.*?```", text, re.S):
        out[m.start() : m.end()] = " " * (m.end() - m.start())
    masked = "".join(out)
    for m in re.finditer(r"`[^`\n]*`", masked):
        out[m.start() : m.end()] = " " * (m.end() - m.start())
    return "".join(out)


prose = mask_code(SPEC)
bold_spans = [(m.start(), m.end()) for m in re.finditer(r"\*\*.+?\*\*", prose, re.S)]
problems = []
for m in re.finditer(rf"(?<!\*\*)\b({RFC2119})\b(?!\*\*)", prose):
    if any(a <= m.start() < b for a, b in bold_spans):
        continue  # inside a bolded sentence
    if re.search(r"\b(a|an|the|is|not|its)\s+(\w+\s+)?$", prose[max(0, m.start() - 40) : m.start()]):
        continue  # prose *about* the keyword
    line = SPEC[: m.start()].count("\n") + 1
    context = " ".join(SPEC[max(0, m.start() - 60) : m.end() + 30].split())
    problems.append(f"SPEC.md:{line} unmarked `{m.group(1)}`: …{context}…")
check("RFC 2119 keywords are emphasised", problems)

# --- 6. relative links resolve ----------------------------------------------
problems = []
for label, text, base in (
    ("README.md", README, ROOT),
    ("SPEC.md", SPEC, ROOT),
    ("examples/README.md", (ROOT / "examples/README.md").read_text(encoding="utf-8"), ROOT / "examples"),
    ("development/README.md", (ROOT / "development/README.md").read_text(encoding="utf-8"), ROOT / "development"),
    ("development/PROPOSALS.md", (ROOT / "development/PROPOSALS.md").read_text(encoding="utf-8"), ROOT / "development"),
    *(
        (str(n.relative_to(ROOT)), n.read_text(encoding="utf-8"), n.parent)
        for n in sorted(ROOT.glob("development/examples/**/NOTES.md"))
    ),
):
    for target in sorted(set(re.findall(r"\]\((?!https?:)([^)#]+)\)", text))):
        if not (base / target).exists():
            problems.append(f"{label} links to {target}, which does not exist")
    headings = {
        re.sub(r"[^a-z0-9 -]", "", h.lower()).replace(" ", "-")
        for h in re.findall(r"^#{1,6} (.+)$", text, re.M)
    }
    for anchor in sorted(set(re.findall(r"\]\(#([a-z0-9-]+)\)", text))):
        if anchor not in headings:
            problems.append(f"{label} links to #{anchor}, which matches no heading")
check("relative links and anchors resolve", problems)

# --- 7. sidecars obey the rules the spec states ------------------------------
# Applied to the worked examples *and* to every complete sidecar documented in
# SPEC.md or README.md, because a documented example that drifts from the schema
# is the same defect as an example file that does — and has shipped once.
problems = []
CREDENTIAL_SHAPED = re.compile(r"(password\s*=\s*\"|secret\s*=\s*\"|token\s*=\s*\"|sk\.[A-Za-z0-9]{8})", re.I)


def entries(container: dict, *path: str) -> list[dict]:
    """Array-of-tables at `path`, or [] — documented fragments are partial, and
    a fragment showing only a nested sub-table parses its parent as a table."""
    node = container
    for part in path:
        if not isinstance(node, dict):
            return []
        node = node.get(part)
    return [e for e in node if isinstance(e, dict)] if isinstance(node, list) else []


def is_skeleton(doc: dict) -> bool:
    """True when every array-of-tables entry is empty, as in §5's schema map."""
    found = []

    def walk(node):
        if isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for item in node:
                if isinstance(item, dict):
                    found.append(item)
                    walk(item)

    walk(doc)
    return bool(found) and all(not e for e in found)


def sidecar_sources():
    for path in EXAMPLES:
        raw = path.read_text(encoding="utf-8")
        yield str(path.relative_to(ROOT)), raw, tomllib.loads(raw)
    for label, text in (("SPEC.md", SPEC), ("README.md", README)):
        for line, body in toml_blocks(text):
            doc = tomllib.loads(body)
            # Only whole sidecars. §4.3 requires `contract`, so its presence is
            # the claim to be one; the documented fragments elsewhere are
            # deliberately partial and reference ids declared in other blocks.
            # §5's structure block also carries `contract` but is a skeleton of
            # empty tables — a map of the schema rather than a sidecar.
            if "contract" in doc and not is_skeleton(doc):
                yield f"{label}:{line}", body, doc


for rel, raw, doc in sidecar_sources():
    # §6.6 — a sidecar must never carry a credential
    if CREDENTIAL_SHAPED.search(raw):
        problems.append(f"{rel} contains something credential-shaped")

    android = doc.get("android", {})
    ios = doc.get("ios", {})

    # §4.5 — a platform table for a platform `platforms` omits is a contradiction
    declared = set(doc.get("platforms", ["android", "ios"]))
    for table in {"android", "ios"} & set(doc):
        if table not in declared:
            problems.append(f"{rel} has [{table}] but platforms={sorted(declared)}")

    # §6.5 — exactly one of coordinate/module, and a bounded range
    for dep in entries(android, "contributes", "gradle_dependencies"):
        if ("coordinate" in dep) == ("module" in dep):
            problems.append(f"{rel} gradle dependency needs exactly one of coordinate/module: {dep}")
        if "module" in dep and set(dep.get("version", {})) != {"at_least", "below"}:
            problems.append(f"{rel} module form needs a bounded version: {dep}")

    # §6.6 — reason required, and participation bounded
    for repo in entries(android, "contributes", "gradle_repositories"):
        if "reason" not in repo or not (repo.get("groups") or repo.get("modules")):
            problems.append(f"{rel} repository needs `reason` and groups/modules: {repo.get('url')}")

    # §6.3 — id + reason, and every inline reference resolves to a declared id
    ids = set()
    for value in entries(android, "requires", "application_values"):
        if not {"id", "reason"} <= set(value):
            problems.append(f"{rel} application value needs `id` and `reason`: {value}")
        if value.get("id") in ids:
            problems.append(f"{rel} declares application value id `{value.get('id')}` more than once")
        ids.add(value.get("id"))
    for ref in set(re.findall(r'application_value\s*=\s*"([^"]+)"', raw)):
        if ref not in ids:
            problems.append(f"{rel} inline reference `{ref}` matches no declared id")

    # §6.9 — keep_classes is owned-namespace only; a dependency's classes need
    #        an explicit [[r8.keep]] naming the dependency that owns them
    r8 = android.get("contributes", {}).get("r8", {})
    if isinstance(r8, dict):
        owned = android.get("owns", {}).get("java_namespaces", [])
        for pattern in r8.get("keep_classes", []) or []:
            base = pattern.rstrip("*").rstrip(".")
            if not any(base == o or base.startswith(o + ".") for o in owned):
                problems.append(
                    f"{rel} keep_classes `{pattern}` is not under an owned namespace "
                    f"{owned or '[]'} — a dependency's classes need [[r8.keep]]"
                )
        declared_deps = {
            d.get("coordinate", "").rsplit(":", 1)[0] or d.get("module")
            for d in entries(android, "contributes", "gradle_dependencies")
        }
        for keep in r8.get("keep", []) or []:
            if not isinstance(keep, dict):
                continue
            if not {"pattern", "from_dependency"} <= set(keep):
                problems.append(f"{rel} [[r8.keep]] needs `pattern` and `from_dependency`: {keep}")
            elif keep["from_dependency"] not in declared_deps:
                problems.append(
                    f"{rel} [[r8.keep]] names undeclared dependency `{keep['from_dependency']}`"
                )

    # §6.8 — view_links is activity-only and export-gated; intent_filters neither
    for comp in entries(android, "contributes", "components"):
        if comp.get("view_links"):
            if comp.get("kind") != "activity" or not comp.get("exported_required"):
                problems.append(f"{rel} view_links needs an exported activity: {comp.get('name')}")
        if comp.get("intent_filters"):
            if comp.get("exported_required") or comp.get("view_links"):
                problems.append(f"{rel} intent_filters must not be exported or carry view_links: {comp.get('name')}")
            for flt in comp["intent_filters"] if isinstance(comp["intent_filters"], list) else []:
                if set(flt) != {"action"}:
                    problems.append(f"{rel} intent filter takes only `action`: {flt}")

    # §7.3 — reason on every prerequisite; conditional ones state the condition;
    #        producer-local ids present and unique, since identity is
    #        (distribution, id) and an application answers on both
    for table in (
        "entitlements",
        "usage_descriptions",
        "app_extensions",
        "application_files",
        "url_schemes",
        "plist_capabilities",
    ):
        rows = entries(ios, "requires", table)
        if table in ("app_extensions", "url_schemes"):
            ids = [e.get("id") for e in rows]
            for entry in rows:
                if not entry.get("id"):
                    problems.append(f"{rel} {table} entry needs an `id`: {entry}")
            dupes = {i for i in ids if i and ids.count(i) > 1}
            for dupe in sorted(dupes):
                problems.append(f"{rel} declares {table} id `{dupe}` more than once")
        for entry in rows:
            if "reason" not in entry:
                problems.append(f"{rel} {table} entry needs a `reason`: {entry}")
            elif entry.get("conditional") and "only if" not in entry["reason"].lower():
                problems.append(f"{rel} conditional {table} `reason` must state the condition: {entry}")

    # §7.7 — a plain identifier, bound to a package the same sidecar declares
    packages = {p.get("name") for p in entries(ios, "contributes", "swift_packages")}
    for mod in entries(ios, "contributes", "python_modules"):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", mod.get("name", "")):
            problems.append(f"{rel} python module name must be a plain identifier: {mod.get('name')}")
        if mod.get("swift_package") not in packages:
            problems.append(f"{rel} python module names undeclared package: {mod.get('swift_package')}")

# module names are unique across the whole set, per §7.7
seen: dict[str, str] = {}
for path in EXAMPLES:
    doc = tomllib.loads(path.read_text(encoding="utf-8"))
    for mod in entries(doc.get("ios", {}), "contributes", "python_modules"):
        name = mod.get("name")
        if name in seen:
            problems.append(f"module `{name}` declared by both {seen[name]} and {path.name}")
        seen[name] = path.name
check("sidecars and documented examples obey the spec's own rules", problems)

# --- 8. §2.2's illustrative app-side blocks stay app-side --------------------
problems = []
illustrative = re.search(
    r"\*\*Illustrative only\*\*.*?(?=\n## )", SPEC, re.S
)
if illustrative:
    for line, body in toml_blocks(illustrative.group(0)):
        is_app = "pyproject.toml" in body
        tables = re.findall(r"^\[+([a-z][^\]]*)\]+", body, re.M)
        for table in tables:
            root = table.split(".")[0]
            if is_app and root != "tool":
                problems.append(f"§2.2 app-side example declares [{table}], which is not [tool.*]")
            if not is_app and root == "tool":
                problems.append(f"§2.2 sidecar example declares [{table}], which belongs to the application")
check("§2.2 keeps sidecar and application examples distinct", problems)

# --- 9. the declaration reference covers every documented key ----------------
# A reference table that silently omits a new key is worse than none, so it is
# checked against the keys the specification's own examples use.
#
# One-directional, deliberately: this catches a key added without a reference
# entry, not an entry left behind after a key is removed. The reverse needs
# context a whole-document scan does not have — when `application_values` moved
# from `name` to `id`, `name` was still legitimately in four other tables.
problems = []
try:
    appendix = SPEC.split("## Appendix D: declaration reference")[1].split("\n## ")[0]
    documented: set[str] = set()
    for _, body in toml_blocks(SPEC):
        table = None
        for raw_line in body.splitlines():
            line = raw_line.strip()
            if line.startswith("["):
                table = line.strip("[]").split("]")[0]
            elif "=" in line and not line.startswith("#") and table is not None:
                root = table.split(".")[0]
                # info_plist children are the application's plist keys, not schema
                if root in ("android", "ios") and not table.startswith(
                    ("ios.contributes.info_plist.values", "ios.contributes.info_plist.append")
                ):
                    documented.add(line.split("=")[0].strip())
    for key in sorted(documented):
        if f"`{key}`" not in appendix:
            problems.append(f"Appendix D does not list `{key}`")
except IndexError:
    problems.append("Appendix D is missing")
check("declaration reference covers every documented key", problems)


# --- 10. the paired application example answers its sidecar -----------------
# examples/pystripe/ carries both halves of §2.2. If the sidecar grows a
# requirement, the application half must answer it or the pair stops teaching
# the thing it exists to teach.
problems = []
pair_dir = ROOT / "examples" / "pystripe"
app_path = pair_dir / "app-pyproject.toml"
if app_path.exists():
    app = tomllib.loads(app_path.read_text(encoding="utf-8"))
    side = tomllib.loads((pair_dir / "native.toml").read_text(encoding="utf-8"))
    tool = app.get("tool", {}).get("examplebuild", {})
    per_pkg = tool.get("native", {}).get("pystripe", {})

    for stray in set(app) - {"project", "tool"}:
        problems.append(f"app-pyproject.toml declares [{stray}] — it is not a sidecar")

    declared = {v.get("id") for v in entries(side.get("android", {}), "requires", "application_values")}
    answered = set(per_pkg.get("android", {}).get("application_values", {}))
    for miss in sorted(declared - answered):
        problems.append(f"app-pyproject.toml does not supply application value `{miss}`")

    exported = {
        c.get("name")
        for c in entries(side.get("android", {}), "contributes", "components")
        if c.get("exported_required")
    }
    approved = set(per_pkg.get("android", {}).get("allow_exported", []))
    for miss in sorted(exported - approved):
        problems.append(f"app-pyproject.toml does not approve exported component `{miss}`")

    schemes = {u.get("id") for u in entries(side.get("ios", {}), "requires", "url_schemes")}
    acked = set(per_pkg.get("ios", {}).get("acknowledged", []))
    for miss in sorted(schemes - acked):
        problems.append(f"app-pyproject.toml does not acknowledge url_scheme `{miss}`")

    floors = side.get("android", {}).get("requires", {})
    app_android = tool.get("android", {})
    for key in ("min_sdk", "compile_sdk", "target_sdk"):
        if key in floors and app_android.get(key, 0) < floors[key]:
            problems.append(f"app-pyproject.toml {key}={app_android.get(key)} is below pystripe's floor {floors[key]}")
else:
    problems.append("examples/pystripe/app-pyproject.toml is missing")
check("the paired application example answers its sidecar", problems)


print()
if failures:
    print(f"{len(failures)} problem(s) found.")
    sys.exit(1)
print("All checks passed.")
