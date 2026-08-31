#!/usr/bin/env python3
"""Generate the worked integration records for `development/examples/mediated-ads/`.

SPEC.md's Appendix C shows the shape of a record, hand-written and
non-normative. This writes a real one, from the three sidecars in that directory
and the `app-pyproject.toml` beside them — including the `origin` line for a
package the application never named, which is the case the whole convention
exists for.

    python3 tools/record_example.py           # write
    python3 tools/record_example.py --check   # fail if the files have drifted

Regenerate whenever a mediated-ads sidecar or the application file changes; the
record is a function of both, which is the property that makes it reviewable.

§9.3 hashes the *bytes* of each input, so a checkout whose line endings differ
from the repository's produces a different record for identical content. That is
correct — a sidecar ships inside a wheel, where the bytes are fixed — and it is
why `.gitattributes` pins this repository to LF.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from native_integration import (  # noqa: E402
    Answer,
    Application,
    Closure,
    Origin,
    read,
    source_from_path,
)

EXAMPLE = ROOT / "development" / "examples" / "mediated-ads"
ADAPTERS = ("pyadmob-applovin", "pyadmob-mintegral")
MEDIATION = "pyadmob"

#: The application depends on the adapters it wants; each adapter depends on the
#: mediation SDK, so `pyadmob` arrives underneath. That is the ordinary shape of
#: this ecosystem, and it puts the package demanding an account identifier one
#: level below anything the application named.
CLOSURE = Closure.of(
    {
        ADAPTERS[0]: Origin(direct=True),
        ADAPTERS[1]: Origin(direct=True),
        MEDIATION: Origin(via=ADAPTERS),
    }
)


def application_for(platform: str) -> Application:
    """The example's own `pyproject.toml`, in one build tool's spelling.

    §2.2 fixes the capability and not the syntax, so this adaptation is the
    example's, not the library's — which is the point of showing it.
    """
    config = tomllib.loads((EXAMPLE / "app-pyproject.toml").read_text(encoding="utf-8"))
    build = config["tool"]["examplebuild"]
    answered = [
        (distribution, per_platform[platform])
        for distribution, per_platform in build["native"].items()
        if platform in per_platform
    ]
    return Application(
        android=build.get("android", {}),
        deployment_target=build.get("ios", {}).get("deployment_target", ""),
        values={
            (distribution, identifier): answer
            for distribution, section in answered
            for identifier, answer in section.get("application_values", {}).items()
        },
        acknowledged={
            (distribution, identifier): Answer(date=held.get("date", ""))
            for distribution, section in answered
            for identifier, held in section.get("acknowledged", {}).items()
        },
    )


def record_for(platform: str) -> str:
    integration = read(
        [
            source_from_path(
                EXAMPLE / name,
                distribution=name,
                version="1.0.0",
                module=f"{name.replace('-', '_')}._native",
            )
            for name in (MEDIATION, *ADAPTERS)
        ],
        platform=platform,
        closure=CLOSURE,
        application=application_for(platform),
    )
    # A sidecar that fails validation contributes nothing, so an example that
    # has drifted from the vocabulary would quietly write a two-line record and
    # report success — a generator overstating itself, which is the thing this
    # repository keeps testing other people's tools for.
    integration.raise_for_errors()
    return integration.record.render()


def main() -> int:
    checking = "--check" in sys.argv
    problems = []
    for platform in ("android", "ios"):
        path = EXAMPLE / f"record-{platform}.record"
        rendered = record_for(platform)
        if checking:
            current = path.read_text(encoding="utf-8") if path.exists() else ""
            if current != rendered:
                problems.append(path.relative_to(ROOT))
            continue
        # newline: this repository pins LF (.gitattributes) and §9.3 hashes file
        # bytes, so a generator emitting CRLF on Windows would write a record no
        # LF checkout can reproduce.
        path.write_text(rendered, encoding="utf-8", newline="\n")
        print(f"wrote {path.relative_to(ROOT)}")

    if problems:
        for path in problems:
            print(f"FAIL  {path} has drifted; run python3 tools/record_example.py")
        return 1
    if checking:
        print("ok    the worked records are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
