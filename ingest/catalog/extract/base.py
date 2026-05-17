"""Shared helpers for Java AST extraction."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import javalang
from javalang.tree import (
    Annotation,
    ClassDeclaration,
    CompilationUnit,
    ElementValuePair,
    Literal,
    MemberReference,
)


def iter_java_files(root: Path) -> Iterator[Path]:
    """Yield .java files under root, skipping build/generated dirs."""
    skip = {"build", "target", ".gradle", "node_modules"}
    for p in root.rglob("*.java"):
        if any(part in skip for part in p.parts):
            continue
        yield p


def parse_file(path: Path) -> CompilationUnit | None:
    """Parse a Java file. Returns None on parse error (logged by caller)."""
    try:
        return javalang.parse.parse(path.read_text(encoding="utf-8"))
    except (javalang.parser.JavaSyntaxError, FileNotFoundError):
        return None


def classes_of(tree: CompilationUnit) -> Iterator[ClassDeclaration]:
    for _, cls in tree.filter(ClassDeclaration):
        yield cls


def has_annotation(node, names: set[str]) -> bool:
    return any(getattr(a, "name", None) in names for a in getattr(node, "annotations", []) or [])


def find_annotation(node, names: set[str]) -> Annotation | None:
    for a in getattr(node, "annotations", []) or []:
        if a.name in names:
            return a
    return None


def annotation_string_value(ann: Annotation | None, attr: str = "value") -> str | None:
    """Extract a string value from an annotation.

    Handles:
      @Mapping("/x")                      → "/x"
      @Mapping(value = "/x")              → "/x"  (attr="value")
      @Mapping(value = "/x", method = ...) → "/x"
      @Mapping                            → None
    """
    if ann is None or ann.element is None:
        return None

    elem = ann.element

    # Single literal: @Mapping("/x")
    if isinstance(elem, Literal):
        return _unquote(elem.value)

    # Named pairs: @Mapping(value = "/x", ...)
    if isinstance(elem, list):
        for pair in elem:
            if isinstance(pair, ElementValuePair) and pair.name == attr:
                if isinstance(pair.value, Literal):
                    return _unquote(pair.value.value)
        # Fall back to first literal pair
        for pair in elem:
            if isinstance(pair, ElementValuePair) and isinstance(pair.value, Literal):
                return _unquote(pair.value.value)

    if isinstance(elem, MemberReference):
        return elem.member
    return None


def _unquote(s: str) -> str:
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s


def type_name(t) -> str | None:
    """Best-effort type name extraction (handles generics)."""
    if t is None:
        return None
    name = getattr(t, "name", None)
    if name:
        return name
    return None


def constructor_param_types(cls: ClassDeclaration) -> list[tuple[str, str]]:
    """Return (type_name, param_name) for the (first) constructor."""
    for ctor in cls.constructors:
        out: list[tuple[str, str]] = []
        for p in ctor.parameters:
            tn = type_name(p.type)
            if tn:
                out.append((tn, p.name))
        return out
    return []


def start_line(node) -> int | None:
    pos = getattr(node, "position", None)
    if pos is None:
        return None
    return pos.line


def rel_to_repo(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)
