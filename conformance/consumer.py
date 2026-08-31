"""The reference consumer: this repository's reader, driven by the harness.

[run.py](run.py) hands a consumer a case's `input/` and an output directory and
reads JSON from its stdout. That interface is the whole of what a consumer must
offer to be tested, and this is the smallest thing that offers it.

It is not part of the library. The corpus's `input/` spelling is **neutral** —
[§2.2](../SPEC.md#22-how-the-application-answers) fixes the capability a
consumer must offer and deliberately not its syntax — so adapting that spelling
into what the reader takes is exactly the work a real build tool does once, for
its own configuration, and exactly what the library must not do on its behalf.

Usage:

    python conformance/consumer.py <input-directory> <output-directory>
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from native_integration import (  # noqa: E402
    Answer,
    Application,
    Approval,
    Closure,
    Credential,
    FeatureDecision,
    Findings,
    Origin,
    PackagingChoice,
    Record,
    graph_of,
    load_registry,
    read,
    source_from_path,
)
from native_integration import advisories  # noqa: E402

#: What this consumer can be told, rather than having to do. `run.py` refuses a
#: case needing a stated resolution unless the consumer says it accepts one.
CAPABILITIES = {"injected_resolution": True}

#: The attested assertions, and only the ones that say something true about this
#: reader. `README.md` labels these the consumer's own claim rather than
#: evidence, which is exactly why the list is short: an assertion about work the
#: reader never attempts would be testimony to nothing, and vouching for it is
#: how a conformance claim overstates itself.
#:
#: `objc_categories_linked` is absent for that reason — linking is a build
#: tool's, and this reader produces no build. So are the verified assertions
#: about a payload or a merged manifest, which `run.py` marks unverified when it
#: finds no file, and which is the honest answer.
ATTESTED = {
    # §3.3: the reader parses a sidecar as data and never imports the
    # distribution that ships it.
    "no_producer_import": True,
    # §8.4 requirement 18, enforced in `Finding.__post_init__` rather than
    # remembered at each call site.
    "every_diagnostic_names_a_distribution": True,
    # §5.1: every finding carries the producer's own `reason`.
    "instructions_attributed_to_producer": True,
    # §9.5: a credential reaches the record as `credential-required` and the
    # locator is never read, let alone written.
    "no_credential_in_record": True,
    # §8.4 requirement 16: an unsupplied value is reported, never guessed at,
    # and a placeholder is not an answer.
    "no_invented_value": True,
    # §8.4 requirement 29: an unapproved export blocks. The failure the
    # requirement guards is a consumer that writes `exported=false` instead.
    "no_unexported_fallback": True,
}


def read_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def application_of(raw: Mapping[str, Any]) -> Application:
    """The corpus's neutral spelling, adapted.

    Every join here is the one requirement 10 names for that row, and the four
    that are not `(distribution, id)` are keyed by the name or path they address
    so that they reach every contributor of it.
    """
    build = raw.get("build", {})
    answers = raw.get("answers", {})
    return Application(
        android={
            key: value
            for key, value in build.items()
            if isinstance(value, int) and not isinstance(value, bool)
        },
        deployment_target=str(build.get("deployment_target", "")),
        date=str(build.get("date", "")),
        core_library_desugaring=bool(build.get("core_library_desugaring", False)),
        values={
            _split_id(key): value for key, value in answers.get("values", {}).items()
        },
        acknowledged={
            (distribution, identifier): Answer(date=_date(answers, distribution, identifier))
            for distribution, listed in answers.get("acknowledged", {}).items()
            for identifier in _identifiers(listed)
        },
        dismissed={
            (distribution, identifier): Answer(date=_date(answers, distribution, identifier))
            for distribution, listed in answers.get("dismissed", {}).items()
            for identifier in _identifiers(listed)
        },
        suppressed_permissions={
            name: Answer(date=held.get("date", ""))
            for name, held in answers.get("suppressed_permissions", {}).items()
        },
        exported_components={
            name: Approval(date=held.get("date", ""), approved=bool(held.get("approved")))
            for name, held in answers.get("exported_components", {}).items()
        },
        credentials={
            url: Credential(kind=held.get("kind", "env"), locator=held.get("locator", ""))
            for url, held in answers.get("credentials", {}).items()
        },
        artifact_features={
            name: FeatureDecision(date=held.get("date", ""), keep=held.get("keep", ""))
            for name, held in answers.get("artifact_features", {}).items()
        },
        packaging_choices={
            path: PackagingChoice(date=held.get("date", ""), artifact=held.get("chosen", ""))
            for path, held in answers.get("packaging_collisions", {}).items()
        },
    )


def _split_id(key: str) -> tuple[str, str]:
    distribution, _, identifier = key.partition(".")
    return distribution, identifier


def _identifiers(listed: Any) -> tuple[str, ...]:
    """An answer is spelled as a list of ids, or as a table keyed by them."""
    if isinstance(listed, dict):
        return tuple(listed)
    return tuple(entry for entry in listed if isinstance(entry, str))


def _date(answers: Mapping[str, Any], distribution: str, identifier: str) -> str:
    for section in ("acknowledged", "dismissed"):
        held = answers.get(section, {}).get(distribution)
        if isinstance(held, dict) and isinstance(held.get(identifier), dict):
            return str(held[identifier].get("date", ""))
    return str(answers.get("dates", {}).get(f"{distribution}.{identifier}", ""))


def input_directory(case: Path, platform: str) -> Path:
    """A case's inputs are either per-platform or shared, which is what `core/`
    buys: one case, run once for each platform its profile covers."""
    per_platform = case / "input" / platform
    return per_platform if per_platform.is_dir() else case / "input"


def sidecar_root(base: Path, distribution: str) -> Path | None:
    found = sorted((base / distribution).rglob("native.toml"))
    return found[0].parent if found else None


def closure_of(raw: Mapping[str, Any]) -> Closure:
    """§3.2's origins, from what the corpus says a resolver would have produced.

    A distribution marked `not-in-closure` is simply absent from the members,
    which is the whole of requirement 1: it is installed alongside, it ships a
    sidecar, and it configures nothing.
    """
    return Closure.of(
        {
            entry["name"]: Origin(
                direct=entry.get("origin") == "direct",
                via=tuple(entry.get("via", ())),
            )
            for entry in raw.get("distribution", [])
            if entry.get("origin") != "not-in-closure"
        }
    )


def sources_of(base: Path, raw: Mapping[str, Any], findings: Findings) -> list:
    """The sidecar of each distribution, located on disk.

    Discovery proper walks installed distributions' entry points; a corpus case
    is a directory tree, so this stands in for that one step and nothing else.
    """
    found = []
    for entry in raw.get("distribution", []):
        name = entry["name"]
        # §3.4: a distribution declaring more than one entry in the group is
        # invalid, and a consumer must not select one or merge them.
        if len(entry.get("entry_points", ())) > 1:
            findings.requirement(
                2,
                name,
                message=(
                    f"the distribution declares {len(entry['entry_points'])} entries "
                    "in the entry-point group"
                ),
            )
            continue
        root = sidecar_root(base, name)
        if root is None:
            continue
        found.append(
            source_from_path(
                root,
                distribution=name,
                version=entry.get("version", ""),
                module=entry.get("entry_point", ""),
            )
        )
    return found


def run(base: Path, platform: str) -> tuple[str, Findings, Record]:
    """One case, for one platform."""
    raw = read_toml(base / "closure.toml")
    application = application_of(read_toml(base / "application.toml"))
    prior = base / "accepted.record"

    # Requirement 2 is found while locating sidecars, before the read begins, so
    # its findings are made here and carried in.
    findings = Findings(load_registry())
    sources = sources_of(base, raw, findings)

    integration = read(
        sources,
        platform=platform,
        application=application,
        closure=closure_of(raw),
        graph=graph_of(read_toml(base / "resolved.toml")),
        accepted=prior.read_text(encoding="utf-8") if prior.exists() else None,
    )
    integration.findings.items[:0] = findings.items

    outcome = "blocking" if integration.findings.blocking else "accept"
    return outcome, integration.findings, integration.record


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    base, outputs = Path(argv[1]), Path(argv[2])
    outputs.mkdir(parents=True, exist_ok=True)
    platform = read_toml(base / "closure.toml").get("platform", "android")

    outcome, findings, record = run(base, platform)
    print(
        json.dumps(
            {
                "outcome": outcome,
                "diagnostics": findings.as_diagnostics(),
                "advisories": findings.as_advisories(),
                "assertions": ATTESTED,
                "capabilities": CAPABILITIES,
                "outputs": str(outputs),
                "record": record.render(),
            }
        )
    )
    return 1 if outcome == "blocking" else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
