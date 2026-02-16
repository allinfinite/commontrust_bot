import { ImageResponse } from "next/og";

import { escapePbString, isTelegramUsername, pbList } from "@/lib/pocketbase";
import { processTextForSatori } from "@/lib/hebrew-rtl";
import { CTB_LOGO_BASE64 } from "@/lib/logo-base64";
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

function Badge({ text, color, bg, border }: { text: string; color: string; bg: string; border: string }) {
  return (
    <div
      style={{
        display: "flex",
        padding: "6px 14px",
        borderRadius: 999,
        background: bg,
        border: `2px solid ${border}`,
        color,
        fontSize: 16,
        fontWeight: 800,
        fontFamily: "monospace",
        textTransform: "uppercase",
        letterSpacing: "0.1em",
      }}
    >
      {text}
    </div>
  );
}

function StatBlock({ label, value, valueColor }: { label: string; value: string; valueColor: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <div
        style={{
          display: "flex",
          fontSize: 14,
          fontFamily: "monospace",
          color: "rgba(16,17,20,0.45)",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
        }}
      >
        {label}
      </div>
      <div style={{ display: "flex", fontSize: 28, fontWeight: 800, color: valueColor }}>
        {value}
      </div>
    </div>
  );
}

export default async function OgImage({ params }: { params: Promise<{ handle: string }> }) {
  const { handle } = await params;
  let member: MemberRecord | null = null;
  
  try {
    member = await findMember(handle);
  } catch (err) {
    // Log but don't crash - return a fallback OG image
    console.error(`Failed to find member for OG image: ${handle}`, err);
  }

  const displayName =
    member?.display_name?.trim() ||
    (member?.username ? `@${member.username}` : handle.replace(/^@/, ""));

  let avgRating: number | null = null;
  let verifiedDeals: number | null = null;
  let reviewCount = 0;

  if (member) {
    try {
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
    } catch (err) {
      // Log but don't crash - use fallback values
      console.error(`Failed to fetch reputation data for member ${member.id}:`, err);
    }
  }

  const isScammer = member?.scammer === true;
  const isVerified = member?.verified === true;

  // Build badge element
  let badge: React.ReactNode = null;
  if (isScammer) {
    badge = <Badge text="Confirmed Scammer" color="#b00020" bg="rgba(176,0,32,0.12)" border="rgba(176,0,32,0.4)" />;
  } else if (isVerified) {
    badge = <Badge text="Verified" color="#0b7a46" bg="rgba(11,122,70,0.08)" border="rgba(11,122,70,0.3)" />;
  }

  const ratingDisplay = avgRating !== null ? `${avgRating.toFixed(2)} / 5` : "—";

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
            display: "flex",
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: 6,
            background: isScammer ? "#b00020" : "#b61b2e",
          }}
        />

        {/* Upper section: kicker + identity */}
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <div
            style={{
              display: "flex",
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

            {/* Name + badge + username */}
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div
                style={{
                  display: "flex",
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
                {processTextForSatori(displayName)}
              </div>

              <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                {badge}
                {member?.username ? (
                  <div
                    style={{
                      display: "flex",
                      fontSize: 20,
                      color: "rgba(16,17,20,0.5)",
                      fontFamily: "monospace",
                    }}
                  >
                    @{processTextForSatori(member.username)}
                  </div>
                ) : null}
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
                  display: "flex",
                  fontSize: 14,
                  fontFamily: "monospace",
                  color: "rgba(16,17,20,0.45)",
                  textTransform: "uppercase",
                  letterSpacing: "0.1em",
                }}
              >
                Rating
              </div>
              <div style={{ display: "flex", fontSize: 28, fontWeight: 800, color: "#b61b2e" }}>
                {ratingDisplay}
              </div>
            </div>

            <StatBlock label="Verified Deals" value={verifiedDeals != null ? String(verifiedDeals) : "—"} valueColor="rgba(16,17,20,0.85)" />
            <StatBlock label="Reviews" value={String(reviewCount)} valueColor="rgba(16,17,20,0.85)" />
          </div>

          <div
            style={{
              display: "flex",
              fontSize: 14,
              fontFamily: "monospace",
              color: "rgba(16,17,20,0.35)",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              alignItems: "center",
              gap: 12,
            }}
          >
            <img src={CTB_LOGO_BASE64} style={{ width: 40, height: 40 }} />
            commontrust.credit
          </div>
        </div>
      </div>
    ),
    { ...size }
  );
}
