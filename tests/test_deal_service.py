import pytest
from datetime import datetime, timedelta, timezone

from commontrust_bot.services.deal import DealService, DealStatus
from commontrust_bot.services.reputation import ReputationService


@pytest.mark.asyncio
async def test_deal_lifecycle_happy_path(fake_pb) -> None:
    rep = ReputationService(pb=fake_pb)
    deals = DealService(pb=fake_pb, reputation=rep)

    created = await deals.create_deal(
        initiator_telegram_id=1,
        counterparty_telegram_id=2,
        group_telegram_id=100,
        description="Test deal",
    )
    deal = created["deal"]
    assert deal["status"] == DealStatus.PENDING.value

    pending_for_initiator = await deals.get_pending_deals_for_user(1)
    assert [d["id"] for d in pending_for_initiator] == [deal["id"]]

    confirmed = await deals.confirm_deal(deal["id"], confirmer_telegram_id=2)
    assert confirmed["deal"]["status"] == DealStatus.CONFIRMED.value

    active_for_initiator = await deals.get_active_deals_for_user(1)
    assert [d["id"] for d in active_for_initiator] == [deal["id"]]

    completed = await deals.complete_deal(deal["id"], completer_telegram_id=1)
    assert completed["deal"]["status"] == DealStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_confirm_only_counterparty(fake_pb) -> None:
    rep = ReputationService(pb=fake_pb)
    deals = DealService(pb=fake_pb, reputation=rep)

    created = await deals.create_deal(1, 2, 100, "x")
    deal_id = created["deal"]["id"]

    with pytest.raises(ValueError, match="Only the counterparty"):
        await deals.confirm_deal(deal_id, confirmer_telegram_id=1)


@pytest.mark.asyncio
async def test_review_window_and_publish_gating(fake_pb) -> None:
    rep = ReputationService(pb=fake_pb)
    deals = DealService(pb=fake_pb, reputation=rep)

    created = await deals.create_deal(1, 2, 100, "x")
    deal_id = created["deal"]["id"]

    await deals.confirm_deal(deal_id, confirmer_telegram_id=2)
    await deals.complete_deal(deal_id, completer_telegram_id=1)

    # First review should be "invisible" until the other party also reviews.
    review_result = await deals.create_review(deal_id, reviewer_telegram_id=1, rating=5, comment="great")
    assert review_result["review"]["rating"] == 5
    assert review_result["deal_fully_reviewed"] is False

    counterparty = await rep.get_member(telegram_id=2)
    assert counterparty is not None
    stats_after_one = await rep.get_reputation(counterparty["id"])
    assert stats_after_one == {"verified_deals": 0, "avg_rating": 0.0, "total_reviews": 0}

    # Second review starts the publish window; reviews are still hidden/publicly gated.
    second = await deals.create_review(deal_id, reviewer_telegram_id=2, rating=4)
    assert second["deal_fully_reviewed"] is True
    assert second["deal_is_public"] is False
    assert isinstance(second["reviews_publish_at"], str)
    assert isinstance(second["seconds_until_lock"], int)
    assert second["seconds_until_lock"] > 0

    stats_after_two = await rep.get_reputation(counterparty["id"])
    assert stats_after_two["verified_deals"] == 0
    assert stats_after_two["avg_rating"] == 0.0
    assert stats_after_two["total_reviews"] == 0

    edited = await deals.create_review(deal_id, reviewer_telegram_id=1, rating=3, comment="updated")
    assert edited["review_updated"] is True
    assert edited["review_created"] is False
    assert edited["deal_fully_reviewed"] is True
    assert edited["deal_is_public"] is False
    assert edited["review"]["rating"] == 3
    assert edited["review"]["comment"] == "updated"

    # After publish time passes, ratings should become visible in reputation.
    await fake_pb.update_record(
        "deals",
        deal_id,
        {"reviews_publish_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()},
    )
    stats_after_publish = await rep.get_reputation(counterparty["id"])
    assert stats_after_publish["verified_deals"] == 1
    assert stats_after_publish["avg_rating"] == 3.0
    assert stats_after_publish["total_reviews"] == 1


@pytest.mark.asyncio
async def test_review_window_single_reset_then_lock(fake_pb) -> None:
    rep = ReputationService(pb=fake_pb)
    deals = DealService(pb=fake_pb, reputation=rep)

    created = await deals.create_deal(1, 2, 100, "x")
    deal_id = created["deal"]["id"]
    await deals.confirm_deal(deal_id, confirmer_telegram_id=2)
    await deals.complete_deal(deal_id, completer_telegram_id=1)
    await deals.create_review(deal_id, reviewer_telegram_id=1, rating=5)
    await deals.create_review(deal_id, reviewer_telegram_id=2, rating=4)
    await fake_pb.update_record(
        "deals",
        deal_id,
        {"reviews_publish_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()},
    )
    await fake_pb.update_record(
        "deals",
        deal_id,
        {"reviews_publish_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()},
    )

    # Force a very short remaining window, then edit to consume one-time extension.
    short_publish_at = datetime.now(timezone.utc) + timedelta(seconds=30)
    await fake_pb.update_record(
        "deals",
        deal_id,
        {"reviews_publish_at": short_publish_at.isoformat(), "reviews_window_resets_used": 0},
    )
    first_edit = await deals.create_review(deal_id, reviewer_telegram_id=1, rating=2)
    first_after = await fake_pb.get_record("deals", deal_id)
    first_publish = datetime.fromisoformat(first_after["reviews_publish_at"].replace("Z", "+00:00"))
    assert first_after.get("reviews_window_resets_used") == 1
    assert first_publish > short_publish_at
    assert first_edit["review"]["rating"] == 2

    # A second edit does not extend again.
    second_edit = await deals.create_review(deal_id, reviewer_telegram_id=1, rating=1)
    second_after = await fake_pb.get_record("deals", deal_id)
    assert second_after.get("reviews_window_resets_used") == 1
    assert second_after["reviews_publish_at"] == first_after["reviews_publish_at"]
    assert second_edit["review"]["rating"] == 1

    # After lock time passes, edits are blocked.
    await fake_pb.update_record(
        "deals",
        deal_id,
        {"reviews_publish_at": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()},
    )
    with pytest.raises(ValueError, match="locked"):
        await deals.create_review(deal_id, reviewer_telegram_id=1, rating=5)


@pytest.mark.asyncio
async def test_legacy_fully_reviewed_reviews_are_public_and_locked(fake_pb) -> None:
    rep = ReputationService(pb=fake_pb)
    deals = DealService(pb=fake_pb, reputation=rep)

    created = await deals.create_deal(1, 2, 100, "x")
    deal_id = created["deal"]["id"]
    await deals.confirm_deal(deal_id, confirmer_telegram_id=2)
    await deals.complete_deal(deal_id, completer_telegram_id=1)

    m1 = await rep.get_or_create_member(1)
    m2 = await rep.get_or_create_member(2)
    await fake_pb.review_create(deal_id=deal_id, reviewer_id=m1["id"], reviewee_id=m2["id"], rating=5)
    await fake_pb.review_create(deal_id=deal_id, reviewer_id=m2["id"], reviewee_id=m1["id"], rating=4)

    visible = await deals.get_deal_reviews(deal_id)
    assert len(visible) == 2

    with pytest.raises(ValueError, match="locked"):
        await deals.create_review(deal_id, reviewer_telegram_id=1, rating=3)


@pytest.mark.asyncio
async def test_sanction_blocks_deal_creation(fake_pb) -> None:
    rep = ReputationService(pb=fake_pb)
    deals = DealService(pb=fake_pb, reputation=rep)

    # Create member + group records so we can attach a sanction.
    counterparty = await rep.get_or_create_member(telegram_id=2)
    group = await fake_pb.group_get_or_create(telegram_id=100, title="g")
    await fake_pb.sanction_create(
        member_id=counterparty["id"],
        group_id=group["id"],
        sanction_type="ban",
        reason="test",
    )

    with pytest.raises(ValueError, match="active sanction"):
        await deals.create_deal(initiator_telegram_id=1, counterparty_telegram_id=2, group_telegram_id=100, description="x")


@pytest.mark.asyncio
async def test_get_deal_reviews_handles_relation_list_shape(fake_pb) -> None:
    rep = ReputationService(pb=fake_pb)
    deals = DealService(pb=fake_pb, reputation=rep)

    created = await deals.create_deal(1, 2, 100, "x")
    deal_id = created["deal"]["id"]
    await deals.confirm_deal(deal_id, confirmer_telegram_id=2)
    await deals.complete_deal(deal_id, completer_telegram_id=1)
    await deals.create_review(deal_id, reviewer_telegram_id=1, rating=5)
    await deals.create_review(deal_id, reviewer_telegram_id=2, rating=4)
    await fake_pb.update_record(
        "deals",
        deal_id,
        {"reviews_publish_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()},
    )

    # Simulate PB relation values coming back as one-item arrays.
    deal = await deals.get_deal(deal_id)
    assert deal is not None
    deal["initiator_id"] = [deal["initiator_id"]]
    deal["counterparty_id"] = [deal["counterparty_id"]]

    all_reviews = await fake_pb.list_records("reviews", filter=f'deal_id="{deal_id}"')
    for r in all_reviews.get("items", []):
        r["reviewer_id"] = [r["reviewer_id"]]

    visible = await deals.get_deal_reviews(deal_id)
    assert len(visible) == 2
