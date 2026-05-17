"""Extract @Service classes and their constructor-injected dependencies."""

from __future__ import annotations

from pathlib import Path

from catalog.extract.base import (
    classes_of,
    constructor_param_types,
    has_annotation,
    iter_java_files,
    parse_file,
    rel_to_repo,
    start_line,
)
from catalog.models import Edge, Node

_SERVICE_ANNS = {"Service", "Component"}


def extract(repo_root: Path, service_root: Path) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []

    if not service_root.is_dir():
        return nodes, edges

    for java_file in iter_java_files(service_root):
        tree = parse_file(java_file)
        if tree is None:
            continue
        for cls in classes_of(tree):
            if not has_annotation(cls, _SERVICE_ANNS):
                continue

            svc_id = Node.make_id("Service", cls.name)
            nodes.append(
                Node(
                    id=svc_id,
                    label="Service",
                    name=cls.name,
                    file_path=rel_to_repo(java_file, repo_root),
                    start_line=start_line(cls),
                )
            )

            for type_name, _ in constructor_param_types(cls):
                if type_name.endswith("Service"):
                    edges.append(
                        Edge(
                            from_id=svc_id,
                            to_id=Node.make_id("Service", type_name),
                            type="DEPENDS_ON",
                        )
                    )
                elif type_name.endswith("Repository"):
                    edges.append(
                        Edge(
                            from_id=svc_id,
                            to_id=Node.make_id("Repository", type_name),
                            type="DEPENDS_ON",
                        )
                    )

    return nodes, edges
