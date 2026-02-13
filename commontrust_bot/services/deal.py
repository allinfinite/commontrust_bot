from datetime import datetime
from enum import Enum

from aiogram import logger

from commontrust_bot.pocketbase_client import PocketBaseError, pb_client
from commontrust_bot.services.reputation import reputation_service


class DealStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


class DealService:
    def __init__(self):
        self.pb = pb_client

    async def create_deal(
        self,
        initiator_telegram_id: int,
        counterparty_telegram_id: int,
        group_telegram_id: int,
        description: str,
        initiator_offer: str | None = None,
        counterparty_offer: str | None = None,
    ) -> dict:
        initiator = await reputation_service.get_or_create_member(initiator_telegram_id)
        counterparty = await reputation_service.get_or_create_member(counterparty_telegram_id)
        
        group = await self.pb.group_get_or_create(group_telegram_id, "")

        sanction = await self.pb.sanction_get_active(counterparty, group.get("id"))
        if sanction:
            raise ValueError(f"Counterparty has active sanction: {sanction.get('type')}")

        deal = await self.pb.deal_create(
            initiator_id=initiator.get("id"),
            counterparty_id=counterparty.get("id"),
            group_id=group.get("id"),
            description=description,
            initiator_offer=initiator_offer,
            counterparty_offer=counterparty_offer,
        )

        return {
            "deal": deal,
            "initiator": initiator,
            "counterparty": counterparty,
            "group": group,
        }

    async def get_deal(self, deal_id: str) -> dict | None:
        return await self.pb.deal_get(deal_id)

    async def confirm_deal(self, deal_id: str, confirmer_telegram_id: int) -> dict:
        deal = await self.get_deal(deal_id)
        if not deal:
            raise ValueError("Deal not found")

        if deal.get("status") != DealStatus.PENDING.value:
            raise ValueError(f"Deal is not pending. Current status: {deal.get('status')}")

        confirmer = await reputation_service.get_member(confirmer_telegram_id)
        if not confirmer:
            raise ValueError("Confirmer not found")

        if confirmer.get("id") != deal.get("counterparty_id"):
            raise ValueError("Only the counterparty can confirm the deal")

        updated_deal = await self.pb.deal_update_status(deal_id, DealStatus.CONFIRMED.value)
        
        return {
            "deal": updated_deal,
            "confirmed_by": confirmer,
            "confirmed_at": datetime.now().isoformat(),
        }

    async def start_deal(self, deal_id: str) -> dict:
        deal = await self.get_deal(deal_id)
        if not deal:
            raise ValueError("Deal not found")

        if deal.get("status") != DealStatus.CONFIRMED.value:
            raise ValueError(f"Deal must be confirmed first. Current status: {deal.get('status')}")

        return await self.pb.deal_update_status(deal_id, DealStatus.IN_PROGRESS.value)

    async def complete_deal(
        self,
        deal_id: str,
        completer_telegram_id: int,
        outcome: str = "success",
    ) -> dict:
        deal = await self.get_deal(deal_id)
        if not deal:
            raise ValueError("Deal not found")

        if deal.get("status") not in [DealStatus.CONFIRMED.value, DealStatus.IN_PROGRESS.value]:
            raise ValueError(f"Deal cannot be completed. Current status: {deal.get('status')}")

        completer = await reputation_service.get_member(completer_telegram_id)
        if not completer:
            raise ValueError("Completer not found")

        if completer.get("id") not in [deal.get("initiator_id"), deal.get("counterparty_id")]:
            raise ValueError("Only deal participants can complete the deal")

        status = DealStatus.COMPLETED.value if outcome == "success" else DealStatus.DISPUTED.value
        updated_deal = await self.pb.deal_update_status(deal_id, status)

        return {
            "deal": updated_deal,
            "completed_by": completer,
            "outcome": outcome,
            "completed_at": datetime.now().isoformat(),
        }

    async def cancel_deal(self, deal_id: str, canceller_telegram_id: int, reason: str | None = None) -> dict:
        deal = await self.get_deal(deal_id)
        if not deal:
            raise ValueError("Deal not found")

        if deal.get("status") == DealStatus.COMPLETED.value:
            raise ValueError("Cannot cancel a completed deal")

        canceller = await reputation_service.get_member(canceller_telegram_id)
        if not canceller:
            raise ValueError("Canceller not found")

        if canceller.get("id") not in [deal.get("initiator_id"), deal.get("counterparty_id")]:
            raise ValueError("Only deal participants can cancel the deal")

        updated_deal = await self.pb.deal_update_status(deal_id, DealStatus.CANCELLED.value)
        
        return {
            "deal": updated_deal,
            "cancelled_by": canceller,
            "reason": reason,
            "cancelled_at": datetime.now().isoformat(),
        }

    async def create_review(
        self,
        deal_id: str,
        reviewer_telegram_id: int,
        rating: int,
        comment: str | None = None,
        outcome: str = "positive",
    ) -> dict:
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")

        deal = await self.get_deal(deal_id)
        if not deal:
            raise ValueError("Deal not found")

        if deal.get("status") != DealStatus.COMPLETED.value:
            raise ValueError("Can only review completed deals")

        reviewer = await reputation_service.get_member(reviewer_telegram_id)
        if not reviewer:
            raise ValueError("Reviewer not found")

        reviewer_id = reviewer.get("id")
        initiator_id = deal.get("initiator_id")
        counterparty_id = deal.get("counterparty_id")

        if reviewer_id not in [initiator_id, counterparty_id]:
            raise ValueError("Only deal participants can review")

        reviewee_id = counterparty_id if reviewer_id == initiator_id else initiator_id

        existing_reviews = await self.pb.list_records(
            "reviews", filter=f'deal_id="{deal_id}" && reviewer_id="{reviewer_id}"'
        )
        if existing_reviews.get("items"):
            raise ValueError("You have already reviewed this deal")

        review = await self.pb.review_create(
            deal_id=deal_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            rating=rating,
            comment=comment,
            outcome=outcome,
        )

        await reputation_service.calculate_reputation(reviewee_id)

        return {
            "review": review,
            "reviewer": reviewer,
            "deal": deal,
        }

    async def get_deal_reviews(self, deal_id: str) -> list[dict]:
        result = await self.pb.list_records("reviews", filter=f'deal_id="{deal_id}"')
        return result.get("items", [])

    async def get_pending_deals_for_user(self, telegram_id: int) -> list[dict]:
        member = await reputation_service.get_member(telegram_id)
        if not member:
            return []

        member_id = member.get("id")
        filter_str = f'(initiator_id="{member_id}" || counterparty_id="{member_id}") && status="pending"'
        result = await self.pb.list_records("deals", filter=filter_str, sort="-created")
        return result.get("items", [])

    async def get_active_deals_for_user(self, telegram_id: int) -> list[dict]:
        member = await reputation_service.get_member(telegram_id)
        if not member:
            return []

        member_id = member.get("id")
        filter_str = f'(initiator_id="{member_id}" || counterparty_id="{member_id}") && (status="confirmed" || status="in_progress")'
        result = await self.pb.list_records("deals", filter=filter_str, sort="-created")
        return result.get("items", [])


deal_service = DealService()
