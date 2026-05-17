"""Load overlay.yml and merge curated metadata into the extracted catalog.

overlay.yml shape:
    nodes:
      TrendController:
        summary: "..."
        importance: high
        tags: [api, search]
    extra_edges:
      - from: DailyDigestJob
        to: EmailService
        type: TRIGGERS
        note: "..."
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from catalog.models import CatalogData, Edge, Node


class OverlayNode(BaseModel):
    summary: str | None = None
    importance: str | None = None
    tags: list[str] = Field(default_factory=list)


class OverlayEdge(BaseModel):
    from_: str = Field(..., alias="from")
    to: str
    type: str
    note: str | None = None

    model_config = {"populate_by_name": True}


class Overlay(BaseModel):
    nodes: dict[str, OverlayNode] = Field(default_factory=dict)
    extra_edges: list[OverlayEdge] = Field(default_factory=list)


def load_overlay(path: Path) -> Overlay:
    if not path.exists():
        return Overlay()
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Overlay.model_validate(raw)


def apply_overlay(catalog: CatalogData, overlay: Overlay) -> tuple[int, int]:
    """Merge overlay metadata into the catalog. Returns (nodes_touched, edges_added)."""
    nodes_touched = 0
    by_name: dict[str, Node] = {}
    for n in catalog.nodes:
        by_name.setdefault(n.name, n)

    for name, meta in overlay.nodes.items():
        node = by_name.get(name)
        if node is None:
            continue
        if meta.summary is not None:
            node.summary = meta.summary
        if meta.importance is not None:
            node.importance = meta.importance
        if meta.tags:
            node.tags = list({*node.tags, *meta.tags})
        nodes_touched += 1

    edges_added = 0
    for e in overlay.extra_edges:
        # overlay edges reference nodes by bare name; resolve to id by lookup.
        a = by_name.get(e.from_)
        b = by_name.get(e.to)
        if a is None or b is None:
            continue
        catalog.edges.append(
            Edge(from_id=a.id, to_id=b.id, type=e.type, note=e.note)  # type: ignore[arg-type]
        )
        edges_added += 1

    return nodes_touched, edges_added
