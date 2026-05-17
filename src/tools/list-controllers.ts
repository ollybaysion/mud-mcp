import { z } from "zod";
import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import type { Config } from "../config.js";

export const listControllersSchema = z.object({});
export type ListControllersArgs = z.infer<typeof listControllersSchema>;

const MAPPING_RE =
  /@(Get|Post|Put|Patch|Delete|Request)Mapping\s*(?:\(\s*(?:value\s*=\s*)?["']([^"']+)["'])?/g;
const CLASS_MAPPING_RE =
  /@RequestMapping\s*\(\s*(?:value\s*=\s*)?["']([^"']+)["']/;

export async function listControllers(_args: ListControllersArgs, config: Config) {
  const controllersDir = join(
    config.repoPath,
    "mud-backend",
    "src",
    "main",
    "java",
    "com",
    "mud",
    "api",
    "controller",
  );

  let files: string[];
  try {
    files = (await readdir(controllersDir)).filter((f) => f.endsWith(".java"));
  } catch {
    throw new Error(`controllers dir not found: ${controllersDir}`);
  }

  const out: string[] = [];
  for (const f of files) {
    const text = await readFile(join(controllersDir, f), "utf8");
    const classMapping = text.match(CLASS_MAPPING_RE)?.[1] ?? "";
    const lines: string[] = [`### ${f}`];
    if (classMapping) lines.push(`Base: ${classMapping}`);

    const seen = new Set<string>();
    for (const m of text.matchAll(MAPPING_RE)) {
      const verb = m[1].toUpperCase();
      const path = m[2] ?? "";
      const full = classMapping + path;
      const key = `${verb} ${full}`;
      if (!seen.has(key)) {
        seen.add(key);
        lines.push(`- ${verb} ${full || "(class-level)"}`);
      }
    }
    out.push(lines.join("\n"));
  }

  return {
    content: [
      { type: "text" as const, text: out.join("\n\n") || "(no controllers found)" },
    ],
  };
}
