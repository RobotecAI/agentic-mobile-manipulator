/**
 * Parse the agent's stringified list format, e.g. `["step one" | "step two"]`.
 * Mirrors the native HMI's parser (items are separated by `|`).
 */
export function parseRosList(raw?: string): string[] {
  if (!raw) return [];
  let s = raw.trim();
  if (s.startsWith("[") && s.endsWith("]")) s = s.slice(1, -1);
  if (!s.trim()) return [];
  return s
    .split("|")
    .map((item) => {
      let t = item.trim();
      if ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith("'") && t.endsWith("'"))) {
        t = t.slice(1, -1);
      }
      return t;
    })
    .filter(Boolean);
}
