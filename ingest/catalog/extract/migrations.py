"""Extract Flyway migrations (Vxx__name.sql)."""

from __future__ import annotations

import re
from pathlib import Path

from catalog.extract.base import rel_to_repo
from catalog.models import Edge, Node

_MIGRATION_RE = re.compile(r"^V(\d+)__(.+)\.sql$")


def extract(repo_root: Path, migration_dir: Path) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []

    if not migration_dir.is_dir():
        return nodes, edges

    for sql_file in sorted(migration_dir.glob("*.sql")):
        m = _MIGRATION_RE.match(sql_file.name)
        if not m:
            continue
        version = int(m.group(1))
        title = m.group(2)
        name = f"V{version}_{title}"

        nodes.append(
            Node(
                id=Node.make_id("Migration", name),
                label="Migration",
                name=name,
                file_path=rel_to_repo(sql_file, repo_root),
                start_line=1,
                extra={
                    "version": version,
                    "title": title,
                    "filename": sql_file.name,
                },
            )
        )

    return nodes, edges
