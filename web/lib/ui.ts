type MemberLike = {
  username?: string;
  display_name?: string;
  telegram_id?: number;
};

export function formatDate(value?: string): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

export function memberLabel(member?: MemberLike): string {
  if (!member) return "Unknown user";
  if (member.display_name?.trim()) return member.display_name.trim();
  if (member.username?.trim()) return `@${member.username.trim()}`;
  if (member.telegram_id) return `ID ${member.telegram_id}`;
  return "Unknown user";
}

export function memberHref(member?: MemberLike): string {
  if (!member) return "/reviews";
  if (member.telegram_id) return `/user/${encodeURIComponent(String(member.telegram_id))}`;
  if (member.username?.trim()) return `/user/${encodeURIComponent(member.username.trim())}`;
  return "/reviews";
}

export function stars(rating: number): { on: string; off: string } {
  const safe = Number.isFinite(rating) ? Math.max(0, Math.min(5, Math.round(rating))) : 0;
  return {
    on: "★".repeat(safe),
    off: "☆".repeat(5 - safe)
  };
}
