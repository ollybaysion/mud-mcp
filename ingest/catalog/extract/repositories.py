"""Extract Repository interfaces and the Entity they query.

Looks for `interface FooRepository extends JpaRepository<TargetEntity, ...>`.
Falls back to filename heuristic (FooRepository → Foo).
"""

from __future__ import annotations

import re
from pathlib import Path

from catalog.extract.base import iter_java_files, parse_file, rel_to_repo, start_line
from catalog.models import Edge, Node

# Detect: extends JpaRepository<X, ...>
_JPA_RE = re.compile(r"extends\s+(?:Jpa|CrudRepository|PagingAndSortingRepository|Repository)[A-Za-z]*\s*<\s*([A-Za-z_][A-Za-z0-9_]*)\s*,")


def extract(repo_root: Path, repo_dir: Path) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []

    if not repo_dir.is_dir():
        return nodes, edges

    for java_file in iter_java_files(repo_dir):
        text = java_file.read_text(encoding="utf-8")
        tree = parse_file(java_file)
        if tree is None:
            continue

        # Repositories are usually interfaces in Spring Data — javalang has
        # InterfaceDeclaration; we'll catch them via filename for simplicity.
        name = java_file.stem
        if not name.endswith("Repository"):
            continue

        repo_id = Node.make_id("Repository", name)
        nodes.append(
            Node(
                id=repo_id,
                label="Repository",
                name=name,
                file_path=rel_to_repo(java_file, repo_root),
                start_line=_first_decl_line(tree),
            )
        )

        # Find target entity via regex on source text (handles interface generics
        # reliably without complicated AST navigation)
        m = _JPA_RE.search(text)
        target_entity = m.group(1) if m else name.replace("Repository", "")
        edges.append(
            Edge(
                from_id=repo_id,
                to_id=Node.make_id("Entity", target_entity),
                type="QUERIES",
            )
        )

    return nodes, edges


def _first_decl_line(tree) -> int | None:
    # Use the first top-level declaration's position as a proxy.
    for tdecl in tree.types or []:
        pos = getattr(tdecl, "position", None)
        if pos:
            return pos.line
    return None
