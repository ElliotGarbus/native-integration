"""A reference reader for the native-integration specification.

`SPEC.md` puts 46 numbered obligations and 15 advisory ones on a **consumer** —
the build tool that reads sidecars and generates the native project. This
library exists so that the reading half of that is a code path a tool gets by
using it, rather than prose it has to remember to implement.

It reads, validates, resolves and records. It generates nothing: no Gradle
files, no Xcode project, no manifest. That boundary is deliberate, and it is
where a build tool's own work starts.

A minimal read::

    from native_integration import Application, Closure, read, source_from_path

    integration = read(
        [source_from_path("pystripe/_native", distribution="pystripe")],
        platform="android",
        closure=Closure.direct("pystripe"),
        application=Application(
            android={"min_sdk": 24, "compile_sdk": 35},
            values={("pystripe", "stripe_return_scheme"): "trailmap-pay"},
        ),
    )
    print(integration.report())
    integration.raise_for_errors()
    print(integration.record.render())

**The vocabulary is not written down twice.** Every declaration, every closed
value, every refusal and every diagnostic id comes from
[`contract/v1.toml`](contract/v1.toml) at run time, so a rule the registry
states is a rule this reader enforces without anyone having transcribed it.
`docs/REQUIREMENTS.md` maps each §8 obligation to the module that discharges it.
"""

from __future__ import annotations

from .acceptance import Delta
from .application import (
    Answer,
    Application,
    Approval,
    Credential,
    FeatureDecision,
    PackagingChoice,
)
from .contract import ENTRY_POINT_GROUP, IMPLEMENTED, ContractVersion
from .discovery import Closure, Origin, discover, normalize_name, source_from_path
from .document import Sidecar
from .findings import Finding, Findings
from .graph import Artifact, Graph, Package, graph_of
from .integration import Resolved
from .reader import Integration, IntegrationError, UnimplementedProfile, read
from .recording import Fact, Record, RecordError
from .registry import PLATFORMS, Registry
from .registry import load as load_registry
from .resources import ResourceError, SidecarSource

__version__ = "0.1.0.dev0"

__all__ = [
    "Answer",
    "Application",
    "Approval",
    "Artifact",
    "Closure",
    "ContractVersion",
    "Credential",
    "Delta",
    "ENTRY_POINT_GROUP",
    "Fact",
    "FeatureDecision",
    "Finding",
    "Findings",
    "Graph",
    "IMPLEMENTED",
    "Integration",
    "IntegrationError",
    "Origin",
    "PLATFORMS",
    "Package",
    "PackagingChoice",
    "Record",
    "RecordError",
    "Registry",
    "ResourceError",
    "Resolved",
    "Sidecar",
    "SidecarSource",
    "UnimplementedProfile",
    "__version__",
    "discover",
    "graph_of",
    "load_registry",
    "normalize_name",
    "read",
    "source_from_path",
]
