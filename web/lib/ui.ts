export function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "2-digit" });
}

export function memberLabel(m?: { username?: string; display_name?: string; telegram_id?: number }): string {
  if (!m) return "Unknown";
  if (m.username?.trim()) return `@${m.username.trim()}`;
  if (m.display_name?.trim()) return m.display_name.trim();
  if (m.telegram_id !== undefined) return `ID ${m.telegram_id}`;
  return "Unknown";
}

export function memberHref(m?: { username?: string; telegram_id?: number }): string {
  if (!m) return "/reviews";
  // Canonicalize to Telegram numeric ID when available (stable across username changes).
  const handle = String(m.telegram_id ?? "").trim() || m.username?.trim() || "";
  return handle ? `/user/${encodeURIComponent(handle)}` : "/reviews";
}

export function stars(rating: number): { on: string; off: string } {
  const r = Math.max(0, Math.min(5, Math.round(rating)));
  return { on: "★★★★★".slice(0, r), off: "★★★★★".slice(r) };
}
