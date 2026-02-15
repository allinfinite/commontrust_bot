"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function ErrorPage(props: { error: Error & { digest?: string }; reset: () => void }) {
  const { error } = props;

  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="card">
      <div style={{ fontWeight: 900, fontSize: 18 }}>Something went wrong</div>
      <div className="muted" style={{ marginTop: 8 }}>
        This usually means the PocketBase backend is unreachable or collection read rules are blocking access.
      </div>
      <div className="muted" style={{ marginTop: 8 }}>
        {error.message}
      </div>
      <div style={{ marginTop: 12, display: "flex", gap: 10, flexWrap: "wrap" }}>
        <button className="btn" onClick={() => props.reset()} type="button">
          Retry
        </button>
        <Link className="pill" href="/">
          Home
        </Link>
      </div>
    </div>
  );
}
