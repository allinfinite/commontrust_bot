import Link from "next/link";

import { escapePbString } from "@/lib/pocketbase";
import { pbAdminDelete, pbAdminList } from "@/lib/pocketbase_admin";
import { formatDate, memberLabel, stars } from "@/lib/ui";

type Member = { id: string; username?: string; display_name?: string; telegram_id?: number };
type Deal = { id: string; description?: string };
type Review = {
  id: string;
  rating: number;
  comment?: string;
  outcome?: string;
  reviewer_username?: string;
  reviewee_username?: string;
  created_at?: string;
  expand?: { reviewer_id?: Member; reviewee_id?: Member; deal_id?: Deal };
};

export const dynamic = "force-dynamic";

async function deleteReviewAction(formData: FormData) {
  "use server";
  const id = String(formData.get("id") ?? "");
  if (!id) return;
  await pbAdminDelete("reviews", id);
}

export default async function AdminReviewsPage(props: { searchParams?: Promise<{ q?: string; page?: string }> }) {
  const sp = (await props.searchParams) ?? {};
  const page = Math.max(1, Number(sp.page ?? "1") || 1);
  const q = (sp.q ?? "").trim().replace(/^@/, "").toLowerCase();

  const filter = q ? `reviewee_username='${escapePbString(q)}' || reviewer_username='${escapePbString(q)}'` : undefined;

  const reviews = await pbAdminList<Review>("reviews", {
    page,
    perPage: 40,
    sort: "-created_at",
    filter,
    expand: "reviewer_id,reviewee_id,deal_id"
  });

  return (
    <>
      <div className="row">
        <h1 style={{ margin: 0, fontFamily: "var(--font-title), ui-serif, serif", fontSize: 34 }}>Reviews</h1>
        <Link className="pill" href="/admin">
          Admin home
        </Link>
      </div>

      <form method="GET" action="/admin/reviews" className="card" style={{ marginTop: 12 }}>
        <div className="row" style={{ gap: 12 }}>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "baseline" }}>
            <label className="muted" htmlFor="q">
              Username
            </label>
            <input className="input" id="q" name="q" placeholder="@username" defaultValue={q ? `@${q}` : ""} />
          </div>
          <button className="btn" type="submit">
            Filter
          </button>
        </div>
      </form>

      <div className="grid" style={{ marginTop: 12 }}>
        {reviews.items.map((r) => {
          const reviewer = r.expand?.reviewer_id;
          const reviewee = r.expand?.reviewee_id;
          const deal = r.expand?.deal_id;
          const s = stars(r.rating);

          const reviewerView = {
            username: reviewer?.username ?? r.reviewer_username,
            display_name: reviewer?.display_name,
            telegram_id: reviewer?.telegram_id
          };
          const revieweeView = {
            username: reviewee?.username ?? r.reviewee_username,
            display_name: reviewee?.display_name,
            telegram_id: reviewee?.telegram_id
          };

          return (
            <div key={r.id} className="card">
              <div className="row">
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "baseline" }}>
                  <span style={{ fontWeight: 900 }}>{r.id}</span>
                  <span className="muted">
                    {memberLabel(reviewerView)} reviewed {memberLabel(revieweeView)}
                  </span>
                </div>
                <div className="muted">{formatDate(r.created_at ?? "")}</div>
              </div>

              <div className="row" style={{ marginTop: 10 }}>
                <div className="stars">
                  <span className="on">{s.on}</span>
                  <span className="off">{s.off}</span>
                </div>
                {r.outcome ? <span className="pill">Outcome: {r.outcome}</span> : null}
              </div>

              {r.comment ? <div style={{ marginTop: 10, whiteSpace: "pre-wrap" }}>{r.comment}</div> : null}
              {deal?.description ? (
                <div className="muted" style={{ marginTop: 10 }}>
                  Deal: {deal.description}
                </div>
              ) : null}

              <form action={deleteReviewAction} style={{ marginTop: 12 }}>
                <input type="hidden" name="id" value={r.id} />
                <button className="btn" type="submit" style={{ borderColor: "rgba(255,92,124,0.35)" }}>
                  Delete review
                </button>
              </form>
            </div>
          );
        })}
      </div>

      <div style={{ display: "flex", gap: 10, justifyContent: "space-between", marginTop: 14, flexWrap: "wrap" }}>
        <div className="muted">
          Page {reviews.page} of {reviews.totalPages} (total {reviews.totalItems})
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          {reviews.page > 1 ? (
            <Link className="pill" href={`/admin/reviews?page=${reviews.page - 1}${q ? `&q=${encodeURIComponent(q)}` : ""}`}>
              Prev
            </Link>
          ) : null}
          {reviews.page < reviews.totalPages ? (
            <Link className="pill" href={`/admin/reviews?page=${reviews.page + 1}${q ? `&q=${encodeURIComponent(q)}` : ""}`}>
              Next
            </Link>
          ) : null}
        </div>
      </div>
    </>
  );
}

