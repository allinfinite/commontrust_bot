import Link from "next/link";

import { escapePbString } from "@/lib/pocketbase";
import { pbAdminDelete, pbAdminList } from "@/lib/pocketbase_admin";
import { formatDate, memberLabel } from "@/lib/ui";

type Member = { id: string; username?: string; display_name?: string; telegram_id?: number };
type Deal = {
  id: string;
  status?: string;
  description?: string;
  created_at?: string;
  expand?: {
    initiator_id?: Member;
    counterparty_id?: Member;
  };
};

export const dynamic = "force-dynamic";

async function deleteDealAction(formData: FormData) {
  "use server";
  const id = String(formData.get("id") ?? "");
  if (!id) return;
  await pbAdminDelete("deals", id);
}

export default async function AdminDealsPage(props: {
  searchParams?: Promise<{ page?: string; status?: string; q?: string }>;
}) {
  const sp = (await props.searchParams) ?? {};
  const page = Math.max(1, Number(sp.page ?? "1") || 1);
  const status = (sp.status ?? "").trim();
  const q = (sp.q ?? "").trim().replace(/^@/, "").toLowerCase();

  // If filtering by username, resolve to member id first and then filter by relation.
  // (PocketBase filters don't support joins on relation fields.)
  let memberId: string | null = null;
  if (q) {
    const m = await pbAdminList<Member>("members", {
      perPage: 1,
      filter: `username='${escapePbString(q)}'`
    });
    memberId = m.items[0]?.id ?? null;
  }

  const filterParts: string[] = [];
  if (status) filterParts.push(`status="${escapePbString(status)}"`);
  if (memberId) filterParts.push(`(initiator_id="${escapePbString(memberId)}" || counterparty_id="${escapePbString(memberId)}")`);
  const filter = filterParts.length ? filterParts.join(" && ") : undefined;

  const deals = await pbAdminList<Deal>("deals", {
    page,
    perPage: 40,
    sort: "-created_at",
    filter,
    expand: "initiator_id,counterparty_id"
  });

  return (
    <>
      <div className="row">
        <h1 style={{ margin: 0, fontFamily: "var(--font-title), ui-serif, serif", fontSize: 34 }}>Deals</h1>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <Link className="pill" href="/admin">
            Admin home
          </Link>
        </div>
      </div>

      <form method="GET" action="/admin/deals" className="card" style={{ marginTop: 12 }}>
        <div className="row" style={{ gap: 12 }}>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "baseline" }}>
            <label className="muted" htmlFor="q">
              Username
            </label>
            <input className="input" id="q" name="q" placeholder="@username" defaultValue={q ? `@${q}` : ""} />
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "baseline" }}>
            <label className="muted" htmlFor="status">
              Status
            </label>
            <input className="input" id="status" name="status" placeholder="pending/completed/..." defaultValue={status} />
          </div>
          <button className="btn" type="submit">
            Filter
          </button>
        </div>
        {q && !memberId ? (
          <div className="muted" style={{ marginTop: 10, color: "var(--bad)" }}>
            No member found for @{q}. (If they never used the bot, PocketBase may not have their username.)
          </div>
        ) : null}
      </form>

      <div className="grid" style={{ marginTop: 12 }}>
        {deals.items.map((d) => {
          const a = d.expand?.initiator_id;
          const b = d.expand?.counterparty_id;
          return (
            <div key={d.id} className="card">
              <div className="row">
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "baseline" }}>
                  <span style={{ fontWeight: 900 }}>{d.id}</span>
                  <span className="pill">Status: {d.status ?? "?"}</span>
                </div>
                <div className="muted">{formatDate(d.created_at ?? "")}</div>
              </div>
              <div className="muted" style={{ marginTop: 8 }}>
                {memberLabel(a)} ↔ {memberLabel(b)}
              </div>
              {d.description ? <div style={{ marginTop: 8 }}>{d.description}</div> : null}
              <div style={{ marginTop: 10, display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
                <Link className="pill" href={`/admin/deals/${encodeURIComponent(d.id)}`}>
                  View / edit
                </Link>
                <form action={deleteDealAction}>
                  <input type="hidden" name="id" value={d.id} />
                  <button className="btn" type="submit" style={{ borderColor: "rgba(255,92,124,0.35)" }}>
                    Delete
                  </button>
                </form>
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ display: "flex", gap: 10, justifyContent: "space-between", marginTop: 14, flexWrap: "wrap" }}>
        <div className="muted">
          Page {deals.page} of {deals.totalPages} (total {deals.totalItems})
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          {deals.page > 1 ? (
            <Link className="pill" href={`/admin/deals?page=${deals.page - 1}${status ? `&status=${encodeURIComponent(status)}` : ""}${q ? `&q=${encodeURIComponent(q)}` : ""}`}>
              Prev
            </Link>
          ) : null}
          {deals.page < deals.totalPages ? (
            <Link className="pill" href={`/admin/deals?page=${deals.page + 1}${status ? `&status=${encodeURIComponent(status)}` : ""}${q ? `&q=${encodeURIComponent(q)}` : ""}`}>
              Next
            </Link>
          ) : null}
        </div>
      </div>
    </>
  );
}

