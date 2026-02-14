import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function AdminLoginPage(props: { searchParams?: Promise<{ next?: string; err?: string }> }) {
  const sp = (await props.searchParams) ?? {};
  const next = sp.next && sp.next.startsWith("/") ? sp.next : "/admin";
  const err = sp.err;

  const hasPassword = Boolean(process.env.ADMIN_PASSWORD);
  const hasSecret = Boolean(process.env.ADMIN_COOKIE_SECRET);

  return (
    <div className="card">
      <div className="row">
        <h1 style={{ margin: 0, fontFamily: "var(--font-title), ui-serif, serif", fontSize: 34 }}>
          Admin Login
        </h1>
        <Link className="pill" href="/">
          Back to site
        </Link>
      </div>

      {!hasPassword || !hasSecret ? (
        <div className="card" style={{ marginTop: 12, borderColor: "rgba(255,92,124,0.35)" }}>
          <div style={{ fontWeight: 900, color: "var(--bad)" }}>Missing configuration</div>
          <div className="muted" style={{ marginTop: 6 }}>
            Set <code>ADMIN_PASSWORD</code> and <code>ADMIN_COOKIE_SECRET</code> in Vercel env for this project.
          </div>
        </div>
      ) : null}

      {err ? (
        <div className="muted" style={{ marginTop: 12, color: "var(--bad)" }}>
          {err}
        </div>
      ) : null}

      <form method="POST" action="/api/admin/login" style={{ marginTop: 14, display: "grid", gap: 10 }}>
        <input type="hidden" name="next" value={next} />
        <label className="muted" htmlFor="password">
          Password
        </label>
        <input className="input" id="password" name="password" type="password" autoComplete="current-password" />
        <button className="btn" type="submit">
          Sign in
        </button>
      </form>

      <div className="muted" style={{ marginTop: 12 }}>
        This uses a signed HttpOnly cookie, stored only in your browser.
      </div>
    </div>
  );
}

