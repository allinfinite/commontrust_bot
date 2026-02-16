type PbListResponse<T> = {
  page: number;
  perPage: number;
  totalItems: number;
  totalPages: number;
  items: T[];
};

function getPbBaseUrl(): string {
  const base =
    process.env.POCKETBASE_URL ??
    process.env.NEXT_PUBLIC_POCKETBASE_URL ??
    "http://localhost:8090";

  return base.replace(/\/+$/, "");
}

function getAuthHeaders(): HeadersInit {
  const token = process.env.POCKETBASE_API_TOKEN;
  if (!token) return {};
  // PocketBase expects the raw token in the Authorization header (no "Bearer " prefix).
  return { Authorization: token };
}

export function pbUrl(path: string, params?: Record<string, string | number | undefined>): string {
  const base = getPbBaseUrl();
  const url = new URL(`${base}${path.startsWith("/") ? "" : "/"}${path}`);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v === undefined) continue;
      url.searchParams.set(k, String(v));
    }
  }
  return url.toString();
}

export async function pbList<T>(
  collection: string,
  opts: {
    page?: number;
    perPage?: number;
    sort?: string;
    filter?: string;
    expand?: string;
    fields?: string;
    revalidateSeconds?: number;
  } = {}
): Promise<PbListResponse<T>> {
  const url = pbUrl(`/api/collections/${collection}/records`, {
    page: opts.page ?? 1,
    perPage: opts.perPage ?? 20,
    sort: opts.sort,
    filter: opts.filter,
    expand: opts.expand,
    fields: opts.fields
  });

  const res = await fetch(url, {
    headers: { ...getAuthHeaders() },
    next: { revalidate: opts.revalidateSeconds ?? 60 }
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`PocketBase ${res.status} for ${collection}: ${body.slice(0, 400)}`);
  }
  return (await res.json()) as PbListResponse<T>;
}

export async function pbGet<T>(
  collection: string,
  id: string,
  opts: { expand?: string; fields?: string; revalidateSeconds?: number } = {}
): Promise<T> {
  const url = pbUrl(`/api/collections/${collection}/records/${encodeURIComponent(id)}`, {
    expand: opts.expand,
    fields: opts.fields
  });
  const res = await fetch(url, {
    headers: { ...getAuthHeaders() },
    next: { revalidate: opts.revalidateSeconds ?? 60 }
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`PocketBase ${res.status} for ${collection}/${id}: ${body.slice(0, 400)}`);
  }
  return (await res.json()) as T;
}

export function escapePbString(v: string): string {
  // PocketBase filter strings are single-quoted.
  // This is intentionally conservative: escape backslash + single-quote.
  return v.replace(/\\/g, "\\\\").replace(/'/g, "\\'");
}

export function isTelegramUsername(s: string): boolean {
  // Telegram usernames: 5-32 chars, letters/digits/underscore. (We'll be a bit permissive on length.)
  return /^[A-Za-z0-9_]{3,64}$/.test(s);
}
