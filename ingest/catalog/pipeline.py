"""End-to-end ingest pipeline: Extract → Transform → Load."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from catalog.config import Settings
from catalog.extract import (
    controllers,
    crawlers,
    entities,
    migrations,
    repositories,
    services,
)
from catalog.load.client import Neo4jClient
from catalog.load.edges import merge_edges
from catalog.load.nodes import mark_all_stale, merge_nodes, sweep_stale
from catalog.models import CatalogData
from catalog.transform.overlay import apply_overlay, load_overlay
from catalog.transform.resolve import resolve_edges

console = Console(stderr=True)


@dataclass
class IngestReport:
    nodes_by_label: dict[str, int] = field(default_factory=dict)
    edges_by_type: dict[str, int] = field(default_factory=dict)
    overlay_nodes_touched: int = 0
    overlay_edges_added: int = 0
    edges_dropped: int = 0
    nodes_merged: int = 0
    edges_merged: int = 0
    edges_skipped: int = 0
    stale_deleted: int = 0


_EXTRACTORS = {
    "controllers": ("api/controller", controllers.extract),
    "services": ("service", services.extract),
    "repositories": ("domain/repository", repositories.extract),
    "entities": ("domain/entity", entities.extract),
    "crawlers": ("crawler", crawlers.extract),
}


def run_ingest(
    settings: Settings,
    only: list[str] | None = None,
    dry_run: bool = False,
) -> IngestReport:
    report = IngestReport()
    catalog = CatalogData()

    # --- 1. Extract ---
    selected = set(only) if only else set(_EXTRACTORS.keys()) | {"migrations"}

    for key, (subdir, fn) in _EXTRACTORS.items():
        if key not in selected:
            continue
        path = settings.backend_src / subdir
        nodes, edges = fn(settings.mud_repo_path, path)
        catalog.nodes.extend(nodes)
        catalog.edges.extend(edges)
        console.log(f"extract[{key}]: {len(nodes)} nodes, {len(edges)} edges")

    if "migrations" in selected:
        mnodes, medges = migrations.extract(
            settings.mud_repo_path, settings.migration_dir
        )
        catalog.nodes.extend(mnodes)
        catalog.edges.extend(medges)
        console.log(f"extract[migrations]: {len(mnodes)} nodes")

    for n in catalog.nodes:
        report.nodes_by_label[n.label] = report.nodes_by_label.get(n.label, 0) + 1
    for e in catalog.edges:
        report.edges_by_type[e.type] = report.edges_by_type.get(e.type, 0) + 1

    # --- 2. Transform ---
    overlay = load_overlay(settings.overlay_path)
    touched, added = apply_overlay(catalog, overlay)
    report.overlay_nodes_touched = touched
    report.overlay_edges_added = added
    console.log(f"overlay: touched {touched} nodes, added {added} edges")

    dropped = resolve_edges(catalog)
    report.edges_dropped = len(dropped)
    if dropped:
        for d in dropped[:5]:
            console.log(f"  dropped edge: {d.from_id} -[{d.type}]-> {d.to_id}", style="yellow")
        if len(dropped) > 5:
            console.log(f"  ... and {len(dropped) - 5} more dropped", style="yellow")

    # --- 3. Load ---
    if dry_run:
        console.log("dry-run: skipping Neo4j load", style="cyan")
        return report

    with Neo4jClient(settings) as client:
        mark_all_stale(client)
        report.nodes_merged = merge_nodes(client, catalog.nodes)
        merged, skipped = merge_edges(client, catalog.edges, catalog)
        report.edges_merged = merged
        report.edges_skipped = skipped
        report.stale_deleted = sweep_stale(client)

    return report


def fetch_status(settings: Settings) -> dict:
    with Neo4jClient(settings) as client:
        with client.session() as session:
            total = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
            rels = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
            by_label = {
                r["label"]: r["count"]
                for r in session.run(
                    """MATCH (n) UNWIND labels(n) AS label
                       RETURN label, count(*) AS count ORDER BY count DESC"""
                ).data()
            }
            last_ingest = session.run(
                "MATCH (n) RETURN max(n.lastIngestedAt) AS last"
            ).single()["last"]
    return {
        "total_nodes": total,
        "total_edges": rels,
        "by_label": by_label,
        "last_ingest": str(last_ingest) if last_ingest else None,
    }
