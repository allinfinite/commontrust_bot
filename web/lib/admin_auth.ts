import { createHmac, timingSafeEqual } from "node:crypto";

const COOKIE_NAME = "ct_admin";
const MAX_AGE_SECONDS = 60 * 60 * 24 * 7;

function base64url(input: Buffer | string): string {
  return Buffer.from(input)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function sign(secret: string, payload: string): string {
  return base64url(createHmac("sha256", secret).update(payload).digest());
}

export function adminCookieName(): string {
  return COOKIE_NAME;
}

export function adminMaxAgeSeconds(): number {
  return MAX_AGE_SECONDS;
}

export async function mintAdminCookieValue(secret: string): Promise<string> {
  const issuedAt = Math.floor(Date.now() / 1000);
  const payload = String(issuedAt);
  const signature = sign(secret, payload);
  return `${payload}.${signature}`;
}

export async function verifyAdminCookieValue(secret: string, value?: string | null): Promise<boolean> {
  if (!value) return false;
  const [payload, sig] = value.split(".");
  if (!payload || !sig) return false;
  const issuedAt = Number(payload);
  if (!Number.isFinite(issuedAt)) return false;
  const now = Math.floor(Date.now() / 1000);
  if (issuedAt > now + 60) return false;
  if (now - issuedAt > MAX_AGE_SECONDS) return false;

  const expected = sign(secret, payload);
  const a = Buffer.from(sig);
  const b = Buffer.from(expected);
  if (a.length !== b.length) return false;
  return timingSafeEqual(a, b);
}
