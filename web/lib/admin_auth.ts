const COOKIE_NAME = "ct_admin";
const MAX_AGE_SECONDS = 60 * 60 * 24 * 7; // 7 days

function b64urlEncode(bytes: Uint8Array): string {
  const b64 = Buffer.from(bytes).toString("base64");
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function b64urlDecode(s: string): Uint8Array {
  const pad = s.length % 4 === 0 ? "" : "=".repeat(4 - (s.length % 4));
  const b64 = s.replace(/-/g, "+").replace(/_/g, "/") + pad;
  return new Uint8Array(Buffer.from(b64, "base64"));
}

function safeEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a[i] ^ b[i];
  return diff === 0;
}

async function hmacSha256(secret: string, message: string): Promise<Uint8Array> {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(message));
  return new Uint8Array(sig);
}

export function adminCookieName(): string {
  return COOKIE_NAME;
}

export function adminMaxAgeSeconds(): number {
  return MAX_AGE_SECONDS;
}

export async function mintAdminCookieValue(secret: string, nowMs = Date.now()): Promise<string> {
  const ts = Math.floor(nowMs / 1000);
  const msg = `v1.${ts}`;
  const sig = await hmacSha256(secret, msg);
  return `${ts}.${b64urlEncode(sig)}`;
}

export async function verifyAdminCookieValue(
  secret: string,
  cookieValue: string | undefined | null,
  nowMs = Date.now()
): Promise<boolean> {
  if (!cookieValue) return false;
  const m = cookieValue.match(/^([0-9]{8,12})\.([A-Za-z0-9_-]{20,})$/);
  if (!m) return false;
  const ts = Number(m[1]);
  if (!Number.isFinite(ts)) return false;

  const now = Math.floor(nowMs / 1000);
  if (ts > now + 60) return false; // small clock-skew guard
  if (now - ts > MAX_AGE_SECONDS) return false;

  const msg = `v1.${ts}`;
  const expected = await hmacSha256(secret, msg);
  const provided = b64urlDecode(m[2]);
  return safeEqual(expected, provided);
}
