import Link from "next/link";
import { notFound } from "next/navigation";

import { escapePbString, pbList } from "@/lib/pocketbase";
import type { ReviewRecord } from "@/lib/types";
import { formatDate, memberHref, memberLabel, stars } from "@/lib/ui";

export const dynamic = "force-dynamic";

export default async function DealPage(props: { params: Promise<{ id: string }> }) {
  const { id } = await props.params;
  const dealId = id.trim();
  if (!dealId) notFound();

  const reviews = await pbList<ReviewRecord>("reviews", {
    perPage: 50,
    sort: "-created_at",
    filter: `deal_id='${escapePbString(dealId)}'`,
    expand: "reviewer_id,reviewee_id,deal_id",
    revalidateSeconds: 60
  });

  return (
    <>
      <div className="row">
        <h1 style={{ margin: 0, fontFamily: "var(--font-title), ui-serif, serif", fontSize: 36 }}>Deal {dealId}</h1>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <Link className="pill" href="/reviews">
            Browse all reviews
          </Link>
        </div>
      </div>

      <p className="muted" style={{ marginTop: 8 }}>
        Reviews submitted for this deal.
      </p>

      <div className="grid" style={{ marginTop: 12 }}>
        {reviews.items.length === 0 ? (
          <div className="card">
            <div style={{ fontWeight: 800 }}>No public reviews found for this deal yet.</div>
          </div>
        ) : (
          reviews.items.map((r) => {
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
                </div>

                {r.comment ? <div style={{ marginTop: 10, whiteSpace: "pre-wrap" }}>{r.comment}</div> : null}
                {deal?.description ? (
                  <div className="muted" style={{ marginTop: 10 }}>
                    Deal: {deal.description}
                  </div>
                ) : null}
              </div>
            );
          })
        )}
      </div>
    </>
  );
}
