import { z } from "zod";
import { existsSync, statSync } from "node:fs";
import { resolve } from "node:path";

const ConfigSchema = z.object({
  repoPath: z.string().min(1, "MUD_REPO_PATH is required"),
  maxFileBytes: z.number().int().positive().default(512 * 1024),
  maxSearchResults: z.number().int().positive().max(500).default(100),

  // Neo4j (optional — server still runs without it; graph tools degrade)
  neo4j: z
    .object({
      uri: z.string().min(1),
      user: z.string().min(1).default("neo4j"),
      password: z.string().min(1),
      database: z.string().min(1).default("neo4j"),
    })
    .optional(),
});

export type Config = z.infer<typeof ConfigSchema>;

export function loadConfig(): Config {
  const neo4jUri = process.env.NEO4J_URI;
  const neo4jPassword = process.env.NEO4J_PASSWORD;

  const config = ConfigSchema.parse({
    repoPath: process.env.MUD_REPO_PATH,
    maxFileBytes: process.env.MUD_MAX_FILE_BYTES
      ? Number(process.env.MUD_MAX_FILE_BYTES)
      : undefined,
    maxSearchResults: process.env.MUD_MAX_SEARCH_RESULTS
      ? Number(process.env.MUD_MAX_SEARCH_RESULTS)
      : undefined,
    neo4j:
      neo4jUri && neo4jPassword
        ? {
            uri: neo4jUri,
            user: process.env.NEO4J_USER ?? undefined,
            password: neo4jPassword,
            database: process.env.NEO4J_DATABASE ?? undefined,
          }
        : undefined,
  });

  const absPath = resolve(config.repoPath);
  if (!existsSync(absPath) || !statSync(absPath).isDirectory()) {
    throw new Error(`MUD_REPO_PATH does not point to a directory: ${absPath}`);
  }

  return { ...config, repoPath: absPath };
}
