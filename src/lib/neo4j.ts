import neo4j, { type Driver, type Session } from "neo4j-driver";
import type { Config } from "../config.js";
import { log } from "./logger.js";

export type Neo4jContext = {
  driver: Driver;
  database: string;
  session: () => Session;
};

/**
 * Try to connect to Neo4j. Returns null if not configured or unreachable —
 * the server still runs (graph-backed tools degrade gracefully).
 */
export async function connectNeo4j(
  config: Config,
): Promise<Neo4jContext | null> {
  if (!config.neo4j) {
    log.info("neo4j: not configured (NEO4J_URI/NEO4J_PASSWORD unset) — skipping");
    return null;
  }

  const { uri, user, password, database } = config.neo4j;
  const driver = neo4j.driver(uri, neo4j.auth.basic(user, password), {
    connectionTimeout: 5000,
    maxConnectionPoolSize: 10,
    disableLosslessIntegers: true,
  });

  try {
    await driver.verifyConnectivity({ database });
    log.info(`neo4j: connected to ${uri} (database=${database})`);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    log.warn(`neo4j: connect failed (${msg}) — graph tools will return errors`);
    await driver.close().catch(() => {});
    return null;
  }

  return {
    driver,
    database,
    session: () => driver.session({ database, defaultAccessMode: neo4j.session.READ }),
  };
}

export async function closeNeo4j(ctx: Neo4jContext | null): Promise<void> {
  if (!ctx) return;
  try {
    await ctx.driver.close();
    log.info("neo4j: closed");
  } catch (e) {
    log.warn("neo4j: close failed", e instanceof Error ? e.message : e);
  }
}

/**
 * Helper: run a read query and return records as plain objects.
 */
export async function runRead<T = Record<string, unknown>>(
  ctx: Neo4jContext,
  cypher: string,
  params: Record<string, unknown> = {},
): Promise<T[]> {
  const session = ctx.session();
  try {
    const result = await session.run(cypher, params);
    return result.records.map((r) => r.toObject() as T);
  } finally {
    await session.close();
  }
}
