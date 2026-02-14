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

    # d1 is fully reviewed (2 reviewers), and r1 reviews this member twice across deals.
    await fake_pb.review_create(deal_id="d1", reviewer_id="r1", reviewee_id=member["id"], rating=5)
    await fake_pb.review_create(deal_id="d1", reviewer_id="r2", reviewee_id=member["id"], rating=3)

    # d2 is also fully reviewed, with r1 again reviewing the same member.
    await fake_pb.review_create(deal_id="d2", reviewer_id="r1", reviewee_id=member["id"], rating=1)
    await fake_pb.review_create(deal_id="d2", reviewer_id="r4", reviewee_id=member["id"], rating=5)

    stats = await rep.calculate_reputation(member["id"])
    assert stats["verified_deals"] == 2
    # Rating is aggregated per unique reviewer:
    # r1 avg = (5 + 1) / 2 = 3.0
    # r2 avg = 3.0
    # r4 avg = 5.0
    # overall = (3 + 3 + 5) / 3 = 3.666.. -> 3.67
    assert stats["avg_rating"] == 3.67
    assert stats["total_reviews"] == 3

    rep_record = await fake_pb.reputation_get(member["id"])
    assert rep_record is not None
    assert rep_record["verified_deals"] == 2
    assert rep_record["avg_rating"] == 3.6666666666666665


def test_compute_credit_limit_defaults() -> None:
    rep = ReputationService(pb=None)
    assert rep.compute_credit_limit(verified_deals=0) >= 0
    assert rep.compute_credit_limit(verified_deals=2) > rep.compute_credit_limit(verified_deals=1)
