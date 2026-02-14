import logging
from collections.abc import Iterable

from commontrust_bot.config import settings
from commontrust_bot.pocketbase_client import pb_client

logger = logging.getLogger(__name__)


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
    # Only expose reviews once both parties have reviewed. For 2-party deals,
    # this means at least 2 distinct reviewers exist for that deal.
    try:
        result = await pb.list_records("reviews", filter=f'deal_id="{deal_id}"', per_page=200)
    except TypeError:
        # Some PB clients don't accept per_page keyword; fall back.
        result = await pb.list_records("reviews", filter=f'deal_id="{deal_id}"')

    items = result.get("items", []) if isinstance(result, dict) else []
    reviewer_ids = {r.get("reviewer_id") for r in items if r.get("reviewer_id")}
    return len(reviewer_ids) >= 2


def _visible_reviews(pb: object, reviews: Iterable[dict], fully_reviewed_deal_ids: set[str]) -> list[dict]:
    # Filter down to reviews whose deal has both parties' reviews submitted.
    out: list[dict] = []
    for r in reviews:
        deal_id = r.get("deal_id")
        if isinstance(deal_id, str) and deal_id in fully_reviewed_deal_ids:
            out.append(r)
    return out


class ReputationService:
    def __init__(self, pb=None):
        # Allow injection for tests; default to global singleton.
        self.pb = pb or pb_client

    async def get_or_create_member(
        self, telegram_id: int, username: str | None = None, display_name: str | None = None
    ) -> dict:
        return await self.pb.member_get_or_create(telegram_id, username, display_name)

    async def get_member(self, telegram_id: int) -> dict | None:
        return await self.pb.member_get(telegram_id)

    async def calculate_reputation(self, member_id: str) -> dict:
        reviews = await self.pb.reviews_for_member(member_id)

        if not reviews:
            return {"verified_deals": 0, "avg_rating": 0.0, "total_reviews": 0}

        deal_ids = {r.get("deal_id") for r in reviews if isinstance(r.get("deal_id"), str)}
        fully_reviewed: set[str] = set()
        for deal_id in deal_ids:
            if await _deal_is_fully_reviewed(self.pb, deal_id):
                fully_reviewed.add(deal_id)

        visible = _visible_reviews(self.pb, reviews, fully_reviewed)
        if not visible:
            return {"verified_deals": 0, "avg_rating": 0.0, "total_reviews": 0}

        # Average is computed per unique reviewer to avoid review farming between pairs.
        by_reviewer = _aggregate_ratings_by_reviewer(visible)
        if not by_reviewer:
            return {"verified_deals": 0, "avg_rating": 0.0, "total_reviews": 0}

        avg_rating = sum(by_reviewer.values()) / len(by_reviewer)
        verified_deals = len({r.get("deal_id") for r in visible if r.get("deal_id")})

        await self.pb.reputation_update(member_id, verified_deals, avg_rating)

        return {
            "verified_deals": verified_deals,
            "avg_rating": round(avg_rating, 2),
            "total_reviews": len(by_reviewer),
        }

    async def get_reputation(self, member_id: str) -> dict | None:
        # Always recompute so gating ("both parties reviewed") is enforced even if a stale
        # record exists in PocketBase.
        return await self.calculate_reputation(member_id)

    def compute_credit_limit(self, verified_deals: int, base_limit: int | None = None) -> int:
        base = base_limit or settings.credit_base_limit
        per_deal = settings.credit_per_deal
        return base + (verified_deals * per_deal)

    async def get_member_deals(
        self, member_id: str, status: str | None = None, limit: int = 10
    ) -> list[dict]:
        filter_parts = []
        filter_parts.append(f'initiator_id="{member_id}" || counterparty_id="{member_id}"')
        if status:
            filter_parts.append(f'status="{status}"')
        
        filter_str = " && ".join(filter_parts) if len(filter_parts) > 1 else filter_parts[0]
        result = await self.pb.list_records("deals", per_page=limit, filter=filter_str, sort="-created_at")
        return result.get("items", [])

    async def get_member_stats(self, member_id: str) -> dict:
        reputation = await self.get_reputation(member_id)
        deals = await self.get_member_deals(member_id, limit=100)
        
        completed_deals = [d for d in deals if d.get("status") == "completed"]
        pending_deals = [d for d in deals if d.get("status") in ("pending", "confirmed")]
        
        return {
            "reputation": reputation,
            "total_deals": len(deals),
            "completed_deals": len(completed_deals),
            "pending_deals": len(pending_deals),
            "credit_limit": self.compute_credit_limit(
                reputation.get("verified_deals", 0) if reputation else 0
            ),
        }

    async def verify_member(self, member_id: str) -> bool:
        try:
            member = await self.pb.get_record("members", member_id)
            if member:
                await self.pb.update_record("members", member_id, {"verified": True})
                return True
        except Exception as e:
            logger.error(f"Failed to verify member: {e}")
        return False


reputation_service = ReputationService()
