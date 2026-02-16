import pytest

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
async def test_review_updates_reputation_and_blocks_duplicates(fake_pb) -> None:
    rep = ReputationService(pb=fake_pb)
    deals = DealService(pb=fake_pb, reputation=rep)

    created = await deals.create_deal(1, 2, 100, "x")
    deal_id = created["deal"]["id"]

    await deals.confirm_deal(deal_id, confirmer_telegram_id=2)
    await deals.complete_deal(deal_id, completer_telegram_id=1)

    # First review should be "invisible" until the other party also reviews.
    review_result = await deals.create_review(deal_id, reviewer_telegram_id=1, rating=5, comment="great")
    assert review_result["review"]["rating"] == 5

    counterparty = await rep.get_member(telegram_id=2)
    assert counterparty is not None
    stats_after_one = await rep.get_reputation(counterparty["id"])
    assert stats_after_one == {"verified_deals": 0, "avg_rating": 0.0, "total_reviews": 0}

    # The second party reviews; now both reviews become visible and count.
    await deals.create_review(deal_id, reviewer_telegram_id=2, rating=4)

    stats_after_two = await rep.get_reputation(counterparty["id"])
    assert stats_after_two["verified_deals"] == 1
    assert stats_after_two["avg_rating"] == 5.0
    assert stats_after_two["total_reviews"] == 1

    with pytest.raises(ValueError, match="already reviewed"):
        await deals.create_review(deal_id, reviewer_telegram_id=1, rating=5)


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
