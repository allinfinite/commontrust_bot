from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any


def _now_iso() -> str:
    # Deterministic enough for tests without pulling in datetime/timezones.
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _eval_filter(record: dict[str, Any], filter_str: str | None) -> bool:
    if not filter_str:
        return True

    # PocketBase filter language is fairly rich; for this repo we only need
    # equality checks combined with && / || and parentheses.
    expr = filter_str
    expr = expr.replace("&&", " and ").replace("||", " or ")

    # Strings: foo="bar"
    expr = re.sub(
        r'(\b[a-zA-Z_]\w*\b)\s*=\s*"([^"]*)"',
        lambda m: f'record.get("{m.group(1)}") == "{m.group(2)}"',
        expr,
    )
    # Booleans: foo=true/false
    expr = re.sub(
        r"(\b[a-zA-Z_]\w*\b)\s*=\s*(true|false)\b",
        lambda m: f'record.get("{m.group(1)}") == {m.group(2).title()}',
        expr,
        flags=re.IGNORECASE,
    )
    # Ints: foo=123
    expr = re.sub(
        r"(\b[a-zA-Z_]\w*\b)\s*=\s*(\d+)\b",
        lambda m: f'record.get("{m.group(1)}") == {int(m.group(2))}',
        expr,
    )

    return bool(eval(expr, {"__builtins__": {}}, {"record": record}))


@dataclass
class FakePocketBase:
    data: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)
    _seq: int = 0

    def _next_id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}_{self._seq}"

    async def list_records(
        self,
        collection: str,
        page: int = 1,
        per_page: int = 50,
        filter: str | None = None,
        sort: str | None = None,
    ) -> dict[str, Any]:
        items = list(self.data.get(collection, {}).values())
        items = [r for r in items if _eval_filter(r, filter)]

        if sort:
            reverse = sort.startswith("-")
            key = sort[1:] if reverse else sort
            items.sort(key=lambda r: r.get(key) or "", reverse=reverse)

        # Very small paging support for callers that request per_page limits.
        start = max(0, (page - 1) * per_page)
        end = start + per_page
        return {"page": page, "perPage": per_page, "items": items[start:end], "totalItems": len(items)}

    async def get_record(self, collection: str, record_id: str) -> dict[str, Any]:
        rec = self.data.get(collection, {}).get(record_id)
        if not rec:
            raise KeyError(f"not found: {collection}/{record_id}")
        return rec

    async def create_record(self, collection: str, data: dict[str, Any]) -> dict[str, Any]:
        self.data.setdefault(collection, {})
        record_id = data.get("id") or self._next_id(collection)
        rec = {"id": record_id, "created": _now_iso(), **data}
        self.data[collection][record_id] = rec
        return rec

    async def update_record(self, collection: str, record_id: str, data: dict[str, Any]) -> dict[str, Any]:
        rec = await self.get_record(collection, record_id)
        rec.update(data)
        return rec

    async def delete_record(self, collection: str, record_id: str) -> None:
        self.data.get(collection, {}).pop(record_id, None)

    async def get_first(self, collection: str, filter: str) -> dict[str, Any] | None:
        result = await self.list_records(collection, page=1, per_page=1, filter=filter)
        items = result.get("items", [])
        return items[0] if items else None

    async def authenticate(self) -> None:  # pragma: no cover
        return None

    async def close(self) -> None:  # pragma: no cover
        return None

    # Convenience wrappers used by services/handlers.
    async def member_get_or_create(
        self, telegram_id: int, username: str | None = None, display_name: str | None = None
    ) -> dict[str, Any]:
        existing = await self.get_first("members", f"telegram_id={telegram_id}")
        if existing:
            updates: dict[str, Any] = {}
            if username and username != existing.get("username"):
                updates["username"] = username
            if display_name and display_name != existing.get("display_name"):
                updates["display_name"] = display_name
            if updates:
                return await self.update_record("members", existing["id"], updates)
            return existing

        return await self.create_record(
            "members",
            {
                "telegram_id": telegram_id,
                "username": username,
                "display_name": display_name,
                "joined_at": _now_iso(),
                "verified": False,
            },
        )

    async def member_get(self, telegram_id: int) -> dict[str, Any] | None:
        return await self.get_first("members", f"telegram_id={telegram_id}")

    async def member_get_by_username(self, username: str) -> dict[str, Any] | None:
        username_norm = username.strip().lstrip("@").lower()
        if not username_norm:
            return None
        return await self.get_first("members", f'username="{username_norm}"')

    async def group_get_or_create(self, telegram_id: int, title: str, mc_enabled: bool = False) -> dict[str, Any]:
        existing = await self.get_first("groups", f"telegram_id={telegram_id}")
        if existing:
            # Mimic PocketBase behavior: updating the title is optional; keep existing.
            if mc_enabled and not existing.get("mc_enabled"):
                await self.update_record("groups", existing["id"], {"mc_enabled": True})
            return existing
        return await self.create_record(
            "groups", {"telegram_id": telegram_id, "title": title, "mc_enabled": mc_enabled}
        )

    async def group_get(self, telegram_id: int) -> dict[str, Any] | None:
        return await self.get_first("groups", f"telegram_id={telegram_id}")

    async def deal_create(
        self,
        initiator_id: str,
        counterparty_id: str,
        group_id: str,
        description: str,
        initiator_offer: str | None = None,
        counterparty_offer: str | None = None,
    ) -> dict[str, Any]:
        return await self.create_record(
            "deals",
            {
                "initiator_id": initiator_id,
                "counterparty_id": counterparty_id,
                "group_id": group_id,
                "description": description,
                "initiator_offer": initiator_offer,
                "counterparty_offer": counterparty_offer,
                "status": "pending",
            },
        )

    async def deal_get(self, deal_id: str) -> dict[str, Any] | None:
        try:
            return await self.get_record("deals", deal_id)
        except KeyError:
            return None

    async def deal_update_status(self, deal_id: str, status: str) -> dict[str, Any]:
        return await self.update_record("deals", deal_id, {"status": status})

    async def review_create(
        self,
        deal_id: str,
        reviewer_id: str,
        reviewee_id: str,
        rating: int,
        comment: str | None = None,
        outcome: str = "positive",
        reviewer_username: str | None = None,
        reviewee_username: str | None = None,
    ) -> dict[str, Any]:
        return await self.create_record(
            "reviews",
            {
                "deal_id": deal_id,
                "reviewer_id": reviewer_id,
                "reviewee_id": reviewee_id,
                "rating": rating,
                "comment": comment,
                "outcome": outcome,
                "reviewer_username": reviewer_username,
                "reviewee_username": reviewee_username,
            },
        )

    async def reviews_for_member(self, member_id: str) -> list[dict[str, Any]]:
        result = await self.list_records("reviews", filter=f'reviewee_id="{member_id}"')
        return result.get("items", [])

    async def reputation_get(self, member_id: str) -> dict[str, Any] | None:
        return await self.get_first("reputation", f'member_id="{member_id}"')

    async def reputation_update(self, member_id: str, verified_deals: int, avg_rating: float) -> dict[str, Any]:
        existing = await self.reputation_get(member_id)
        if existing:
            return await self.update_record(
                "reputation",
                existing["id"],
                {"verified_deals": verified_deals, "avg_rating": avg_rating, "total_reviews": None},
            )
        return await self.create_record(
            "reputation",
            {"member_id": member_id, "verified_deals": verified_deals, "avg_rating": avg_rating},
        )

    async def mc_group_get(self, group_id: str) -> dict[str, Any] | None:
        return await self.get_first("mc_groups", f'group_id="{group_id}"')

    async def mc_group_create(self, group_id: str, currency_name: str = "Credit", currency_symbol: str = "Cr"):
        return await self.create_record(
            "mc_groups", {"group_id": group_id, "currency_name": currency_name, "currency_symbol": currency_symbol}
        )

    async def mc_group_update_currency(self, mc_group_id: str, currency_name: str, currency_symbol: str) -> dict[str, Any]:
        return await self.update_record(
            "mc_groups",
            mc_group_id,
            {"currency_name": currency_name, "currency_symbol": currency_symbol},
        )

    async def mc_account_get(self, mc_group_id: str, member_id: str) -> dict[str, Any] | None:
        return await self.get_first(
            "mc_accounts", f'mc_group_id="{mc_group_id}" && member_id="{member_id}"'
        )

    async def mc_account_create(self, mc_group_id: str, member_id: str, credit_limit: int = 0) -> dict[str, Any]:
        return await self.create_record(
            "mc_accounts",
            {"mc_group_id": mc_group_id, "member_id": member_id, "balance": 0, "credit_limit": credit_limit},
        )

    async def mc_account_update(self, account_id: str, balance: int, credit_limit: int | None = None) -> dict[str, Any]:
        data: dict[str, Any] = {"balance": balance}
        if credit_limit is not None:
            data["credit_limit"] = credit_limit
        return await self.update_record("mc_accounts", account_id, data)

    async def mc_transaction_get_by_idempotency(
        self, mc_group_id: str, idempotency_key: str
    ) -> dict[str, Any] | None:
        if not idempotency_key:
            return None
        return await self.get_first(
            "mc_transactions", f'mc_group_id="{mc_group_id}" && idempotency_key="{idempotency_key}"'
        )

    async def mc_transaction_create(
        self,
        mc_group_id: str,
        payer_id: str,
        payee_id: str,
        amount: int,
        description: str | None = None,
        idempotency_key: str | None = None,
    ):
        return await self.create_record(
            "mc_transactions",
            {
                "mc_group_id": mc_group_id,
                "payer_id": payer_id,
                "payee_id": payee_id,
                "amount": amount,
                "description": description,
                "idempotency_key": idempotency_key,
            },
        )

    async def mc_entry_create(self, transaction_id: str, account_id: str, amount: int, balance_after: int):
        return await self.create_record(
            "mc_entries",
            {"transaction_id": transaction_id, "account_id": account_id, "amount": amount, "balance_after": balance_after},
        )

    async def sanction_create(
        self,
        member_id: str,
        group_id: str | None,
        sanction_type: str,
        reason: str,
        expires_at: str | None = None,
    ) -> dict[str, Any]:
        return await self.create_record(
            "sanctions",
            {"member_id": member_id, "group_id": group_id, "type": sanction_type, "reason": reason, "expires_at": expires_at, "is_active": True},
        )

    async def sanction_get_active(self, member_id: str, group_id: str | None = None) -> dict[str, Any] | None:
        filter_str = f'member_id="{member_id}" && is_active=true'
        if group_id:
            filter_str += f' && group_id="{group_id}"'
        return await self.get_first("sanctions", filter_str)

    async def sanction_deactivate(self, sanction_id: str) -> dict[str, Any]:
        return await self.update_record("sanctions", sanction_id, {"is_active": False})
