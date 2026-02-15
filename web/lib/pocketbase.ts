import type { PbListResponse } from "@/lib/types";

type QueryOpts = {
  page?: number;
  perPage?: number;
  sort?: string;
  filter?: string;
  expand?: string;
  revalidateSeconds?: number;
};

const EMPTY_LIST = {
  page: 1,
  perPage: 30,
  totalItems: 0,
  totalPages: 1,
  items: []
} as const;

function getBaseUrl(): string {
  const raw = process.env.POCKETBASE_URL?.trim();
  if (!raw) {
    throw new Error("Missing POCKETBASE_URL environment variable");
  }
  return raw.replace(/\/+$/, "");
}

function requestHeaders(): HeadersInit {
  const token = process.env.POCKETBASE_API_TOKEN?.trim();
  const headers: Record<string, string> = { Accept: "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

async function pbFetch<T>(url: string, revalidateSeconds = 60): Promise<T> {
  const res = await fetch(url, {
    headers: requestHeaders(),
    next: { revalidate: revalidateSeconds }
  });
  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText);
    throw new Error(`PocketBase request failed (${res.status}): ${msg || res.statusText}`);
  }
  return (await res.json()) as T;
}

export async function pbList<T>(collection: string, opts: QueryOpts = {}): Promise<PbListResponse<T>> {
  try {
    const params = new URLSearchParams();
    params.set("page", String(opts.page ?? 1));
    params.set("perPage", String(opts.perPage ?? 30));
    if (opts.sort) params.set("sort", opts.sort);
    if (opts.filter) params.set("filter", opts.filter);
    if (opts.expand) params.set("expand", opts.expand);

    const url = `${getBaseUrl()}/api/collections/${encodeURIComponent(collection)}/records?${params.toString()}`;
    return await pbFetch<PbListResponse<T>>(url, opts.revalidateSeconds ?? 60);
  } catch {
    return {
      page: opts.page ?? EMPTY_LIST.page,
      perPage: opts.perPage ?? EMPTY_LIST.perPage,
      totalItems: 0,
      totalPages: 1,
      items: []
    };
  }
}

export function escapePbString(value: string): string {
  return value.replace(/\\/g, "\\\\").replace(/'/g, "\\'");
}

export function isTelegramUsername(value: string): boolean {
  return /^[a-zA-Z][a-zA-Z0-9_]{4,31}$/.test(value);
}
