from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

from commontrust_api.config import api_settings
from commontrust_api.hub.crypto import decrypt_token
from commontrust_api.ledger.models import (
    BalanceOut,
    EnableLedgerIn,
    PaymentIn,
    PaymentOut,
    SetAccountIn,
    ZeroSumOut,
)
from commontrust_api.ledger.service import InsufficientCreditError, MutualCreditService
from commontrust_api.reputation.service import ReputationService


router = APIRouter(prefix="/v1/ledger", tags=["ledger"])


async def _maybe_proxy(req: Request) -> Response | None:
    if api_settings.ledger_mode != "hub":
        return None
    pb = req.app.state.pb
    # Path always contains /v1/ledger/groups/{telegram_chat_id}/...
    parts = req.url.path.split("/")
    try:
        idx = parts.index("groups")
        chat_id = int(parts[idx + 1])
    except Exception:
        return None

    remote = await pb.ledger_remote_get(chat_id)
    if not remote:
        return None

    if not api_settings.hub_remote_token_encryption_key:
        raise HTTPException(status_code=500, detail="Hub encryption key missing")

    base_url = (remote.get("base_url") or "").rstrip("/")
    token = decrypt_token(api_settings.hub_remote_token_encryption_key, remote.get("token_encrypted") or "")

    # Forward the request as-is, swapping auth header.
    url = f"{base_url}{req.url.path}"
    if req.url.query:
        url += f"?{req.url.query}"

    body: bytes = await req.body()
    headers = {"Authorization": f"Bearer {token}"}
    method = req.method.upper()

    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.request(method, url, content=body, headers=headers)

    content_type = r.headers.get("content-type", "application/json")
    return Response(content=r.content, status_code=r.status_code, media_type=content_type)


def _mc_service(req: Request) -> MutualCreditService:
    pb = req.app.state.pb
    reputation = ReputationService(pb=pb)
    return MutualCreditService(pb=pb, reputation=reputation)


async def _get_mc_group_id_or_400(pb: Any, telegram_chat_id: int) -> str:
    group = await pb.group_get(telegram_chat_id)
    if not group or not group.get("mc_enabled"):
        raise HTTPException(status_code=400, detail="Mutual credit is not enabled for this group")
    mc_group = await pb.mc_group_get(group.get("id"))
    if not mc_group:
        raise HTTPException(status_code=400, detail="Mutual credit group not found")
    return str(mc_group.get("id"))


@router.post("/groups/{telegram_chat_id}/enable")
async def enable_ledger(req: Request, telegram_chat_id: int, payload: EnableLedgerIn) -> dict[str, object]:
    proxied = await _maybe_proxy(req)
    if proxied is not None:
        return proxied  # type: ignore[return-value]

    pb = req.app.state.pb
    group = await pb.group_get_or_create(
        telegram_id=telegram_chat_id,
        title=payload.group_title or "Group",
        mc_enabled=True,
    )
    mc = _mc_service(req)
    mc_group = await mc.get_or_create_mc_group(
        group_record_id=group.get("id"),
        currency_name=payload.currency_name,
        currency_symbol=payload.currency_symbol,
    )
    await pb.update_record("groups", group.get("id"), {"mc_enabled": True})
    return {"mc_group_id": mc_group.get("id"), "currency_name": mc_group.get("currency_name"), "currency_symbol": mc_group.get("currency_symbol")}


@router.get("/groups/{telegram_chat_id}/accounts/{telegram_user_id}/balance", response_model=BalanceOut)
async def get_balance(req: Request, telegram_chat_id: int, telegram_user_id: int) -> BalanceOut:
    proxied = await _maybe_proxy(req)
    if proxied is not None:
        if proxied.status_code >= 400:
            return proxied  # type: ignore[return-value]
        return BalanceOut.model_validate_json(proxied.body)

    pb = req.app.state.pb
    mc_group_id = await _get_mc_group_id_or_400(pb, telegram_chat_id)
    member = await pb.member_get_or_create(telegram_user_id)
    mc = _mc_service(req)
    info = await mc.get_account_balance(mc_group_id, member.get("id"))
    return BalanceOut(
        balance=int(info["balance"]),
        credit_limit=int(info["credit_limit"]),
        available=int(info["available"]),
        currency=str(info["currency"]),
        symbol=str(info["symbol"]),
    )


@router.post("/groups/{telegram_chat_id}/payments", response_model=PaymentOut)
async def create_payment(req: Request, telegram_chat_id: int, payload: PaymentIn) -> PaymentOut:
    proxied = await _maybe_proxy(req)
    if proxied is not None:
        if proxied.status_code >= 400:
            return proxied  # type: ignore[return-value]
        return PaymentOut.model_validate_json(proxied.body)

    pb = req.app.state.pb
    mc_group_id = await _get_mc_group_id_or_400(pb, telegram_chat_id)
    payer = await pb.member_get_or_create(payload.payer_telegram_user_id)
    payee = await pb.member_get_or_create(payload.payee_telegram_user_id)
    mc = _mc_service(req)
    try:
        result = await mc.create_payment(
            mc_group_id=mc_group_id,
            payer_member_record_id=payer.get("id"),
            payee_member_record_id=payee.get("id"),
            amount=payload.amount,
            description=payload.description,
            idempotency_key=payload.idempotency_key,
        )
    except InsufficientCreditError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    mc_group = await pb.get_record("mc_groups", mc_group_id)
    return PaymentOut(
        transaction_id=str(result["transaction"].get("id")),
        new_payer_balance=int(result["new_payer_balance"]),
        new_payee_balance=int(result["new_payee_balance"]),
        symbol=str(mc_group.get("currency_symbol", "Cr")),
        already_applied=bool(result.get("already_applied", False)),
    )


@router.get("/groups/{telegram_chat_id}/accounts/{telegram_user_id}/transactions")
async def get_transactions(
    req: Request, telegram_chat_id: int, telegram_user_id: int, limit: int = 20
) -> dict[str, object]:
    proxied = await _maybe_proxy(req)
    if proxied is not None:
        return proxied  # type: ignore[return-value]

    pb = req.app.state.pb
    mc_group_id = await _get_mc_group_id_or_400(pb, telegram_chat_id)
    member = await pb.member_get_or_create(telegram_user_id)
    mc = _mc_service(req)
    items = await mc.get_transaction_history(mc_group_id, member.get("id"), limit=limit)

    member_cache: dict[str, dict[str, Any]] = {}

    async def _member(rec_id: str) -> dict[str, Any]:
        if rec_id not in member_cache:
            member_cache[rec_id] = await pb.get_record("members", rec_id)
        return member_cache[rec_id]

    out_items: list[dict[str, Any]] = []
    for tx in items:
        payer_id = tx.get("payer_id")
        payee_id = tx.get("payee_id")
        if not isinstance(payer_id, str) or not isinstance(payee_id, str):
            continue
        payer = await _member(payer_id)
        payee = await _member(payee_id)

        payer_tid = int(payer.get("telegram_id", 0) or 0)
        payee_tid = int(payee.get("telegram_id", 0) or 0)
        is_sender = payer_tid == telegram_user_id
        other = payee if is_sender else payer

        out_items.append(
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

    return {"items": out_items}


@router.patch("/groups/{telegram_chat_id}/accounts/{telegram_user_id}")
async def set_account(req: Request, telegram_chat_id: int, telegram_user_id: int, payload: SetAccountIn) -> dict[str, object]:
    proxied = await _maybe_proxy(req)
    if proxied is not None:
        return proxied  # type: ignore[return-value]

    pb = req.app.state.pb
    mc_group_id = await _get_mc_group_id_or_400(pb, telegram_chat_id)
    member = await pb.member_get_or_create(telegram_user_id)
    mc = _mc_service(req)
    updated = await mc.update_credit_limit(mc_group_id, member.get("id"), payload.credit_limit)
    return {"account_id": updated.get("id"), "credit_limit": updated.get("credit_limit")}


@router.get("/groups/{telegram_chat_id}/verify_zero_sum", response_model=ZeroSumOut)
async def verify_zero_sum(req: Request, telegram_chat_id: int) -> ZeroSumOut:
    proxied = await _maybe_proxy(req)
    if proxied is not None:
        if proxied.status_code >= 400:
            return proxied  # type: ignore[return-value]
        return ZeroSumOut.model_validate_json(proxied.body)

    pb = req.app.state.pb
    mc_group_id = await _get_mc_group_id_or_400(pb, telegram_chat_id)
    mc = _mc_service(req)
    result = await mc.verify_zero_sum(mc_group_id)
    return ZeroSumOut(
        is_zero_sum=bool(result["is_zero_sum"]),
        total_balance=int(result["total_balance"]),
        account_count=int(result["account_count"]),
    )
