from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from commontrust_api.config import api_settings
from commontrust_api.hub.crypto import encrypt_token


router = APIRouter(prefix="/v1/hub", tags=["hub"])


class LedgerRemoteIn(BaseModel):
    base_url: str = Field(..., min_length=1)
    token: str = Field(..., min_length=1)


class LedgerRemoteOut(BaseModel):
    base_url: str


def _validate_base_url(url: str) -> str:
    u = url.strip().rstrip("/")
    parsed = urlparse(u)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=400, detail="base_url must be an http(s) URL")
    return u


@router.put("/groups/{telegram_chat_id}/ledger_remote", response_model=LedgerRemoteOut)
async def set_ledger_remote(req: Request, telegram_chat_id: int, payload: LedgerRemoteIn) -> LedgerRemoteOut:
    if api_settings.ledger_mode != "hub":
        raise HTTPException(status_code=400, detail="Hub mode is not enabled (LEDGER_MODE=hub)")
    if not api_settings.hub_remote_token_encryption_key:
        raise HTTPException(
            status_code=500,
            detail="Hub encryption key missing (HUB_REMOTE_TOKEN_ENCRYPTION_KEY)",
        )

    pb = req.app.state.pb
    base_url = _validate_base_url(payload.base_url)
    token_enc = encrypt_token(api_settings.hub_remote_token_encryption_key, payload.token.strip())
    await pb.ledger_remote_upsert(telegram_chat_id=telegram_chat_id, base_url=base_url, token_encrypted=token_enc)
    return LedgerRemoteOut(base_url=base_url)


@router.get("/groups/{telegram_chat_id}/ledger_remote", response_model=LedgerRemoteOut)
async def get_ledger_remote(req: Request, telegram_chat_id: int) -> LedgerRemoteOut:
    if api_settings.ledger_mode != "hub":
        raise HTTPException(status_code=400, detail="Hub mode is not enabled (LEDGER_MODE=hub)")
    pb = req.app.state.pb
    rec = await pb.ledger_remote_get(telegram_chat_id)
    if not rec:
        raise HTTPException(status_code=404, detail="No remote ledger configured")
    return LedgerRemoteOut(base_url=rec.get("base_url"))


@router.delete("/groups/{telegram_chat_id}/ledger_remote")
async def delete_ledger_remote(req: Request, telegram_chat_id: int) -> dict[str, str]:
    if api_settings.ledger_mode != "hub":
        raise HTTPException(status_code=400, detail="Hub mode is not enabled (LEDGER_MODE=hub)")
    pb = req.app.state.pb
    await pb.ledger_remote_delete(telegram_chat_id)
    return {"status": "deleted"}

