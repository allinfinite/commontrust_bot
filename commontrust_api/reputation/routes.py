from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from commontrust_api.reputation.service import ReputationService


router = APIRouter(prefix="/v1/reputation", tags=["reputation"])


class ReputationOut(BaseModel):
    verified_deals: int
    avg_rating: float
    total_reviews: int
    computed_credit_limit: int


@router.get("/users/{telegram_user_id}", response_model=ReputationOut)
async def get_reputation(req: Request, telegram_user_id: int) -> ReputationOut:
    pb = req.app.state.pb
    rep = ReputationService(pb=pb)
    member = await pb.member_get_or_create(telegram_user_id)
    if not member or not member.get("id"):
        raise HTTPException(status_code=404, detail="Member not found")
    result = await rep.get_reputation(member["id"])
    return ReputationOut(
        verified_deals=result["verified_deals"],
        avg_rating=result["avg_rating"],
        total_reviews=result["total_reviews"],
        computed_credit_limit=rep.compute_credit_limit(result["verified_deals"]),
    )

