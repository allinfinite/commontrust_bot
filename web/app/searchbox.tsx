"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function SearchBox() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [err, setErr] = useState<string | null>(null);

  return (
    <form
      className="search"
      onSubmit={(e) => {
        e.preventDefault();
        const v = q.trim().replace(/^@/, "");
        if (!v) return;
        if (/^[0-9]+$/.test(v)) {
          setErr("Search by @username (not numeric ID).");
          return;
        }
        setErr(null);
        router.push(`/user/${encodeURIComponent(v)}`);
      }}
    >
      <input
        className="input"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Lookup user: @username"
        aria-label="Lookup user reviews"
      />
      <button className="btn" type="submit">
        Search
      </button>
      {err ? (
        <div className="muted" style={{ color: "var(--bad)", fontSize: 12, marginLeft: 8 }}>
          {err}
        </div>
      ) : null}
    </form>
  );
}
