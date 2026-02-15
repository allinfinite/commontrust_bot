import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { escapePbString, isTelegramUsername, pbList } from "@/lib/pocketbase";
import type { MemberRecord, ReputationRecord, ReviewRecord } from "@/lib/types";
import { formatDate, memberHref, memberLabel, stars } from "@/lib/ui";

export const dynamic = "force-dynamic";

async function findMemberByHandle(handle: string): Promise<MemberRecord | null> {
  const h = handle.trim().replace(/^@/, "");
  if (!h) return null;

  // Numeric Telegram ID
  if (/^[0-9]{4,20}$/.test(h)) {
    const list = await pbList<MemberRecord>("members", {
      perPage: 1,
      filter: `telegram_id=${Number(h)}`,
      revalidateSeconds: 60
    });
    return list.items[0] ?? null;
  }

  // Username
  if (!isTelegramUsername(h)) return null;
  const u = escapePbString(h.toLowerCase());
  const list = await pbList<MemberRecord>("members", {
    perPage: 1,
    filter: `username='${u}'`,
    revalidateSeconds: 60
  });
  return list.items[0] ?? null;
}

async function getReputation(memberId: string): Promise<ReputationRecord | null> {
  const rep = await pbList<ReputationRecord>("reputation", {
    perPage: 1,
    filter: `member_id='${escapePbString(memberId)}'`,
    revalidateSeconds: 60
  });
  return rep.items[0] ?? null;
}

export default async function UserPage(props: { params: Promise<{ handle: string }> }) {
  const { handle } = await props.params;
  const h = handle.trim().replace(/^@/, "");
  if (!h) notFound();

  const member = await findMemberByHandle(h);

  // If we can't resolve a member record (e.g. legacy data missing username),
  // fall back to username-based review lookup.
  if (!member) {
    if (!isTelegramUsername(h)) notFound();
    const u = escapePbString(h.toLowerCase());
    const reviewsAbout = await pbList<ReviewRecord>("reviews", {
      perPage: 30,
      sort: "-created_at",
      filter: `reviewee_username='${u}'`,
      expand: "reviewer_id,reviewee_id,deal_id",
      revalidateSeconds: 60
    });

    return (
      <>
        <div className="row">
          <h1 className="pageTitle">@{h}</h1>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <span className="pill">Username profile</span>
          </div>
        </div>

        <div className="row" style={{ marginTop: 14 }}>
          <h2 style={{ margin: 0, fontSize: 18, letterSpacing: 0.2 }}>Reviews about @{h}</h2>
          <Link className="pill" href="/reviews">
            Browse all
          </Link>
        </div>

        <div className="grid" style={{ marginTop: 12 }}>
          {reviewsAbout.items.length === 0 ? (
            <div className="card">
              <div style={{ fontWeight: 800 }}>No reviews found</div>
              <div className="muted" style={{ marginTop: 6 }}>
                This can happen if older records were created before usernames were stored.
              </div>
            </div>
          ) : (
            reviewsAbout.items.map((r) => {
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
                username: reviewee?.username ?? r.reviewee_username ?? h,
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

  // If the user came in via username, canonicalize to the numeric Telegram ID route.
  // This keeps links stable even if the user changes their Telegram username later.
  if (!/^[0-9]{4,20}$/.test(h) && member.telegram_id) {
    redirect(`/user/${encodeURIComponent(String(member.telegram_id))}`);
  }

  const [reputation, reviewsAbout, reviewsByMember] = await Promise.all([
    getReputation(member.id),
    pbList<ReviewRecord>("reviews", {
      perPage: 30,
      sort: "-created_at",
      filter: `reviewee_id='${escapePbString(member.id)}'`,
      expand: "reviewer_id,reviewee_id,deal_id",
      revalidateSeconds: 60
    }),
    pbList<ReviewRecord>("reviews", {
      perPage: 200,
      sort: "-created_at",
      filter: `reviewer_id='${escapePbString(member.id)}' || reviewee_id='${escapePbString(member.id)}'`,
      expand: "reviewer_id,reviewee_id",
      revalidateSeconds: 60
    })
  ]);

  const title = member.display_name?.trim() || (member.username ? `@${member.username}` : `ID ${member.telegram_id}`);
  const profileName = member.display_name?.trim() || "Unknown name";
  const profileImageUrl =
    (member as MemberRecord & { profile_image_url?: string | null; photo_url?: string | null }).profile_image_url ??
    (member as MemberRecord & { profile_image_url?: string | null; photo_url?: string | null }).photo_url ??
    null;
  const usernameHistory = new Set<string>();

  if (member.username) usernameHistory.add(member.username.toLowerCase());
  for (const review of reviewsByMember.items) {
    if (review.reviewer_id === member.id && review.reviewer_username) {
      usernameHistory.add(review.reviewer_username.toLowerCase());
    }
    if (review.reviewee_id === member.id && review.reviewee_username) {
      usernameHistory.add(review.reviewee_username.toLowerCase());
    }
  }

  const usernames = Array.from(usernameHistory).sort();
  const avatarInitial = (profileName || member.username || "?").trim().slice(0, 1).toUpperCase() || "?";

  return (
    <>
      <div className="row" style={{ alignItems: "flex-start", gap: 14 }}>
        {profileImageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={profileImageUrl}
            alt={`${profileName} profile`}
            style={{ width: 70, height: 70, borderRadius: "50%", objectFit: "cover", border: "1px solid var(--line)" }}
          />
        ) : (
          <div
            aria-hidden
            style={{
              width: 70,
              height: 70,
              borderRadius: "50%",
              display: "grid",
              placeItems: "center",
              border: "1px solid var(--line)",
              fontWeight: 800,
              fontSize: 24,
              color: "var(--text)"
            }}
          >
            {avatarInitial}
          </div>
        )}

        <div style={{ flex: 1, minWidth: 260 }}>
          <h1 className="pageTitle">{title}</h1>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 8 }}>
            <span className="pill">Profile name: {profileName}</span>
            {member.verified ? (
              <span className="pill" style={{ borderColor: "rgba(89,255,168,0.25)", color: "var(--good)" }}>
                Verified
              </span>
            ) : (
              <span className="pill">Unverified</span>
            )}
            {member.username ? <span className="pill">Current username: @{member.username}</span> : null}
            <span className="pill">Telegram ID: {member.telegram_id}</span>
          </div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
            {usernames.length > 0 ? usernames.map((u) => <span key={u} className="pill">@{u}</span>) : <span className="muted">No known usernames yet.</span>}
          </div>
          <div className="muted" style={{ marginTop: 6 }}>
            Known username history
          </div>
        </div>
      </div>

      <div className="kpi">
        <div className="kpiItem">
          <div className="kpiLabel">Average rating</div>
          <div className="kpiValue">{reputation?.avg_rating?.toFixed(2) ?? "—"}</div>
        </div>
        <div className="kpiItem">
          <div className="kpiLabel">Verified deals</div>
          <div className="kpiValue">{reputation?.verified_deals ?? "—"}</div>
        </div>
        <div className="kpiItem">
          <div className="kpiLabel">Reviews (shown)</div>
          <div className="kpiValue">{reviewsAbout.totalItems}</div>
        </div>
      </div>

      <div className="row" style={{ marginTop: 14 }}>
        <h2 style={{ margin: 0, fontSize: 18, letterSpacing: 0.2 }}>Reviews about {memberLabel(member)}</h2>
        <Link className="pill" href="/reviews">
          Browse all
        </Link>
      </div>

      <div className="grid" style={{ marginTop: 12 }}>
        {reviewsAbout.items.length === 0 ? (
          <div className="card">
            <div style={{ fontWeight: 800 }}>No reviews yet</div>
            <div className="muted" style={{ marginTop: 6 }}>
              Reviews appear after deals are completed and reviewed in the Telegram bot.
            </div>
          </div>
        ) : (
          reviewsAbout.items.map((r) => {
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
