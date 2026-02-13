from aiogram import logger

from commontrust_bot.config import settings
from commontrust_bot.pocketbase_client import pb_client


class ReputationService:
    def __init__(self):
        self.pb = pb_client

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

        total_rating = sum(r.get("rating", 0) for r in reviews)
        avg_rating = total_rating / len(reviews)
        verified_deals = len(set(r.get("deal_id") for r in reviews))

        await self.pb.reputation_update(member_id, verified_deals, avg_rating)

        return {
            "verified_deals": verified_deals,
            "avg_rating": round(avg_rating, 2),
            "total_reviews": len(reviews),
        }

    async def get_reputation(self, member_id: str) -> dict | None:
        rep = await self.pb.reputation_get(member_id)
        if not rep:
            return await self.calculate_reputation(member_id)
        return rep

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
        result = await self.pb.list_records("deals", per_page=limit, filter=filter_str, sort="-created")
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
