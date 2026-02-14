import pytest
import httpx

from commontrust_bot.pocketbase_client import PocketBaseClient, PocketBaseError


@pytest.mark.asyncio
async def test_headers_requires_auth() -> None:
    pb = PocketBaseClient(base_url="http://example.invalid")
    with pytest.raises(PocketBaseError, match="Not authenticated"):
        pb._headers()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_authenticate_with_token_short_circuits(monkeypatch) -> None:
    pb = PocketBaseClient(base_url="http://example.invalid")

    from commontrust_bot import config as config_mod

    monkeypatch.setattr(config_mod.settings, "pocketbase_admin_token", "tok", raising=False)
    await pb.authenticate()
    assert pb.token == "tok"


@pytest.mark.asyncio
async def test_request_204_returns_empty_dict() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    transport = httpx.MockTransport(handler)
    pb = PocketBaseClient(base_url="http://test")
    pb.token = "t"
    pb._client = httpx.AsyncClient(transport=transport)

    out = await pb._request("DELETE", "/api/x")  # type: ignore[attr-defined]
    assert out == {}
    await pb.close()


@pytest.mark.asyncio
async def test_request_raises_on_4xx() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="bad")

    transport = httpx.MockTransport(handler)
    pb = PocketBaseClient(base_url="http://test")
    pb.token = "t"
    pb._client = httpx.AsyncClient(transport=transport)

    with pytest.raises(PocketBaseError, match="Request failed: 400"):
        await pb._request("GET", "/api/x")  # type: ignore[attr-defined]
    await pb.close()

