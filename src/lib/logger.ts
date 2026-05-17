// stdout is reserved for MCP protocol. All logs go to stderr.
function ts(): string {
  return new Date().toISOString();
}

export const log = {
  info: (...args: unknown[]) => console.error(`[${ts()}] [info]`, ...args),
  warn: (...args: unknown[]) => console.error(`[${ts()}] [warn]`, ...args),
  error: (...args: unknown[]) => console.error(`[${ts()}] [error]`, ...args),
};
