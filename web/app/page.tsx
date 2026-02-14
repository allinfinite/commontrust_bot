import Link from "next/link";

import { pbList } from "@/lib/pocketbase";
import type { ReviewRecord } from "@/lib/types";
import { formatDate, memberHref, memberLabel, stars } from "@/lib/ui";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const reviewsRes = await pbList<ReviewRecord>("reviews", {
    perPage: 20,
    sort: "-created_at",
    expand: "reviewer_id,reviewee_id,deal_id",
    revalidateSeconds: 60
  })
    .then((v) => ({ ok: true as const, value: v }))
    .catch((e: unknown) => ({ ok: false as const, error: e instanceof Error ? e.message : String(e) }));

  return (
    <>
      <div className="row">
          <h1 style={{ margin: 0, fontFamily: "var(--font-title), ui-serif, serif", fontSize: 40, letterSpacing: 0.2 }}>
            Reviews
          </h1>
        <Link className="pill" href="/reviews">
          Browse all reviews
        </Link>
      </div>
      <p className="muted" style={{ marginTop: 8 }}>
        View reputation and deal reviews created by the CommonTrust Telegram bot.
      </p>

      {!reviewsRes.ok ? (
        <div className="card">
          <div style={{ fontWeight: 800 }}>PocketBase access error</div>
          <div className="muted" style={{ marginTop: 6 }}>
            This usually means either:
          </div>
          <ul className="muted" style={{ marginTop: 8, marginBottom: 0, paddingLeft: 18 }}>
            <li>
              <code>POCKETBASE_URL</code> is wrong or PocketBase is unreachable from Vercel, or
            </li>
            <li>
              collection read rules are private (common 403). Fix by making the relevant collections public-read, or
              set a server-only <code>POCKETBASE_API_TOKEN</code> env var in Vercel.
            </li>
          </ul>
          <div className="muted" style={{ marginTop: 10, fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}>
            {reviewsRes.error}
          </div>
        </div>
      ) : (
        <div className="grid" style={{ marginTop: 12 }}>
          {reviewsRes.value.items.map((r) => {
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
              telegram_id: reviewee?.telegram_id,
              verified: reviewee?.verified
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
                    {revieweeView.verified ? (
                      <span className="pill" style={{ borderColor: "rgba(89,255,168,0.25)", color: "var(--good)" }}>
                        Verified
                      </span>
                    ) : null}
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
          })}
        </div>
      )}
    </>
  );
}
