import { resolve, relative, isAbsolute, sep } from "node:path";

const BLOCKED_PATTERNS = [
  /(^|[\\/])\.git([\\/]|$)/,
  /(^|[\\/])node_modules([\\/]|$)/,
  /(^|[\\/])\.next([\\/]|$)/,
  /(^|[\\/])build([\\/]|$)/,
  /(^|[\\/])\.gradle([\\/]|$)/,
  /(^|[\\/])\.env(\.|$)/,
];

export function safeJoin(root: string, userPath: string): string {
  const absRoot = resolve(root);
  const target = isAbsolute(userPath) ? resolve(userPath) : resolve(absRoot, userPath);
  const rel = relative(absRoot, target);

  if (rel === "" || rel.startsWith("..") || isAbsolute(rel)) {
    throw new Error(`path escapes repo root: ${userPath}`);
  }

  const normalized = rel.split(sep).join("/");
  for (const pat of BLOCKED_PATTERNS) {
    if (pat.test(normalized)) {
      throw new Error(`blocked path: ${normalized}`);
    }
  }

  return target;
}
