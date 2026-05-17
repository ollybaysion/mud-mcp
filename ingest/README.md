# mud-catalog (ingest)

Python pipeline that scans the mud codebase and writes a Neo4j catalog graph that backs `mud-mcp`'s graph-based tools.

```
[mud Java/SQL] → extract (javalang) → transform (overlay.yml) → load (Cypher MERGE) → [Neo4j]
```

The MCP server is read-only against this graph; ingest is the only writer.

## Setup

```bash
cd ingest
uv venv && source .venv/bin/activate    # or python -m venv .venv
uv pip install -e .                     # installs `mud-catalog` script + deps
```

Required env (set in shell or `.env`):

```bash
export MUD_REPO_PATH=/absolute/path/to/mud
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=local-dev-password
export NEO4J_DATABASE=neo4j   # optional, defaults to "neo4j"
```

## Commands

```bash
# 1. One-time: create UNIQUE constraints + indexes
python -m catalog init-schema

# 2. Full ingest (extract → transform → load)
python -m catalog ingest

# Dry run (no Neo4j writes)
python -m catalog ingest --dry-run

# Run only specific extractors
python -m catalog ingest --only controllers,services,entities

# Check the graph
python -m catalog status

# Wipe everything (destructive)
python -m catalog wipe --yes
```

## What gets extracted

| Label | Source | Identifier |
|---|---|---|
| `Controller` | `@RestController` / `@Controller` | name |
| `Endpoint` | `@GetMapping` / `@PostMapping` / ... | (verb, path) |
| `Service` | `@Service` / `@Component` | name |
| `Repository` | filename `*Repository.java` + `extends JpaRepository<X,Y>` | name |
| `Entity` | `@Entity` | name |
| `Crawler` | `extends CrawlerBase` | name |
| `Migration` | `Vxx__name.sql` | `V<n>_<title>` |

## Relationships

- `(Controller)-[:EXPOSES]->(Endpoint)`
- `(Controller)-[:DEPENDS_ON]->(Service|Repository)` — from constructor injection
- `(Service)-[:DEPENDS_ON]->(Service|Repository)`
- `(Repository)-[:QUERIES]->(Entity)` — from generic parameter

Additional relationships that code cannot infer (e.g. scheduled jobs → services) live in `overlay.yml` under `extra_edges`.

## Idempotency & stale handling

Each ingest:

1. **Marks every node `stale = true`** before extraction
2. **MERGE** queries write nodes/edges, setting `stale = false` and `lastIngestedAt = datetime()`
3. **Sweeps** anything still `stale = true` at the end (`DETACH DELETE`)

So:
- Re-running ingest is safe — same input produces the same graph.
- Deleted code is removed from the graph at the next ingest.

## overlay.yml

Curated metadata that supplements auto-extraction. Edit this when you want to:
- Add an LLM-facing `summary` for a node
- Tag nodes for filtering (`tags: [core, search]`)
- Mark importance (`critical`/`high`/...)
- Add `extra_edges` that the AST extractor can't see

Overlay metadata survives code refactors — only `summary`/`tags` here are authoritative for the catalog metadata layer.

## Synchronization strategy

| Stage | How catalog stays fresh |
|---|---|
| Local dev | Manual `python -m catalog ingest` |
| Server hosting | CI job on PR merge + daily cron full rebuild as safety net |

`lastIngestedAt` is per-node, so `mud-mcp`'s `catalog_status` tool can warn when the graph is stale.

## Project layout

```
ingest/
├── pyproject.toml
├── overlay.yml                 # curated metadata
└── catalog/
    ├── __main__.py / cli.py    # typer CLI
    ├── config.py               # env via pydantic-settings
    ├── models.py               # Node / Edge / CatalogData
    ├── pipeline.py             # extract → transform → load orchestrator
    ├── extract/                # javalang-based AST extraction
    │   ├── base.py
    │   ├── controllers.py      # + endpoints
    │   ├── services.py
    │   ├── repositories.py
    │   ├── entities.py
    │   ├── crawlers.py
    │   └── migrations.py
    ├── transform/
    │   ├── overlay.py          # YAML merge
    │   └── resolve.py          # drop dangling edges
    └── load/
        ├── client.py           # neo4j-driver wrapper
        ├── schema.py           # CREATE CONSTRAINT / INDEX
        ├── nodes.py            # MERGE nodes + stale marking/sweep
        └── edges.py            # MERGE relationships
```
