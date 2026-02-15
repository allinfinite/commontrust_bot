import type { PbListResult } from "./types";

type AdminListOptions = {
  page?: number;
  perPage?: number;
  sort?: string;
  filter?: string;
  expand?: string;
};

function pbBaseUrl(): string {
  const base = process.env.POCKETBASE_URL?.trim();
  if (!base) throw new Error("POCKETBASE_URL is not configured");
  return base.replace(/\/$/, "");
}

function adminHeaders(): HeadersInit {
  const token = process.env.POCKETBASE_ADMIN_TOKEN?.trim() || process.env.POCKETBASE_API_TOKEN?.trim();
  if (!token) {
    throw new Error("POCKETBASE_ADMIN_TOKEN (or POCKETBASE_API_TOKEN) is required for admin routes");
  }
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json"
  };
}

async function parseJsonOrThrow<T>(res: Response, context: string): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${context} failed (${res.status}): ${text || res.statusText}`);
  }
  return (await res.json()) as T;
}

export async function pbAdminList<T>(collection: string, options: AdminListOptions = {}): Promise<PbListResult<T>> {
  const url = new URL(`${pbBaseUrl()}/api/collections/${encodeURIComponent(collection)}/records`);
  url.searchParams.set("page", String(options.page ?? 1));
  url.searchParams.set("perPage", String(options.perPage ?? 20));
  if (options.sort) url.searchParams.set("sort", options.sort);
  if (options.filter) url.searchParams.set("filter", options.filter);
  if (options.expand) url.searchParams.set("expand", options.expand);

  const res = await fetch(url, { headers: adminHeaders(), cache: "no-store" });
  return parseJsonOrThrow<PbListResult<T>>(res, `Admin list ${collection}`);
}

export async function pbAdminGet<T>(collection: string, id: string, expand?: string): Promise<T> {
  const url = new URL(`${pbBaseUrl()}/api/collections/${encodeURIComponent(collection)}/records/${encodeURIComponent(id)}`);
  if (expand) url.searchParams.set("expand", expand);
  const res = await fetch(url, { headers: adminHeaders(), cache: "no-store" });
  return parseJsonOrThrow<T>(res, `Admin get ${collection}/${id}`);
}

export async function pbAdminPatch(collection: string, id: string, data: Record<string, unknown>): Promise<void> {
  const url = `${pbBaseUrl()}/api/collections/${encodeURIComponent(collection)}/records/${encodeURIComponent(id)}`;
  const res = await fetch(url, { method: "PATCH", headers: adminHeaders(), body: JSON.stringify(data), cache: "no-store" });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Admin patch ${collection}/${id} failed (${res.status}): ${text || res.statusText}`);
  }
}

export async function pbAdminDelete(collection: string, id: string): Promise<void> {
  const url = `${pbBaseUrl()}/api/collections/${encodeURIComponent(collection)}/records/${encodeURIComponent(id)}`;
  const res = await fetch(url, { method: "DELETE", headers: adminHeaders(), cache: "no-store" });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Admin delete ${collection}/${id} failed (${res.status}): ${text || res.statusText}`);
  }
}
