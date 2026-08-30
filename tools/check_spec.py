#!/usr/bin/env python3
"""Consistency checks for SPEC.md, its predecessor, README.md and the examples.

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

import json
import re
import sys
import textwrap
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW = (ROOT / "SPEC.md").read_text(encoding="utf-8")
SPEC = (ROOT / "development" / "first-attempt.md").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")

#: Both specifications, for the checks that apply to any document of this shape.
#: The first attempt is frozen, so nothing there should drift — but its links
#: still break if a file moves, and the checks cost nothing to keep running.
DOCS = (("SPEC.md", NEW), ("development/first-attempt.md", SPEC))
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


def fenced(text: str, lang: str) -> list[tuple[int, str]]:
    """Fenced blocks of one language, with the 1-based line each starts on.

    A fence inside a blockquote carries the quote marker on every line; strip it
    before parsing, or a legitimate example in a Note reads as a syntax error.
    """
    out = []
    for m in re.finditer(rf"(?:^|\n)((?:> )?)```{lang}\n(.*?)\n\1?```", text, re.S):
        quoted, body = m.group(1), m.group(2)
        if quoted:
            body = "\n".join(re.sub(r"^> ?", "", line) for line in body.split("\n"))
        out.append((text[: m.start()].count("\n") + 2, body))
    return out


def toml_blocks(text: str) -> list[tuple[int, str]]:
    return fenced(text, "toml")


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
problems = []
for label, text in DOCS:
    sections = {
        m.group(1) for m in re.finditer(r"^#{2,3}\s+(\d+(?:\.\d+)?)[.\s]", text, re.M)
    }
    for r in sorted(set(re.findall(r"§(\d+(?:\.\d+)?)", text)) - sections):
        problems.append(f"{label}: §{r} referenced but no such section")
check("§ references resolve", problems)

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
for label, text in (*DOCS, ("README.md", README)):
    for line, body in toml_blocks(text):
        try:
            tomllib.loads(body)
        except tomllib.TOMLDecodeError as exc:
            problems.append(f"{label}:{line} does not parse: {exc}")
    for line, body in fenced(text, "json"):
        try:
            json.loads(body)
        except json.JSONDecodeError as exc:
            problems.append(f"{label}:{line} is not valid JSON: {exc}")
check("TOML and JSON blocks parse", problems)

# --- 3b. §9.3's digest form, in the record SPEC.md offers as a worked example -
# The canonical form is 64 lowercase hex characters, unprefixed. An appendix
# that abbreviates them teaches the one thing a record cannot afford: two
# consumers eliding to different lengths produce records that never compare.
problems = []
DIGEST_KEYS = ("artifacts", "inputs", "swift_binaries")
for line, body in fenced(NEW, "json"):
    record = json.loads(body)
    for dist in record.get("distributions", []):
        for key in DIGEST_KEYS:
            for name, digest in (dist.get(key) or {}).items():
                if not re.fullmatch(r"[0-9a-f]{64}", str(digest)):
                    problems.append(
                        f"SPEC.md:{line} {key}[{name}] is {digest!r}, not 64 lowercase hex"
                    )
check("record digests are written in §9.3's canonical form", problems)

# --- 4. documented keys exist in the spec -----------------------------------
# Catches an example or a README block drifting after a schema change.
problems = []
for path in EXAMPLES:
    for key in keys_of(tomllib.loads(path.read_text(encoding="utf-8"))):
        if key not in SPEC:
            problems.append(f"{path.relative_to(ROOT)} uses `{key}`, absent from first-attempt.md")
for line, body in toml_blocks(README):
    doc = tomllib.loads(body)
    # A `[project]` or `[tool.*]` fragment is the package's own build
    # configuration — backend keys and its own distribution name, none of it
    # this convention's vocabulary. Everything else is sidecar keys, and
    # README documents the current specification, so they are SPEC.md's.
    if doc.keys() & {"project", "tool"}:
        continue
    for key in keys_of(doc):
        if key not in NEW:
            problems.append(f"README.md:{line} uses `{key}`, absent from SPEC.md")
check("keys used in examples and README exist in their specification", problems)

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


problems = []
for label, text in DOCS:
    prose = mask_code(text)
    bold_spans = [(m.start(), m.end()) for m in re.finditer(r"\*\*.+?\*\*", prose, re.S)]
    for m in re.finditer(rf"(?<!\*\*)\b({RFC2119})\b(?!\*\*)", prose):
        if any(a <= m.start() < b for a, b in bold_spans):
            continue  # inside a bolded sentence
        if re.search(r"\b(a|an|the|is|not|its)\s+(\w+\s+)?$", prose[max(0, m.start() - 40) : m.start()]):
            continue  # prose *about* the keyword
        line = text[: m.start()].count("\n") + 1
        context = " ".join(text[max(0, m.start() - 60) : m.end() + 30].split())
        problems.append(f"{label}:{line} unmarked `{m.group(1)}`: …{context}…")
check("RFC 2119 keywords are emphasised", problems)

# --- 5b. rationale states no requirement ------------------------------------
# The contents block tells a reader that indented blocks are rationale and that
# skipping them loses nothing binding. That is only safe if it is true: a
# normative keyword inside one is a requirement a reader was invited to skip.
problems = []
for label, text in DOCS:
    quotes, cur, start = [], [], 0
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith(">"):
            if not cur:
                start = i
            cur.append(line[1:])
        elif cur:
            quotes.append((start, " ".join(cur)))
            cur = []
    for line, body in quotes:
        for kw in re.findall(rf"\*\*({RFC2119})\*\*", re.sub(r"`[^`]*`", " ", body)):
            problems.append(f"{label}:{line} rationale block states a normative `{kw}`")
check("rationale blocks state no requirement", problems)

# --- 6. relative links resolve ----------------------------------------------
def heading_anchors(text: str) -> set[str]:
    """The anchors GitHub would generate, its -1/-2 disambiguation included.

    Two sections here call a subsection "Common rules"; the second one's anchor
    is `common-rules-1`, and a contents entry linking to the bare form points
    silently at the first. Fenced blocks are blanked first, since a
    `# producer's native.toml` comment is not a heading.
    """
    body = re.sub(
        r"```.*?```", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S
    )
    seen: dict[str, int] = {}
    found: set[str] = set()
    for heading in re.findall(r"^#{1,6} (.+)$", body, re.M):
        base = re.sub(r"[^a-z0-9 -]", "", heading.lower()).replace(" ", "-")
        nth = seen.get(base, 0)
        seen[base] = nth + 1
        found.add(base if nth == 0 else f"{base}-{nth}")
    return found


problems = []
for label, text, base in (
    ("SPEC.md", NEW, ROOT),
    ("README.md", README, ROOT),
    ("development/first-attempt.md", SPEC, ROOT / "development"),
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
    headings = heading_anchors(text)
    for anchor in sorted(set(re.findall(r"\]\(#([a-z0-9-]+)\)", text))):
        if anchor not in headings:
            problems.append(f"{label} links to #{anchor}, which matches no heading")
check("relative links and anchors resolve", problems)

# --- 7. sidecars obey the rules the spec states ------------------------------
# Applied to the worked examples *and* to every complete sidecar documented in
# first-attempt.md or README.md, because a documented example that drifts from the schema
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


def literal_prefix(pattern: str) -> str:
    """The part of a shrinker keep pattern that §6.7 compares to a namespace.

    The longest leading run of complete dot-separated segments containing no
    wildcard, so `org.example.mypkg.**` yields `org.example.mypkg` and
    `org.example.my*.Foo` yields `org.example` — which an owned
    `org.example.mypkg` does not contain, and which is the point.
    """
    kept: list[str] = []
    for segment in pattern.split("."):
        if "*" in segment or "?" in segment:
            break
        kept.append(segment)
    return ".".join(kept)


def sidecar_sources():
    for path in EXAMPLES:
        raw = path.read_text(encoding="utf-8")
        yield str(path.relative_to(ROOT)), raw, tomllib.loads(raw)
    for label, text in (("first-attempt.md", SPEC),):
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
            base = literal_prefix(pattern)
            if not base or not any(base == o or base.startswith(o + ".") for o in owned):
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


# --- 11. SPEC.md is finished ------------------------------------------------
# A stub that survives into a release is a section a reader trusts and finds
# empty. This is the cheapest possible guard against that.
check(
    "SPEC.md has no unwritten sections",
    [f"SPEC.md still says {m.group(0)!r}" for m in re.finditer(r"\*To be (?:ported|written)[^*]*\*", NEW)],
)

# --- 12. SPEC.md's §8 is numbered 1..N and wholly indexed -------------------
# The thematic index exists so an implementer can find the requirements for one
# concern. A requirement in no theme is one nobody arrives at on purpose.
problems = []
try:
    body = NEW.split("A conforming consumer **MUST**:")[1].split("### 8.5")[0]
    nums = [int(n) for n in re.findall(r"^(\d+)\.\s", body, re.M)]
    if nums != list(range(1, len(nums) + 1)):
        problems.append(f"§8.3 numbering is not 1..N: {nums}")
    index = NEW.split("### 8.3 Thematic index")[1].split("### 8.4")[0]
    listed: set[int] = set()
    for lo, hi in re.findall(r"\b(\d+)(?:[–-](\d+))?\b", index):
        listed |= set(range(int(lo), int(hi or lo) + 1))
    for missing in sorted(set(nums) - listed):
        problems.append(f"requirement {missing} is in no index theme")
    for phantom in sorted(listed - set(nums)):
        problems.append(f"the index names requirement {phantom}, which does not exist")
    advisory = [int(n) for n in re.findall(r"\*\*S(\d+)\*\*", NEW.split("### 8.5")[1])]
    if advisory != list(range(1, len(advisory) + 1)):
        problems.append(f"advisory numbering is not S1..SN: {advisory}")
except IndexError:
    problems.append("could not locate §8's requirement list, index, or advisory table")
check("SPEC.md §8 is sequential and fully indexed", problems)

# --- 12b. the conformance profiles cover every requirement, once ------------
# A requirement in no profile binds nobody; one in two profiles is ambiguous
# unless it is deliberately shared, which only the core row is.
problems = []
try:
    profiles = NEW.split("### 8.1 Conformance is per platform")[1].split("### 8.2")[0]
    rows = dict(re.findall(r"\| \*\*(?:Core|Android|iOS)\*\*([^|]*)\|([^|]*)\|", profiles))
    seen: dict[int, int] = {}
    for _, cell in re.findall(r"\| (\*\*(?:Core|Android|iOS)\*\*[^|]*)\|([^|]*)\|", profiles):
        for lo, hi in re.findall(r"\b(\d+)(?:[–-](\d+))?\b", cell):
            for n in range(int(lo), int(hi or lo) + 1):
                seen[n] = seen.get(n, 0) + 1
    nums = set(int(n) for n in re.findall(r"^(\d+)\.\s", body, re.M))
    for missing in sorted(nums - set(seen)):
        problems.append(f"requirement {missing} is in no conformance profile")
    for phantom in sorted(set(seen) - nums):
        problems.append(f"a profile names requirement {phantom}, which does not exist")
except IndexError:
    problems.append("could not locate the conformance profile table")
check("SPEC.md §8's profiles cover every requirement", problems)

# --- 13. §8 cites every section that binds a consumer -----------------------
# §8 claims to restate §§2-7 and §9. A section carrying a consumer obligation
# that §8 never cites is one an implementer working from the checklist misses.
cited = set(re.findall(r"§(\d+(?:\.\d+)?)", NEW[NEW.index("## 8. Consuming") : NEW.index("## 9. Recording")]))
problems = []
parts = re.split(r"^(#{2,3} (\d+(?:\.\d+)?)\.? .+)$", mask_code(NEW), flags=re.M)
for i in range(1, len(parts), 3):
    num, section = parts[i + 1], " ".join(parts[i + 2].split())
    if num.startswith("8") or num in cited:
        continue
    # "a consumer MUST …" binds one; "the slots are the consumer's, and a
    # producer MUST NOT …" does not. Require the keyword to follow the subject.
    if re.search(rf"consumer\s+(?:\w+\s+){{0,2}}\*\*({RFC2119})\*\*", section):
        problems.append(f"§{num} binds a consumer and §8 never cites it")
check("§8 cites every section that binds a consumer", problems)

# --- 14. the declaration reference covers SPEC.md's own examples ------------
# Appendix B is the contract-minor registry §4.3 rests on: a key missing from it
# has no recorded revision, so the under-declaration rule cannot be applied.
appendix_b = NEW[NEW.index("## Appendix B") : NEW.index("## Appendix C")]
declared: set[str] = set()
for _, block in toml_blocks(NEW):
    try:
        doc = tomllib.loads(block)
    except tomllib.TOMLDecodeError:
        continue
    # An application's own configuration and a producer's pyproject.toml are
    # illustrations of the consumer's spelling, not sidecar keys: their leaves
    # are distribution names and value ids, which no registry could list.
    if doc.keys() & {"tool", "project"}:
        continue
    declared |= keys_of(doc)
problems = [
    f"`{k}` appears in a SPEC.md sidecar example but not in Appendix B"
    for k in sorted(declared)
    if k not in appendix_b and k.islower() and "." not in k
]
check("Appendix B covers every key SPEC.md declares", problems)

# --- 15. the converted sidecars validate against the current specification --
# An example nothing checks is a claim about the specification that nobody is
# testing — which is how the probe's own Airship sidecar carried fields that had
# been removed from the model weeks earlier.
def check_v1_sidecar(rel: str, raw: str, doc: dict, problems: list[str]) -> None:
    """Every rule SPEC.md states that a sidecar alone can be checked against."""
    if doc.get("contract") != "1":
        problems.append(f"{rel} declares contract {doc.get('contract')!r}, not \"1\"")
    for key in sorted(keys_of(doc)):
        if key in {"contract", "platforms"} or not key.islower() or "." in key:
            continue
        if key not in appendix_b:
            problems.append(f"{rel} uses `{key}`, which Appendix B does not list")

    # §5 — one `id` per platform table, across values and actions alike
    for platform in ("android", "ios"):
        table = doc.get(platform, {})
        values = entries(table, "requires", "application_value")
        actions = entries(table, "requires", "application_action")
        ids = [r.get("id") for r in (*values, *actions)]
        for dupe in sorted({i for i in ids if i and ids.count(i) > 1}):
            problems.append(f"{rel} [{platform}] declares requirement id `{dupe}` more than once")

        # §5.5 — `key` belongs to every kind but `inline`, and an `inline`
        # value is consumed by a view_links reference or an action's `uses`
        used = {u for a in actions for u in a.get("uses", [])}
        referenced = set(re.findall(r'application_value\s*=\s*"([^"]+)"', raw))
        declared = {v.get("id") for v in values}
        for ident in sorted(used - declared):
            problems.append(f"{rel} [{platform}] action `uses` undeclared value `{ident}`")
        for value in values:
            kind, ident = value.get("kind"), value.get("id")
            if kind == "inline":
                if "key" in value:
                    problems.append(f"{rel} inline value `{ident}` declares a `key`")
                if ident not in used | referenced:
                    problems.append(
                        f"{rel} inline value `{ident}` is neither referenced nor `uses`d"
                    )
            elif "key" not in value:
                problems.append(f"{rel} value `{ident}` of kind `{kind}` needs a `key`")
            elif ident in referenced:
                # §5.5 — an inline reference resolves only to a kind `inline`
                # value; any other kind already has a delivery site of its own.
                problems.append(
                    f"{rel} inline reference names `{ident}`, of kind `{kind}` rather than inline"
                )
            if kind == "usage_description" and not value.get("key", "").endswith(
                "UsageDescription"
            ):
                problems.append(f"{rel} usage_description `{ident}` names `{value.get('key')}`")
            if kind == "info_plist" and value.get("key", "").endswith("UsageDescription"):
                problems.append(
                    f"{rel} info_plist value `{ident}` names a usage-description key"
                )

    # §5.1 — Android floors are integers; TOML booleans are not
    for platform, keys in (("android", ("min_sdk", "compile_sdk", "target_sdk")),):
        floors = doc.get(platform, {}).get("requires", {})
        for key in keys:
            if key in floors and not (
                isinstance(floors[key], int) and not isinstance(floors[key], bool)
            ):
                problems.append(f"{rel} {key} is {floors[key]!r}, not an integer")
    target = doc.get("ios", {}).get("requires", {}).get("deployment_target")
    if target is not None and not re.fullmatch(r"[0-9]+(\.[0-9]+){0,2}", str(target)):
        problems.append(f"{rel} deployment_target {target!r} is malformed")

    # §5.5, §7.4 — the keys a producer may not reach through an Info.plist value
    REFUSED_PLIST = {
        "UIBackgroundModes",
        "UIRequiredDeviceCapabilities",
        "CFBundleURLTypes",
        "NSUserActivityTypes",
        "CFBundleIdentifier",
        "CFBundleShortVersionString",
        "CFBundleVersion",
        "MinimumOSVersion",
    }
    for value in entries(doc.get("ios", {}), "requires", "application_value"):
        if value.get("kind") == "info_plist" and value.get("key") in REFUSED_PLIST:
            problems.append(f"{rel} info_plist value writes refused key `{value.get('key')}`")

    # §5.5 — the Platform column is normative: a kind belongs to one table
    KIND_PLATFORM = {
        "manifest_meta_data": "android",
        "manifest_placeholder": "android",
        "info_plist": "ios",
        "usage_description": "ios",
        "inline": None,
    }
    for platform in ("android", "ios"):
        for value in entries(doc.get(platform, {}), "requires", "application_value"):
            kind = value.get("kind")
            if kind not in KIND_PLATFORM:
                problems.append(f"{rel} value `{value.get('id')}` has unknown kind `{kind}`")
            elif KIND_PLATFORM[kind] not in (None, platform):
                problems.append(
                    f"{rel} [{platform}] value `{value.get('id')}` uses `{kind}`, "
                    f"which belongs to [{KIND_PLATFORM[kind]}]"
                )

    # §7.4 — one key belongs to one mode, and neither mode admits a refused key
    plist = doc.get("ios", {}).get("contributes", {}).get("info_plist", {})
    if isinstance(plist, dict):
        scalar, arrays = plist.get("values", {}) or {}, plist.get("append", {}) or {}
        # a value of kind `info_plist` writes one string, so it is a scalar
        # claim on that key like any `values` entry
        delivered = {
            v.get("key")
            for v in entries(doc.get("ios", {}), "requires", "application_value")
            if v.get("kind") == "info_plist"
        }
        for key in sorted((set(scalar) | delivered) & set(arrays)):
            problems.append(f"{rel} claims `{key}` as both an array and a scalar")
        for key in sorted((set(scalar) | set(arrays)) & REFUSED_PLIST):
            problems.append(f"{rel} contributes refused Info.plist key `{key}`")

    # §6.6 — a view_links attribute converts to a platform name mechanically
    for comp in entries(doc.get("android", {}), "contributes", "components"):
        for link in comp.get("view_links", []) or []:
            for attr, val in link.items():
                if not re.fullmatch(r"[a-z][a-z0-9]*(_[a-z0-9]+)*", attr):
                    problems.append(f"{rel} view_links attribute `{attr}` has no conversion")
                if not isinstance(val, (str, dict)):
                    problems.append(f"{rel} view_links `{attr}` is not a string or inline ref")

    # §6.4, §7.2 — repositories and packages are https, and a package states
    # the products it is linked for
    for repo in entries(doc.get("android", {}), "contributes", "gradle_repositories"):
        if not repo.get("url", "").startswith("https://"):
            problems.append(f"{rel} repository url is not https: {repo.get('url')}")
    for pkg in entries(doc.get("ios", {}), "contributes", "swift_packages"):
        if not pkg.get("url", "").startswith("https://"):
            problems.append(f"{rel} swift package url is not https: {pkg.get('url')}")
        if not pkg.get("products"):
            problems.append(f"{rel} swift package `{pkg.get('name')}` declares no products")
problems = []
for path in sorted((ROOT / "development" / "redesign" / "examples").rglob("*.toml")):
    raw = path.read_text(encoding="utf-8")
    try:
        doc = tomllib.loads(raw)
    except tomllib.TOMLDecodeError as exc:
        problems.append(f"{path.relative_to(ROOT)} does not parse: {exc}")
        continue
    if doc.keys() & {"tool", "project"}:
        continue  # an application's own configuration, not a sidecar
    check_v1_sidecar(str(path.relative_to(ROOT)), raw, doc, problems)

# README.md documents the current specification, so its whole sidecars are held
# to it too — the same rules, the same failures, one source of truth for both.
for line, body in toml_blocks(README):
    doc = tomllib.loads(body)
    if "contract" in doc and not (doc.keys() & {"tool", "project"}):
        check_v1_sidecar(f"README.md:{line}", body, doc, problems)

check("sidecars in the redesign examples and README obey SPEC.md", problems)

# --- 16. the registry regenerates its three targets without a diff ----------
# The drift guard. Without it `contract/v1.toml` is a second source of truth
# rather than the source of truth: a key edited in Appendix B by hand, or a
# rule added to §8 without a diagnostic ID, would pass everything above.
sys.path.insert(0, str(ROOT / "tools"))

import gen_appendix_b  # noqa: E402
import gen_error_ids  # noqa: E402
import gen_schema  # noqa: E402

REGISTRY = tomllib.loads((ROOT / "contract" / "v1.toml").read_text(encoding="utf-8"))
DIAGNOSTICS = tomllib.loads(
    (ROOT / "contract" / "diagnostics-v1.toml").read_text(encoding="utf-8")
)["diagnostics"]

problems = []
if gen_appendix_b.rewritten(NEW, gen_appendix_b.build(REGISTRY["declarations"])) != NEW:
    problems.append("SPEC.md Appendix B — run: python3 tools/gen_appendix_b.py")
if (
    json.dumps(gen_schema.build(REGISTRY), indent=2, sort_keys=False) + "\n"
    != (ROOT / "schema" / "native-integration-v1.schema.json").read_text(encoding="utf-8")
):
    problems.append("schema/native-integration-v1.schema.json — run: python3 tools/gen_schema.py")
if gen_error_ids.build() != (ROOT / "contract" / "diagnostics-v1.toml").read_text(encoding="utf-8"):
    problems.append("contract/diagnostics-v1.toml — run: python3 tools/gen_error_ids.py")
check("the registry's generated targets are current", problems)

# --- 17. the registry agrees with SPEC.md ------------------------------------
# Anchors, because a section link that does not resolve makes `explain` useless;
# and the closed vocabularies, because Appendix B's own introduction names six
# and §4.3's under-declaration rule is checked against exactly those.
problems = []
anchors = heading_anchors(NEW)
for declaration_id, entry in REGISTRY["declarations"].items():
    if entry["anchor"] not in anchors:
        problems.append(f"{declaration_id} cites #{entry['anchor']}, which SPEC.md has no heading for")
for name, register in REGISTRY["registers"].items():
    if register["anchor"] not in anchors:
        problems.append(f"register {name} cites #{register['anchor']}, which SPEC.md has no heading for")

closed = {i for i, e in REGISTRY["declarations"].items() if e.get("closed")}
expected_closed = {
    "platforms",
    "<platform>.requires.application_value.kind",
    "android.contributes.gradle_dependencies.configuration",
    "android.contributes.components.kind",
    "ios.contributes.swift_packages.requirement",
}
if closed != expected_closed:
    problems.append(
        f"the registry's closed vocabularies are {sorted(closed)}; Appendix B names "
        f"{sorted(expected_closed)} plus §7.4's capability keys, which are a register"
    )
if not REGISTRY["registers"]["capability_keys"].get("closed"):
    problems.append("§7.4's capability keys are a closed list and the register does not say so")
check("the registry agrees with SPEC.md's anchors and closed vocabularies", problems)

# --- 18. every current-specification sidecar validates against the schema ----
# `examples/` is deliberately not here: it still holds the first attempt's
# sidecar, which `development/redesign/examples/` is the current-model
# conversion of. See development/findings/phase1-registry.md.
SCHEMA = json.loads((ROOT / "schema" / "native-integration-v1.schema.json").read_text(encoding="utf-8"))
problems = []
try:
    from jsonschema import Draft202012Validator

    Draft202012Validator.check_schema(SCHEMA)
    validator = Draft202012Validator(SCHEMA)

    sidecars = [
        (str(p.relative_to(ROOT)), tomllib.loads(p.read_text(encoding="utf-8")))
        for p in sorted((ROOT / "development" / "redesign" / "examples").rglob("native.toml"))
    ]
    appendix_a = NEW[NEW.index("## Appendix A") : NEW.index("## Appendix B")]
    for line, body in toml_blocks(appendix_a):
        sidecars.append((f"SPEC.md Appendix A:{line}", tomllib.loads(body)))
    for line, body in toml_blocks(README):
        doc = tomllib.loads(body)
        if "contract" in doc and not (doc.keys() & {"tool", "project"}):
            sidecars.append((f"README.md:{line}", doc))

    for label, doc in sidecars:
        for error in sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path)):
            where = ".".join(str(p) for p in error.absolute_path) or "<root>"
            problems.append(f"{label} fails the schema at {where}: {error.message}")
except ImportError:  # pragma: no cover - the check degrades rather than lying
    problems.append("jsonschema is not installed, so the schema was not exercised")
check("every current-specification sidecar validates against the generated schema", problems)

# --- 19. the schema refuses what it claims to refuse -------------------------
# A schema nothing is known to fail is a schema that might accept anything.
#
# Each case names the instance path and the JSON Schema keyword that must
# reject it. Asserting only "this document is invalid" is too weak: several of
# these violate more than one rule, so removing the rule under test would leave
# the case failing for an unrelated reason and the regression would not show.
#
# TOML_STRICT is the validator used here, and it is deliberately stricter than
# the published schema. JSON Schema defines `integer` as any number with a zero
# fractional part, so a standard validator accepts `min_sdk = 24.0` where §5.1
# rejects it — "`24.0` is a float". A schema cannot express TOML's lexical
# integer/float distinction at all, so `gen_schema.py` records the gap in the
# schema's own description and §8 requirement 12 puts the check in a consumer's
# code. This repository's own gate does not have to be that lenient.
def _toml_integer(checker, instance):
    return isinstance(instance, int) and not isinstance(instance, bool)


def _toml_float(checker, instance):
    return isinstance(instance, float)


MUST_FAIL: dict[str, tuple[str, str, str]] = {
    # closed vocabularies and forms
    "a Gradle configuration outside the closed set": (
        '''contract = "1"
        [[android.contributes.gradle_dependencies]]
        coordinate = "g:a:1"
        configuration = "kapt"''',
        "android.contributes.gradle_dependencies.0.configuration", "enum",
    ),
    "a component kind outside the closed set": (
        '''contract = "1"
        [[android.contributes.components]]
        kind = "provider"
        name = "org.example.P"''',
        "android.contributes.components.0.kind", "enum",
    ),
    "a branch Swift requirement": (
        '''contract = "1"
        [[ios.contributes.swift_packages]]
        name = "P"
        url = "https://example.com/p"
        products = ["P"]
        requirement = { branch = "main" }''',
        "ios.contributes.swift_packages.0.requirement", "additionalProperties",
    ),
    "two Swift requirement forms at once": (
        '''contract = "1"
        [[ios.contributes.swift_packages]]
        name = "P"
        url = "https://example.com/p"
        products = ["P"]
        requirement = { exact = "1.0.0", from = "1.0.0" }''',
        "ios.contributes.swift_packages.0.requirement", "maxProperties",
    ),
    "a platform name this document does not define": (
        '''contract = "1"
        platforms = ["web"]''',
        "platforms.0", "enum",
    ),

    # the two dependency forms
    "both coordinate and module": (
        '''contract = "1"
        [[android.contributes.gradle_dependencies]]
        coordinate = "g:a:1"
        module = "g:a"
        version = { at_least = "1", below = "2" }''',
        "android.contributes.gradle_dependencies.0", "oneOf",
    ),
    "neither coordinate nor module": (
        '''contract = "1"
        [[android.contributes.gradle_dependencies]]
        configuration = "api"''',
        "android.contributes.gradle_dependencies.0", "oneOf",
    ),
    "a version range open at one end": (
        '''contract = "1"
        [[android.contributes.gradle_dependencies]]
        module = "g:a"
        version = { at_least = "1" }''',
        "android.contributes.gradle_dependencies.0.version", "required",
    ),
    "a module with no version": (
        '''contract = "1"
        [[android.contributes.gradle_dependencies]]
        module = "g:a"''',
        "android.contributes.gradle_dependencies.0", "required",
    ),
    "a coordinate with no version component": (
        '''contract = "1"
        [[android.contributes.gradle_dependencies]]
        coordinate = "g:a"''',
        "android.contributes.gradle_dependencies.0.coordinate", "pattern",
    ),
    "a dynamic version inside a coordinate": (
        '''contract = "1"
        [[android.contributes.gradle_dependencies]]
        coordinate = "g:a:+"''',
        "android.contributes.gradle_dependencies.0.coordinate", "pattern",
    ),
    "a changing version inside a coordinate": (
        '''contract = "1"
        [[android.contributes.gradle_dependencies]]
        coordinate = "g:a:1.0-SNAPSHOT"''',
        "android.contributes.gradle_dependencies.0.coordinate", "pattern",
    ),
    "a range spelled inside a coordinate": (
        '''contract = "1"
        [[android.contributes.gradle_dependencies]]
        coordinate = "g:a:[1.0,2.0)"''',
        "android.contributes.gradle_dependencies.0.coordinate", "pattern",
    ),
    "a module that is not group:artifact": (
        '''contract = "1"
        [[android.contributes.gradle_dependencies]]
        module = "notacoordinate"
        version = { at_least = "1", below = "2" }''',
        "android.contributes.gradle_dependencies.0.module", "pattern",
    ),
    "a changing version in a bound": (
        '''contract = "1"
        [[android.contributes.gradle_dependencies]]
        module = "g:a"
        version = { at_least = "1.0-SNAPSHOT", below = "2" }''',
        "android.contributes.gradle_dependencies.0.version.at_least", "pattern",
    ),

    # value kinds, keys and the platform column
    "an iOS value kind inside the Android table": (
        '''contract = "1"
        [[android.requires.application_value]]
        id = "x"
        kind = "info_plist"
        key = "K"
        reason = "r"''',
        "android.requires.application_value.0.kind", "enum",
    ),
    "a `key` on an inline value": (
        '''contract = "1"
        [[ios.requires.application_value]]
        id = "x"
        kind = "inline"
        key = "K"
        reason = "r"''',
        "ios.requires.application_value.0", "not",
    ),
    "a missing `key` on a delivering value": (
        '''contract = "1"
        [[ios.requires.application_value]]
        id = "x"
        kind = "info_plist"
        reason = "r"''',
        "ios.requires.application_value.0", "required",
    ),
    "an info_plist value naming a usage description": (
        '''contract = "1"
        [[ios.requires.application_value]]
        id = "x"
        kind = "info_plist"
        key = "NSCameraUsageDescription"
        reason = "r"''',
        "ios.requires.application_value.0.key", "not",
    ),
    "a usage_description naming another key": (
        '''contract = "1"
        [[ios.requires.application_value]]
        id = "x"
        kind = "usage_description"
        key = "CFBundleName"
        reason = "r"''',
        "ios.requires.application_value.0.key", "pattern",
    ),
    "an info_plist value naming a capability key": (
        '''contract = "1"
        [[ios.requires.application_value]]
        id = "x"
        kind = "info_plist"
        key = "UIBackgroundModes"
        reason = "r"''',
        "ios.requires.application_value.0.key", "not",
    ),
    "an info_plist value naming a consumer-managed key": (
        '''contract = "1"
        [[ios.requires.application_value]]
        id = "x"
        kind = "info_plist"
        key = "CFBundleIdentifier"
        reason = "r"''',
        "ios.requires.application_value.0.key", "not",
    ),

    # floors
    "a boolean floor declared false": (
        '''contract = "1"
        [android.requires]
        core_library_desugaring = false''',
        "android.requires.core_library_desugaring", "const",
    ),
    "objc_categories declared false": (
        '''contract = "1"
        [ios.contributes]
        objc_categories = false''',
        "ios.contributes.objc_categories", "const",
    ),
    "an Android floor as a string": (
        '''contract = "1"
        [android.requires]
        min_sdk = "24"''',
        "android.requires.min_sdk", "type",
    ),
    "an Android floor as a float": (
        '''contract = "1"
        [android.requires]
        min_sdk = 24.0''',
        "android.requires.min_sdk", "type",
    ),
    "a malformed deployment_target": (
        '''contract = "1"
        [ios.requires]
        deployment_target = "15.0.0.1"''',
        "ios.requires.deployment_target", "pattern",
    ),
    "an iOS floor in the Android table": (
        '''contract = "1"
        [android.requires]
        deployment_target = "15.0"''',
        "android.requires", "additionalProperties",
    ),

    # platforms
    "an empty platforms list": (
        '''contract = "1"
        platforms = []''',
        "platforms", "minItems",
    ),
    "an Android table under platforms = [ios]": (
        '''contract = "1"
        platforms = ["ios"]
        [android.requires]
        min_sdk = 24''',
        "", "not",
    ),
    "an iOS table under platforms = [android]": (
        '''contract = "1"
        platforms = ["android"]
        [ios.requires]
        deployment_target = "15.0"''',
        "", "not",
    ),

    # fail closed
    "a misspelled top-level scalar": (
        '''contract = "1"
        platfroms = ["ios"]''',
        "platfroms", "type",
    ),
    "an unknown key in a platform table": (
        '''contract = "1"
        [android.contributes]
        permisions = []''',
        "android.contributes", "additionalProperties",
    ),
    "a malformed contract value": (
        '''contract = "1.0.0"''',
        "contract", "pattern",
    ),
    "a missing contract": (
        '''platforms = ["ios"]''',
        "", "required",
    ),

    # keys a producer may not spell
    "a producer-declared feature `required`": (
        '''contract = "1"
        [[android.contributes.features]]
        name = "android.hardware.camera"
        required = true''',
        "android.contributes.features.0", "features/items/properties",
    ),
    "a producer-declared `exported`": (
        '''contract = "1"
        [[android.contributes.components]]
        kind = "service"
        name = "org.example.S"
        exported = true''',
        "android.contributes.components.0", "components/items/properties",
    ),

    # components
    "an exported component with no reason": (
        '''contract = "1"
        [[android.contributes.components]]
        kind = "activity"
        name = "org.example.A"
        exported_required = true''',
        "android.contributes.components.0", "required",
    ),
    "a foreground service type on a non-service": (
        '''contract = "1"
        [[android.contributes.components]]
        kind = "activity"
        name = "org.example.A"
        foreground_service_type = "mediaProjection"''',
        "android.contributes.components.0.kind", "const",
    ),
    "view_links on an unexported component": (
        '''contract = "1"
        [[android.contributes.components]]
        kind = "activity"
        name = "org.example.A"
        [[android.contributes.components.view_links]]
        scheme = "myapp"''',
        "android.contributes.components.0", "required",
    ),
    "intent_filters beside view_links": (
        '''contract = "1"
        [[android.contributes.components]]
        kind = "activity"
        name = "org.example.A"
        exported_required = true
        reason = "r"
        [[android.contributes.components.view_links]]
        scheme = "myapp"
        [[android.contributes.components.intent_filters]]
        action = "com.example.ACTION"''',
        "android.contributes.components.0", "not",
    ),
    "a camelCase view_links attribute": (
        '''contract = "1"
        [[android.contributes.components]]
        kind = "activity"
        name = "org.example.A"
        exported_required = true
        reason = "r"
        [[android.contributes.components.view_links]]
        scheme = "myapp"
        pathPrefix = "/cb"''',
        "android.contributes.components.0.view_links.0", "view_links/items/propertyNames",
    ),
    "a non-string view_links value": (
        '''contract = "1"
        [[android.contributes.components]]
        kind = "activity"
        name = "org.example.A"
        exported_required = true
        reason = "r"
        [[android.contributes.components.view_links]]
        scheme = "myapp"
        port = 8080''',
        "android.contributes.components.0.view_links.0.port", "oneOf",
    ),

    # shrinker, queries
    "an r8 keep with no from_dependency": (
        '''contract = "1"
        [[android.contributes.r8.keep]]
        pattern = "okhttp3.**"''',
        "android.contributes.r8.keep.0", "required",
    ),
    "a queries entry naming both targets": (
        '''contract = "1"
        [[android.contributes.queries]]
        package = "com.example"
        provider_authority = "com.example.provider"
        reason = "r"''',
        "android.contributes.queries.0", "oneOf",
    ),

    # repositories and packages
    "a non-https repository url": (
        '''contract = "1"
        [[android.contributes.gradle_repositories]]
        url = "http://example.com/m"
        reason = "r"
        groups = ["g"]''',
        "android.contributes.gradle_repositories.0.url", "pattern",
    ),
    "a repository url carrying user-info": (
        '''contract = "1"
        [[android.contributes.gradle_repositories]]
        url = "https://user:pass@example.com/m"
        reason = "r"
        groups = ["g"]''',
        "android.contributes.gradle_repositories.0.url", "pattern",
    ),
    "a repository bounded by neither groups nor modules": (
        '''contract = "1"
        [[android.contributes.gradle_repositories]]
        url = "https://example.com/m"
        reason = "r"''',
        "android.contributes.gradle_repositories.0", "anyOf",
    ),
    "a package url carrying user-info": (
        '''contract = "1"
        [[ios.contributes.swift_packages]]
        name = "P"
        url = "https://user:pass@example.com/p"
        products = ["P"]
        requirement = { exact = "1.0.0" }''',
        "ios.contributes.swift_packages.0.url", "pattern",
    ),
    "an empty products list": (
        '''contract = "1"
        [[ios.contributes.swift_packages]]
        name = "P"
        url = "https://example.com/p"
        products = []
        requirement = { exact = "1.0.0" }''',
        "ios.contributes.swift_packages.0.products", "minItems",
    ),
    "an authenticated package with no reason": (
        '''contract = "1"
        [[ios.contributes.swift_packages]]
        name = "P"
        url = "https://example.com/p"
        products = ["P"]
        requirement = { exact = "1.0.0" }
        credentials_required = true''',
        "ios.contributes.swift_packages.0", "required",
    ),

    # contributed Swift
    "symbol_prefixes with no contributed Swift": (
        '''contract = "1"
        [ios.contributes.src]
        symbol_prefixes = ["MyPkg"]''',
        "ios.contributes.src", "required",
    ),
    "accessed_api_types with no contributed Swift": (
        '''contract = "1"
        [[ios.contributes.accessed_api_types]]
        type = "NSPrivacyAccessedAPICategoryUserDefaults"
        reasons = ["CA92.1"]''',
        "ios.contributes", "required",
    ),

    # ownership
    "Java source with no owned namespace": (
        '''contract = "1"
        [android.contributes.src]
        java = ["java"]''',
        "android", "required",
    ),
    "Kotlin source with no owned namespace": (
        '''contract = "1"
        [android.contributes.src]
        kotlin = ["kotlin"]''',
        "android", "required",
    ),

    # Info.plist
    "a consumer-managed Info.plist key": (
        '''contract = "1"
        [ios.contributes.info_plist.values]
        CFBundleIdentifier = "com.example"''',
        "ios.contributes.info_plist.values", "values/propertyNames",
    ),
    "a capability key offered through append": (
        '''contract = "1"
        [ios.contributes.info_plist.append]
        UIBackgroundModes = ["remote-notification"]''',
        "ios.contributes.info_plist.append", "append/propertyNames",
    ),
    "a usage description offered through values": (
        '''contract = "1"
        [ios.contributes.info_plist.values]
        NSCameraUsageDescription = "why"''',
        "ios.contributes.info_plist.values", "values/propertyNames",
    ),
    "SKAdNetworkItems offered through append": (
        '''contract = "1"
        [ios.contributes.info_plist.append]
        SKAdNetworkItems = ["x"]''',
        "ios.contributes.info_plist.append", "append/propertyNames",
    ),
    "an array offered through values": (
        '''contract = "1"
        [ios.contributes.info_plist.values]
        LSApplicationQueriesSchemes = ["a"]''',
        "ios.contributes.info_plist.values.LSApplicationQueriesSchemes", "type",
    ),
    "a mixed-type Info.plist array": (
        '''contract = "1"
        [ios.contributes.info_plist.append]
        K = ["a", 1]''',
        "ios.contributes.info_plist.append.K", "anyOf",
    ),
    "an Info.plist array mixing integers and floats": (
        '''contract = "1"
        [ios.contributes.info_plist.append]
        K = [1, 1.5]''',
        "ios.contributes.info_plist.append.K", "anyOf",
    ),
    "an uppercase SKAdNetwork identifier": (
        '''contract = "1"
        [ios.contributes.info_plist]
        skadnetwork_identifiers = ["SU67R6K2V3.skadnetwork"]''',
        "ios.contributes.info_plist.skadnetwork_identifiers.0", "pattern",
    ),

    # Python modules
    "a dotted Python module name": (
        '''contract = "1"
        [[ios.contributes.python_modules]]
        name = "web.views"
        swift_package = "P"''',
        "ios.contributes.python_modules.0.name", "pattern",
    ),
    "a Python module naming no package": (
        '''contract = "1"
        [[ios.contributes.python_modules]]
        name = "web_views"''',
        "ios.contributes.python_modules.0", "required",
    ),

    # meta_data
    "a float meta_data value": (
        '''contract = "1"
        [[android.contributes.meta_data]]
        key = "k"
        value = 1.5
        reason = "r"''',
        "android.contributes.meta_data.0.value", "type",
    ),
    "a meta_data entry with no reason": (
        '''contract = "1"
        [[android.contributes.meta_data]]
        key = "k"
        value = "v"''',
        "android.contributes.meta_data.0", "required",
    ),
}

problems = []
try:
    from jsonschema import Draft202012Validator
    from jsonschema.validators import extend

    TOML_STRICT = extend(
        Draft202012Validator,
        type_checker=Draft202012Validator.TYPE_CHECKER.redefine(
            "integer", _toml_integer
        ).redefine("number", _toml_float),
    )
    strict = TOML_STRICT(SCHEMA)

    for name, (body, where, keyword) in MUST_FAIL.items():
        document = tomllib.loads(textwrap.dedent(body))
        signatures = {
            (
                ".".join(str(part) for part in error.absolute_path),
                str(error.validator),
                "/".join(str(part) for part in error.absolute_schema_path),
            )
            for error in strict.iter_errors(document)
        }
        if not signatures:
            problems.append(f"the schema accepts {name}, and SPEC.md does not")
        elif not any(
            path == where
            and (not keyword or keyword == validator or keyword in schema_path)
            for path, validator, schema_path in signatures
        ):
            problems.append(
                f"{name} is rejected, but not at {where or '<root>'}"
                f"/{keyword or 'any'} — got {sorted(signatures)}"
            )
except ImportError:  # pragma: no cover
    problems.append("jsonschema is not installed, so the negative cases were not exercised")
check("the schema refuses what SPEC.md refuses, for the stated reason", problems)

# --- 20. the conformance corpus obeys its own record format ------------------
# `conformance/record-facts.toml` is the authoritative fact list, and a format
# whose only specification is its examples is one two implementers can satisfy
# differently. So both are held to it: every fixture's expected record, and
# every example in the document that explains it.
sys.path.insert(0, str(ROOT / "conformance"))
import run as conformance_run  # noqa: E402

problems = []
for record in sorted((ROOT / "conformance").glob("*/*/expected/*.record")):
    where = record.relative_to(ROOT)
    lines, malformed = conformance_run.read_record(record.read_bytes())
    problems.extend(f"{where}: {problem}" for problem in malformed)
    if lines != sorted(lines):
        problems.append(f"{where}: the file is not in sorted order")
    if len(set(lines)) != len(lines):
        problems.append(f"{where}: a fact is stated twice")
    for line in lines:
        problems.extend(f"{where}: {problem}" for problem in conformance_run.validate_fact(line))

format_doc = (ROOT / "conformance" / "record-format.md").read_text(encoding="utf-8")
# The language tag matters: `r"```\n(.*?)```"` skips a tagged fence as an
# opener, then pairs its closing fence with the next opening one — so alternate
# blocks go unchecked, which is how an invalid `query` example survived.
for block in re.findall(r"```[a-z]*\n(.*?)```", format_doc, re.S):
    for line in block.split("\n"):
        if line and line.split(" ")[0] in ("build", "dist", "decision"):
            problems.extend(
                f"record-format.md: {problem}" for problem in conformance_run.validate_fact(line)
            )

for path in sorted((ROOT / "conformance").glob("*/*/case.toml")):
    case = tomllib.loads(path.read_text(encoding="utf-8"))
    where = path.relative_to(ROOT)
    if case.get("outcome") not in ("accept", "blocking"):
        problems.append(f"{where}: outcome is {case.get('outcome')!r}, not accept or blocking")
    if case.get("profile") != path.parent.parent.name:
        problems.append(f"{where}: profile {case.get('profile')!r} is not its directory")
    for identifier in case.get("diagnostics", []) + case.get("advisories", []):
        if identifier not in DIAGNOSTICS:
            problems.append(f"{where}: expects {identifier}, which no generator emits")

    # Structural hygiene. A case missing its closure is a case the harness will
    # hand a consumer with nothing to read, and it would pass silently.
    for required in ("closure.toml", "application.toml"):
        if not (path.parent / "input" / required).exists():
            problems.append(f"{where}: input/ has no {required}")
    sidecars = list((path.parent / "input").glob("*/*/_native/native.toml"))
    if not sidecars:
        problems.append(f"{where}: input/ carries no sidecar")
    for sidecar in sidecars:
        try:
            tomllib.loads(sidecar.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            problems.append(f"{where}: {sidecar.name} does not parse: {exc}")
    closure = tomllib.loads((path.parent / "input" / "closure.toml").read_text(encoding="utf-8"))
    if closure.get("platform") not in ("android", "ios"):
        problems.append(f"{where}: closure.toml names no platform this document defines")
    declared = {d["name"] for d in closure.get("distribution", [])}
    shipped = {s.parents[2].name.replace("_", "-") for s in sidecars}
    for orphan in sorted(shipped - declared):
        problems.append(f"{where}: {orphan} ships a sidecar and closure.toml does not name it")

    # `accepted.record` is a prior state in the same canonical form, so it is
    # held to the same rules — except where the case's whole point is that the
    # stored record is wrong, which it has to say.
    prior = path.parent / "input" / "accepted.record"
    if prior.exists() and "accepted.record" not in case.get("malformed_inputs", []):
        lines, malformed = conformance_run.read_record(prior.read_bytes())
        problems.extend(f"{where}: accepted.record {problem}" for problem in malformed)
        for line in lines:
            problems.extend(
                f"{where}: accepted.record {problem}"
                for problem in conformance_run.validate_fact(line)
            )

    # `resolved.toml` stands in for a resolver, so every artifact it states has
    # to be attributable — §9.4's whole point is naming the distribution that
    # pulled a thing in, and a fixture that could not would be testing nothing.
    resolution = path.parent / "input" / "resolved.toml"
    if resolution.exists():
        stated = tomllib.loads(resolution.read_text(encoding="utf-8"))
        for entry in stated.get("artifact", []) + stated.get("package", []):
            subject = entry.get("coordinate") or entry.get("url", "?")
            if entry.get("declared_by") not in declared:
                problems.append(
                    f"{where}: resolved.toml attributes {subject} to "
                    f"{entry.get('declared_by')!r}, which the closure does not name"
                )
            for digest in (entry.get("sha256"), entry.get("checksum")):
                if digest is not None and not re.fullmatch(r"[0-9a-f]{64}", digest):
                    problems.append(f"{where}: {subject} has a digest §9.3 does not admit")
            for feature in entry.get("feature", []):
                if not isinstance(feature.get("required"), bool):
                    problems.append(f"{where}: {subject} declares a feature with no `required`")
check("the conformance corpus obeys its own record format", problems)


print()
if failures:
    print(f"{len(failures)} problem(s) found.")
    sys.exit(1)
print("All checks passed.")
