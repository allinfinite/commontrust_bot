import crypto from "crypto";

type Payload = {
  review_id: string;
  reviewee_tid: number;
  exp: number;
};

function b64urlDecode(s: string): Buffer {
  const pad = s.length % 4 === 0 ? "" : "=".repeat(4 - (s.length % 4));
  return Buffer.from((s + pad).replace(/-/g, "+").replace(/_/g, "/"), "base64");
}

function hmacSha256(key: Buffer, msg: Buffer): Buffer {
  return crypto.createHmac("sha256", key).update(msg).digest();
}

export function verifyReviewResponseToken(token: string, nowUnixSeconds = Math.floor(Date.now() / 1000)): Payload {
  const secret = (process.env.REVIEW_RESPONSE_SECRET ?? "").trim();
  if (!secret) throw new Error("Missing REVIEW_RESPONSE_SECRET");

  const t = token.trim();
  const parts = t.split(".");
  if (parts.length !== 2) throw new Error("Invalid token");

  const payloadRaw = b64urlDecode(parts[0]);
  const sigRaw = b64urlDecode(parts[1]);
  const expected = hmacSha256(Buffer.from(secret, "utf8"), payloadRaw);

  // constant time compare
  if (sigRaw.length !== expected.length || !crypto.timingSafeEqual(sigRaw, expected)) {
    throw new Error("Invalid token signature");
  }

  let payload: unknown;
  try {
    payload = JSON.parse(payloadRaw.toString("utf8"));
  } catch {
    throw new Error("Invalid token payload");
  }
  if (!payload || typeof payload !== "object") throw new Error("Invalid token payload");

  const p = payload as Partial<Payload>;
  if (typeof p.review_id !== "string" || !p.review_id.trim()) throw new Error("Invalid token payload");
  if (typeof p.reviewee_tid !== "number" || !Number.isInteger(p.reviewee_tid) || p.reviewee_tid <= 0) {
    throw new Error("Invalid token payload");
  }
  if (typeof p.exp !== "number" || !Number.isInteger(p.exp) || p.exp <= 0) throw new Error("Invalid token payload");
  if (p.exp < nowUnixSeconds) throw new Error("Token expired");

  return { review_id: p.review_id, reviewee_tid: p.reviewee_tid, exp: p.exp };
}

export function reviewResponseTokenPreview(token: string): string {
  // safe helper for UI, returns first/last few chars only.
  const t = token.trim();
  if (t.length <= 16) return t;
  return `${t.slice(0, 8)}...${t.slice(-6)}`;
}
