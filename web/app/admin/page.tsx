import Link from "next/link";

import { pbList } from "@/lib/pocketbase";

export const dynamic = "force-dynamic";

async function count(collection: string): Promise<number> {
  const r = await pbList<{ id: string }>(collection, { perPage: 1, revalidateSeconds: 10 });
  return r.totalItems;
}

export default async function AdminPage() {
  const [members, reviews, deals, reputation, reports] = await Promise.all([
    count("members"),
    count("reviews"),
    count("deals"),
    count("reputation"),
    count("reports")
  ]);

  return (
    <>
      <div className="row">
        <h1 style={{ margin: 0, fontFamily: "var(--font-title), ui-serif, serif", fontSize: 38 }}>Admin</h1>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <Link className="pill" href="/">
            Public site
          </Link>
          <form method="POST" action="/api/admin/logout">
            <button className="btn" type="submit">
              Log out
            </button>
          </form>
        </div>
      </div>

      <div className="kpi" style={{ marginTop: 12 }}>
        <div className="kpiItem">
          <div className="kpiLabel">Members</div>
          <div className="kpiValue">{members}</div>
        </div>
        <div className="kpiItem">
          <div className="kpiLabel">Deals</div>
          <div className="kpiValue">{deals}</div>
        </div>
        <div className="kpiItem">
          <div className="kpiLabel">Reviews</div>
          <div className="kpiValue">{reviews}</div>
        </div>
      </div>

      <div className="kpi">
        <div className="kpiItem">
          <div className="kpiLabel">Reports</div>
          <div className="kpiValue">{reports}</div>
        </div>
        <div className="kpiItem">
          <div className="kpiLabel">Reputation records</div>
          <div className="kpiValue">{reputation}</div>
        </div>
        <div className="kpiItem">
          <div className="kpiLabel">PocketBase URL</div>
          <div className="kpiValue" style={{ fontSize: 14, wordBreak: "break-word" }}>
            {process.env.POCKETBASE_URL || "unset"}
          </div>
        </div>
        <div className="kpiItem">
          <div className="kpiLabel">Auth mode</div>
          <div className="kpiValue" style={{ fontSize: 14 }}>
            {process.env.POCKETBASE_API_TOKEN ? "POCKETBASE_API_TOKEN" : "public"}
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        <div style={{ fontWeight: 900 }}>Admin Tools</div>
        <div style={{ marginTop: 10, display: "flex", gap: 10, flexWrap: "wrap" }}>
          <Link className="pill" href="/admin/deals">
            Manage deals
          </Link>
          <Link className="pill" href="/admin/members">
            Manage members
          </Link>
          <Link className="pill" href="/admin/reviews">
            Manage reviews
          </Link>
          <Link className="pill" href="/admin/reports">
            Manage reports
          </Link>
        </div>
        <div className="muted" style={{ marginTop: 10 }}>
          This panel uses PocketBase admin access server-side. Set <code>POCKETBASE_ADMIN_TOKEN</code> in Vercel env.
        </div>
      </div>
    </>
  );
}
