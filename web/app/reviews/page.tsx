import type { Metadata } from "next";
import Link from "next/link";

import { pbList } from "@/lib/pocketbase";
import type { ReviewRecord } from "@/lib/types";
import { formatDate, memberHref, memberLabel, stars } from "@/lib/ui";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "All Reviews",
  description:
    "Browse all peer-to-peer trade reviews on Trust Ledger. Every filed review is public, transparent, and permanent.",
  openGraph: {
    title: "All Reviews — Trust Ledger",
    description:
      "Browse all peer-to-peer trade reviews. Every filed review is public, transparent, and permanent.",
  },
};

export default async function ReviewsPage(props: { searchParams?: Promise<{ q?: string; page?: string }> }) {
  const sp = (await props.searchParams) ?? {};
  const page = Math.max(1, Number(sp.page ?? "1") || 1);

  const reviews = await pbList<ReviewRecord>("reviews", {
    page,
    perPage: 30,
    sort: "-created_at",
    expand: "reviewer_id,reviewee_id,deal_id",
    revalidateSeconds: 60
  });

  return (
    <>
      <div className="row">
        <h1 className="pageTitle">All Reviews</h1>
        <span className="pill">Total: {reviews.totalItems.toLocaleString("en-US")}</span>
      </div>
      <p className="muted" style={{ marginTop: 8 }}>
        For a specific user, use the search box above (recommended).
      </p>

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
                  <Link href={memberHref(reviewerView)} style={{ fontWeight: 800 }}>
                    {memberLabel(reviewerView)}
                  </Link>
                  <span className="muted">reviewed</span>
                  <Link href={memberHref(revieweeView)} style={{ fontWeight: 800 }}>
                    {memberLabel(revieweeView)}
                  </Link>
                </div>
                <div className="muted">{formatDate(r.created)}</div>
              </div>

              <div className="row" style={{ marginTop: 10 }}>
                <div className="stars" aria-label={`Rating ${r.rating} out of 5`}>
                  <span className="on">{s.on}</span>
                  <span className="off">{s.off}</span>
                </div>
                {r.outcome ? <span className="pill">Outcome: {r.outcome}</span> : null}
                <Link className="pill" href={`/reviews/${encodeURIComponent(r.id)}`}>
                  Open filing
                </Link>
              </div>

              {r.comment ? <div style={{ marginTop: 10, whiteSpace: "pre-wrap" }}>{r.comment}</div> : null}
              {r.response ? (
                <div style={{ marginTop: 12, borderTop: "1px solid var(--line)", paddingTop: 10 }}>
                  <div className="muted" style={{ fontWeight: 800 }}>
                    Response {r.response_at ? `(${formatDate(r.response_at)})` : ""}
                  </div>
                  <div style={{ marginTop: 6, whiteSpace: "pre-wrap" }}>{r.response}</div>
                </div>
              ) : null}
              {deal?.description ? (
                <div className="muted" style={{ marginTop: 10 }}>
                  Deal: {deal.description}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      <div className="rowBetween" style={{ marginTop: 14 }}>
        <div className="muted">
          Page {reviews.page} of {reviews.totalPages}
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          {reviews.page > 1 ? (
            <Link className="pill" href={`/reviews?page=${reviews.page - 1}`}>
              Prev
            </Link>
          ) : null}
          {reviews.page < reviews.totalPages ? (
            <Link className="pill" href={`/reviews?page=${reviews.page + 1}`}>
              Next
            </Link>
          ) : null}
        </div>
      </div>
    </>
  );
}
