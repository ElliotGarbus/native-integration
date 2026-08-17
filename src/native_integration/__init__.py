"""A reference reader for the native-integration specification.

The specification puts 26 numbered obligations on a *consumer* — the build tool
that reads sidecars and generates the native project. This library exists so
that those are code paths a tool gets by using it, rather than prose it has to
remember to implement.

A minimal read::

    from native_integration import Application, Closure, MappingAnswers, Platform, read

    integration = read(
        platform=Platform.ANDROID,
        closure=Closure.direct("pystripe"),
        application=Application(
            android_sdk={"min_sdk": 24, "compile_sdk": 35},
            answers=MappingAnswers(
                application_values={"pystripe": {"stripe_return_scheme": "trailmap-pay"}},
                allow_exported={"pystripe": ["org.pystripe.PaymentReturnActivity"]},
            ),
        ),
        record_path="native-integration.lock.json",
    )
    print(integration.report())
    integration.raise_for_errors()

``docs/REQUIREMENTS.md`` maps every §8 requirement to the code path that
discharges it, and ``tests/test_requirement_coverage.py`` fails if one falls
out of both tables.
"""

from __future__ import annotations

from .answers import AnswerSource, CredentialKind, CredentialReference, MappingAnswers, NoAnswers
from .context import Application, ConsumerProfile
from .contract import ENTRY_POINT_GROUP, IMPLEMENTED, ContractVersion
from .diagnostics import (
    Diagnostic,
    DiagnosticBag,
    IntegrationError,
    Rule,
    Severity,
    SpecViolation,
    UnimplementedObligation,
)
from .discovery import Closure, Origin, discover, normalize_name, source_from_path
from .effective import Contribution, EffectiveSet, PrerequisiteStatus
from .model import (
    AndroidSection,
    ApplicationValue,
    Component,
    GradleDependency,
    GradleRepository,
    IosSection,
    Permission,
    Platform,
    Prerequisite,
    PrerequisiteKind,
    PythonModule,
    Sidecar,
    SwiftPackage,
)
from .ports import (
    ArtifactInspector,
    ArtifactManifest,
    BinaryTarget,
    DependencyRequest,
    GradleGraph,
    GradleResolver,
    ManifestComponent,
    ManifestFeature,
    NO_RESOLVERS,
    ResolutionFailure,
    ResolvedArtifact,
    ResolvedSwiftPackage,
    Resolvers,
    SwiftGraph,
    SwiftPackageRequest,
    SwiftResolver,
)
from .record import Delta, DistributionRecord, IntegrationRecord, MalformedRecord
from .resolution import Integration, check_sidecar, read
from .resources import SidecarSource

__version__ = "0.1.0.dev0"

__all__ = [
    "AndroidSection",
    "AnswerSource",
    "Application",
    "ApplicationValue",
    "ArtifactInspector",
    "ArtifactManifest",
    "BinaryTarget",
    "Closure",
    "Component",
    "ConsumerProfile",
    "ContractVersion",
    "Contribution",
    "CredentialKind",
    "CredentialReference",
    "Delta",
    "DependencyRequest",
    "Diagnostic",
    "DiagnosticBag",
    "DistributionRecord",
    "ENTRY_POINT_GROUP",
    "EffectiveSet",
    "GradleDependency",
    "GradleGraph",
    "GradleRepository",
    "GradleResolver",
    "IMPLEMENTED",
    "Integration",
    "IntegrationError",
    "IntegrationRecord",
    "MalformedRecord",
    "IosSection",
    "ManifestComponent",
    "ManifestFeature",
    "MappingAnswers",
    "NO_RESOLVERS",
    "NoAnswers",
    "Origin",
    "Permission",
    "Platform",
    "Prerequisite",
    "PrerequisiteKind",
    "PrerequisiteStatus",
    "PythonModule",
    "ResolutionFailure",
    "ResolvedArtifact",
    "ResolvedSwiftPackage",
    "Resolvers",
    "Rule",
    "Severity",
    "Sidecar",
    "SidecarSource",
    "SpecViolation",
    "SwiftGraph",
    "SwiftPackage",
    "SwiftPackageRequest",
    "SwiftResolver",
    "UnimplementedObligation",
    "__version__",
    "check_sidecar",
    "discover",
    "normalize_name",
    "read",
    "source_from_path",
]
