import { z } from "zod";
import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import type { Config } from "../config.js";

export const listEntitiesSchema = z.object({});
export type ListEntitiesArgs = z.infer<typeof listEntitiesSchema>;

const TABLE_RE = /@Table\s*\(\s*name\s*=\s*"([^"]+)"/;
const COLUMN_RE = /private\s+[\w<>?,\s]+\s+(\w+)\s*;/g;

export async function listEntities(_args: ListEntitiesArgs, config: Config) {
  const entityDir = join(
    config.repoPath,
    "mud-backend",
    "src",
    "main",
    "java",
    "com",
    "mud",
    "domain",
    "entity",
  );

  let files: string[];
  try {
    files = (await readdir(entityDir)).filter((f) => f.endsWith(".java"));
  } catch {
    throw new Error(`entity dir not found: ${entityDir}`);
  }

  const out: string[] = [];
  for (const f of files) {
    const text = await readFile(join(entityDir, f), "utf8");
    const table = text.match(TABLE_RE)?.[1];
    const fields = Array.from(text.matchAll(COLUMN_RE))
      .map((m) => m[1])
      .slice(0, 20);

    out.push(
      `### ${f.replace(/\.java$/, "")}${table ? ` (table: ${table})` : ""}\n` +
        fields.map((c) => `- ${c}`).join("\n"),
    );
  }

  return {
    content: [
      { type: "text" as const, text: out.join("\n\n") || "(no entities found)" },
    ],
  };
}
