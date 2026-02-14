import pytest

from commontrust_bot.handlers import credit as credit_handlers
from commontrust_bot.handlers import reputation as reputation_handlers
from commontrust_bot.services.deal import DealService
from commontrust_bot.services.mutual_credit import MutualCreditService
from commontrust_bot.services.reputation import ReputationService
from tests.fake_pocketbase import FakePocketBase
from tests.fake_telegram import FakeChat, FakeMessage, FakeUser


@pytest.mark.asyncio
async def test_reputation_mydeals_stats_pending_active(monkeypatch) -> None:
    pb = FakePocketBase()
    rep = ReputationService(pb=pb)
    deals = DealService(pb=pb, reputation=rep)
    monkeypatch.setattr(reputation_handlers, "reputation_service", rep)
    monkeypatch.setattr(reputation_handlers, "deal_service", deals)

    # Create a pending deal for user 1.
    created = await deals.create_deal(1, 2, 100, "desc")
    deal_id = created["deal"]["id"]

    mydeals = FakeMessage(text="/mydeals", from_user=FakeUser(1, "u1", "U1"), chat=FakeChat(100, "group"))
    await reputation_handlers.cmd_mydeals(mydeals)  # type: ignore[arg-type]
    assert "Your Deals" in mydeals.answers[-1]["text"]

    stats = FakeMessage(text="/stats", from_user=FakeUser(1, "u1", "U1"), chat=FakeChat(100, "group"))
    await reputation_handlers.cmd_stats(stats)  # type: ignore[arg-type]
    assert "Total Deals" in stats.answers[-1]["text"]

    pending = FakeMessage(text="/pending", from_user=FakeUser(1, "u1", "U1"), chat=FakeChat(100, "group"))
    await reputation_handlers.cmd_pending(pending)  # type: ignore[arg-type]
    assert "Pending Deals" in pending.answers[-1]["text"]

    # Confirm makes it active.
    await deals.confirm_deal(deal_id, confirmer_telegram_id=2)
    active = FakeMessage(text="/active", from_user=FakeUser(1, "u1", "U1"), chat=FakeChat(100, "group"))
    await reputation_handlers.cmd_active(active)  # type: ignore[arg-type]
    assert "Active Deals" in active.answers[-1]["text"]


@pytest.mark.asyncio
async def test_credit_balance_and_transactions(monkeypatch) -> None:
    pb = FakePocketBase()
    rep = ReputationService(pb=pb)
    mc = MutualCreditService(pb=pb, reputation=rep)

    import commontrust_bot.pocketbase_client as pb_mod

    monkeypatch.setattr(pb_mod, "pb_client", pb)
    monkeypatch.setattr(credit_handlers, "mutual_credit_service", mc)
    monkeypatch.setattr(credit_handlers, "reputation_service", rep)

    group = await pb.group_get_or_create(telegram_id=100, title="G", mc_enabled=True)
    mc_group = await pb.mc_group_create(group_id=group["id"], currency_name="Credit", currency_symbol="Cr")

    # Create a payment so there is history.
    payer = await rep.get_or_create_member(1)
    payee = await rep.get_or_create_member(2)
    await mc.create_payment(mc_group["id"], payer["id"], payee["id"], amount=5)

    bal = FakeMessage(text="/balance", from_user=FakeUser(1, "u1", "U1"), chat=FakeChat(100, "group"))
    await credit_handlers.cmd_balance(bal)  # type: ignore[arg-type]
    assert "Balance" in bal.answers[-1]["text"]

    tx = FakeMessage(text="/transactions", from_user=FakeUser(1, "u1", "U1"), chat=FakeChat(100, "group"))
    await credit_handlers.cmd_transactions(tx)  # type: ignore[arg-type]
    assert "Recent Transactions" in tx.answers[-1]["text"]

