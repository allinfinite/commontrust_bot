import Link from "next/link";

import { escapePbString } from "@/lib/pocketbase";
import { pbAdminList, pbAdminPatch } from "@/lib/pocketbase_admin";
import { memberLabel } from "@/lib/ui";

type Member = {
  id: string;
  telegram_id: number;
  username?: string;
  display_name?: string;
  verified?: boolean;
  scammer?: boolean;
  scammer_at?: string;
  joined_at?: string;
};

export const dynamic = "force-dynamic";

async function toggleVerifyAction(formData: FormData) {
  "use server";
  const id = String(formData.get("id") ?? "");
  const verified = String(formData.get("verified") ?? "") === "true";
  if (!id) return;
  await pbAdminPatch("members", id, { verified });
}

async function toggleScammerAction(formData: FormData) {
  "use server";
  const id = String(formData.get("id") ?? "");
  const flag = String(formData.get("scammer") ?? "") === "true";
  if (!id) return;
  await pbAdminPatch("members", id, {
    scammer: flag,
    scammer_at: flag ? new Date().toISOString() : ""
  });
}

export default async function AdminMembersPage(props: { searchParams?: Promise<{ q?: string; page?: string }> }) {
  const sp = (await props.searchParams) ?? {};
  const page = Math.max(1, Number(sp.page ?? "1") || 1);
  const q = (sp.q ?? "").trim().replace(/^@/, "").toLowerCase();

  const filter =
    q && /^[0-9]{4,20}$/.test(q)
      ? `telegram_id=${Number(q)}`
      : q
        ? `username='${escapePbString(q)}'`
        : undefined;

  const members = await pbAdminList<Member>("members", { page, perPage: 50, filter, sort: "-created_at" });

  return (
    <>
      <div className="row">
        <h1 style={{ margin: 0, fontFamily: "var(--font-title), ui-serif, serif", fontSize: 34 }}>Members</h1>
        <Link className="pill" href="/admin">
          Admin home
        </Link>
      </div>

      <form method="GET" action="/admin/members" className="card" style={{ marginTop: 12 }}>
        <div className="row" style={{ gap: 12 }}>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "baseline" }}>
            <label className="muted" htmlFor="q">
              Search
            </label>
            <input className="input" id="q" name="q" placeholder="@username or telegram id" defaultValue={q} />
          </div>
          <button className="btn" type="submit">
            Search
          </button>
        </div>
      </form>

      <div className="grid" style={{ marginTop: 12 }}>
        {members.items.map((m) => (
          <div key={m.id} className="card">
            <div className="row">
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "baseline" }}>
                <span style={{ fontWeight: 900 }}>{memberLabel(m)}</span>
                {m.username ? <span className="pill">@{m.username}</span> : <span className="pill">no username</span>}
                <span className="pill">Telegram ID: {m.telegram_id}</span>
                {m.scammer ? (
                  <span className="pill" style={{ borderColor: "rgba(255,92,124,0.35)", color: "var(--bad)" }}>
                    Scammer
                  </span>
                ) : null}
                {m.verified ? (
                  <span className="pill" style={{ borderColor: "rgba(89,255,168,0.25)", color: "var(--good)" }}>
                    Verified
                  </span>
                ) : (
                  <span className="pill">Unverified</span>
                )}
              </div>
              <div className="muted">{m.joined_at ?? ""}</div>
            </div>
            <div style={{ marginTop: 10, display: "flex", gap: 10, flexWrap: "wrap" }}>
              <form action={toggleVerifyAction}>
                <input type="hidden" name="id" value={m.id} />
                <input type="hidden" name="verified" value={m.verified ? "false" : "true"} />
                <button className="btn" type="submit">
                  {m.verified ? "Unverify" : "Verify"}
                </button>
              </form>
              <form action={toggleScammerAction}>
                <input type="hidden" name="id" value={m.id} />
                <input type="hidden" name="scammer" value={m.scammer ? "false" : "true"} />
                <button className="btn" type="submit" style={{ borderColor: "rgba(255,92,124,0.35)" }}>
                  {m.scammer ? "Unflag scammer" : "Flag scammer"}
                </button>
              </form>
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: 10, justifyContent: "space-between", marginTop: 14, flexWrap: "wrap" }}>
        <div className="muted">
          Page {members.page} of {members.totalPages} (total {members.totalItems})
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          {members.page > 1 ? (
            <Link className="pill" href={`/admin/members?page=${members.page - 1}${q ? `&q=${encodeURIComponent(q)}` : ""}`}>
              Prev
            </Link>
          ) : null}
          {members.page < members.totalPages ? (
            <Link className="pill" href={`/admin/members?page=${members.page + 1}${q ? `&q=${encodeURIComponent(q)}` : ""}`}>
              Next
            </Link>
          ) : null}
        </div>
      </div>
    </>
  );
}
