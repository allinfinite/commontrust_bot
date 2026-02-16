import Link from "next/link";
import { notFound } from "next/navigation";

import { escapePbString, pbList } from "@/lib/pocketbase";
import type { DealRecord, ReviewRecord } from "@/lib/types";
import { formatDate, memberHref, memberLabel, stars } from "@/lib/ui";

export const dynamic = "force-dynamic";

function isFullyReviewed(reviews: ReviewRecord[]): boolean {
  const reviewers = new Set<string>();
  for (const r of reviews) {
    if (r.reviewer_id) reviewers.add(r.reviewer_id);
  }
  return reviewers.size >= 2;
}

export default async function DealPage(props: { params: Promise<{ id: string }> }) {
  const { id } = await props.params;
  const dealId = id.trim();
  if (!dealId) notFound();

  const dealRes = await pbList<DealRecord>("deals", {
    perPage: 1,
    filter: `id='${escapePbString(dealId)}'`,
    revalidateSeconds: 60
  });
  const deal = dealRes.items[0] ?? null;
  if (!deal) notFound();

  const reviews = await pbList<ReviewRecord>("reviews", {
    perPage: 20,
    sort: "-created_at",
    filter: `deal_id='${escapePbString(dealId)}'`,
    expand: "reviewer_id,reviewee_id,deal_id",
    revalidateSeconds: 60
  });

  const visible = isFullyReviewed(reviews.items);

  return (
    <>
      <div className="row">
        <h1 className="pageTitle">Deal</h1>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <Link className="pill" href="/reviews">
            Browse all reviews
          </Link>
        </div>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        <div style={{ fontWeight: 900 }}>Deal ID</div>
        <div className="mono muted" style={{ marginTop: 6 }}>
          {dealId}
        </div>
        {deal.description ? (
          <div style={{ marginTop: 12 }}>
            <div style={{ fontWeight: 900 }}>Description</div>
            <div className="muted" style={{ marginTop: 6, whiteSpace: "pre-wrap" }}>
              {deal.description}
            </div>
          </div>
        ) : null}
      </div>

      <div className="row" style={{ marginTop: 14 }}>
        <h2 style={{ margin: 0, fontSize: 18, letterSpacing: 0.2 }}>Reviews for this deal</h2>
        <span className="pill">Total: {reviews.totalItems.toLocaleString("en-US")}</span>
      </div>

      {!visible ? (
        <div className="card" style={{ marginTop: 12 }}>
          <div style={{ fontWeight: 900 }}>Not public yet</div>
          <div className="muted" style={{ marginTop: 6 }}>
            Reviews only appear after both parties have reviewed the deal.
          </div>
        </div>
      ) : (
        <div className="grid" style={{ marginTop: 12 }}>
          {reviews.items.map((r) => {
            const reviewer = r.expand?.reviewer_id;
            const reviewee = r.expand?.reviewee_id;
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
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}

