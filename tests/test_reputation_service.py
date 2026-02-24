from datetime import datetime, timedelta, timezone

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
    r1 = await fake_pb.create_record("members", {"telegram_id": 101})
    r2 = await fake_pb.create_record("members", {"telegram_id": 102})
    r4 = await fake_pb.create_record("members", {"telegram_id": 104})
    group = await fake_pb.group_get_or_create(telegram_id=999, title="g")
    d1 = await fake_pb.deal_create(
        initiator_id=r1["id"],
        counterparty_id=r2["id"],
        group_id=group["id"],
        description="d1",
    )
    d2 = await fake_pb.deal_create(
        initiator_id=r1["id"],
        counterparty_id=r4["id"],
        group_id=group["id"],
        description="d2",
    )
    published = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    await fake_pb.update_record("deals", d1["id"], {"reviews_publish_at": published})
    await fake_pb.update_record("deals", d2["id"], {"reviews_publish_at": published})

    # d1 is fully reviewed (2 reviewers), and r1 reviews this member twice across deals.
    await fake_pb.review_create(deal_id=d1["id"], reviewer_id=r1["id"], reviewee_id=member["id"], rating=5)
    await fake_pb.review_create(deal_id=d1["id"], reviewer_id=r2["id"], reviewee_id=member["id"], rating=3)

    # d2 is also fully reviewed, with r1 again reviewing the same member.
    await fake_pb.review_create(deal_id=d2["id"], reviewer_id=r1["id"], reviewee_id=member["id"], rating=1)
    await fake_pb.review_create(deal_id=d2["id"], reviewer_id=r4["id"], reviewee_id=member["id"], rating=5)

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


@pytest.mark.asyncio
async def test_calculate_reputation_excludes_pre_publish_window(fake_pb) -> None:
    rep = ReputationService(pb=fake_pb)
    member = await fake_pb.create_record("members", {"telegram_id": 1})
    r1 = await fake_pb.create_record("members", {"telegram_id": 101})
    r2 = await fake_pb.create_record("members", {"telegram_id": 102})
    group = await fake_pb.group_get_or_create(telegram_id=999, title="g")
    deal = await fake_pb.deal_create(
        initiator_id=r1["id"],
        counterparty_id=r2["id"],
        group_id=group["id"],
        description="windowed",
    )
    await fake_pb.update_record(
        "deals",
        deal["id"],
        {"reviews_publish_at": (datetime.now(timezone.utc) + timedelta(minutes=20)).isoformat()},
    )
    await fake_pb.review_create(deal_id=deal["id"], reviewer_id=r1["id"], reviewee_id=member["id"], rating=5)
    await fake_pb.review_create(deal_id=deal["id"], reviewer_id=r2["id"], reviewee_id=member["id"], rating=3)

    stats = await rep.calculate_reputation(member["id"])
    assert stats == {"verified_deals": 0, "avg_rating": 0.0, "total_reviews": 0}


def test_compute_credit_limit_defaults() -> None:
    rep = ReputationService(pb=None)
    assert rep.compute_credit_limit(verified_deals=0) >= 0
    assert rep.compute_credit_limit(verified_deals=2) > rep.compute_credit_limit(verified_deals=1)
