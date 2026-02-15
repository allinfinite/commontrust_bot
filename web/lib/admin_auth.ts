const te = new TextEncoder();

export function adminCookieName(): string {
  return "ct_admin";
}

export function adminMaxAgeSeconds(): number {
  return 60 * 60 * 24 * 14;
}

function toBase64Url(bytes: Uint8Array): string {
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  const b64 = btoa(binary);
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

async function sign(secret: string, payload: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    te.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, te.encode(payload));
  return toBase64Url(new Uint8Array(sig));
}

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i += 1) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}

export async function mintAdminCookieValue(secret: string): Promise<string> {
  const exp = Date.now() + adminMaxAgeSeconds() * 1000;
  const nonce = Math.random().toString(36).slice(2);
  const payload = `${exp}.${nonce}`;
  const sig = await sign(secret, payload);
  return `${payload}.${sig}`;
}

export async function verifyAdminCookieValue(secret: string, raw?: string): Promise<boolean> {
  if (!raw) return false;
  const parts = raw.split(".");
  if (parts.length !== 3) return false;

  const [expStr, nonce, suppliedSig] = parts;
  const exp = Number(expStr);
  if (!Number.isFinite(exp) || !nonce || exp < Date.now()) return false;

  const payload = `${expStr}.${nonce}`;
  const expectedSig = await sign(secret, payload);
  return timingSafeEqual(suppliedSig, expectedSig);
}
