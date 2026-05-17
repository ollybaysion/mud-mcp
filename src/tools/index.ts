import type { Server } from "@modelcontextprotocol/sdk/server/index.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { zodToJsonSchema } from "zod-to-json-schema";
import type { ZodTypeAny } from "zod";

import type { Config } from "../config.js";
import type { Neo4jContext } from "../lib/neo4j.js";
import { log } from "../lib/logger.js";

import { searchCode, searchCodeSchema } from "./search-code.js";
import { readFileTool, readFileSchema } from "./read-file.js";
import { listControllers, listControllersSchema } from "./list-controllers.js";
import { listCrawlers, listCrawlersSchema } from "./list-crawlers.js";
import { listEntities, listEntitiesSchema } from "./list-entities.js";
import { catalogStatus, catalogStatusSchema } from "./catalog-status.js";

export type ToolContext = {
  config: Config;
  neo4j: Neo4jContext | null;
};

type ToolDef = {
  name: string;
  description: string;
  schema: ZodTypeAny;
  handler: (
    args: any,
    ctx: ToolContext,
  ) => Promise<{
    content: { type: "text"; text: string }[];
    isError?: boolean;
  }>;
};

// Adapter: existing tools that only take Config get config extracted from ctx
const fsTool =
  <A>(
    fn: (args: A, config: Config) => Promise<{ content: { type: "text"; text: string }[] }>,
  ) =>
  (args: A, ctx: ToolContext) =>
    fn(args, ctx.config);

const graphTool =
  <A>(
    fn: (
      args: A,
      ctx: { neo4j: Neo4jContext | null },
    ) => Promise<{ content: { type: "text"; text: string }[]; isError?: boolean }>,
  ) =>
  (args: A, ctx: ToolContext) =>
    fn(args, { neo4j: ctx.neo4j });

export function registerTools(server: Server, ctx: ToolContext) {
  const tools: ToolDef[] = [
    {
      name: "search_code",
      description:
        "Search the mud codebase with ripgrep. Excludes build/.git/node_modules. Use 'type' to restrict to a language (java, ts, sql, etc).",
      schema: searchCodeSchema,
      handler: fsTool(searchCode),
    },
    {
      name: "read_file",
      description:
        "Read a file from the mud repo by repo-relative path. Returns line-numbered content; supports start_line/end_line for slicing.",
      schema: readFileSchema,
      handler: fsTool(readFileTool),
    },
    {
      name: "list_controllers",
      description:
        "List all Spring Boot controllers in mud-backend and their HTTP route mappings (verb + path).",
      schema: listControllersSchema,
      handler: fsTool(listControllers),
    },
    {
      name: "list_crawlers",
      description:
        "List all crawler classes in mud-backend. Optionally include the source URL each crawler targets.",
      schema: listCrawlersSchema,
      handler: fsTool(listCrawlers),
    },
    {
      name: "list_entities",
      description:
        "List JPA entities in mud-backend with their table names and field names.",
      schema: listEntitiesSchema,
      handler: fsTool(listEntities),
    },
    {
      name: "catalog_status",
      description:
        "Report Neo4j catalog status: total nodes, node counts per label, last ingest timestamp. Use this to check whether the graph catalog is populated and fresh.",
      schema: catalogStatusSchema,
      handler: graphTool(catalogStatus),
    },
  ];

  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: tools.map((t) => ({
      name: t.name,
      description: t.description,
      inputSchema: zodToJsonSchema(t.schema, { target: "openApi3" }) as Record<string, unknown>,
    })),
  }));

  server.setRequestHandler(CallToolRequestSchema, async (req) => {
    const tool = tools.find((t) => t.name === req.params.name);
    if (!tool) throw new Error(`unknown tool: ${req.params.name}`);

    let parsed: unknown;
    try {
      parsed = tool.schema.parse(req.params.arguments ?? {});
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      throw new Error(`invalid arguments for ${tool.name}: ${msg}`);
    }

    log.info(`tool: ${tool.name}`);
    try {
      return await tool.handler(parsed, ctx);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      return {
        isError: true,
        content: [{ type: "text" as const, text: `Error: ${msg}` }],
      };
    }
  });
}
