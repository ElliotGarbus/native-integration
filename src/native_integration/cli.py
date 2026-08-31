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

Nothing here writes a project, resolves a coordinate, or executes anything a
sidecar contains.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
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

    conformance = subcommands.add_parser(
        "conformance", help="run the conformance corpus against a consumer",
        description="Run the corpus in `conformance/` against an external "
        "consumer command. The harness is the authority on the outcome. "
        + NON_NORMATIVE,
        epilog=NON_NORMATIVE,
    )
    conformance.add_argument(
        "--profile", choices=("core", *sorted(PLATFORMS)), action="append", required=True,
        help="§8.1 profiles to claim; naming a platform profile brings core with it",
    )
    conformance.add_argument("--corpus", default="", help="the corpus directory")
    conformance.add_argument(
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

    outstanding = [
        f for f in findings
        if f["requirement"] in obligations.ANSWERED_BY_THE_APPLICATION
    ]
    producer = [f for f in findings if f not in outstanding]
    blocking = [f for f in producer if f["severity"] == "blocking"]
    unchecked.append(
        "one distribution was read, so every rule that needs the whole "
        "dependency closure went unchecked: an owned namespace two "
        "distributions claim, two values targeting one key, a packaging "
        "collision, and the §9.1 acceptance gate"
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
