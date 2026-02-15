type MemberView = {
  username?: string | null;
  display_name?: string | null;
  telegram_id?: number | string | null;
};

export function memberLabel(member?: MemberView | null): string {
  if (!member) return "Unknown member";
  const name = member.display_name?.trim();
  const username = member.username?.trim().replace(/^@/, "");
  if (name) return name;
  if (username) return `@${username}`;
  if (member.telegram_id !== null && member.telegram_id !== undefined) return `ID ${member.telegram_id}`;
  return "Unknown member";
}

export function memberHref(member?: MemberView | null): string {
  if (!member) return "/reviews";
  if (member.telegram_id !== null && member.telegram_id !== undefined) {
    return `/user/${encodeURIComponent(String(member.telegram_id))}`;
  }
  const username = member.username?.trim().replace(/^@/, "");
  if (username) return `/user/${encodeURIComponent(username)}`;
  return "/reviews";
}

export function stars(value: number): { on: string; off: string } {
  const rating = Math.max(0, Math.min(5, Math.round(Number(value) || 0)));
  return {
    on: "★".repeat(rating),
    off: "☆".repeat(5 - rating)
  };
}

export function formatDate(v: string): string {
  if (!v) return "";
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return v;
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric"
  });
}
