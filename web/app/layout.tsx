import type { Metadata } from "next";
import { Fraunces, IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import Link from "next/link";
import "./globals.css";

import { SearchBox } from "./searchbox";

const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-title" });
const plex = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "600", "700"], variable: "--font-body" });
const plexMono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "600"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: {
    default: "Trust Ledger | CommonTrust",
    template: "%s | Trust Ledger"
  },
  description:
    "A public, transparent reputation ledger for peer-to-peer trades. Look up any trader's verified deal history, ratings, and reviews before you trade.",
  metadataBase: new URL("https://commontrust.credit"),
  keywords: [
    "trust ledger",
    "reputation",
    "peer to peer",
    "trade reviews",
    "scam check",
    "telegram trading",
    "deal verification",
    "commontrust"
  ],
  authors: [{ name: "Big Island Bulletin", url: "https://bigislandbulletin.com" }],
  creator: "CommonTrust Bot",
  publisher: "Big Island Bulletin",
  openGraph: {
    type: "website",
    siteName: "Trust Ledger",
    title: "Trust Ledger — Transparent Reputation for P2P Trades",
    description:
      "Look up any trader's verified deal history, ratings, and reviews. A public community ledger powered by CommonTrust.",
    url: "https://commontrust.credit",
    locale: "en_US"
  },
  twitter: {
    card: "summary_large_image",
    title: "Trust Ledger — Transparent Reputation for P2P Trades",
    description:
      "Look up any trader's verified deal history, ratings, and reviews before you trade."
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true }
  },
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
                <Link className="pill" href="/how-to">
                  How to start
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
