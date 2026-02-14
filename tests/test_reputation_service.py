import pytest

from commontrust_bot.services.reputation import ReputationService


@pytest.mark.asyncio
async def test_calculate_reputation_empty(fake_pb) -> None:
    rep = ReputationService(pb=fake_pb)
    member = await fake_pb.create_record("members", {"telegram_id": 1})

    stats = await rep.calculate_reputation(member["id"])
    assert stats == {"verified_deals": 0, "avg_rating": 0.0, "total_reviews": 0}


@pytest.mark.asyncio
async def test_calculate_reputation_unique_verified_deals(fake_pb) -> None:
    rep = ReputationService(pb=fake_pb)
    member = await fake_pb.create_record("members", {"telegram_id": 1})

    await fake_pb.review_create(deal_id="d1", reviewer_id="r1", reviewee_id=member["id"], rating=5)
    await fake_pb.review_create(deal_id="d1", reviewer_id="r2", reviewee_id=member["id"], rating=3)
    await fake_pb.review_create(deal_id="d2", reviewer_id="r3", reviewee_id=member["id"], rating=4)

    stats = await rep.calculate_reputation(member["id"])
    # Reviews only count once both parties have reviewed the deal. `d2` has only one review.
    assert stats["verified_deals"] == 1
    assert stats["avg_rating"] == 4.0
    assert stats["total_reviews"] == 2

    rep_record = await fake_pb.reputation_get(member["id"])
    assert rep_record is not None
    assert rep_record["verified_deals"] == 1
    assert rep_record["avg_rating"] == 4.0


def test_compute_credit_limit_defaults() -> None:
    rep = ReputationService(pb=None)
    assert rep.compute_credit_limit(verified_deals=0) >= 0
    assert rep.compute_credit_limit(verified_deals=2) > rep.compute_credit_limit(verified_deals=1)
