"""The command line: an executable oracle for the specification.

**This tool is not normative.** `SPEC.md` is. Where this disagrees with the
specification the specification wins and this is a defect — the same rule
`conformance/README.md` states for the corpus, and for the same reason. A tool
that could settle a question about the contract would be a second definition of
it, and two definitions are one too many.

What it is for is retrieval. §8 is forty-six numbered requirements over twelve
sections, and an author who trips one needs the paragraph that decides it rather
than a tour of the document. `explain` is that: an id in, one rule out.

Four subcommands, and the boundary between them is what a consumer knows:

* `explain`     — needs nothing. The registry answers.
* `inspect`     — one sidecar, read and reported. No judgement.
* `validate`    — one sidecar, held to the specification. No closure, so the
                  rules that need one are reported as unchecked rather than
                  passed.
* `conformance` — the corpus, run against someone else's consumer.
* `authoring-guide` — §12.2, emitted where the author is working.

Nothing here writes a project, resolves a coordinate, or executes anything a
sidecar contains.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import re
import tempfile
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from . import fragments, obligations, registry
from .contract import SPEC_MAJOR, SPEC_MINOR
from .discovery import Closure, normalize_name, source_from_path
from .reader import PLATFORMS, read
from .resources import SIDECAR_NAME, SidecarSource

#: Printed by `--version`, and the first line `explain` renders. The contract is
#: the thing a reader of the output actually needs; this tool's own version is
#: the package's and says nothing about which rules were applied.
CONTRACT = f"{SPEC_MAJOR}.{SPEC_MINOR}"

NON_NORMATIVE = (
    "This tool is not normative. SPEC.md is; where the two disagree, the "
    "specification wins and this is a defect."
)


class UsageError(Exception):
    """Something the invocation got wrong, reported without a traceback."""


# -- locating a sidecar ------------------------------------------------------


@dataclass(frozen=True)
class Located:
    """A sidecar found somewhere, and where it was found."""

    source: SidecarSource
    origin: str


def _wheel_members(archive: zipfile.ZipFile) -> Iterator[str]:
    return (name for name in archive.namelist() if name.endswith("/" + SIDECAR_NAME))


def _from_wheel(path: Path, into: Path) -> Located:
    """Read a wheel's sidecar without installing or importing anything.

    A wheel is a zip and this reads it as one. §3.2's obligation not to import
    a producing distribution is not a rule about installed packages — it is
    about executing a producer's code, and unpacking a zip executes none.
    """
    with zipfile.ZipFile(path) as archive:
        found = sorted(_wheel_members(archive))
        if not found:
            raise UsageError(
                f"{path.name} carries no {SIDECAR_NAME}; a sidecar lives in a "
                "directory the distribution's entry point names"
            )
        if len(found) > 1:
            listed = ", ".join(sorted(name.rsplit("/", 2)[0] for name in found))
            raise UsageError(
                f"{path.name} carries {len(found)} sidecars ({listed}); §3.4 gives "
                "a distribution one entry, so this wheel cannot be read as one"
            )
        directory = found[0].rsplit("/", 1)[0]
        # Only the sidecar directory. A wheel's other contents are not this
        # tool's business, and unpacking them would make a wheel's size the
        # cost of asking one question about it.
        for name in archive.namelist():
            if name.startswith(directory + "/") and not name.endswith("/"):
                target = into / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))

    module = directory.replace("/", ".")
    distribution, _, version = path.name.split("-")[0], "", ""
    stem = path.name.split("-")
    version = stem[1] if len(stem) > 1 else ""
    return Located(
        source=source_from_path(
            into / directory,
            distribution=normalize_name(distribution),
            version=version,
            module=module,
        ),
        origin=f"{path.name} ({directory}/)",
    )


def _from_directory(path: Path) -> Located:
    """A sidecar directory on disk — a producer checking its own before shipping."""
    root = path if (path / SIDECAR_NAME).is_file() else None
    if root is None:
        candidates = sorted(path.rglob(SIDECAR_NAME))
        if not candidates:
            raise UsageError(f"{path} holds no {SIDECAR_NAME}")
        if len(candidates) > 1:
            listed = ", ".join(str(c.parent.relative_to(path)) for c in candidates)
            raise UsageError(f"{path} holds more than one sidecar: {listed}")
        root = candidates[0].parent
    # The directory name is the module's last segment, and the distribution's
    # name is not on disk. `_native` under `pystripe/` says the distribution is
    # `pystripe`, which is a convention rather than a rule — so it is a default
    # the caller can override rather than something this claims to know.
    # `pystripe/_native/native.toml` names `pystripe`; `pystripe/native.toml`
    # names it too. Which of the two a path is cannot be read off the name, so
    # the sidecar directory's own name is used unless it is the conventional
    # `_native`, and `--distribution` settles it either way.
    distribution = root.parent.name if root.name.startswith("_") else root.name
    return Located(
        source=source_from_path(
            root,
            distribution=normalize_name(distribution),
            module=f"{distribution}.{root.name}",
        ),
        origin=str(root),
    )


def locate(target: str, workspace: Path, *, distribution: str = "") -> Located:
    path = Path(target)
    if not path.exists():
        raise UsageError(f"{target} does not exist")
    found = _from_wheel(path, workspace) if path.suffix == ".whl" else _from_directory(path)
    if distribution:
        found = Located(
            source=SidecarSource(
                distribution=normalize_name(distribution),
                version=found.source.version,
                module=found.source.module,
                root=found.source.root,
                package_relpath=found.source.package_relpath,
            ),
            origin=found.origin,
        )
    return found


# -- the parser --------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="native-integration",
        description=f"An executable oracle for SPEC.md, contract {CONTRACT}. "
        + NON_NORMATIVE,
        epilog=NON_NORMATIVE,
    )
    parser.add_argument(
        "--version", action="version",
        version=f"native-integration, contract {CONTRACT} (not normative)",
    )
    subcommands = parser.add_subparsers(dest="command", metavar="<command>")

    explain_command = subcommands.add_parser(
        "explain", help="resolve a diagnostic or declaration id to its rule",
        description="Resolve an id to the rule that decides it: the section, the "
        "text, and a minimal fragment in correct form. " + NON_NORMATIVE,
    )
    explain_command.add_argument("identifier", help="a diagnostic id, or a declaration's dotted path")
    explain_command.add_argument("--json", action="store_true", help="emit the answer as JSON")
    explain_command.add_argument(
        "--platform", choices=sorted(PLATFORMS), default="android",
        help="which platform table to write a platform-neutral fragment into",
    )

    for name, help_text in (
        ("inspect", "report what a sidecar declares, without judging it"),
        ("validate", "hold a sidecar to the specification"),
    ):
        sub = subcommands.add_parser(name, help=help_text, epilog=NON_NORMATIVE)
        sub.add_argument("target", help="a wheel, or a directory holding a sidecar")
        sub.add_argument("--json", action="store_true", help="emit the answer as JSON")
        sub.add_argument(
            "--platform", choices=sorted(PLATFORMS), action="append",
            help="platforms to read for (default: every platform the sidecar supports)",
        )
        sub.add_argument(
            "--distribution", default="",
            help="the distribution's name, where the path does not give it",
        )
        if name == "validate":
            sub.add_argument(
                "--explain-failures", action="store_true",
                help="pair each finding with the step of §12.2 that decides it",
            )

    guide = subcommands.add_parser(
        "authoring-guide", help="print §12.2, the sidecar authoring procedure",
        description="Print the specification's authoring procedure. The people "
        "who need it are working in another package's repository and will not "
        "have this specification checked out, so it travels with the tool. "
        + NON_NORMATIVE,
        epilog=NON_NORMATIVE,
    )
    guide.add_argument(
        "--template", action="store_true",
        help="print a commented `native.toml` skeleton instead of the procedure",
    )

    conformance_command = subcommands.add_parser(
        "conformance", help="run the conformance corpus against a consumer",
        description="Run the conformance corpus against an external consumer "
        "command, and report per case. The harness is the authority on the "
        "outcome. "
        + NON_NORMATIVE,
        epilog="The corpus is not part of the installed package: it belongs to "
        "the specification rather than to this library, and its harness is kept "
        "out of the implementation it measures. So this needs a checkout of the "
        "repository — found automatically when you are working inside one, and "
        "named by --corpus otherwise. " + NON_NORMATIVE,
    )
    conformance_command.add_argument(
        "--profile", choices=("core", *sorted(PLATFORMS)), action="append", required=True,
        help="§8.1 profiles to claim; naming a platform profile brings core with it",
    )
    conformance_command.add_argument(
        "--corpus", default="",
        help="the `conformance/` directory of a checkout of this repository",
    )
    conformance_command.add_argument(
        "consumer", nargs=argparse.REMAINDER,
        help="-- followed by the consumer command to run",
    )
    return parser




# -- explain -----------------------------------------------------------------


def resolve(known: registry.Registry, identifier: str) -> tuple[str, str]:
    """What the user typed, as something the registry holds.

    Two spellings are accepted for one thing, because two are what an author
    has. A diagnostic names `<platform>` where the rule is written once for
    both; the sidecar in front of them says `android`. Refusing the second
    would make the id in a build log the wrong thing to paste.
    """
    for candidate, kind in (
        (identifier, "diagnostic" if identifier.startswith("ni.") else "declaration"),
    ):
        if kind == "diagnostic" and candidate in known.diagnostics:
            return candidate, kind
        if kind == "declaration" and candidate in known.declarations:
            return candidate, kind

    for platform in PLATFORMS:
        generic = identifier.replace(f"{platform}.", "<platform>.", 1)
        if generic in known.diagnostics:
            return generic, "diagnostic"
        if generic in known.declarations:
            return generic, "declaration"

    known_ids = sorted(known.diagnostics) + sorted(known.declarations)
    near = [name for name in known_ids if identifier in name][:5]
    hint = ("\n  did you mean: " + ", ".join(near)) if near else ""
    raise UsageError(
        f"{identifier} is neither a diagnostic id nor a declaration this "
        f"contract defines{hint}"
    )


def _answer(known: registry.Registry, identifier: str, platform: str) -> dict[str, Any]:
    resolved, kind = resolve(known, identifier)
    about: dict[str, Any] = {"id": resolved, "kind": kind, "contract": CONTRACT}

    if kind == "diagnostic":
        entry = known.about(resolved)
        about.update(
            severity=entry["severity"],
            section=entry["section"],
            anchor=entry["anchor"],
            rule=entry["summary"],
        )
        for field in ("declaration", "requirement", "profile"):
            if field in entry:
                about[field] = entry[field]
        subject = str(entry.get("declaration", ""))
    else:
        entry = known.declaration(resolved)
        about.update(
            section=entry["section"],
            anchor=entry["anchor"],
            rule=entry.get("description", ""),
            node=entry["node"],
            category=entry["category"],
            platform=entry["platform"],
            required=bool(entry.get("required")),
            since=entry["since"],
        )
        if entry.get("values"):
            about["values"] = list(entry["values"])
        subject = resolved

    about["specification"] = f"SPEC.md#{about['anchor']}"
    if subject:
        try:
            about["fragment"] = fragments.fragment(known, subject, platform)
        except fragments.Unwritable as why:
            about["fragment"] = None
            about["no_fragment"] = str(why)
        except registry.RegistryError:
            about["fragment"] = None
    # Every other id keyed to the same declaration, which is the set an author
    # who tripped one is likely to trip next.
    if subject:
        about["related"] = sorted(
            name for name, entry in known.diagnostics.items()
            if entry.get("declaration") == subject and name != resolved
        )
    return about


def _render_explanation(about: dict[str, Any]) -> str:
    lines = [about["id"]]
    if about.get("severity"):
        lines[0] += f"   [{about['severity']}]"
    lines.append("")
    lines.append(f"  §{about['section']}   {about['specification']}")
    if about.get("profile"):
        lines.append(f"  profile: {about['profile']} (§8.1)")
    if about.get("category"):
        detail = f"  {about['node']}, {about['category']}, {about['platform']}"
        detail += ", required" if about.get("required") else ", optional"
        lines.append(detail + f", since {about['since']}")
    lines.append("")
    for paragraph in str(about.get("rule") or "").split("\n"):
        lines.append(f"  {paragraph}")
    if about.get("values"):
        lines.append("")
        lines.append("  one of: " + ", ".join(f"`{v}`" for v in about["values"]))
    if about.get("fragment"):
        lines += ["", "  correct form:", ""]
        lines += [f"    {line}" if line else "" for line in about["fragment"].split("\n")]
    elif about.get("no_fragment"):
        lines += ["", f"  no fragment: {about['no_fragment']}"]
    if about.get("related"):
        lines += ["", "  other rules on this declaration:"]
        lines += [f"    {name}" for name in about["related"]]
    lines += ["", f"  {NON_NORMATIVE}"]
    return "\n".join(lines)


def explain(args: argparse.Namespace) -> int:
    known = registry.load()
    about = _answer(known, args.identifier, args.platform)
    print(json.dumps(about, indent=2) if args.json else _render_explanation(about))
    return 0


# -- the authoring procedure -------------------------------------------------

#: Where an author can read the whole specification, printed on the skeleton so
#: that a file copied into another repository still says where it came from.
SPECIFICATION_URL = (
    "https://github.com/ElliotGarbus/native-integration/blob/main/SPEC.md"
)

TEMPLATE = f"""# native.toml — the sidecar for this distribution.
#
# The specification: {SPECIFICATION_URL}
# The procedure that produces this file: `native-integration authoring-guide`
# Every key: SPEC.md's Appendix B, or `native-integration explain <key>`
#
# Delete what you do not declare. An empty table is not a placeholder: §4.4
# makes a consumer fail closed on anything it does not recognize, and a table
# left behind is one more thing for a reader to interpret.

contract = "1"

# Optional. The platforms this distribution functions on (§4.5). Omit it and
# every platform is assumed; declare a table for a platform this omits and the
# build fails.
# platforms = ["android", "ios"]

# --- what this distribution claims exclusively (§6.1) ------------------------
# [android.owns]
# java_namespaces = ["com.example.yourpackage"]

# --- what the application's build must satisfy (§5) --------------------------
# A floor is a minimum (§5.1); a value is a string the consumer can place
# (§5.2); an action is an outcome it cannot (§5.3). Step 4 of the procedure
# chooses between them.
# [android.requires]
# min_sdk = 24

# --- what this distribution supplies (§6, §7) --------------------------------
# Run step 3's three-part test before adding anything here: the producer knows
# exactly what is required, the consumer can do it deterministically, and little
# or no application policy is involved. A failure on any one of the three makes
# it a requirement instead.
# [[android.contributes.gradle_dependencies]]
# coordinate = "com.example:sdk:1.0.0"

# Check it before you ship it:
#     native-integration validate path/to/_native --explain-failures
"""


def guide_text() -> str:
    """§12.2, from the copy that ships beside the registry.

    Read from package data rather than from `SPEC.md`, because the author this
    is for does not have `SPEC.md`. `tools/gen_authoring_guide.py --check`
    fails the build if the copy and the specification disagree.
    """
    path = registry.contract_directory() / "authoring-guide.md"
    if not path.is_file():
        raise UsageError(
            f"{path.name} is missing from the package; run "
            "tools/gen_authoring_guide.py"
        )
    return "\n".join(
        line for line in path.read_text(encoding="utf-8").split("\n")
        if not line.startswith("<!--")
    ).strip("\n")


def authoring_guide(args: argparse.Namespace) -> int:
    if args.template:
        print(TEMPLATE, end="")
        return 0
    print(guide_text())
    print(f"\n  Read it in full at {SPECIFICATION_URL}")
    print(f"  {NON_NORMATIVE}")
    return 0


#: Each step of §12.2, by the sections it cites. Derived from the guide's own
#: text rather than written down again: a step is authoritative because of what
#: it cites, so the citations are what a finding is matched against. A step
#: whose citations changed changes what it answers for, automatically.
def steps() -> list[tuple[int, str, set[str]]]:
    found: list[tuple[int, str, set[str]]] = []
    text = guide_text()
    for match in re.finditer(r"\*\*(\d)\. (.+?)\*\*(.*?)(?=\n\*\*\d\. |\Z)", text, re.S):
        number, title, body = int(match.group(1)), match.group(2), match.group(3)
        sections = set(re.findall(r"\[\u00a7(\d+(?:\.\d+)?)\]", title + body))
        found.append((number, title.rstrip("."), sections))
    return found


#: Which step of §12.2 answers for a section of the specification.
#:
#: The one hand-derived table in this phase, and it is a mapping of the
#: document's own structure onto the procedure's, not a list of requirements.
#: §12.2's steps 2 to 4 are *about* §2.1's three categories, so a finding is
#: paired with the step that decides the category its rule belongs to:
#:
#:   §5  a requirement — step 4 chooses between floor, value and action
#:   §6.1  an owned namespace — step 2 classifies it
#:   §6, §7  a contribution — step 3's three-part test admits or refuses it
#:   §12  conditionality — step 6
#:   §4  the file and its declarations — step 7 checks them against Appendix B
#:   §3  discovery — step 8 confirms what shipped
#:
#: Matching on the finding's own section is tried first and is exact; this is
#: the fallback, because §8.4 is where a numbered requirement is *indexed* and
#: the sections above are where its rules are *stated*.
BY_SECTION = (("5", 4), ("6.1", 2), ("6", 3), ("7", 3), ("12", 6), ("4", 7), ("3", 8))


def _step_for(section: str) -> int | None:
    for prefix, number in BY_SECTION:
        if section == prefix or section.startswith(prefix + "."):
            return number
    return None


def explaining(findings: list[dict[str, Any]]) -> list[str]:
    """One line per finding, naming the step of §12.2 that decides it.

    A finding carries the section its rule comes from, and every step says which
    sections it draws on, so an exact citation match is tried first. Where there
    is none — a numbered requirement carries §8.4, the index rather than the
    rule — the sections the requirement's own summary cites are tried, and then
    `BY_SECTION`.
    """
    procedure = {number: title for number, title, _ in steps()}
    cited = {number: sections for number, _, sections in steps()}
    known = registry.load()
    lines: list[str] = []
    for finding in findings:
        sections = {finding["section"]}
        entry = known.diagnostics.get(finding["id"], {})
        sections |= set(re.findall(r"\[§(\d+(?:\.\d+)?)\]", str(entry.get("summary", ""))))
        chosen = next(
            (number for number, wanted in sorted(cited.items()) if sections & wanted),
            next((s for s in (_step_for(x) for x in sorted(sections)) if s), None),
        )
        where = "§" + ", §".join(sorted(sections - {"8.4"}) or sorted(sections))
        if chosen is None:
            lines.append(
                f"  {finding['id']}  {where} — no step of §12.2 covers this; "
                "`native-integration explain` has the rule"
            )
            continue
        lines.append(f"  {finding['id']}  {where} — step {chosen}, {procedure[chosen]}")
    return lines


# -- inspect and validate ----------------------------------------------------


def _platforms_for(args: argparse.Namespace) -> tuple[str, ...]:
    return tuple(args.platform) if args.platform else tuple(sorted(PLATFORMS))


def _read_one(found: Located, platform: str):
    """One sidecar, read for one platform, with no closure and no application.

    A single distribution is all a wheel or a directory offers, so the rules
    that need a closure — an owned namespace another distribution also claims,
    two values targeting one key — cannot fire. That is a limit of the input
    rather than a verdict, and `validate` says so rather than reporting a clean
    build.
    """
    return read(
        [found.source],
        platform=platform,
        closure=Closure.direct(found.source.distribution),
    )


def inspect(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory(prefix="native-integration-") as workspace:
        found = locate(args.target, Path(workspace), distribution=args.distribution)
        document = tomllib.loads(
            (found.source.root / SIDECAR_NAME).read_text(encoding="utf-8")
        )
        report: dict[str, Any] = {
            "distribution": found.source.distribution,
            "origin": found.origin,
            "contract": document.get("contract", ""),
            "platforms": document.get("platforms", sorted(PLATFORMS)),
            "declares": {},
        }
        for platform in sorted(PLATFORMS):
            table = document.get(platform)
            if not isinstance(table, Mapping):
                continue
            report["declares"][platform] = {
                category: sorted(table[category])
                for category in ("owns", "requires", "contributes")
                if isinstance(table.get(category), Mapping)
            }

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(f"{report['distribution']}  —  {report['origin']}")
    print(f"  contract {report['contract']}")
    print(f"  platforms: {', '.join(report['platforms'])}")
    for platform, categories in report["declares"].items():
        print(f"  [{platform}]")
        for category, keys in categories.items():
            print(f"    {category}: {', '.join(keys) or '—'}")
    print(f"\n  {NON_NORMATIVE}")
    return 0


def validate(args: argparse.Namespace) -> int:
    findings: list[dict[str, Any]] = []
    unchecked: list[str] = []
    with tempfile.TemporaryDirectory(prefix="native-integration-") as workspace:
        found = locate(args.target, Path(workspace), distribution=args.distribution)
        document = tomllib.loads(
            (found.source.root / SIDECAR_NAME).read_text(encoding="utf-8")
        )
        supported = document.get("platforms") or sorted(PLATFORMS)
        for platform in _platforms_for(args):
            if platform not in supported:
                continue
            integration = _read_one(found, platform)
            for finding in integration.findings:
                findings.append(
                    {"platform": platform, **_as_json(finding)}
                )

    # §9.1's gate is the application's act, and this reads one sidecar with no
    # application and no stored record — so the gate is not evaluated against
    # anything, it fires on the absence of an application. It would appear on
    # every sidecar ever passed to this command, which makes it noise rather
    # than a finding: an obligation that cannot vary with the input says
    # nothing about the input. It belongs with what went unchecked.
    unreachable = [f for f in findings if f["requirement"] == "ni.req.38"]
    # By requirement number *and* by what kind of check fired, because a number
    # is not one rule. Requirement 29 covers both an export only the application
    # can approve and the structural component rules a producer must satisfy —
    # so a missing `reason` beside `exported_required` came back as the
    # application's to answer, which is a key only the producer can add.
    #
    # A finding whose `id` is finer than its requirement was produced by a
    # registry rule: `ni.decl.…` or `ni.constraint.…`, a property of the
    # document itself. Those are the producer's whatever number they roll up to.
    outstanding = [
        f for f in findings
        if f not in unreachable
        and f["id"] == f["requirement"]
        and f["requirement"] in obligations.ANSWERED_BY_THE_APPLICATION
    ]
    producer = [f for f in findings if f not in outstanding and f not in unreachable]
    blocking = [f for f in producer if f["severity"] == "blocking"]
    unchecked.append(
        "one distribution was read, so every rule that needs the whole "
        "dependency closure went unchecked: an owned namespace two "
        "distributions claim, two values targeting one key, one module "
        "declared twice, and a packaging collision"
    )
    unchecked.append(
        "no application was supplied, so §9.1's acceptance gate was not "
        "evaluated either — there is no configuration to meet a floor, no "
        "answer to a value, and no accepted record to compare against"
    )

    if args.json:
        print(json.dumps({
            "distribution": found.source.distribution,
            "contract": CONTRACT,
            "outcome": "blocking" if blocking else "accept",
            "findings": producer,
            "outstanding": outstanding,
            "unchecked": unchecked,
            "normative": False,
            **({"steps": explaining(producer + outstanding)}
               if getattr(args, "explain_failures", False) else {}),
        }, indent=2))
        return 1 if blocking else 0

    def show(entries: list[dict[str, Any]]) -> None:
        for finding in entries:
            print(f"  [{finding['severity']}] ({finding['platform']}) {finding['id']}")
            print(f"      {finding['message']}")
            if finding.get("where"):
                print(f"      at {finding['where']}")
            print(f"      native-integration explain {finding['id']}")

    print(f"{found.source.distribution}  —  {found.origin}")
    show(producer)
    if not producer:
        print("  no finding, for the rules one sidecar can be held to")
    if outstanding:
        # Reported, and not counted against the producer. Every one of these is
        # a real obligation and three of the four block a build — but they are
        # the application's to discharge, and a sidecar cannot.
        print("\n  outstanding, for the application to answer:")
        show(outstanding)
    if getattr(args, "explain_failures", False) and (producer or outstanding):
        print("\n  the step of §12.2 each of these comes from:")
        for line in explaining(producer + outstanding):
            print(line)
        print("\n  the whole procedure: native-integration authoring-guide")
    for note in unchecked:
        print(f"\n  not checked here: {note}")
    print(f"\n  {NON_NORMATIVE}")
    return 1 if blocking else 0


def _as_json(finding: Any) -> dict[str, Any]:
    return {
        "id": finding.identifiers[0],
        "requirement": finding.obligation,
        "distributions": list(finding.distributions),
        "section": finding.section,
        "severity": finding.severity,
        "message": finding.message,
        "where": finding.where,
        "detail": list(finding.detail),
    }


# -- conformance -------------------------------------------------------------


def _corpus_directory(given: str) -> Path:
    if given:
        directory = Path(given)
        if not (directory / "run.py").is_file():
            raise UsageError(f"{given} holds no run.py, so it is not the corpus")
        return directory
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "conformance"
        if (candidate / "run.py").is_file():
            return candidate
    raise UsageError(
        "the conformance corpus was not found above this package. It is not "
        "shipped in the wheel — the fixtures are the specification's, not the "
        "library's — so pass --corpus <path> to a checkout of the repository"
    )


def conformance(args: argparse.Namespace) -> int:
    """Hand the corpus to its own harness, which is the authority on the result.

    Deliberately a subprocess rather than an import. `conformance/run.py` states
    that it shares no code with any consumer, and a CLI that reached inside it
    to reuse its comparison would make this library part of the thing being
    measured.
    """
    corpus = _corpus_directory(args.corpus)
    command = [part for part in args.consumer if part != "--"]
    if not command:
        raise UsageError("a consumer command is required: … -- mytool build …")
    invocation = [sys.executable, str(corpus / "run.py")]
    for profile in args.profile:
        invocation += ["--profile", profile]
    return subprocess.call(invocation + ["--", *command])



def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2

    handler = {
        "authoring-guide": authoring_guide,
        "explain": explain,
        "inspect": inspect,
        "validate": validate,
        "conformance": conformance,
    }[args.command]
    try:
        return handler(args)
    except UsageError as problem:
        print(f"native-integration: {problem}", file=sys.stderr)
        return 2
    except registry.RegistryError as problem:
        print(f"native-integration: {problem}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover - module entry
    raise SystemExit(main())
