"""Generate the worked integration records for `development/examples/mediated-ads/`.

Appendix E shows the shape of a §9 record, hand-written and non-normative. This
writes a real one, from the three sidecars in that directory and the
`app-pyproject.toml` beside them — including the `origin` line for a package the
application never named, which is the case the whole convention exists for.

    python3 tools/record_example.py           # write
    python3 tools/record_example.py --check   # fail if the files have drifted

Regenerate whenever a mediated-ads sidecar or the application file changes; the
record is a function of both, which is the property that makes it reviewable.

§9 hashes the *bytes* of each input, so a checkout whose line endings differ
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
    Application,
    Closure,
    ConsumerProfile,
    MappingAnswers,
    Origin,
    Platform,
    read,
    source_from_path,
)
from native_integration.testing import stub_resolvers  # noqa: E402

EXAMPLE = ROOT / "development" / "examples" / "mediated-ads"
ADAPTERS = ("pyadmob-applovin", "pyadmob-mintegral")
MEDIATION = "pyadmob"

#: The application depends on the adapters it wants; each adapter depends on the
#: mediation SDK, so `pyadmob` arrives underneath. That is the ordinary shape of
#: this ecosystem and it puts the package demanding an account identifier one
#: level below anything the application named.
CLOSURE = Closure.of(
    {
        ADAPTERS[0]: Origin(direct=True),
        ADAPTERS[1]: Origin(direct=True),
        MEDIATION: Origin(via=ADAPTERS),
    }
)


def answers(platform: Platform) -> MappingAnswers:
    config = tomllib.loads((EXAMPLE / "app-pyproject.toml").read_text(encoding="utf-8"))
    build = config["tool"]["examplebuild"]
    values = {
        distribution: per_platform[platform.value]["application_values"]
        for distribution, per_platform in build["native"].items()
        if platform.value in per_platform
        and "application_values" in per_platform[platform.value]
    }
    return MappingAnswers(
        application_values=values,
        usage_descriptions=build.get(platform.value, {}).get("usage_descriptions", {}),
    )


def record_for(platform: Platform) -> str:
    integration = read(
        platform=platform,
        closure=CLOSURE,
        application=Application(
            android_sdk={"min_sdk": 24, "compile_sdk": 35},
            deployment_target="15.0",
            answers=answers(platform),
        ),
        profile=ConsumerProfile(verify_resources=False),
        sources=[
            source_from_path(
                EXAMPLE / name,
                distribution=name,
                version="1.0.0",
                module=f"{name.replace('-', '_')}._native",
            )
            for name in (MEDIATION, *ADAPTERS)
        ],
        resolvers=stub_resolvers(),
        accept_current_surface=True,
    )
    return integration.record.dumps()


def main() -> int:
    checking = "--check" in sys.argv
    problems = []
    for platform in (Platform.ANDROID, Platform.IOS):
        path = EXAMPLE / f"record-{platform.value}.json"
        rendered = record_for(platform)
        if checking:
            current = path.read_text(encoding="utf-8") if path.exists() else ""
            if current != rendered:
                problems.append(path.relative_to(ROOT))
            continue
        path.write_text(rendered, encoding="utf-8", newline=chr(10))
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
