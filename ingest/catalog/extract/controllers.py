"""Extract Controllers + their Endpoints."""

from __future__ import annotations

from pathlib import Path

from catalog.extract.base import (
    annotation_string_value,
    classes_of,
    constructor_param_types,
    find_annotation,
    has_annotation,
    iter_java_files,
    parse_file,
    rel_to_repo,
    start_line,
)
from catalog.models import Edge, Node

_CONTROLLER_ANNS = {"RestController", "Controller"}
_MAPPING_VERBS = {
    "GetMapping": "GET",
    "PostMapping": "POST",
    "PutMapping": "PUT",
    "PatchMapping": "PATCH",
    "DeleteMapping": "DELETE",
}


def extract(repo_root: Path, controllers_dir: Path) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []

    if not controllers_dir.is_dir():
        return nodes, edges

    for java_file in iter_java_files(controllers_dir):
        tree = parse_file(java_file)
        if tree is None:
            continue
        for cls in classes_of(tree):
            if not has_annotation(cls, _CONTROLLER_ANNS):
                continue

            base_path = annotation_string_value(
                find_annotation(cls, {"RequestMapping"})
            ) or ""

            ctrl_id = Node.make_id("Controller", cls.name)
            nodes.append(
                Node(
                    id=ctrl_id,
                    label="Controller",
                    name=cls.name,
                    file_path=rel_to_repo(java_file, repo_root),
                    start_line=start_line(cls),
                    extra={"basePath": base_path} if base_path else {},
                )
            )

            # Constructor dependencies → DEPENDS_ON candidates
            for type_name, _ in constructor_param_types(cls):
                if type_name.endswith(("Service", "Repository", "Component")):
                    label = "Service" if type_name.endswith("Service") else (
                        "Repository" if type_name.endswith("Repository") else "Service"
                    )
                    edges.append(
                        Edge(
                            from_id=ctrl_id,
                            to_id=Node.make_id(label, type_name),
                            type="DEPENDS_ON",
                        )
                    )

            # Endpoints
            for method in cls.methods:
                for ann in method.annotations or []:
                    if ann.name not in _MAPPING_VERBS:
                        continue
                    verb = _MAPPING_VERBS[ann.name]
                    sub_path = annotation_string_value(ann) or ""
                    full_path = _join_paths(base_path, sub_path)
                    ep_id = Node.make_id("Endpoint", f"{verb} {full_path}")

                    nodes.append(
                        Node(
                            id=ep_id,
                            label="Endpoint",
                            name=f"{verb} {full_path}",
                            file_path=rel_to_repo(java_file, repo_root),
                            start_line=start_line(method),
                            extra={
                                "verb": verb,
                                "path": full_path,
                                "handler": method.name,
                                "controller": cls.name,
                            },
                        )
                    )
                    edges.append(
                        Edge(from_id=ctrl_id, to_id=ep_id, type="EXPOSES")
                    )

    return nodes, edges


def _join_paths(a: str, b: str) -> str:
    if not a:
        return b
    if not b:
        return a
    if a.endswith("/") and b.startswith("/"):
        return a[:-1] + b
    if not a.endswith("/") and not b.startswith("/"):
        return a + "/" + b
    return a + b
