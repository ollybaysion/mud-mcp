import type { Server } from "@modelcontextprotocol/sdk/server/index.js";
import {
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import type { Config } from "../config.js";

type ResourceMap = Record<
  string,
  { name: string; description: string; path: string; mimeType: string }
>;

export function registerResources(server: Server, config: Config) {
  const resources: ResourceMap = {
    "mud://readme": {
      name: "README",
      description: "Top-level README of the mud monorepo",
      path: join(config.repoPath, "README.md"),
      mimeType: "text/markdown",
    },
    "mud://claude-md": {
      name: "CLAUDE.md",
      description: "Conventions and architecture notes for AI assistants",
      path: join(config.repoPath, "CLAUDE.md"),
      mimeType: "text/markdown",
    },
    "mud://backend-claude-md": {
      name: "Backend CLAUDE.md",
      description: "Backend-specific conventions",
      path: join(config.repoPath, "mud-backend", "CLAUDE.md"),
      mimeType: "text/markdown",
    },
    "mud://frontend-claude-md": {
      name: "Frontend CLAUDE.md",
      description: "Frontend-specific conventions",
      path: join(config.repoPath, "mud-frontend", "CLAUDE.md"),
      mimeType: "text/markdown",
    },
    "mud://application-yml": {
      name: "application.yml",
      description: "Spring Boot application config",
      path: join(
        config.repoPath,
        "mud-backend",
        "src",
        "main",
        "resources",
        "application.yml",
      ),
      mimeType: "text/yaml",
    },
  };

  server.setRequestHandler(ListResourcesRequestSchema, async () => ({
    resources: Object.entries(resources).map(([uri, r]) => ({
      uri,
      name: r.name,
      description: r.description,
      mimeType: r.mimeType,
    })),
  }));

  server.setRequestHandler(ReadResourceRequestSchema, async (req) => {
    const r = resources[req.params.uri];
    if (!r) throw new Error(`unknown resource: ${req.params.uri}`);
    const text = await readFile(r.path, "utf8");
    return {
      contents: [
        {
          uri: req.params.uri,
          mimeType: r.mimeType,
          text,
        },
      ],
    };
  });
}
