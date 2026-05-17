"""Resolve dangling edges and warn about references to unknown nodes.

Extractors emit edges to ids like 'Service:TrendService' based on naming.
Some of those targets may not exist (e.g. a Controller depends on a class
whose source we don't parse). Resolve drops those edges and records them
for reporting.
"""

from __future__ import annotations

from catalog.models import CatalogData, Edge


def resolve_edges(catalog: CatalogData) -> list[Edge]:
    """Return the list of edges that point to unknown nodes (so caller can warn).

    Mutates `catalog.edges` to keep only resolvable ones.
    """
    index = catalog.node_index()
    keep: list[Edge] = []
    dropped: list[Edge] = []
    for edge in catalog.edges:
        if edge.from_id in index and edge.to_id in index:
            keep.append(edge)
        else:
            dropped.append(edge)
    catalog.edges = keep
    return dropped
