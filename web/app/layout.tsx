import type { Metadata } from "next";
import { Fraunces, IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import Link from "next/link";
import "./globals.css";

import { SearchBox } from "./searchbox";

const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-title" });
const plex = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "600", "700"], variable: "--font-body" });
const plexMono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "600"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "Trust Ledger | CommonTrust Bot",
  description: "A public community trust ledger powered by CommonTrust",
  metadataBase: new URL("https://trust.bigislandbulletin.com"),
  icons: {
    icon: [
      { url: "/favicon.ico" },
      { url: "/favicon-32x32.png", type: "image/png", sizes: "32x32" },
      { url: "/favicon-16x16.png", type: "image/png", sizes: "16x16" }
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180" }]
  }
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${fraunces.variable} ${plex.variable} ${plexMono.variable}`}>
      <body style={{ fontFamily: "var(--font-body), ui-sans-serif, system-ui" }}>
        <header className="topbar" role="banner">
          <div className="topbarInner">
            <div className="brand">
              <div className="brandKicker">
                <a href="https://bigislandbulletin.com" target="_blank" rel="noreferrer">
                  Big Island Bulletin
                </a>{" "}
                presents
              </div>
              <Link href="/" className="brandBannerLink" aria-label="Trust Ledger home">
                <img className="brandBanner" src="/logo-banner.png" alt="CommonTrust Bot" width={768} height={512} />
              </Link>
              <div className="brandMeta">
                <span className="brandSection">Trust Ledger</span>
                <span className="brandSub">Public reputation filings</span>
              </div>
            </div>

            <div className="topbarTools">
              <nav className="navPills" aria-label="Site navigation">
                <Link className="pill" href="/">
                  Home
                </Link>
                <Link className="pill" href="/reviews">
                  All reviews
                </Link>
                <a className="btn btnPrimary" href="https://t.me/commontrust_bot" target="_blank" rel="noreferrer">
                  Open Telegram Bot
                </a>
              </nav>
              <SearchBox />
            </div>
          </div>
        </header>
        <main>{children}</main>
        <div className="footer">
          <a href="https://bigislandbulletin.com">Big Island Bulletin</a>
        </div>
      </body>
    </html>
  );
}
