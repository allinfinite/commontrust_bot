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
      <section className="homeHero" aria-label="Trust ledger intro">
        <div className="homeKicker">Community ledger</div>
        <h1 className="homeTitle">Trust Ledger</h1>
        <p className="homeDek">
          A public, publication-style record of reputation and deal reviews created through the CommonTrust Telegram bot.
          Search for a user above, or browse the archive.
        </p>
        <div className="homeCtas">
          <Link className="btn btnPrimary" href="/how-to">
            How to start (required)
          </Link>
          <Link className="pill" href="/reviews">
            Browse all reviews
          </Link>
          <div className="homeMeta">
            {reviewsRes.ok ? (
              <>
                <span className="homeMetaItem">
                  Total filings: <span className="mono">{reviewsRes.value.totalItems.toLocaleString("en-US")}</span>
                </span>
                <span className="homeMetaDot" aria-hidden>
                  •
                </span>
                <span className="homeMetaItem">Latest 20 shown below</span>
              </>
            ) : (
              <span className="homeMetaItem">Latest filings unavailable</span>
            )}
          </div>
        </div>
      </section>

      {!reviewsRes.ok ? (
        <div className="callout calloutBad">
          <div className="calloutTitle">PocketBase access error</div>
          <div className="muted" style={{ marginTop: 6 }}>
            This usually means either:
          </div>
          <ul className="muted" style={{ marginTop: 10, marginBottom: 0, paddingLeft: 18 }}>
            <li>
              <code>POCKETBASE_URL</code> is wrong or PocketBase is unreachable from Vercel, or
            </li>
            <li>
              collection read rules are private (common 403). Fix by making the relevant collections public-read, or
              set a server-only <code>POCKETBASE_API_TOKEN</code> env var in Vercel.
            </li>
          </ul>
          <div className="mono muted" style={{ marginTop: 12 }}>
            {reviewsRes.error}
          </div>
        </div>
      ) : (
        <div className="homeLayout">
          <section aria-label="Latest filings">
            <div className="sectionHead">
              <h2 className="sectionTitle">Latest filings</h2>
              <div className="sectionTools">
                <span className="pill">
                  Total: <span className="mono">{reviewsRes.value.totalItems.toLocaleString("en-US")}</span>
                </span>
                <Link className="pill" href="/reviews">
                  Open archive
                </Link>
              </div>
            </div>

            <div className="ledger" role="list">
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
                  <article key={r.id} className="ledgerRow" role="listitem">
                    <div className="ledgerMeta">
                      <div className="ledgerDate">{formatDate(r.created)}</div>
                      <div className="ledgerStars" aria-label={`Rating ${r.rating} out of 5`}>
                        <span className="on">{s.on}</span>
                        <span className="off">{s.off}</span>
                      </div>
                      {r.outcome ? <span className="pill pillTight">Outcome: {r.outcome}</span> : null}
                    </div>

                    <div className="ledgerMain">
                      <div className="ledgerHeadline">
                        <Link href={memberHref(reviewerView)} className="ledgerLink">
                          {memberLabel(reviewerView)}
                        </Link>
                        <span className="ledgerVerb muted">reviewed</span>
                        <Link href={memberHref(revieweeView)} className="ledgerLink">
                          {memberLabel(revieweeView)}
                        </Link>
                        {revieweeView.verified ? <span className="pill pillGood pillTight">Verified</span> : null}
                      </div>

                      {r.comment ? <div className="ledgerBody clamp3">{r.comment}</div> : null}
                      {r.response ? (
                        <div className="ledgerBody clamp3" style={{ marginTop: 10 }}>
                          <span className="muted" style={{ fontWeight: 800 }}>
                            Response{r.response_at ? ` (${formatDate(r.response_at)})` : ""}:
                          </span>{" "}
                          {r.response}
                        </div>
                      ) : null}
                      {deal?.description ? <div className="muted clamp2">Deal: {deal.description}</div> : null}
                    </div>
                  </article>
                );
              })}
            </div>
          </section>

          <aside className="homeAside" aria-label="Ledger context">
            <div className="card cardTight">
              <div className="asideKicker">About</div>
              <h3 className="asideTitle">A community record, not a rating app</h3>
              <p className="muted" style={{ marginTop: 8 }}>
                Entries here are written after a completed deal in the CommonTrust Telegram bot flow. Think of it as a
                lightweight public ledger: who traded with whom, how it went, and what was said.
              </p>
            </div>

            <div className="card cardTight">
              <div className="asideKicker">How It Works</div>
              <ol className="steps">
                <li>
                  <span className="stepsN">1</span>
                  <span>
                    In DM, run <span className="mono">/newdeal description</span>.
                  </span>
                </li>
                <li>
                  <span className="stepsN">2</span>
                  <span>Complete and confirm.</span>
                </li>
                <li>
                  <span className="stepsN">3</span>
                  <span>Both sides leave a review.</span>
                </li>
              </ol>
              <div className="muted" style={{ marginTop: 10 }}>
                Search works best by <span className="mono">@username</span>.
              </div>
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
