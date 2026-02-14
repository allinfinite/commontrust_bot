import Link from "next/link";

import { pbAdminDelete, pbAdminGet, pbAdminPatch } from "@/lib/pocketbase_admin";
import { formatDate, memberLabel } from "@/lib/ui";

type Member = { id: string; username?: string; display_name?: string; telegram_id?: number };
type Deal = {
  id: string;
  status?: string;
  description?: string;
  initiator_offer?: string;
  counterparty_offer?: string;
  created_at?: string;
  updated?: string;
  expand?: {
    initiator_id?: Member;
    counterparty_id?: Member;
  };
};

export const dynamic = "force-dynamic";

async function updateDealAction(formData: FormData) {
  "use server";
  const id = String(formData.get("id") ?? "");
  const status = String(formData.get("status") ?? "");
  const description = String(formData.get("description") ?? "");
  if (!id) return;
  await pbAdminPatch("deals", id, { status, description });
}

async function deleteDealAction(formData: FormData) {
  "use server";
  const id = String(formData.get("id") ?? "");
  if (!id) return;
  await pbAdminDelete("deals", id);
}

export default async function AdminDealPage(props: { params: Promise<{ id: string }> }) {
  const { id } = await props.params;
  const deal = await pbAdminGet<Deal>("deals", id, "initiator_id,counterparty_id");

  const a = deal.expand?.initiator_id;
  const b = deal.expand?.counterparty_id;

  return (
    <>
      <div className="row">
        <h1 style={{ margin: 0, fontFamily: "var(--font-title), ui-serif, serif", fontSize: 34 }}>
          Deal {deal.id}
        </h1>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <Link className="pill" href="/admin/deals">
            Back to deals
          </Link>
        </div>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        <div className="row">
          <div className="pill">Status: {deal.status ?? "?"}</div>
          <div className="muted">{formatDate(deal.created_at ?? "")}</div>
        </div>
        <div className="muted" style={{ marginTop: 10 }}>
          {memberLabel(a)} ↔ {memberLabel(b)}
        </div>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        <div style={{ fontWeight: 900 }}>Edit</div>
        <form action={updateDealAction} style={{ marginTop: 10, display: "grid", gap: 10 }}>
          <input type="hidden" name="id" value={deal.id} />
          <label className="muted" htmlFor="status">
            Status
          </label>
          <input className="input" id="status" name="status" defaultValue={deal.status ?? ""} />
          <label className="muted" htmlFor="description">
            Description
          </label>
          <input className="input" id="description" name="description" defaultValue={deal.description ?? ""} />
          <button className="btn" type="submit">
            Save
          </button>
        </form>
      </div>

      <div className="card" style={{ marginTop: 12, borderColor: "rgba(255,92,124,0.35)" }}>
        <div style={{ fontWeight: 900, color: "var(--bad)" }}>Danger zone</div>
        <form action={deleteDealAction} style={{ marginTop: 10 }}>
          <input type="hidden" name="id" value={deal.id} />
          <button className="btn" type="submit" style={{ borderColor: "rgba(255,92,124,0.35)" }}>
            Delete deal
          </button>
        </form>
        <div className="muted" style={{ marginTop: 8 }}>
          Deleting deals can leave orphaned reviews/reputation records depending on PocketBase rules.
        </div>
      </div>
    </>
  );
}

