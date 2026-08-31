"""The examples this repository publishes, read by the reader.

`check_spec.py` tests that every key an example uses appears somewhere in the
specification. That catches a removed declaration and nothing else: a key can
exist, be spelled correctly, and still be wrong — the wrong type, in the wrong
platform's table, missing the field a constraint requires. An example that
teaches a sidecar no consumer accepts is worse than no example, so the live ones
are held to the validator rather than to a substring search.

The design-exploration sidecars under `development/examples/` are deliberately
not here. They were written alongside `first-attempt.md` to argue for a
declaration or against one, and rewriting an argument into the vocabulary it
produced would destroy the evidence. They are frozen with the document they
belong to.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

from native_integration import PLATFORMS, Closure, read, source_from_path  # noqa: E402

#: Held to SPEC.md. `check_spec.py` names the same set, for the same reason.
LIVE = ("examples/pystripe", "development/examples/mediated-ads")

#: Obligations an example sidecar cannot discharge, because they are discharged
#: by the *application* rather than by the producer: a value only the developer
#: knows (12), an action only they can acknowledge (13, 14), an export only they
#: can approve (29). A sidecar that could satisfy these on its own would mean
#: the consent §8.4 requires had been designed out, so their presence here is
#: the point rather than a gap.
UNANSWERED = ("ni.req.12", "ni.req.13", "ni.req.14", "ni.req.29")


def sidecars() -> list[Path]:
    found = [
        path.parent
        for prefix in LIVE
        for path in sorted((ROOT / prefix).rglob("native.toml"))
    ]
    assert found, "the live examples moved, and this test stopped testing them"
    return found


@pytest.mark.parametrize("directory", sidecars(), ids=lambda p: p.name)
@pytest.mark.parametrize("platform", sorted(PLATFORMS))
def test_every_published_example_is_a_sidecar_a_consumer_accepts(directory, platform):
    """Structure only. Whether the application answered is a different question,
    and `tools/record_example.py` asks it — this asks whether the *producer's*
    half is well-formed, which is the half an example is teaching.
    """
    name = directory.name
    integration = read(
        [source_from_path(directory, distribution=name, version="1.0.0")],
        platform=platform,
        closure=Closure.direct(name),
    )
    structural = [found for found in integration.findings.blocking if found.obligation not in UNANSWERED]
    assert not structural, "\n".join(found.render() for found in structural)


def test_the_worked_records_still_regenerate():
    """The other half, which nothing here was asking.

    `tools/record_example.py` is a CI step of its own, and the suite's only
    claim about the worked example was the producer half above. So when the
    §9.1 acceptance gate landed, the generator stopped being able to write a
    record at all -- the example had never answered the bootstrap action -- and
    every test still passed. The failure surfaced only in CI, in the one step
    nothing in here shadows.

    This runs the step. It is a subprocess rather than an import because that
    is what CI runs, and a test that reimplemented it would be checking a
    second copy of the thing that broke.
    """
    finished = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "record_example.py"), "--check"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert finished.returncode == 0, finished.stdout + finished.stderr
