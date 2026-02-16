from __future__ import annotations

from typing import Any

import httpx

from commontrust_credit_bot.config import credit_settings


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class CommonTrustApiClient:
    def __init__(self, base_url: str | None = None, token: str | None = None):
        self.base_url = (base_url or credit_settings.commontrust_api_base_url).rstrip("/")
        self.token = token or credit_settings.commontrust_api_token
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=20.0)
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    async def _request(self, method: str, path: str, json_body: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        r = await self.client.request(method, url, json=json_body, headers=self._headers())
        if r.status_code >= 400:
            detail = ""
            try:
                detail = (r.json() or {}).get("detail") or r.text
            except Exception:
                detail = r.text
            raise ApiError(r.status_code, detail)
        if r.status_code == 204:
            return {}
        return r.json()

    async def upsert_member(self, telegram_user_id: int, username: str | None, display_name: str | None) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/identity/members/upsert",
            {"telegram_user_id": telegram_user_id, "username": username, "display_name": display_name},
        )

    async def member_by_username(self, username: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/identity/members/by_username/{username.lstrip('@')}")

    async def enable_credit(self, telegram_chat_id: int, group_title: str | None, currency_name: str, currency_symbol: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/v1/ledger/groups/{telegram_chat_id}/enable",
            {"group_title": group_title, "currency_name": currency_name, "currency_symbol": currency_symbol},
        )

    async def balance(self, telegram_chat_id: int, telegram_user_id: int) -> dict[str, Any]:
        return await self._request(
            "GET", f"/v1/ledger/groups/{telegram_chat_id}/accounts/{telegram_user_id}/balance"
        )

    async def pay(
        self,
        telegram_chat_id: int,
        payer_telegram_user_id: int,
        payee_telegram_user_id: int,
        amount: int,
        description: str | None,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/v1/ledger/groups/{telegram_chat_id}/payments",
            {
                "payer_telegram_user_id": payer_telegram_user_id,
                "payee_telegram_user_id": payee_telegram_user_id,
                "amount": amount,
                "description": description,
                "idempotency_key": idempotency_key,
            },
        )

    async def transactions(self, telegram_chat_id: int, telegram_user_id: int, limit: int = 20) -> dict[str, Any]:
        return await self._request(
            "GET", f"/v1/ledger/groups/{telegram_chat_id}/accounts/{telegram_user_id}/transactions?limit={limit}"
        )

    async def set_credit_limit(self, telegram_chat_id: int, telegram_user_id: int, credit_limit: int) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/v1/ledger/groups/{telegram_chat_id}/accounts/{telegram_user_id}",
            {"credit_limit": credit_limit},
        )

    async def verify_zero_sum(self, telegram_chat_id: int) -> dict[str, Any]:
        return await self._request("GET", f"/v1/ledger/groups/{telegram_chat_id}/verify_zero_sum")

    async def set_remote_ledger(self, telegram_chat_id: int, base_url: str, token: str) -> dict[str, Any]:
        return await self._request(
            "PUT",
            f"/v1/hub/groups/{telegram_chat_id}/ledger_remote",
            {"base_url": base_url, "token": token},
        )

    async def clear_remote_ledger(self, telegram_chat_id: int) -> dict[str, Any]:
        return await self._request("DELETE", f"/v1/hub/groups/{telegram_chat_id}/ledger_remote")


api_client = CommonTrustApiClient()

