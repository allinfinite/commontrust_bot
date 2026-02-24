import { escapePbString, pbList } from "@/lib/pocketbase";
import type { DealRecord, ReviewRecord } from "@/lib/types";

function parseIsoUtc(value: string): Date | null {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

export async function getPublicDealIdsForReviews(
  reviews: Pick<ReviewRecord, "deal_id" | "reviewer_id">[],
  noStore = true,
): Promise<Set<string>> {
  const dealIds = Array.from(
    new Set(
      reviews
        .map((r) => r.deal_id)
        .filter((id): id is string => typeof id === "string" && id.length > 0),
    ),
  );
  if (dealIds.length === 0) return new Set();

  const filter = dealIds.map((id) => `deal_id='${escapePbString(id)}'`).join(" || ");
  const allDealReviews = await pbList<Pick<ReviewRecord, "deal_id" | "reviewer_id">>("reviews", {
    perPage: Math.max(200, dealIds.length * 4),
    filter: `(${filter})`,
    fields: "deal_id,reviewer_id",
    noStore,
  });

  const reviewerCountByDeal = new Map<string, Set<string>>();
  for (const r of allDealReviews.items) {
    if (!r.deal_id || !r.reviewer_id) continue;
    const bucket = reviewerCountByDeal.get(r.deal_id) ?? new Set<string>();
    bucket.add(r.reviewer_id);
    reviewerCountByDeal.set(r.deal_id, bucket);
  }

  const dealFilter = dealIds.map((id) => `id='${escapePbString(id)}'`).join(" || ");
  const deals = await pbList<DealRecord>("deals", {
    perPage: Math.max(50, dealIds.length),
    filter: `(${dealFilter})`,
    fields: "id,reviews_publish_at",
    noStore,
  });
  const dealById = new Map(deals.items.map((d) => [d.id, d]));

  const now = Date.now();
  const publicDealIds = new Set<string>();
  for (const dealId of dealIds) {
    const reviewerCount = reviewerCountByDeal.get(dealId)?.size ?? 0;
    if (reviewerCount < 2) continue;

    const deal = dealById.get(dealId);
    if (!deal) continue;
    const publishAtRaw = deal.reviews_publish_at;
    if (!publishAtRaw) {
      // Legacy fully-reviewed deals are public.
      publicDealIds.add(dealId);
      continue;
    }
    const publishAt = parseIsoUtc(publishAtRaw);
    if (!publishAt) continue;
    if (now >= publishAt.getTime()) publicDealIds.add(dealId);
  }
  return publicDealIds;
}

export async function filterPublicReviews<T extends Pick<ReviewRecord, "deal_id" | "reviewer_id">>(
  reviews: T[],
  noStore = true,
): Promise<T[]> {
  if (reviews.length === 0) return reviews;
  const publicDealIds = await getPublicDealIdsForReviews(reviews, noStore);
  return reviews.filter((r) => typeof r.deal_id === "string" && publicDealIds.has(r.deal_id));
}
