from __future__ import annotations

from collections.abc import Iterable

from commontrust_api.config import api_settings


def _aggregate_ratings_by_reviewer(reviews: Iterable[dict]) -> dict[str, float]:
    # Prevent review farming: multiple reviews from the same reviewer count as one "vote".
    buckets: dict[str, list[int]] = {}
    for r in reviews:
        reviewer_id = r.get("reviewer_id")
        rating = r.get("rating")
        if not isinstance(reviewer_id, str) or not isinstance(rating, int):
            continue
        buckets.setdefault(reviewer_id, []).append(rating)

    out: dict[str, float] = {}
    for reviewer_id, rs in buckets.items():
        if not rs:
            continue
        out[reviewer_id] = sum(rs) / len(rs)
    return out


async def _deal_is_fully_reviewed(pb: object, deal_id: str) -> bool:
    # Only expose reviews once both parties have reviewed.
    try:
        result = await pb.list_records("reviews", filter=f'deal_id="{deal_id}"', per_page=200)
    except TypeError:
        result = await pb.list_records("reviews", filter=f'deal_id="{deal_id}"')

    items = result.get("items", []) if isinstance(result, dict) else []
    reviewer_ids = {r.get("reviewer_id") for r in items if r.get("reviewer_id")}
    return len(reviewer_ids) >= 2


def _visible_reviews(pb: object, reviews: Iterable[dict], fully_reviewed_deal_ids: set[str]) -> list[dict]:
    out: list[dict] = []
    for r in reviews:
        deal_id = r.get("deal_id")
        if isinstance(deal_id, str) and deal_id in fully_reviewed_deal_ids:
            out.append(r)
    return out


class ReputationService:
    def __init__(self, pb: object):
        self.pb = pb

    def compute_credit_limit(self, verified_deals: int, base_limit: int | None = None) -> int:
        base = base_limit if base_limit is not None else api_settings.credit_base_limit
        return base + (verified_deals * api_settings.credit_per_deal)

    async def calculate_reputation(self, member_id: str) -> dict[str, object]:
        reviews = await self.pb.reviews_for_member(member_id)
        if not reviews:
            await self.pb.reputation_update(member_id, 0, 0.0)
            return {"verified_deals": 0, "avg_rating": 0.0, "total_reviews": 0}

        deal_ids = {r.get("deal_id") for r in reviews if isinstance(r.get("deal_id"), str)}
        fully_reviewed: set[str] = set()
        for deal_id in deal_ids:
            if await _deal_is_fully_reviewed(self.pb, deal_id):
                fully_reviewed.add(deal_id)

        visible = _visible_reviews(self.pb, reviews, fully_reviewed)
        if not visible:
            await self.pb.reputation_update(member_id, 0, 0.0)
            return {"verified_deals": 0, "avg_rating": 0.0, "total_reviews": 0}

        by_reviewer = _aggregate_ratings_by_reviewer(visible)
        if not by_reviewer:
            await self.pb.reputation_update(member_id, 0, 0.0)
            return {"verified_deals": 0, "avg_rating": 0.0, "total_reviews": 0}

        avg_rating = sum(by_reviewer.values()) / len(by_reviewer)
        verified_deals = len({r.get("deal_id") for r in visible if r.get("deal_id")})
        await self.pb.reputation_update(member_id, verified_deals, avg_rating)

        return {
            "verified_deals": verified_deals,
            "avg_rating": round(avg_rating, 2),
            "total_reviews": len(by_reviewer),
        }

    async def get_reputation(self, member_id: str) -> dict[str, object]:
        return await self.calculate_reputation(member_id)

