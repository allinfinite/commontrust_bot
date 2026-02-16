import { ImageResponse } from "next/og";
import { CTB_LOGO_BASE64 } from "@/lib/logo-base64";

export const runtime = "edge";
export const alt = "Trust Ledger — Public reputation filings for peer-to-peer trades";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function OgImage() {
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
          background: "linear-gradient(135deg, #fbf6ea 0%, #f4eddc 100%)",
          fontFamily: "serif",
        }}
      >
        {/* Decorative accent bars */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: 6,
            display: "flex",
          }}
        >
          <div style={{ flex: 1, background: "#b61b2e" }} />
          <div style={{ flex: 1, background: "#1b4d8f" }} />
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div
            style={{
              fontFamily: "monospace",
              fontSize: 16,
              letterSpacing: "0.2em",
              textTransform: "uppercase",
              color: "rgba(16,17,20,0.55)",
            }}
          >
            Big Island Bulletin presents
          </div>

          <div
            style={{
              fontSize: 72,
              fontWeight: 800,
              lineHeight: 1.05,
              letterSpacing: "-0.5px",
              color: "rgba(16,17,20,0.92)",
            }}
          >
            Trust Ledger
          </div>

          <div
            style={{
              fontSize: 28,
              lineHeight: 1.4,
              color: "rgba(16,17,20,0.65)",
              maxWidth: 700,
            }}
          >
            A public, transparent reputation ledger for peer-to-peer trades.
            Look up any trader&apos;s verified deal history, ratings, and
            reviews.
          </div>
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-end",
          }}
        >
          <div
            style={{
              display: "flex",
              gap: 16,
              alignItems: "center",
            }}
          >
            <div
              style={{
                display: "flex",
                gap: 12,
              }}
            >
              <div
                style={{
                  padding: "10px 20px",
                  border: "2px solid rgba(182,27,46,0.3)",
                  borderRadius: 999,
                  fontSize: 16,
                  fontFamily: "monospace",
                  color: "rgba(16,17,20,0.7)",
                  background: "rgba(255,255,255,0.6)",
                }}
              >
                commontrust.credit
              </div>
            </div>
          </div>

          <div
            style={{
              display: "flex",
              gap: 8,
              fontSize: 14,
              fontFamily: "monospace",
              color: "rgba(16,17,20,0.4)",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              alignItems: "center",
            }}
          >
            <img src={CTB_LOGO_BASE64} style={{ width: 32, height: 32 }} />
            Powered by CommonTrust Bot
          </div>
        </div>
      </div>
    ),
    { ...size }
  );
}
