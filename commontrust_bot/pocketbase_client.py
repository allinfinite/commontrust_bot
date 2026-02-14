from datetime import datetime
import logging
from typing import Any

import httpx

from commontrust_bot.config import settings

logger = logging.getLogger(__name__)


class PocketBaseError(Exception):
    pass


class PocketBaseClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.pocketbase_url
        self.token: str | None = None
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def authenticate(self) -> None:
        # Preferred: use a long-lived admin/superuser token (API key) from env.
        if settings.pocketbase_admin_token and settings.pocketbase_admin_token.strip():
            self.token = settings.pocketbase_admin_token.strip()
            return

        if not settings.pocketbase_admin_email or not settings.pocketbase_admin_password:
            raise PocketBaseError(
                "Missing PocketBase credentials. Set POCKETBASE_ADMIN_TOKEN (preferred) "
                "or POCKETBASE_ADMIN_EMAIL and POCKETBASE_ADMIN_PASSWORD."
            )

        url = f"{self.base_url}/api/admins/auth-with-password"
        response = await self.client.post(
            url,
            json={
                "identity": settings.pocketbase_admin_email,
                "password": settings.pocketbase_admin_password,
            },
        )
        if response.status_code != 200:
            raise PocketBaseError(f"Authentication failed: {response.text}")
        data = response.json()
        self.token = data.get("token")

    def _headers(self) -> dict[str, str]:
        if not self.token:
            raise PocketBaseError("Not authenticated")
        return {"Authorization": self.token}

    async def _request(
        self, method: str, path: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = self._headers()

        if method == "GET":
            response = await self.client.get(url, headers=headers, params=data)
        elif method == "POST":
            response = await self.client.post(url, headers=headers, json=data)
        elif method == "PATCH":
            response = await self.client.patch(url, headers=headers, json=data)
        elif method == "DELETE":
            response = await self.client.delete(url, headers=headers)
        else:
            raise PocketBaseError(f"Unsupported method: {method}")

        if response.status_code >= 400:
            logger.error(f"PocketBase error: {response.status_code} - {response.text}")
            raise PocketBaseError(f"Request failed: {response.status_code} - {response.text}")

        if response.status_code == 204:
            return {}
        return response.json()

    async def list_records(
        self,
        collection: str,
        page: int = 1,
        per_page: int = 50,
        filter: str | None = None,
        sort: str | None = None,
    ) -> dict[str, Any]:
        params = {"page": page, "perPage": per_page}
        if filter:
            params["filter"] = filter
        if sort:
            params["sort"] = sort
        return await self._request("GET", f"/api/collections/{collection}/records", params)

    async def get_record(self, collection: str, record_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/collections/{collection}/records/{record_id}")

    async def create_record(self, collection: str, data: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/api/collections/{collection}/records", data)

    async def update_record(
        self, collection: str, record_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request(
            "PATCH", f"/api/collections/{collection}/records/{record_id}", data
        )

    async def delete_record(self, collection: str, record_id: str) -> None:
        await self._request("DELETE", f"/api/collections/{collection}/records/{record_id}")

    async def get_first(self, collection: str, filter: str) -> dict[str, Any] | None:
        result = await self.list_records(collection, page=1, per_page=1, filter=filter)
        items = result.get("items", [])
        return items[0] if items else None

    async def member_get_or_create(
        self, telegram_id: int, username: str | None = None, display_name: str | None = None
    ) -> dict[str, Any]:
        username_norm = username.strip().lstrip("@").lower() if username and username.strip() else None
        existing = await self.get_first("members", f"telegram_id={telegram_id}")
        if existing:
            update_data = {}
            if username_norm and username_norm != (existing.get("username") or ""):
                update_data["username"] = username_norm
            if display_name and display_name != existing.get("display_name"):
                update_data["display_name"] = display_name
            if update_data:
                return await self.update_record("members", existing["id"], update_data)
            return existing

        return await self.create_record(
            "members",
            {
                "telegram_id": telegram_id,
                "username": username_norm,
                "display_name": display_name,
                "joined_at": datetime.now().isoformat(),
            },
        )

    async def member_get(self, telegram_id: int) -> dict[str, Any] | None:
        return await self.get_first("members", f"telegram_id={telegram_id}")

    async def group_get_or_create(
        self, telegram_id: int, title: str, mc_enabled: bool = False
    ) -> dict[str, Any]:
        existing = await self.get_first("groups", f"telegram_id={telegram_id}")
        if existing:
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
        return await self.get_record("deals", deal_id)

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
                "reviewer_username": reviewer_username.strip().lstrip("@").lower()
                if reviewer_username and reviewer_username.strip()
                else None,
                "reviewee_username": reviewee_username.strip().lstrip("@").lower()
                if reviewee_username and reviewee_username.strip()
                else None,
            },
        )

    async def reviews_for_member(self, member_id: str) -> list[dict[str, Any]]:
        result = await self.list_records("reviews", filter=f'reviewee_id="{member_id}"')
        return result.get("items", [])

    async def reputation_get(self, member_id: str) -> dict[str, Any] | None:
        return await self.get_first("reputation", f'member_id="{member_id}"')

    async def reputation_update(
        self, member_id: str, verified_deals: int, avg_rating: float
    ) -> dict[str, Any]:
        existing = await self.reputation_get(member_id)
        if existing:
            return await self.update_record(
                "reputation", existing["id"], {"verified_deals": verified_deals, "avg_rating": avg_rating}
            )
        return await self.create_record(
            "reputation", {"member_id": member_id, "verified_deals": verified_deals, "avg_rating": avg_rating}
        )

    async def mc_group_get(self, group_id: str) -> dict[str, Any] | None:
        return await self.get_first("mc_groups", f'group_id="{group_id}"')

    async def mc_group_create(
        self, group_id: str, currency_name: str = "Credit", currency_symbol: str = "Cr"
    ) -> dict[str, Any]:
        return await self.create_record(
            "mc_groups",
            {"group_id": group_id, "currency_name": currency_name, "currency_symbol": currency_symbol},
        )

    async def mc_account_get(self, mc_group_id: str, member_id: str) -> dict[str, Any] | None:
        return await self.get_first(
            "mc_accounts", f'mc_group_id="{mc_group_id}" && member_id="{member_id}"'
        )

    async def mc_account_create(
        self, mc_group_id: str, member_id: str, credit_limit: int = 0
    ) -> dict[str, Any]:
        return await self.create_record(
            "mc_accounts",
            {"mc_group_id": mc_group_id, "member_id": member_id, "balance": 0, "credit_limit": credit_limit},
        )

    async def mc_account_update(
        self, account_id: str, balance: int, credit_limit: int | None = None
    ) -> dict[str, Any]:
        data = {"balance": balance}
        if credit_limit is not None:
            data["credit_limit"] = credit_limit
        return await self.update_record("mc_accounts", account_id, data)

    async def mc_transaction_create(
        self, mc_group_id: str, payer_id: str, payee_id: str, amount: int, description: str | None = None
    ) -> dict[str, Any]:
        return await self.create_record(
            "mc_transactions",
            {
                "mc_group_id": mc_group_id,
                "payer_id": payer_id,
                "payee_id": payee_id,
                "amount": amount,
                "description": description,
            },
        )

    async def mc_entry_create(
        self, transaction_id: str, account_id: str, amount: int, balance_after: int
    ) -> dict[str, Any]:
        return await self.create_record(
            "mc_entries",
            {
                "transaction_id": transaction_id,
                "account_id": account_id,
                "amount": amount,
                "balance_after": balance_after,
            },
        )

    async def mc_entries_for_transaction(self, transaction_id: str) -> list[dict[str, Any]]:
        result = await self.list_records("mc_entries", filter=f'transaction_id="{transaction_id}"')
        return result.get("items", [])

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
            {
                "member_id": member_id,
                "group_id": group_id,
                "type": sanction_type,
                "reason": reason,
                "expires_at": expires_at,
                "is_active": True,
            },
        )

    async def sanction_get_active(self, member_id: str, group_id: str | None = None) -> dict[str, Any] | None:
        filter_str = f'member_id="{member_id}" && is_active=true'
        if group_id:
            filter_str += f' && group_id="{group_id}"'
        return await self.get_first("sanctions", filter_str)

    async def sanction_deactivate(self, sanction_id: str) -> dict[str, Any]:
        return await self.update_record("sanctions", sanction_id, {"is_active": False})


pb_client = PocketBaseClient()
