import pytest

from commontrust_bot.config import settings
from commontrust_bot.handlers import admin as admin_handlers
from commontrust_bot.handlers import credit as credit_handlers
from commontrust_bot.handlers import reputation as reputation_handlers
from commontrust_bot.services.deal import DealService
from commontrust_bot.services.mutual_credit import MutualCreditService
from commontrust_bot.services.reputation import ReputationService
from tests.fake_pocketbase import FakePocketBase
from tests.fake_telegram import FakeChat, FakeMessage, FakeUser


@pytest.mark.asyncio
async def test_enable_credit_requires_admin(monkeypatch) -> None:
    pb = FakePocketBase()
    rep = ReputationService(pb=pb)
    mc = MutualCreditService(pb=pb, reputation=rep)

    monkeypatch.setattr(admin_handlers, "pb_client", pb)
    monkeypatch.setattr(admin_handlers, "mutual_credit_service", mc)
    monkeypatch.setattr(admin_handlers, "reputation_service", rep)
    monkeypatch.setattr(settings, "admin_user_ids", [999], raising=False)

    msg = FakeMessage(
        text="/enable_credit",
        from_user=FakeUser(1),
        chat=FakeChat(100, "group", "G"),
    )
    await admin_handlers.cmd_enable_credit(msg)  # type: ignore[arg-type]
    assert msg.answers[-1]["text"].startswith("Only bot admins")


@pytest.mark.asyncio
async def test_enable_credit_happy_path(monkeypatch) -> None:
    pb = FakePocketBase()
    rep = ReputationService(pb=pb)
    mc = MutualCreditService(pb=pb, reputation=rep)

    monkeypatch.setattr(admin_handlers, "pb_client", pb)
    monkeypatch.setattr(admin_handlers, "mutual_credit_service", mc)
    monkeypatch.setattr(admin_handlers, "reputation_service", rep)
    monkeypatch.setattr(settings, "admin_user_ids", [1], raising=False)

    msg = FakeMessage(
        text="/enable_credit Credits Cr",
        from_user=FakeUser(1),
        chat=FakeChat(100, "group", "G"),
    )
    await admin_handlers.cmd_enable_credit(msg)  # type: ignore[arg-type]
    assert "Mutual credit enabled" in msg.answers[-1]["text"]

    group = await pb.group_get(telegram_id=100)
    assert group is not None and group.get("mc_enabled") is True


@pytest.mark.asyncio
async def test_pay_requires_mc_enabled(monkeypatch) -> None:
    pb = FakePocketBase()
    rep = ReputationService(pb=pb)
    mc = MutualCreditService(pb=pb, reputation=rep)

    # Patch the pb_client used inside get_mc_group_for_chat (imported at runtime).
    import commontrust_bot.pocketbase_client as pb_mod

    monkeypatch.setattr(pb_mod, "pb_client", pb)
    monkeypatch.setattr(credit_handlers, "mutual_credit_service", mc)
    monkeypatch.setattr(credit_handlers, "reputation_service", rep)

    payer = FakeUser(1, username="payer", full_name="Payer")
    payee = FakeUser(2, username="payee", full_name="Payee")
    replied = FakeMessage(text="hi", from_user=payee, chat=FakeChat(100, "group"))
    msg = FakeMessage(
        text="/pay 10",
        from_user=payer,
        chat=FakeChat(100, "group"),
        reply_to_message=replied,
    )

    await credit_handlers.cmd_pay(msg)  # type: ignore[arg-type]
    assert "Mutual credit is not enabled" in msg.answers[-1]["text"]


@pytest.mark.asyncio
async def test_pay_happy_path(monkeypatch) -> None:
    pb = FakePocketBase()
    rep = ReputationService(pb=pb)
    mc = MutualCreditService(pb=pb, reputation=rep)

    import commontrust_bot.pocketbase_client as pb_mod

    monkeypatch.setattr(pb_mod, "pb_client", pb)
    monkeypatch.setattr(credit_handlers, "mutual_credit_service", mc)
    monkeypatch.setattr(credit_handlers, "reputation_service", rep)

    # Enable MC for the chat.
    group = await pb.group_get_or_create(telegram_id=100, title="G", mc_enabled=True)
    await pb.mc_group_create(group_id=group["id"], currency_name="Credit", currency_symbol="Cr")

    payer = FakeUser(1, username="payer", full_name="Payer")
    payee = FakeUser(2, username="payee", full_name="Payee")
    replied = FakeMessage(text="hi", from_user=payee, chat=FakeChat(100, "group"))
    msg = FakeMessage(
        text="/pay 10 lunch",
        from_user=payer,
        chat=FakeChat(100, "group"),
        reply_to_message=replied,
    )

    await credit_handlers.cmd_pay(msg)  # type: ignore[arg-type]
    assert "Payment successful" in msg.answers[-1]["text"]


@pytest.mark.asyncio
async def test_reputation_hidden_until_both_reviews(monkeypatch) -> None:
    pb = FakePocketBase()
    rep = ReputationService(pb=pb)
    deals = DealService(pb=pb, reputation=rep)

    monkeypatch.setattr(reputation_handlers, "reputation_service", rep)

    created = await deals.create_deal(1, 2, 100, "x")
    deal_id = created["deal"]["id"]
    await deals.confirm_deal(deal_id, confirmer_telegram_id=2)
    await deals.complete_deal(deal_id, completer_telegram_id=1)
    await deals.create_review(deal_id, reviewer_telegram_id=1, rating=5)

    # User 2 should still see 0 reviews because only 1 party reviewed.
    msg = FakeMessage(text="/reputation", from_user=FakeUser(2, username="u2", full_name="U2"), chat=FakeChat(100, "group"))
    await reputation_handlers.cmd_reputation(msg)  # type: ignore[arg-type]
    out = msg.answers[-1]["text"]
    assert "Verified Deals:</b> 0" in out
    assert "Total Reviews:</b> 0" in out


@pytest.mark.asyncio
async def test_admin_warn_mute_ban(monkeypatch) -> None:
    pb = FakePocketBase()
    rep = ReputationService(pb=pb)
    mc = MutualCreditService(pb=pb, reputation=rep)

    monkeypatch.setattr(admin_handlers, "pb_client", pb)
    monkeypatch.setattr(admin_handlers, "mutual_credit_service", mc)
    monkeypatch.setattr(admin_handlers, "reputation_service", rep)
    monkeypatch.setattr(settings, "admin_user_ids", [1], raising=False)

    admin = FakeUser(1, username="admin", full_name="Admin")
    target = FakeUser(2, username="t", full_name="Target")
    replied = FakeMessage(text="hi", from_user=target, chat=FakeChat(100, "group", "G"))

    warn = FakeMessage(
        text="/warn be nice",
        from_user=admin,
        chat=FakeChat(100, "group", "G"),
        reply_to_message=replied,
    )
    await admin_handlers.cmd_warn(warn)  # type: ignore[arg-type]
    assert "has been warned" in warn.answers[-1]["text"]

    mute = FakeMessage(
        text="/mute 1 too loud",
        from_user=admin,
        chat=FakeChat(100, "group", "G"),
        reply_to_message=replied,
    )
    await admin_handlers.cmd_mute(mute)  # type: ignore[arg-type]
    assert "has been muted" in mute.answers[-1]["text"]

    ban = FakeMessage(
        text="/ban spam",
        from_user=admin,
        chat=FakeChat(100, "group", "G"),
        reply_to_message=replied,
    )
    await admin_handlers.cmd_ban(ban)  # type: ignore[arg-type]
    assert "has been banned" in ban.answers[-1]["text"]

    sanctions = (await pb.list_records("sanctions", per_page=50)).get("items", [])
    types = {s.get("type") for s in sanctions}
    assert {"warning", "mute", "ban"} <= types


@pytest.mark.asyncio
async def test_admin_freeze_setcredit_verify_checkzero(monkeypatch) -> None:
    pb = FakePocketBase()
    rep = ReputationService(pb=pb)
    mc = MutualCreditService(pb=pb, reputation=rep)

    monkeypatch.setattr(admin_handlers, "pb_client", pb)
    monkeypatch.setattr(admin_handlers, "mutual_credit_service", mc)
    monkeypatch.setattr(admin_handlers, "reputation_service", rep)
    monkeypatch.setattr(settings, "admin_user_ids", [1], raising=False)

    admin = FakeUser(1, username="admin", full_name="Admin")
    target = FakeUser(2, username="t", full_name="Target")
    replied = FakeMessage(text="hi", from_user=target, chat=FakeChat(100, "group", "G"))

    # Enable MC + create account for target.
    group = await pb.group_get_or_create(telegram_id=100, title="G", mc_enabled=True)
    mc_group = await pb.mc_group_create(group_id=group["id"], currency_name="Credit", currency_symbol="Cr")
    target_member = await rep.get_or_create_member(target.id, target.username, target.full_name)
    account = await pb.mc_account_create(mc_group_id=mc_group["id"], member_id=target_member["id"], credit_limit=10)

    freeze = FakeMessage(
        text="/freeze too risky",
        from_user=admin,
        chat=FakeChat(100, "group", "G"),
        reply_to_message=replied,
    )
    await admin_handlers.cmd_freeze(freeze)  # type: ignore[arg-type]
    assert "has been frozen" in freeze.answers[-1]["text"]
    updated = await pb.get_record("mc_accounts", account["id"])
    assert updated["credit_limit"] == 0

    setcredit = FakeMessage(
        text="/setcredit 7",
        from_user=admin,
        chat=FakeChat(100, "group", "G"),
        reply_to_message=replied,
    )
    await admin_handlers.cmd_setcredit(setcredit)  # type: ignore[arg-type]
    assert "credit limit set to 7" in setcredit.answers[-1]["text"]
    updated2 = await pb.get_record("mc_accounts", account["id"])
    assert updated2["credit_limit"] == 7

    verify = FakeMessage(
        text="/verify",
        from_user=admin,
        chat=FakeChat(100, "group", "G"),
        reply_to_message=replied,
    )
    await admin_handlers.cmd_verify(verify)  # type: ignore[arg-type]
    assert "has been verified" in verify.answers[-1]["text"]
    member_rec = await pb.get_record("members", target_member["id"])
    assert member_rec.get("verified") is True

    # Checkzero should show invalid if sum != 0.
    # Create two accounts with non-zero balances.
    m2 = await rep.get_or_create_member(3)
    a2 = await pb.mc_account_create(mc_group_id=mc_group["id"], member_id=m2["id"], credit_limit=0)
    await pb.mc_account_update(a2["id"], balance=5)

    checkzero = FakeMessage(text="/checkzero", from_user=admin, chat=FakeChat(100, "group", "G"))
    await admin_handlers.cmd_checkzero(checkzero)  # type: ignore[arg-type]
    assert "Invalid" in checkzero.answers[-1]["text"]
