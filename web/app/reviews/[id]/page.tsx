import Link from "next/link";
import { notFound } from "next/navigation";

import { pbGet } from "@/lib/pocketbase";
import { pbAdminGet } from "@/lib/pocketbase_admin";
import type { ReviewRecord } from "@/lib/types";
import { formatDate, memberHref, memberLabel, stars } from "@/lib/ui";

export const dynamic = "force-dynamic";

export default async function ReviewPage(props: { params: Promise<{ id: string }> }) {
  const { id } = await props.params;
  const reviewId = id.trim();
  if (!reviewId) notFound();

  let r: ReviewRecord | null = null;
  try {
    r = await pbGet<ReviewRecord>("reviews", reviewId, {
      expand: "reviewer_id,reviewee_id,deal_id",
      revalidateSeconds: 60
    });
  } catch {
    // Fall through to admin-token fallback below.
  }
  if (!r && process.env.POCKETBASE_ADMIN_TOKEN) {
    try {
      r = await pbAdminGet<ReviewRecord>("reviews", reviewId, "reviewer_id,reviewee_id,deal_id");
    } catch {
      // Keep notFound behavior below if the record truly doesn't exist or isn't accessible.
    }
  }
  if (!r) notFound();

  const dealId = r.deal_id;

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
    <>
      <div className="row">
        <h1 className="pageTitle">Filing</h1>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <Link className="pill" href="/reviews">
            Browse all
          </Link>
          <Link className="pill" href={`/deals/${encodeURIComponent(dealId)}`}>
            Open deal
          </Link>
        </div>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
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
          <span className="pill mono">{r.id}</span>
        </div>

        {r.comment ? <div style={{ marginTop: 10, whiteSpace: "pre-wrap" }}>{r.comment}</div> : null}
        {deal?.description ? (
          <div className="muted" style={{ marginTop: 10 }}>
            Deal: {deal.description}
          </div>
        ) : null}

        {r.response ? (
          <div style={{ marginTop: 12, borderTop: "1px solid var(--line)", paddingTop: 10 }}>
            <div className="muted" style={{ fontWeight: 800 }}>
              Response {r.response_at ? `(${formatDate(r.response_at)})` : ""}
            </div>
            <div style={{ marginTop: 6, whiteSpace: "pre-wrap" }}>{r.response}</div>
          </div>
        ) : null}
      </div>
    </>
  );
}
