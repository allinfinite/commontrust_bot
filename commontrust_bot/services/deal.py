import asyncio
from datetime import datetime
from enum import Enum

from commontrust_bot.pocketbase_client import pb_client
from commontrust_bot.services.reputation import reputation_service


class DealStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


class DealService:
    def __init__(self, pb=None, reputation=None):
        # Allow injection for tests; default to global singletons.
        self.pb = pb or pb_client
        self.reputation = reputation or reputation_service

    async def create_deal(
        self,
        initiator_telegram_id: int,
        counterparty_telegram_id: int,
        group_telegram_id: int,
        description: str,
        initiator_offer: str | None = None,
        counterparty_offer: str | None = None,
    ) -> dict:
        initiator = await self.reputation.get_or_create_member(initiator_telegram_id)
        counterparty = await self.reputation.get_or_create_member(counterparty_telegram_id)
        
        group = await self.pb.group_get_or_create(group_telegram_id, "")

        sanction = await self.pb.sanction_get_active(counterparty.get("id"), group.get("id"))
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

    async def _get_member_telegram_id(self, member_record_id: str) -> int:
        rec = await self.pb.get_record("members", member_record_id)
        telegram_id = rec.get("telegram_id")
        if not isinstance(telegram_id, int):
            raise ValueError("Member telegram_id missing/invalid")
        return telegram_id

    async def get_deal_participant_telegram_ids(self, deal_id: str) -> tuple[int, int]:
        deal = await self.get_deal(deal_id)
        if not deal:
            raise ValueError("Deal not found")
        initiator_id = deal.get("initiator_id")
        counterparty_id = deal.get("counterparty_id")
        if not isinstance(initiator_id, str) or not isinstance(counterparty_id, str):
            raise ValueError("Deal participants missing")
        return (await self._get_member_telegram_id(initiator_id), await self._get_member_telegram_id(counterparty_id))

    async def create_invite_deal(
        self,
        initiator_telegram_id: int,
        description: str,
        initiator_offer: str | None = None,
        counterparty_offer: str | None = None,
    ) -> dict:
        # DM-first flow: create an "unclaimed" deal invite by setting counterparty_id=initiator_id.
        # The first non-initiator who opens the invite deep-link will claim it.
        initiator = await self.reputation.get_or_create_member(initiator_telegram_id)
        # PocketBase can treat `0` as "blank" for required number fields in some setups.
        # Use a stable sentinel value that won't collide with real Telegram group IDs.
        group = await self.pb.group_get_or_create(-1, "Direct Messages")

        initiator_id = initiator.get("id")
        if not isinstance(initiator_id, str):
            raise ValueError("Initiator missing id")

        deal = await self.pb.deal_create(
            initiator_id=initiator_id,
            counterparty_id=initiator_id,
            group_id=group.get("id"),
            description=description,
            initiator_offer=initiator_offer,
            counterparty_offer=counterparty_offer,
        )

        return {"deal": deal, "initiator": initiator, "group": group}

    async def accept_invite_deal(self, deal_id: str, accepter_telegram_id: int) -> dict:
        deal = await self.get_deal(deal_id)
        if not deal:
            raise ValueError("Deal not found")

        if deal.get("status") != DealStatus.PENDING.value:
            raise ValueError("This deal invite is no longer pending")

        initiator_id = deal.get("initiator_id")
        counterparty_id = deal.get("counterparty_id")
        if not isinstance(initiator_id, str) or not isinstance(counterparty_id, str):
            raise ValueError("Deal participants missing")

        accepter = await self.reputation.get_or_create_member(accepter_telegram_id)
        accepter_id = accepter.get("id")
        if not isinstance(accepter_id, str):
            raise ValueError("Accepter missing id")

        if accepter_id == initiator_id:
            raise ValueError("You cannot accept your own invite")

        # Unclaimed invite: counterparty_id == initiator_id
        if counterparty_id == initiator_id:
            updated = await self.pb.update_record(
                "deals",
                deal_id,
                {"counterparty_id": accepter_id, "status": DealStatus.CONFIRMED.value},
            )
            return {"deal": updated, "initiator_id": initiator_id, "counterparty_id": accepter_id}

        # Already claimed: allow the same counterparty to re-open without error.
        if counterparty_id == accepter_id:
            if deal.get("status") != DealStatus.CONFIRMED.value:
                updated = await self.pb.deal_update_status(deal_id, DealStatus.CONFIRMED.value)
            else:
                updated = deal
            return {"deal": updated, "initiator_id": initiator_id, "counterparty_id": accepter_id}

        raise ValueError("This invite has already been accepted by someone else")

    async def confirm_deal(self, deal_id: str, confirmer_telegram_id: int) -> dict:
        deal = await self.get_deal(deal_id)
        if not deal:
            raise ValueError("Deal not found")

        if deal.get("status") != DealStatus.PENDING.value:
            raise ValueError(f"Deal is not pending. Current status: {deal.get('status')}")

        # DM invite deals are created "unclaimed" (counterparty_id == initiator_id).
        if deal.get("counterparty_id") == deal.get("initiator_id"):
            raise ValueError("This deal invite has not been accepted yet. Send the invite link to the other party.")

        confirmer = await self.reputation.get_member(confirmer_telegram_id)
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

        completer = await self.reputation.get_member(completer_telegram_id)
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

        canceller = await self.reputation.get_member(canceller_telegram_id)
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

        reviewer = await self.reputation.get_member(reviewer_telegram_id)
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

        reviewee = await self.pb.get_record("members", reviewee_id)
        review = await self.pb.review_create(
            deal_id=deal_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            rating=rating,
            comment=comment,
            outcome=outcome,
            reviewer_username=reviewer.get("username"),
            reviewee_username=reviewee.get("username") if isinstance(reviewee, dict) else None,
        )

        # Recompute for both participants:
        # When the second party submits their review, the deal becomes "fully reviewed"
        # and the other party's incoming review becomes visible for reputation purposes.
        await asyncio.gather(
            self.reputation.calculate_reputation(initiator_id),
            self.reputation.calculate_reputation(counterparty_id),
        )

        return {
            "review": review,
            "reviewer": reviewer,
            "reviewee": reviewee,
            "deal": deal,
        }

    async def get_deal_reviews(self, deal_id: str) -> list[dict]:
        result = await self.pb.list_records("reviews", filter=f'deal_id="{deal_id}"')
        items = result.get("items", [])

        # Hide reviews until both parties have left a review.
        reviewer_ids = {r.get("reviewer_id") for r in items if r.get("reviewer_id")}
        if len(reviewer_ids) < 2:
            return []
        return items

    async def get_pending_deals_for_user(self, telegram_id: int) -> list[dict]:
        member = await self.reputation.get_member(telegram_id)
        if not member:
            return []

        member_id = member.get("id")
        filter_str = f'(initiator_id="{member_id}" || counterparty_id="{member_id}") && status="pending"'
        result = await self.pb.list_records("deals", filter=filter_str, sort="-created_at")
        return result.get("items", [])

    async def get_active_deals_for_user(self, telegram_id: int) -> list[dict]:
        member = await self.reputation.get_member(telegram_id)
        if not member:
            return []

        member_id = member.get("id")
        filter_str = f'(initiator_id="{member_id}" || counterparty_id="{member_id}") && (status="confirmed" || status="in_progress")'
        result = await self.pb.list_records("deals", filter=filter_str, sort="-created_at")
        return result.get("items", [])


deal_service = DealService()
