# mud-mcp

MCP server exposing the [mud](../mud) codebase (Spring Boot backend + Next.js frontend) to MCP-compatible clients (Claude Code, opencode, Cursor, etc).

## What it provides

### Tools
- `search_code(query, type?, max_results?)` — ripgrep search across the repo
- `read_file(path, start_line?, end_line?)` — read repo files safely (size/path guarded)
- `list_controllers()` — Spring controllers + HTTP route mappings
- `list_crawlers(include_source_urls?)` — every crawler in `mud-backend`
- `list_entities()` — JPA entities + table names + field names
- `catalog_status()` — Neo4j catalog summary (node counts per label, last ingest)

### Resources
- `mud://readme` — top-level README
- `mud://claude-md` — repo conventions
- `mud://backend-claude-md`, `mud://frontend-claude-md`
- `mud://application-yml` — Spring config

## Local development

```bash
# install
npm install

# build
npm run build

# inspect interactively (MCP Inspector)
MUD_REPO_PATH=/absolute/path/to/mud npm run inspect

# or just run the server (stdio; pipe a client to it)
MUD_REPO_PATH=/absolute/path/to/mud npm start
```

## Install in a client

### Claude Code (`~/.claude.json`)

```json
{
  "mcpServers": {
    "mud": {
      "command": "npx",
      "args": ["-y", "mud-mcp@latest"],
      "env": { "MUD_REPO_PATH": "/absolute/path/to/mud" }
    }
  }
}
```

### opencode (`~/.config/opencode/opencode.json`)

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "mud": {
      "type": "local",
      "command": ["npx", "-y", "mud-mcp@latest"],
      "environment": { "MUD_REPO_PATH": "/absolute/path/to/mud" },
      "enabled": true
    }
  }
}
```

### Local checkout (before publishing)

```bash
npm run build
npm link
```

Then in the client, use `"command": "mud-mcp"` (no `npx`).

## Environment variables

| Var | Default | Description |
| --- | --- | --- |
| `MUD_REPO_PATH` | (required) | Absolute path to the mud repo |
| `MUD_MAX_FILE_BYTES` | `524288` | `read_file` size cap |
| `MUD_MAX_SEARCH_RESULTS` | `100` | `search_code` default match cap |
| `NEO4J_URI` | (optional) | e.g. `bolt://localhost:7687`. If unset, graph tools degrade. |
| `NEO4J_USER` | `neo4j` | Neo4j user |
| `NEO4J_PASSWORD` | (required if `NEO4J_URI` set) | Neo4j password |
| `NEO4J_DATABASE` | `neo4j` | Database name |

## Running Neo4j locally (docker-compose snippet)

Add to your `docker-compose.yml`:

```yaml
services:
  neo4j:
    image: neo4j:5.24-community
    container_name: mud-neo4j
    ports:
      - "7474:7474"   # browser UI
      - "7687:7687"   # bolt protocol
    environment:
      - NEO4J_AUTH=neo4j/local-dev-password
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_memory_heap_max__size=1G
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs

volumes:
  neo4j_data:
  neo4j_logs:
```

Then:

```bash
docker compose up -d neo4j
# UI: http://localhost:7474  (login: neo4j / local-dev-password)

MUD_REPO_PATH=/absolute/path/to/mud \
NEO4J_URI=bolt://localhost:7687 \
NEO4J_PASSWORD=local-dev-password \
npm run inspect
```

Call `catalog_status` in MCP Inspector to verify the connection. Until ingest is run, the graph is empty.

## Security notes

- All paths are resolved against `MUD_REPO_PATH` and rejected if they escape it.
- `.git`, `node_modules`, `build`, `.next`, `.gradle`, `.env*` are blocked from `read_file`.
- The server is read-only — no write tools are exposed.

## Ingest (Python) — catalog graph

The MCP server's graph tools (e.g. `catalog_status`, future `find_code` / `related`) are backed by a Neo4j catalog populated by a separate Python pipeline under [`ingest/`](./ingest/README.md).

```bash
cd ingest
uv pip install -e .
python -m catalog init-schema    # one-time
python -m catalog ingest         # extract → transform → load
python -m catalog status
```

See [`ingest/README.md`](./ingest/README.md) for full details. The MCP server stays read-only against the graph; ingest is the only writer.

## Publishing

```bash
npm version patch
npm publish --access public
```

`prepublishOnly` runs the build automatically. The published tarball contains only `dist/` and `README.md` (see `files` in `package.json`).
