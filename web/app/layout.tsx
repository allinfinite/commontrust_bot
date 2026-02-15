import type { Metadata } from "next";
import { Fraunces, IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import Link from "next/link";
import "./globals.css";

import { SearchBox } from "./searchbox";

const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-title" });
const plex = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "600", "700"], variable: "--font-body" });
const plexMono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "600"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "Trust Ledger | Big Island Bulletin",
  description: "A public community trust ledger powered by CommonTrust",
  metadataBase: new URL("https://trust.bigislandbulletin.com")
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${fraunces.variable} ${plex.variable} ${plexMono.variable}`}>
      <body style={{ fontFamily: "var(--font-body), ui-sans-serif, system-ui" }}>
        <header className="topbar" role="banner">
          <div className="topbarInner">
            <div className="brand">
              <Link href="/" className="brandTitle" style={{ fontFamily: "var(--font-title), ui-serif, serif" }}>
                Big Island Bulletin
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
              </nav>
              <SearchBox />
            </div>
          </div>
        </header>
        <main>{children}</main>
        <div className="footer">
          Data shown here comes from the CommonTrust PocketBase backend. For new reviews, use the Telegram bot flow
          (deals and confirmations).
        </div>
      </body>
    </html>
  );
}
