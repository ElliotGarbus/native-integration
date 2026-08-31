"""§6.1's five rules, and rule 1's two operands in particular.

The corpus carries the two dangerous cases — a Kotlin `package` disagreeing with
its path, and a component outside every owned namespace. The rest of rule 1 is
here: a file in the default package, a path segment that cannot name one, and
the case-sensitivity the platform itself applies. Each is a separate `MUST
reject` in §6.1 and none of them is expensive enough to earn a fixture of its
own.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from native_integration import Closure, Origin, read, source_from_path
from native_integration.semantics import declared_package, path_namespace

OWNED = "org.example.mypkg"


def sidecar(tmp_path: Path, *, sources: str, files: dict[str, str], owns: str = OWNED) -> Path:
    root = tmp_path / "pyx" / "_native"
    root.mkdir(parents=True)
    (root / "native.toml").write_text(
        f'contract = "1"\n\n'
        f'[android.owns]\njava_namespaces = ["{owns}"]\n\n'
        f'[android.contributes.src]\n{sources}\n',
        encoding="utf-8",
    )
    for relpath, text in files.items():
        target = root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return root


def complaints(root: Path) -> list[str]:
    integration = read(
        [source_from_path(root, distribution="pyx", version="1.0.0", module="pyx._native")],
        platform="android",
        closure=Closure.of({"pyx": Origin(direct=True)}),
    )
    return [
        found.message
        for found in integration.findings
        if found.obligation == "ni.req.23"
    ]


# -- the derivation ----------------------------------------------------------


def test_the_path_namespace_is_the_directory_relative_to_its_root():
    """§6.1's worked example, which the rule states rather than implies."""
    assert path_namespace("java", "java/org/example/mypkg/Bridge.java") == OWNED


def test_a_file_directly_in_the_root_derives_the_default_package():
    assert path_namespace("java", "java/Bridge.java") == ""


def test_a_nested_source_root_is_stripped_whole():
    assert path_namespace("src/java", "src/java/org/example/Bridge.java") == "org.example"


@pytest.mark.parametrize("text, expected", [
    ("package org.example.mypkg;\n", OWNED),
    ("package org.example.mypkg\n", OWNED),  # Kotlin needs no terminator
    ("@file:JvmName(\"X\")\npackage org.example.mypkg\n", OWNED),
    ("package  org . example . mypkg ;\n", OWNED),
    ("class Bridge {}\n", None),
])
def test_the_declared_package_in_either_language(text, expected):
    assert declared_package(text) == expected


def test_a_commented_out_package_is_not_a_declaration():
    """Otherwise the check reads a line the compiler never will."""
    assert declared_package("// package org.other\npackage org.example.mypkg;\n") == OWNED
    assert declared_package("/*\npackage org.other\n*/\nclass B {}\n") is None


# -- what rule 1 must reject -------------------------------------------------


def test_a_file_in_the_default_package(tmp_path):
    root = sidecar(
        tmp_path,
        sources='java = ["java"]',
        files={"java/Bridge.java": "class Bridge {}\n"},
    )
    assert any("names no package" in c for c in complaints(root))


def test_a_file_declaring_no_package_at_all(tmp_path):
    root = sidecar(
        tmp_path,
        sources='java = ["java"]',
        files={"java/org/example/mypkg/Bridge.java": "class Bridge {}\n"},
    )
    assert any("declares no `package`" in c for c in complaints(root))


def test_a_path_segment_that_cannot_name_a_package(tmp_path):
    """`my-pkg` is a legal directory name and not a legal identifier."""
    root = sidecar(
        tmp_path,
        sources='java = ["java"]',
        files={"java/org/example/my-pkg/Bridge.java": "package org.example.my-pkg;\n"},
    )
    assert any("cannot name a package" in c for c in complaints(root))


def test_a_file_outside_every_owned_namespace_by_both_operands(tmp_path):
    root = sidecar(
        tmp_path,
        sources='java = ["java"]',
        files={"java/com/vendor/Bridge.java": "package com.vendor;\n"},
    )
    assert any("outside every namespace" in c for c in complaints(root))


def test_the_comparison_is_case_sensitive_as_the_platform_is(tmp_path):
    """`org.example.MyPkg` is a different package from `org.example.mypkg`, and
    a filesystem that disagrees is not the authority here."""
    root = sidecar(
        tmp_path,
        sources='java = ["java"]',
        files={"java/org/example/MyPkg/Bridge.java": "package org.example.MyPkg;\n"},
    )
    assert any("outside every namespace" in c for c in complaints(root))


# -- what it must accept -----------------------------------------------------


def test_a_file_whose_path_and_package_agree_and_are_owned(tmp_path):
    root = sidecar(
        tmp_path,
        sources='java = ["java"]',
        files={"java/org/example/mypkg/Bridge.java": "package org.example.mypkg;\n"},
    )
    assert complaints(root) == []


def test_a_file_deeper_than_the_claim_is_still_contained(tmp_path):
    """§6.1's containment: a namespace contains anything beneath it."""
    root = sidecar(
        tmp_path,
        sources='java = ["java"]',
        files={
            "java/org/example/mypkg/inner/Bridge.java": "package org.example.mypkg.inner;\n"
        },
    )
    assert complaints(root) == []
