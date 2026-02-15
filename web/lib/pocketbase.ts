import type { PbListResult } from "./types";

type ListOptions = {
  page?: number;
  perPage?: number;
  sort?: string;
  filter?: string;
  expand?: string;
  revalidateSeconds?: number;
};

function pbBaseUrl(): string {
  const base = process.env.POCKETBASE_URL?.trim();
  if (!base) throw new Error("POCKETBASE_URL is not configured");
  return base.replace(/\/$/, "");
}

export function escapePbString(value: string): string {
  return value.replace(/\\/g, "\\\\").replace(/'/g, "\\'");
}

export function isTelegramUsername(value: string): boolean {
  return /^[a-zA-Z][a-zA-Z0-9_]{3,31}$/.test(value.trim());
}

export async function pbList<T>(collection: string, options: ListOptions = {}): Promise<PbListResult<T>> {
  const url = new URL(`${pbBaseUrl()}/api/collections/${encodeURIComponent(collection)}/records`);
  url.searchParams.set("page", String(options.page ?? 1));
  url.searchParams.set("perPage", String(options.perPage ?? 20));
  if (options.sort) url.searchParams.set("sort", options.sort);
  if (options.filter) url.searchParams.set("filter", options.filter);
  if (options.expand) url.searchParams.set("expand", options.expand);

  const token = process.env.POCKETBASE_API_TOKEN?.trim();
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    next: { revalidate: options.revalidateSeconds ?? 60 }
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`PocketBase list failed (${res.status}): ${text || res.statusText}`);
  }

  return (await res.json()) as PbListResult<T>;
}
