import type { PbListResponse } from "@/lib/types";

type QueryOpts = {
  page?: number;
  perPage?: number;
  sort?: string;
  filter?: string;
  expand?: string;
};

function getBaseUrl(): string {
  const raw = process.env.POCKETBASE_URL?.trim();
  if (!raw) throw new Error("Missing POCKETBASE_URL environment variable");
  return raw.replace(/\/+$/, "");
}

function adminHeaders(): HeadersInit {
  const token = process.env.POCKETBASE_API_TOKEN?.trim();
  if (!token) throw new Error("Missing POCKETBASE_API_TOKEN for admin operations");
  return {
    Accept: "application/json",
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json"
  };
}

async function adminFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${getBaseUrl()}${path}`, {
    cache: "no-store",
    ...init,
    headers: {
      ...adminHeaders(),
      ...(init?.headers ?? {})
    }
  });

  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText);
    throw new Error(`PocketBase admin request failed (${res.status}): ${msg || res.statusText}`);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function pbAdminList<T>(collection: string, opts: QueryOpts = {}): Promise<PbListResponse<T>> {
  const params = new URLSearchParams();
  params.set("page", String(opts.page ?? 1));
  params.set("perPage", String(opts.perPage ?? 30));
  if (opts.sort) params.set("sort", opts.sort);
  if (opts.filter) params.set("filter", opts.filter);
  if (opts.expand) params.set("expand", opts.expand);

  return adminFetch<PbListResponse<T>>(`/api/collections/${encodeURIComponent(collection)}/records?${params.toString()}`);
}

export async function pbAdminGet<T>(collection: string, id: string, expand?: string): Promise<T> {
  const params = new URLSearchParams();
  if (expand) params.set("expand", expand);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return adminFetch<T>(`/api/collections/${encodeURIComponent(collection)}/records/${encodeURIComponent(id)}${suffix}`);
}

export async function pbAdminPatch<T>(collection: string, id: string, body: Record<string, unknown>): Promise<T> {
  return adminFetch<T>(`/api/collections/${encodeURIComponent(collection)}/records/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(body)
  });
}

export async function pbAdminDelete(collection: string, id: string): Promise<void> {
  await adminFetch<void>(`/api/collections/${encodeURIComponent(collection)}/records/${encodeURIComponent(id)}`, {
    method: "DELETE"
  });
}
