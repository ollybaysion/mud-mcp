"""MERGE queries for nodes.

Strategy:
  1. mark_all_stale() — before ingest, set stale=true on every node
  2. merge_*() — during ingest, write nodes with stale=false + lastIngestedAt
  3. sweep_stale() — after ingest, DETACH DELETE anything still stale
"""

from __future__ import annotations

from catalog.load.client import Neo4jClient
from catalog.models import Node


def mark_all_stale(client: Neo4jClient) -> int:
    with client.session() as session:
        result = session.run("MATCH (n) SET n.stale = true RETURN count(n) AS c")
        return result.single()["c"]  # type: ignore[index]


def merge_nodes(client: Neo4jClient, nodes: list[Node]) -> int:
    """Merge a batch of nodes. Uses one Cypher per label for clarity."""
    if not nodes:
        return 0
    total = 0
    by_label: dict[str, list[Node]] = {}
    for n in nodes:
        by_label.setdefault(n.label, []).append(n)

    with client.session() as session:
        for label, items in by_label.items():
            payload = [
                {"key": n.name, "props": n.cypher_props()} for n in items
            ]
            # For Endpoint, the unique key is (verb, path), not name.
            if label == "Endpoint":
                payload = [
                    {
                        "verb": n.extra["verb"],
                        "path": n.extra["path"],
                        "props": n.cypher_props(),
                    }
                    for n in items
                ]
                session.run(
                    """
                    UNWIND $rows AS row
                    MERGE (e:Endpoint {verb: row.verb, path: row.path})
                    SET e += row.props,
                        e.stale = false,
                        e.lastIngestedAt = datetime()
                    """,
                    rows=payload,
                )
            else:
                session.run(
                    f"""
                    UNWIND $rows AS row
                    MERGE (n:{label} {{name: row.key}})
                    SET n += row.props,
                        n.stale = false,
                        n.lastIngestedAt = datetime()
                    """,
                    rows=payload,
                )
            total += len(items)
    return total


def sweep_stale(client: Neo4jClient) -> int:
    with client.session() as session:
        result = session.run(
            """
            MATCH (n {stale: true})
            WITH count(n) AS c, collect(n) AS nodes
            FOREACH (x IN nodes | DETACH DELETE x)
            RETURN c
            """
        )
        return result.single()["c"]  # type: ignore[index]
