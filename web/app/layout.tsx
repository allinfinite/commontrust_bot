import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

import { SearchBox } from "./searchbox";

export const metadata: Metadata = {
  title: "Trust Reviews",
  description: "Public reputation and reviews powered by CommonTrust",
  metadataBase: new URL("https://trust.bigislandbulletin.com")
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" style={{ ["--font-title" as string]: "ui-serif, Georgia, serif", ["--font-body" as string]: "ui-sans-serif, system-ui, sans-serif" }}>
      <body style={{ fontFamily: "var(--font-body), ui-sans-serif, system-ui" }}>
        <div className="topbar">
          <div className="topbarInner">
            <div className="brand">
              <Link href="/" className="brandTitle" style={{ fontFamily: "var(--font-title), ui-serif, serif" }}>
                Trust Reviews
              </Link>
              <span className="brandSub">Big Island Bulletin</span>
            </div>
            <SearchBox />
          </div>
        </div>
        <main>{children}</main>
        <div className="footer">
          Data shown here comes from the CommonTrust PocketBase backend. For new reviews, use the Telegram bot flow
          (deals and confirmations).
        </div>
      </body>
    </html>
  );
}
