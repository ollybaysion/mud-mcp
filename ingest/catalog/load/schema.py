"""One-time schema setup: uniqueness constraints and indexes.

Run with `python -m catalog init-schema`. Idempotent (IF NOT EXISTS).
"""

from __future__ import annotations

from catalog.load.client import Neo4jClient

CONSTRAINTS = [
    # Each label's `name` is unique within that label.
    "CREATE CONSTRAINT controller_name IF NOT EXISTS FOR (n:Controller) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT service_name IF NOT EXISTS FOR (n:Service) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT repository_name IF NOT EXISTS FOR (n:Repository) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (n:Entity) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT crawler_name IF NOT EXISTS FOR (n:Crawler) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT migration_name IF NOT EXISTS FOR (n:Migration) REQUIRE n.name IS UNIQUE",
    # Endpoints keyed by verb + path (composite)
    "CREATE CONSTRAINT endpoint_verb_path IF NOT EXISTS FOR (n:Endpoint) REQUIRE (n.verb, n.path) IS UNIQUE",
]

INDEXES = [
    "CREATE INDEX node_tags IF NOT EXISTS FOR (n:Controller) ON (n.tags)",
    "CREATE INDEX service_tags IF NOT EXISTS FOR (n:Service) ON (n.tags)",
]


def init_schema(client: Neo4jClient) -> list[str]:
    """Apply constraints/indexes. Returns the statements that ran."""
    applied: list[str] = []
    with client.session() as session:
        for stmt in CONSTRAINTS + INDEXES:
            session.run(stmt)
            applied.append(stmt)
    return applied
