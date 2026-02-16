from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field


router = APIRouter(prefix="/v1/identity", tags=["identity"])


class MemberUpsertIn(BaseModel):
    telegram_user_id: int = Field(..., ge=1)
    username: str | None = None
    display_name: str | None = None


class MemberOut(BaseModel):
    telegram_user_id: int
    username: str | None = None
    display_name: str | None = None


@router.post("/members/upsert", response_model=MemberOut)
async def upsert_member(req: Request, payload: MemberUpsertIn) -> MemberOut:
    pb = req.app.state.pb
    rec = await pb.member_get_or_create(
        telegram_id=payload.telegram_user_id,
        username=payload.username,
        display_name=payload.display_name,
    )
    return MemberOut(
        telegram_user_id=rec.get("telegram_id") or payload.telegram_user_id,
        username=rec.get("username"),
        display_name=rec.get("display_name"),
    )


@router.get("/members/by_username/{username}", response_model=MemberOut)
async def member_by_username(req: Request, username: str) -> MemberOut:
    pb = req.app.state.pb
    rec = await pb.member_get_by_username(username)
    if not rec:
        raise HTTPException(status_code=404, detail="Member not found")
    return MemberOut(
        telegram_user_id=rec.get("telegram_id"),
        username=rec.get("username"),
        display_name=rec.get("display_name"),
    )

