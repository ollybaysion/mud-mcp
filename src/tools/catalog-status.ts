import { z } from "zod";
import { runRead, type Neo4jContext } from "../lib/neo4j.js";

export const catalogStatusSchema = z.object({});
export type CatalogStatusArgs = z.infer<typeof catalogStatusSchema>;

type StatusRow = {
  totalNodes: number;
  byLabel: Array<{ label: string; count: number }>;
  lastIngestAt: string | null;
};

export async function catalogStatus(
  _args: CatalogStatusArgs,
  ctx: { neo4j: Neo4jContext | null },
) {
  if (!ctx.neo4j) {
    return {
      isError: true,
      content: [
        {
          type: "text" as const,
          text: "Neo4j is not configured. Set NEO4J_URI and NEO4J_PASSWORD to enable catalog tools.",
        },
      ],
    };
  }

  const rows = await runRead<StatusRow>(
    ctx.neo4j,
    `
    MATCH (n)
    WITH count(n) AS totalNodes, max(n.lastIngestedAt) AS lastIngestAt
    OPTIONAL MATCH (m)
    WITH totalNodes, lastIngestAt, labels(m) AS lbls
    UNWIND lbls AS label
    RETURN totalNodes, lastIngestAt,
           collect(DISTINCT { label: label, count: 0 }) AS byLabel
    LIMIT 1
    `,
  );

  // Separate per-label count (cleaner than the trick above)
  const labelCounts = await runRead<{ label: string; count: number }>(
    ctx.neo4j,
    `MATCH (n)
     UNWIND labels(n) AS label
     RETURN label, count(*) AS count
     ORDER BY count DESC`,
  );

  const totalNodes = rows[0]?.totalNodes ?? 0;
  const lastIngestAt = rows[0]?.lastIngestAt ?? null;

  const lines = [
    `**Catalog status**`,
    ``,
    `- Total nodes: ${totalNodes}`,
    `- Last ingest: ${lastIngestAt ?? "(never)"}`,
    ``,
    `**Nodes by label**`,
  ];
  if (labelCounts.length === 0) {
    lines.push("(empty — run ingest to populate the catalog)");
  } else {
    for (const r of labelCounts) {
      lines.push(`- ${r.label}: ${r.count}`);
    }
  }

  return {
    content: [{ type: "text" as const, text: lines.join("\n") }],
  };
}
