import { z } from "zod";
import { readFile, stat } from "node:fs/promises";
import { relative } from "node:path";
import { safeJoin } from "../lib/safe-path.js";
import type { Config } from "../config.js";

export const readFileSchema = z.object({
  path: z
    .string()
    .min(1)
    .describe("Path relative to the mud repo root (e.g. 'mud-backend/src/main/java/com/mud/MudApplication.java')"),
  start_line: z.number().int().min(1).optional(),
  end_line: z.number().int().min(1).optional(),
});

export type ReadFileArgs = z.infer<typeof readFileSchema>;

export async function readFileTool(args: ReadFileArgs, config: Config) {
  const abs = safeJoin(config.repoPath, args.path);
  const info = await stat(abs);
  if (!info.isFile()) throw new Error(`not a file: ${args.path}`);
  if (info.size > config.maxFileBytes) {
    throw new Error(
      `file too large (${info.size} bytes, limit ${config.maxFileBytes}). Use start_line/end_line.`,
    );
  }

  const text = await readFile(abs, "utf8");
  const lines = text.split("\n");
  const start = Math.max(1, args.start_line ?? 1);
  const end = Math.min(lines.length, args.end_line ?? lines.length);
  const slice = lines.slice(start - 1, end);
  const numbered = slice.map((l, i) => `${start + i}\t${l}`).join("\n");

  const rel = relative(config.repoPath, abs);
  return {
    content: [
      {
        type: "text" as const,
        text: `// ${rel} (lines ${start}-${end} of ${lines.length})\n${numbered}`,
      },
    ],
  };
}
