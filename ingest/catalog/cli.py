"""Typer CLI for the mud-catalog ingest pipeline."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from catalog.config import load_settings
from catalog.load.client import Neo4jClient
from catalog.load.schema import init_schema as do_init_schema
from catalog.pipeline import fetch_status, run_ingest

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()


@app.command("init-schema")
def init_schema_cmd() -> None:
    """Apply uniqueness constraints and indexes (idempotent)."""
    settings = load_settings()
    with Neo4jClient(settings) as client:
        applied = do_init_schema(client)
    console.print(f"[green]Applied {len(applied)} schema statements[/green]")


@app.command()
def ingest(
    dry_run: bool = typer.Option(False, "--dry-run", help="Skip Neo4j writes"),
    only: str = typer.Option(
        "",
        "--only",
        help="Comma-separated list of extractors: controllers,services,repositories,entities,crawlers,migrations",
    ),
) -> None:
    """Run a full ingest pass."""
    settings = load_settings()
    only_list = [s.strip() for s in only.split(",") if s.strip()] or None

    report = run_ingest(settings, only=only_list, dry_run=dry_run)

    table = Table(title="Ingest report", show_header=True)
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Nodes extracted", str(sum(report.nodes_by_label.values())))
    table.add_row("Edges extracted", str(sum(report.edges_by_type.values())))
    table.add_row("Overlay nodes touched", str(report.overlay_nodes_touched))
    table.add_row("Overlay edges added", str(report.overlay_edges_added))
    table.add_row("Edges dropped (unresolved)", str(report.edges_dropped))
    if not dry_run:
        table.add_row("Nodes merged", str(report.nodes_merged))
        table.add_row("Edges merged", str(report.edges_merged))
        table.add_row("Edges skipped at load", str(report.edges_skipped))
        table.add_row("Stale nodes deleted", str(report.stale_deleted))
    console.print(table)

    label_table = Table(title="Nodes by label")
    label_table.add_column("Label")
    label_table.add_column("Count", justify="right")
    for label, c in sorted(report.nodes_by_label.items(), key=lambda x: -x[1]):
        label_table.add_row(label, str(c))
    console.print(label_table)


@app.command()
def status() -> None:
    """Print current Neo4j catalog status."""
    settings = load_settings()
    s = fetch_status(settings)
    console.print(f"Total nodes: [bold]{s['total_nodes']}[/bold]")
    console.print(f"Total edges: [bold]{s['total_edges']}[/bold]")
    console.print(f"Last ingest: {s['last_ingest'] or '(never)'}")
    if s["by_label"]:
        t = Table("Label", "Count")
        for label, c in s["by_label"].items():
            t.add_row(label, str(c))
        console.print(t)


@app.command()
def wipe(
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation"),
) -> None:
    """Delete all nodes and relationships. Destructive."""
    if not yes:
        confirm = typer.confirm("This will delete the entire catalog. Continue?")
        if not confirm:
            raise typer.Exit(1)
    settings = load_settings()
    with Neo4jClient(settings) as client:
        with client.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
    console.print("[red]catalog wiped[/red]")


if __name__ == "__main__":
    app()
