import { z } from "zod";
import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import type { Config } from "../config.js";

export const listCrawlersSchema = z.object({
  include_source_urls: z
    .boolean()
    .optional()
    .describe("If true, scan each crawler for a sourceUrl/baseUrl/feedUrl field"),
});
export type ListCrawlersArgs = z.infer<typeof listCrawlersSchema>;

const URL_RE = /(?:sourceUrl|baseUrl|feedUrl|rssUrl|URL)\s*=\s*"([^"]+)"/;

export async function listCrawlers(args: ListCrawlersArgs, config: Config) {
  const crawlersDir = join(
    config.repoPath,
    "mud-backend",
    "src",
    "main",
    "java",
    "com",
    "mud",
    "crawler",
  );

  let files: string[];
  try {
    files = (await readdir(crawlersDir))
      .filter((f) => f.endsWith("Crawler.java") && f !== "CrawlerBase.java")
      .sort();
  } catch {
    throw new Error(`crawlers dir not found: ${crawlersDir}`);
  }

  const lines: string[] = [`Found ${files.length} crawlers:`];
  for (const f of files) {
    const name = f.replace(/\.java$/, "");
    if (args.include_source_urls) {
      const text = await readFile(join(crawlersDir, f), "utf8");
      const url = text.match(URL_RE)?.[1];
      lines.push(`- ${name}${url ? `  →  ${url}` : ""}`);
    } else {
      lines.push(`- ${name}`);
    }
  }

  return { content: [{ type: "text" as const, text: lines.join("\n") }] };
}
