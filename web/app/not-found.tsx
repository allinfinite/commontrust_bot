import Link from "next/link";

export default function NotFound() {
  return (
    <div className="card">
      <div style={{ fontWeight: 900, fontSize: 18 }}>User not found</div>
      <div className="muted" style={{ marginTop: 8 }}>
        Try searching by exact Telegram username (without the @) or numeric Telegram ID.
      </div>
      <div style={{ marginTop: 12, display: "flex", gap: 10, flexWrap: "wrap" }}>
        <Link className="pill" href="/">
          Home
        </Link>
        <Link className="pill" href="/reviews">
          Browse reviews
        </Link>
      </div>
    </div>
  );
}

