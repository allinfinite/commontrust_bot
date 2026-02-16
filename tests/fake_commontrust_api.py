from __future__ import annotations

from typing import Any

from commontrust_api.ledger.service import InsufficientCreditError, MutualCreditService
from commontrust_api.reputation.service import ReputationService
from commontrust_credit_bot.api_client import ApiError


class FakeCommonTrustApiClient:
    """
    In-process stand-in for the CommonTrust HTTP API.

    It uses FakePocketBase storage and the same service layer used by the API.
    """

    def __init__(self, pb: Any):
        self.pb = pb
        self.rep = ReputationService(pb=pb)
        self.mc = MutualCreditService(pb=pb, reputation=self.rep)

    async def upsert_member(self, telegram_user_id: int, username: str | None, display_name: str | None) -> dict[str, Any]:
        rec = await self.pb.member_get_or_create(telegram_user_id, username=username, display_name=display_name)
        return {
            "telegram_user_id": rec.get("telegram_id"),
            "username": rec.get("username"),
            "display_name": rec.get("display_name"),
        }

    async def member_by_username(self, username: str) -> dict[str, Any]:
        rec = await self.pb.member_get_by_username(username)
        if not rec:
            raise ApiError(404, "Member not found")
        return {
            "telegram_user_id": rec.get("telegram_id"),
            "username": rec.get("username"),
            "display_name": rec.get("display_name"),
        }

    async def enable_credit(self, telegram_chat_id: int, group_title: str | None, currency_name: str, currency_symbol: str) -> dict[str, Any]:
        group = await self.pb.group_get_or_create(telegram_chat_id, group_title or "Group", mc_enabled=True)
        mc_group = await self.mc.get_or_create_mc_group(group["id"], currency_name, currency_symbol)
        await self.pb.update_record("groups", group["id"], {"mc_enabled": True})
        return {"mc_group_id": mc_group["id"], "currency_name": currency_name, "currency_symbol": currency_symbol}

    async def _mc_group_id(self, telegram_chat_id: int) -> str:
        group = await self.pb.group_get(telegram_chat_id)
        if not group or not group.get("mc_enabled"):
            raise ApiError(400, "Mutual credit is not enabled for this group")
        mc_group = await self.pb.mc_group_get(group["id"])
        if not mc_group:
            raise ApiError(400, "Mutual credit group not found")
        return mc_group["id"]

    async def balance(self, telegram_chat_id: int, telegram_user_id: int) -> dict[str, Any]:
        mc_group_id = await self._mc_group_id(telegram_chat_id)
        member = await self.pb.member_get_or_create(telegram_user_id)
        info = await self.mc.get_account_balance(mc_group_id, member["id"])
        return info

    async def pay(
        self,
        telegram_chat_id: int,
        payer_telegram_user_id: int,
        payee_telegram_user_id: int,
        amount: int,
        description: str | None,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        mc_group_id = await self._mc_group_id(telegram_chat_id)
        payer = await self.pb.member_get_or_create(payer_telegram_user_id)
        payee = await self.pb.member_get_or_create(payee_telegram_user_id)
        try:
            res = await self.mc.create_payment(
                mc_group_id,
                payer["id"],
                payee["id"],
                amount=amount,
                description=description,
                idempotency_key=idempotency_key,
            )
        except InsufficientCreditError as e:
            raise ApiError(400, str(e)) from e
        except ValueError as e:
            raise ApiError(400, str(e)) from e

        mc_group = await self.pb.get_record("mc_groups", mc_group_id)
        return {
            "transaction_id": res["transaction"]["id"],
            "new_payer_balance": res["new_payer_balance"],
            "new_payee_balance": res["new_payee_balance"],
            "symbol": mc_group.get("currency_symbol", "Cr"),
        }

    async def set_credit_limit(self, telegram_chat_id: int, telegram_user_id: int, credit_limit: int) -> dict[str, Any]:
        mc_group_id = await self._mc_group_id(telegram_chat_id)
        member = await self.pb.member_get_or_create(telegram_user_id)
        updated = await self.mc.update_credit_limit(mc_group_id, member["id"], credit_limit)
        return {"account_id": updated["id"], "credit_limit": updated["credit_limit"]}

    async def verify_zero_sum(self, telegram_chat_id: int) -> dict[str, Any]:
        mc_group_id = await self._mc_group_id(telegram_chat_id)
        return await self.mc.verify_zero_sum(mc_group_id)

    async def transactions(self, telegram_chat_id: int, telegram_user_id: int, limit: int = 20) -> dict[str, Any]:
        mc_group_id = await self._mc_group_id(telegram_chat_id)
        member = await self.pb.member_get_or_create(telegram_user_id)
        items = await self.mc.get_transaction_history(mc_group_id, member["id"], limit=limit)
        out: list[dict[str, Any]] = []
        # Provide the same shape the real API returns (direction + other).
        for tx in items:
            payer = await self.pb.get_record("members", tx["payer_id"])
            payee = await self.pb.get_record("members", tx["payee_id"])
            is_sender = int(payer.get("telegram_id", 0) or 0) == telegram_user_id
            other = payee if is_sender else payer
            out.append(
                {
                    "amount": int(tx.get("amount", 0) or 0),
                    "description": tx.get("description"),
                    "created": tx.get("created"),
                    "direction": "sent" if is_sender else "received",
                    "other_telegram_user_id": int(other.get("telegram_id", 0) or 0),
                    "other_username": other.get("username"),
                    "other_display_name": other.get("display_name"),
                }
            )
        return {"items": out}

    async def set_remote_ledger(self, telegram_chat_id: int, base_url: str, token: str) -> dict[str, Any]:
        return {"base_url": base_url}

    async def clear_remote_ledger(self, telegram_chat_id: int) -> dict[str, Any]:
        return {"status": "deleted"}
