"""Extract JPA @Entity classes and their @Table + fields."""

from __future__ import annotations

from pathlib import Path

from catalog.extract.base import (
    annotation_string_value,
    classes_of,
    find_annotation,
    has_annotation,
    iter_java_files,
    parse_file,
    rel_to_repo,
    start_line,
)
from catalog.models import Edge, Node


def extract(repo_root: Path, entity_dir: Path) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []

    if not entity_dir.is_dir():
        return nodes, edges

    for java_file in iter_java_files(entity_dir):
        tree = parse_file(java_file)
        if tree is None:
            continue
        for cls in classes_of(tree):
            if not has_annotation(cls, {"Entity"}):
                continue

            table_name = annotation_string_value(
                find_annotation(cls, {"Table"}), attr="name"
            )

            fields: list[str] = []
            for field in cls.fields:
                for decl in field.declarators:
                    fields.append(decl.name)

            ent_id = Node.make_id("Entity", cls.name)
            nodes.append(
                Node(
                    id=ent_id,
                    label="Entity",
                    name=cls.name,
                    file_path=rel_to_repo(java_file, repo_root),
                    start_line=start_line(cls),
                    extra={
                        "tableName": table_name,
                        "fields": fields,
                    },
                )
            )

    return nodes, edges
