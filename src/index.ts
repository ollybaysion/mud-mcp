#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { loadConfig } from "./config.js";
import { log } from "./lib/logger.js";
import { connectNeo4j, closeNeo4j, type Neo4jContext } from "./lib/neo4j.js";
import { registerTools } from "./tools/index.js";
import { registerResources } from "./resources/index.js";

async function main() {
  const config = loadConfig();
  log.info(`repo: ${config.repoPath}`);

  const neo4jCtx: Neo4jContext | null = await connectNeo4j(config);

  const server = new Server(
    { name: "mud-mcp", version: "0.1.0" },
    {
      capabilities: {
        tools: {},
        resources: {},
      },
    },
  );

  registerTools(server, { config, neo4j: neo4jCtx });
  registerResources(server, config);

  const shutdown = async (signal: string) => {
    log.info(`${signal} received, shutting down`);
    await closeNeo4j(neo4jCtx);
    process.exit(0);
  };
  process.on("SIGINT", () => void shutdown("SIGINT"));
  process.on("SIGTERM", () => void shutdown("SIGTERM"));

  const transport = new StdioServerTransport();
  await server.connect(transport);
  log.info("mud-mcp ready (stdio)");
}

main().catch((err) => {
  log.error("fatal:", err instanceof Error ? err.message : err);
  process.exit(1);
});
