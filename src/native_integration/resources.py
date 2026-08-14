"""Reading a sidecar's files, safely (§3.2, §4.1).

Every path a sidecar declares is interpreted relative to ``native.toml`` and
must not escape its directory, checked **after** normalization and symlink
resolution; symlinked resources are rejected outright in version 1. Contributed
source must be UTF-8. Those checks live here so that no caller can read a
declared path without them.

The sidecar directory is also *build input, not application payload*
(requirement 8.14): :meth:`SidecarSource.payload_exclusions` is what a consumer
hands its Python-payload assembler.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Iterator

SIDECAR_NAME = "native.toml"


class ResourceError(Exception):
    """A declared resource could not be read, or violates §4.1."""

    def __init__(self, relpath: str, reason: str, *, kind: str) -> None:
        self.relpath = relpath
        self.reason = reason
        self.kind = kind  # "escapes" | "symlink" | "unreadable" | "encoding"
        super().__init__(f"{relpath}: {reason}")


def normalize(relpath: str) -> str:
    """A declared path in its recorded form: forward slashes, no ``.`` parts."""
    pure = PurePosixPath(str(relpath).replace(os.sep, "/"))
    parts = [p for p in pure.parts if p not in (".", "")]
    return "/".join(parts)


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class SidecarSource:
    """The files of one distribution's sidecar directory.

    ``root`` is the directory the entry-point value names, reached through the
    distribution's own file-resource interface — never by assuming a
    conventional ``site-packages`` layout.
    """

    distribution: str
    version: str
    module: str
    root: Path
    #: Where ``root`` sits relative to the distribution's install root, which is
    #: what a Python-payload assembler needs in order to exclude it.
    package_relpath: str = ""

    # --- reading ------------------------------------------------------------

    def resolve(self, relpath: str) -> Path:
        """Resolve a declared path, enforcing §4.1's containment and symlink rules."""
        rel = normalize(relpath)
        if not rel:
            raise ResourceError(relpath, "is empty", kind="escapes")
        if PurePosixPath(rel).is_absolute() or rel.startswith("/"):
            raise ResourceError(relpath, "is absolute", kind="escapes")

        base = self.root
        candidate = base / rel
        # Symlinks first: resolving before checking would let a link that points
        # back inside the directory pass a containment test it should not reach.
        walked = base
        for part in PurePosixPath(rel).parts:
            if part == "..":
                raise ResourceError(relpath, "escapes the sidecar directory", kind="escapes")
            walked = walked / part
            if walked.is_symlink():
                raise ResourceError(
                    relpath,
                    f"{part} is a symlink; symlinked resources are not permitted in version 1",
                    kind="symlink",
                )
        if not candidate.exists():
            raise ResourceError(relpath, "does not exist", kind="unreadable")

        real_base = os.path.realpath(base)
        real = os.path.realpath(candidate)
        if os.path.commonpath([real_base, real]) != real_base:
            raise ResourceError(relpath, "escapes the sidecar directory", kind="escapes")
        return candidate

    def read_bytes(self, relpath: str) -> bytes:
        path = self.resolve(relpath)
        try:
            return path.read_bytes()
        except OSError as exc:  # pragma: no cover - platform dependent
            raise ResourceError(relpath, f"could not be read ({exc})", kind="unreadable") from exc

    def read_text(self, relpath: str) -> str:
        """Read a contributed source file, which §4.1 requires to be UTF-8."""
        data = self.read_bytes(relpath)
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ResourceError(relpath, "is not UTF-8 encoded", kind="encoding") from exc

    def sidecar_bytes(self) -> bytes:
        return self.read_bytes(SIDECAR_NAME)

    # --- enumeration --------------------------------------------------------

    def walk(self, relpath: str, suffix: str) -> tuple[str, ...]:
        """Every file under ``relpath`` whose name ends in ``suffix``, recursively.

        §6.4 and §7.5: from each listed directory the consumer stages exactly
        the files with the matching extension and ignores other files. The
        returned paths are normalized and sorted, so staging order — and the
        record — does not depend on directory iteration order.
        """
        base = self.resolve(relpath)
        if not base.is_dir():
            raise ResourceError(relpath, "is not a directory", kind="unreadable")
        found: list[str] = []
        prefix = normalize(relpath)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames.sort()
            rel_dir = normalize(os.path.relpath(dirpath, base))
            for name in sorted(filenames):
                if not name.endswith(suffix):
                    continue
                rel = "/".join(p for p in (prefix, rel_dir, name) if p)
                # Re-resolve each hit so a symlinked file inside a listed root
                # is rejected rather than silently staged.
                self.resolve(rel)
                found.append(rel)
        return tuple(found)

    def hash_all(self, relpaths: Iterable[str]) -> dict[str, str]:
        """SHA-256 per file, keyed by normalized relative path (§9)."""
        return {normalize(p): sha256_bytes(self.read_bytes(p)) for p in sorted(set(relpaths))}

    # --- payload ------------------------------------------------------------

    def payload_exclusions(self) -> tuple[str, ...]:
        """Paths a Python payload for the device must not contain (§4.1).

        The sidecar directory is build input: ``native.toml`` and every resource
        under it have already been consumed at build time.
        """
        base = normalize(self.package_relpath) if self.package_relpath else self.module.replace(".", "/")
        return (base + "/",)

    def __iter__(self) -> Iterator[str]:  # pragma: no cover - convenience
        for dirpath, _dirnames, filenames in os.walk(self.root):
            rel_dir = normalize(os.path.relpath(dirpath, self.root))
            for name in sorted(filenames):
                yield "/".join(p for p in (rel_dir, name) if p)
