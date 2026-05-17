"""Pydantic models for catalog nodes and edges.

A Node represents one entity in the graph (a Controller, Service, Entity, etc.).
An Edge represents a typed relationship between two nodes by stable id.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

NodeLabel = Literal[
    "Controller",
    "Endpoint",
    "Service",
    "Repository",
    "Entity",
    "Crawler",
    "Migration",
]

RelType = Literal[
    "EXPOSES",       # Controller -> Endpoint
    "DEPENDS_ON",    # Controller/Service -> Service/Repository
    "QUERIES",       # Repository -> Entity
    "STORES_IN",     # Crawler -> Entity (via overlay)
    "TRIGGERS",      # Job/Scheduler -> Service (via overlay)
]


class Node(BaseModel):
    """A catalog node.

    `id` is a stable string used to look up the node across the pipeline.
    Convention: "<Label>:<name>" — e.g. "Controller:TrendController".
    """

    id: str
    label: NodeLabel
    name: str
    file_path: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    summary: str | None = None
    importance: str | None = None
    tags: list[str] = Field(default_factory=list)
    # Extra label-specific properties (e.g. Endpoint.verb, Entity.tableName)
    extra: dict[str, Any] = Field(default_factory=dict)

    @staticmethod
    def make_id(label: NodeLabel, name: str) -> str:
        return f"{label}:{name}"

    def cypher_props(self) -> dict[str, Any]:
        """Flattened property dict for Cypher SET clauses."""
        base = {
            "name": self.name,
            "filePath": self.file_path,
            "startLine": self.start_line,
            "endLine": self.end_line,
            "summary": self.summary,
            "importance": self.importance,
            "tags": self.tags,
        }
        base.update(self.extra)
        # Strip None values so Cypher SET doesn't blank existing data
        return {k: v for k, v in base.items() if v is not None}


class Edge(BaseModel):
    """A directed, typed relationship between two node ids."""

    from_id: str
    to_id: str
    type: RelType
    note: str | None = None


class CatalogData(BaseModel):
    """In-memory representation of one ingest pass."""

    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)

    def node_index(self) -> dict[str, Node]:
        return {n.id: n for n in self.nodes}
