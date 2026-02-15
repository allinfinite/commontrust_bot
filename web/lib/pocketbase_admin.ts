type PbListResponse<T> = {
  page: number;
  perPage: number;
  totalItems: number;
  totalPages: number;
  items: T[];
};

function pbBaseUrl(): string {
  const base = process.env.POCKETBASE_URL ?? "http://localhost:8090";
  return base.replace(/\/+$/, "");
}

function adminToken(): string {
  const t = process.env.POCKETBASE_ADMIN_TOKEN;
  if (!t) {
    throw new Error(
      "Missing POCKETBASE_ADMIN_TOKEN (required for admin panel). Set it in Vercel env as a sensitive variable."
    );
  }
  return t;
}

export function pbAdminUrl(path: string, params?: Record<string, string | number | undefined>): string {
  const url = new URL(`${pbBaseUrl()}${path.startsWith("/") ? "" : "/"}${path}`);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v === undefined) continue;
      url.searchParams.set(k, String(v));
    }
  }
  return url.toString();
}

export async function pbAdminFetch(path: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(pbAdminUrl(path), {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
      // PocketBase expects the raw token in Authorization.
      Authorization: adminToken()
    },
    cache: "no-store"
  });
  return res;
}

export async function pbAdminList<T>(
  collection: string,
  opts: { page?: number; perPage?: number; sort?: string; filter?: string; expand?: string } = {}
): Promise<PbListResponse<T>> {
  const url = pbAdminUrl(`/api/collections/${collection}/records`, {
    page: opts.page ?? 1,
    perPage: opts.perPage ?? 30,
    sort: opts.sort,
    filter: opts.filter,
    expand: opts.expand
  });

  const res2 = await fetch(url, {
    method: "GET",
    headers: { Authorization: adminToken() },
    cache: "no-store"
  });
  if (!res2.ok) {
    const body = await res2.text().catch(() => "");
    throw new Error(`PocketBase admin ${res2.status} ${collection}: ${body.slice(0, 400)}`);
  }
  return (await res2.json()) as PbListResponse<T>;
}

export async function pbAdminGet<T>(collection: string, id: string, expand?: string): Promise<T> {
  const url = pbAdminUrl(`/api/collections/${collection}/records/${id}`, expand ? { expand } : undefined);
  const res = await fetch(url, { headers: { Authorization: adminToken() }, cache: "no-store" });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`PocketBase admin ${res.status} ${collection}/${id}: ${body.slice(0, 400)}`);
  }
  return (await res.json()) as T;
}

export async function pbAdminPatch<T>(collection: string, id: string, data: unknown): Promise<T> {
  const res = await fetch(pbAdminUrl(`/api/collections/${collection}/records/${id}`), {
    method: "PATCH",
    headers: { Authorization: adminToken(), "content-type": "application/json" },
    body: JSON.stringify(data),
    cache: "no-store"
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`PocketBase admin ${res.status} PATCH ${collection}/${id}: ${body.slice(0, 400)}`);
  }
  return (await res.json()) as T;
}

export async function pbAdminDelete(collection: string, id: string): Promise<void> {
  const res = await fetch(pbAdminUrl(`/api/collections/${collection}/records/${id}`), {
    method: "DELETE",
    headers: { Authorization: adminToken() },
    cache: "no-store"
  });
  if (!res.ok && res.status !== 204) {
    const body = await res.text().catch(() => "");
    throw new Error(`PocketBase admin ${res.status} DELETE ${collection}/${id}: ${body.slice(0, 400)}`);
  }
}
