import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { pbAdminGet, pbAdminPatch } from "@/lib/pocketbase_admin";
import type { MemberRecord, ReviewRecord } from "@/lib/types";
import { formatDate, memberHref, memberLabel, stars } from "@/lib/ui";
import { reviewResponseTokenPreview, verifyReviewResponseToken } from "@/lib/review_response_token";

export const dynamic = "force-dynamic";

type ReviewWithExpand = ReviewRecord & {
  expand?: {
    reviewer_id?: MemberRecord;
    reviewee_id?: MemberRecord;
    deal_id?: { id: string; description?: string };
  };
};

async function submitResponseAction(formData: FormData) {
  "use server";
  const token = String(formData.get("token") ?? "").trim();
  const response = String(formData.get("response") ?? "").trim();

  const p = verifyReviewResponseToken(token);
  if (!response) throw new Error("Response is required");
  if (response.length > 4000) throw new Error("Response is too long");

  const review = await pbAdminGet<ReviewWithExpand>("reviews", p.review_id, "reviewee_id");
  const revieweeTid = review.expand?.reviewee_id?.telegram_id;
  if (!revieweeTid || revieweeTid !== p.reviewee_tid) throw new Error("Token does not match reviewee");
  const existingResponse = (review.response ?? "").trim();
  if (existingResponse || review.response_at) {
    throw new Error("A response has already been submitted for this review");
  }

  await pbAdminPatch("reviews", p.review_id, { response, response_at: new Date().toISOString() });
  redirect(`/reviews/${encodeURIComponent(p.review_id)}`);
}

export default async function RespondPage(props: { params: Promise<{ token: string }> }) {
  const { token } = await props.params;
  const t = token.trim();
  if (!t) notFound();

  let p: { review_id: string; reviewee_tid: number; exp: number };
  try {
    p = verifyReviewResponseToken(t);
  } catch {
    notFound();
  }

  const r = await pbAdminGet<ReviewWithExpand>("reviews", p.review_id, "reviewer_id,reviewee_id,deal_id");
  const revieweeTid = r.expand?.reviewee_id?.telegram_id;
  if (!revieweeTid || revieweeTid !== p.reviewee_tid) notFound();

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
  const hasResponse = Boolean((r.response ?? "").trim() || r.response_at);

  return (
    <>
      <div className="row">
        <h1 className="pageTitle">Respond</h1>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <Link className="pill" href={`/reviews/${encodeURIComponent(r.id)}`}>
            Open filing
          </Link>
          {deal?.id ? (
            <Link className="pill" href={`/deals/${encodeURIComponent(deal.id)}`}>
              Open deal
            </Link>
          ) : null}
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
          <span className="pill mono">{reviewResponseTokenPreview(t)}</span>
        </div>

        {r.comment ? <div style={{ marginTop: 10, whiteSpace: "pre-wrap" }}>{r.comment}</div> : null}
        {deal?.description ? (
          <div className="muted" style={{ marginTop: 10 }}>
            Deal: {deal.description}
          </div>
        ) : null}

        <div style={{ marginTop: 12, borderTop: "1px solid var(--line)", paddingTop: 12 }}>
          <div style={{ fontWeight: 900 }}>Your response</div>
          {hasResponse ? (
            <>
              <div className="muted" style={{ marginTop: 6 }}>
                A response has already been submitted. Only one response is allowed.
              </div>
              <div style={{ marginTop: 10, whiteSpace: "pre-wrap" }}>{r.response}</div>
            </>
          ) : (
            <>
              <div className="muted" style={{ marginTop: 6 }}>
                This will be published under the review. You can submit only once.
              </div>
              <form action={submitResponseAction} style={{ marginTop: 10 }}>
                <input type="hidden" name="token" value={t} />
                <textarea
                  className="input"
                  name="response"
                  rows={6}
                  defaultValue=""
                  placeholder="Write a public response..."
                  style={{ width: "100%", resize: "vertical", fontFamily: "inherit", lineHeight: 1.45, padding: 12 }}
                />
                <div className="rowBetween" style={{ marginTop: 10 }}>
                  <button className="btn btnPrimary" type="submit">
                    Publish response
                  </button>
                  <Link className="pill" href={`/reviews/${encodeURIComponent(r.id)}`}>
                    Cancel
                  </Link>
                </div>
              </form>
            </>
          )}
        </div>
      </div>
    </>
  );
}
