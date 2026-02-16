import { ImageResponse } from "next/og";

import { escapePbString, isTelegramUsername, pbList } from "@/lib/pocketbase";
import type { MemberRecord, ReputationRecord, ReviewRecord } from "@/lib/types";

export const runtime = "edge";
export const alt = "Trader profile on Trust Ledger";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

async function findMember(handle: string): Promise<MemberRecord | null> {
  const h = handle.trim().replace(/^@/, "");
  if (!h) return null;
  if (/^[0-9]{4,20}$/.test(h)) {
    const list = await pbList<MemberRecord>("members", {
      perPage: 1,
      filter: `telegram_id=${Number(h)}`,
      revalidateSeconds: 60,
    });
    return list.items[0] ?? null;
  }
  if (!isTelegramUsername(h)) return null;
  const list = await pbList<MemberRecord>("members", {
    perPage: 1,
    filter: `username='${escapePbString(h.toLowerCase())}'`,
    revalidateSeconds: 60,
  });
  return list.items[0] ?? null;
}

export default async function OgImage({ params }: { params: Promise<{ handle: string }> }) {
  const { handle } = await params;
  const member = await findMember(handle);

  const displayName =
    member?.display_name?.trim() ||
    (member?.username ? `@${member.username}` : handle.replace(/^@/, ""));

  let avgRating: number | null = null;
  let verifiedDeals: number | null = null;
  let reviewCount = 0;

  if (member) {
    const [rep, reviews] = await Promise.all([
      pbList<ReputationRecord>("reputation", {
        perPage: 1,
        filter: `member_id='${escapePbString(member.id)}'`,
        revalidateSeconds: 60,
      }),
      pbList<ReviewRecord>("reviews", {
        perPage: 1,
        filter: `reviewee_id='${escapePbString(member.id)}'`,
        revalidateSeconds: 60,
      }),
    ]);
    avgRating = rep.items[0]?.avg_rating ?? null;
    verifiedDeals = rep.items[0]?.verified_deals ?? null;
    reviewCount = reviews.totalItems;
  }

  const isScammer = member?.scammer === true;
  const isVerified = member?.verified === true;

  const starsFull = avgRating !== null ? Math.round(avgRating) : 0;
  const starsDisplay = avgRating !== null
    ? "★".repeat(starsFull) + "☆".repeat(5 - starsFull)
    : "No ratings yet";

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "60px 70px",
          background: isScammer
            ? "linear-gradient(135deg, #fbf6ea 0%, #f8e8ea 100%)"
            : "linear-gradient(135deg, #fbf6ea 0%, #f4eddc 100%)",
          fontFamily: "serif",
        }}
      >
        {/* Top accent bar */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: 6,
            background: isScammer ? "#b00020" : "#b61b2e",
          }}
        />

        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <div
            style={{
              fontFamily: "monospace",
              fontSize: 16,
              letterSpacing: "0.2em",
              textTransform: "uppercase",
              color: "rgba(16,17,20,0.55)",
            }}
          >
            Trust Ledger — Trader Profile
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
            {/* Avatar circle */}
            <div
              style={{
                width: 100,
                height: 100,
                borderRadius: "50%",
                border: isScammer
                  ? "3px solid rgba(176,0,32,0.5)"
                  : "3px solid rgba(16,17,20,0.12)",
                background: isScammer
                  ? "rgba(176,0,32,0.08)"
                  : "rgba(255,255,255,0.6)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 44,
                fontWeight: 800,
                color: isScammer ? "#b00020" : "rgba(16,17,20,0.7)",
              }}
            >
              {(displayName || "?").slice(0, 1).toUpperCase()}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div
                style={{
                  fontSize: 52,
                  fontWeight: 800,
                  lineHeight: 1.1,
                  color: isScammer ? "#b00020" : "rgba(16,17,20,0.92)",
                  maxWidth: 800,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {displayName}
              </div>

              <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                {isScammer && (
                  <div
                    style={{
                      padding: "6px 14px",
                      borderRadius: 999,
                      background: "rgba(176,0,32,0.12)",
                      border: "2px solid rgba(176,0,32,0.4)",
                      color: "#b00020",
                      fontSize: 16,
                      fontWeight: 800,
                      fontFamily: "monospace",
                      textTransform: "uppercase",
                      letterSpacing: "0.1em",
                    }}
                  >
                    Confirmed Scammer
                  </div>
                )}
                {!isScammer && isVerified && (
                  <div
                    style={{
                      padding: "6px 14px",
                      borderRadius: 999,
                      background: "rgba(11,122,70,0.08)",
                      border: "2px solid rgba(11,122,70,0.3)",
                      color: "#0b7a46",
                      fontSize: 16,
                      fontWeight: 700,
                      fontFamily: "monospace",
                    }}
                  >
                    Verified
                  </div>
                )}
                {member?.username && (
                  <div
                    style={{
                      fontSize: 20,
                      color: "rgba(16,17,20,0.5)",
                      fontFamily: "monospace",
                    }}
                  >
                    @{member.username}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Stats row */}
        <div style={{ display: "flex", gap: 40, alignItems: "flex-end" }}>
          <div style={{ display: "flex", gap: 40, flex: 1 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <div
                style={{
                  fontSize: 14,
                  fontFamily: "monospace",
                  color: "rgba(16,17,20,0.45)",
                  textTransform: "uppercase",
                  letterSpacing: "0.1em",
                }}
              >
                Rating
              </div>
              <div style={{ fontSize: 28, fontWeight: 800, color: "#b61b2e" }}>
                {avgRating !== null ? avgRating.toFixed(2) : "—"}
              </div>
              <div
                style={{
                  fontSize: 22,
                  letterSpacing: 2,
                  color: avgRating !== null ? "#b61b2e" : "rgba(16,17,20,0.25)",
                }}
              >
                {starsDisplay}
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <div
                style={{
                  fontSize: 14,
                  fontFamily: "monospace",
                  color: "rgba(16,17,20,0.45)",
                  textTransform: "uppercase",
                  letterSpacing: "0.1em",
                }}
              >
                Verified Deals
              </div>
              <div style={{ fontSize: 28, fontWeight: 800, color: "rgba(16,17,20,0.85)" }}>
                {verifiedDeals ?? "—"}
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <div
                style={{
                  fontSize: 14,
                  fontFamily: "monospace",
                  color: "rgba(16,17,20,0.45)",
                  textTransform: "uppercase",
                  letterSpacing: "0.1em",
                }}
              >
                Reviews
              </div>
              <div style={{ fontSize: 28, fontWeight: 800, color: "rgba(16,17,20,0.85)" }}>
                {reviewCount}
              </div>
            </div>
          </div>

          <div
            style={{
              fontSize: 14,
              fontFamily: "monospace",
              color: "rgba(16,17,20,0.35)",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
            }}
          >
            commontrust.credit
          </div>
        </div>
      </div>
    ),
    { ...size }
  );
}
