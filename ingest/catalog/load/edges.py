"""MERGE queries for edges.

Edges reference nodes by stable id (e.g. "Service:TrendService"). We look up
the target node by its key and create the relationship if both endpoints exist.
Edges to unknown nodes are skipped with a warning.
"""

from __future__ import annotations

from typing import Iterable

from catalog.load.client import Neo4jClient
from catalog.models import CatalogData, Edge


def _node_match_clause(node_id: str) -> tuple[str, dict]:
    """Build a MATCH fragment + params for a node id like 'Service:TrendService' or
    'Endpoint:GET /api/trends'.
    """
    label, key = node_id.split(":", 1)
    if label == "Endpoint":
        verb, path = key.split(" ", 1)
        return (
            "(:Endpoint {verb: $verb, path: $path})",
            {"verb": verb, "path": path},
        )
    return (f"(:{label} {{name: $name}})", {"name": key})


def merge_edges(client: Neo4jClient, edges: Iterable[Edge], catalog: CatalogData) -> tuple[int, int]:
    """Merge edges; returns (merged, skipped) counts."""
    index = catalog.node_index()
    merged = 0
    skipped = 0

    with client.session() as session:
        for edge in edges:
            if edge.from_id not in index or edge.to_id not in index:
                skipped += 1
                continue

            from_match, from_params = _node_match_clause(edge.from_id)
            to_match, to_params = _node_match_clause(edge.to_id)

            # Disambiguate param names
            params = {f"a_{k}": v for k, v in from_params.items()}
            params.update({f"b_{k}": v for k, v in to_params.items()})

            from_match_aliased = from_match.replace("$verb", "$a_verb").replace("$path", "$a_path").replace("$name", "$a_name")
            to_match_aliased = to_match.replace("$verb", "$b_verb").replace("$path", "$b_path").replace("$name", "$b_name")

            cypher = f"""
                MATCH (a){from_match_aliased[1:]}
                MATCH (b){to_match_aliased[1:]}
                MERGE (a)-[r:{edge.type}]->(b)
                RETURN id(r) AS rid
            """.replace("(a)(:", "(a:").replace("(b)(:", "(b:")

            session.run(cypher, **params)
            merged += 1

    return merged, skipped
