import { z } from "zod";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import type { Config } from "../config.js";

const execFileP = promisify(execFile);

export const searchCodeSchema = z.object({
  query: z.string().min(1).describe("Search pattern (literal text or regex)"),
  type: z
    .enum(["java", "ts", "tsx", "js", "md", "yml", "sql"])
    .optional()
    .describe("Restrict to a file type (ripgrep -t)"),
  max_results: z
    .number()
    .int()
    .min(1)
    .max(500)
    .optional()
    .describe("Maximum number of matches to return"),
});

export type SearchCodeArgs = z.infer<typeof searchCodeSchema>;

export async function searchCode(args: SearchCodeArgs, config: Config) {
  const max = args.max_results ?? config.maxSearchResults;
  const rgArgs = [
    "-n",
    "--max-count",
    String(max),
    "--hidden",
    "-g",
    "!.git",
    "-g",
    "!node_modules",
    "-g",
    "!build",
    "-g",
    "!.next",
    "-g",
    "!.gradle",
  ];
  if (args.type) rgArgs.push("-t", args.type);
  rgArgs.push("--", args.query, config.repoPath);

  try {
    const { stdout } = await execFileP("rg", rgArgs, {
      maxBuffer: 8 * 1024 * 1024,
    });
    const text = stdout.trim() || "(no matches)";
    return { content: [{ type: "text" as const, text }] };
  } catch (e: unknown) {
    const err = e as { code?: number; message?: string };
    if (err.code === 1) {
      return { content: [{ type: "text" as const, text: "(no matches)" }] };
    }
    throw new Error(`ripgrep failed: ${err.message ?? String(e)}`);
  }
}
