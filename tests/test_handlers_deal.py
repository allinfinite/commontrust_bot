import pytest

from commontrust_bot.handlers import deal as deal_handlers
from commontrust_bot.services.deal import DealService
from commontrust_bot.services.reputation import ReputationService
from tests.fake_pocketbase import FakePocketBase
from tests.fake_telegram import FakeChat, FakeMessage, FakeUser


@pytest.mark.asyncio
async def test_cmd_deal_requires_reply(monkeypatch) -> None:
    pb = FakePocketBase()
    rep = ReputationService(pb=pb)
    deals = DealService(pb=pb, reputation=rep)
    monkeypatch.setattr(deal_handlers, "deal_service", deals)

    msg = FakeMessage(text="/deal test", from_user=FakeUser(1), chat=FakeChat(100, "group"))
    await deal_handlers.cmd_deal(msg)  # type: ignore[arg-type]
    assert msg.answers[-1]["text"].startswith("Reply to a user's message")


@pytest.mark.asyncio
async def test_cmd_deal_happy_path(monkeypatch) -> None:
    pb = FakePocketBase()
    rep = ReputationService(pb=pb)
    deals = DealService(pb=pb, reputation=rep)
    monkeypatch.setattr(deal_handlers, "deal_service", deals)

    initiator = FakeUser(1, username="a", full_name="A")
    counterparty = FakeUser(2, username="b", full_name="B")
    replied = FakeMessage(text="hi", from_user=counterparty, chat=FakeChat(100, "group"))
    msg = FakeMessage(
        text="/deal something",
        from_user=initiator,
        chat=FakeChat(100, "group"),
        reply_to_message=replied,
    )

    await deal_handlers.cmd_deal(msg)  # type: ignore[arg-type]
    out = msg.answers[-1]["text"]
    assert "Deal created!" in out
    assert "Deal ID:" in out


@pytest.mark.asyncio
async def test_cmd_confirm_usage(monkeypatch) -> None:
    pb = FakePocketBase()
    rep = ReputationService(pb=pb)
    deals = DealService(pb=pb, reputation=rep)
    monkeypatch.setattr(deal_handlers, "deal_service", deals)

    msg = FakeMessage(text="/confirm", from_user=FakeUser(2), chat=FakeChat(100, "group"))
    await deal_handlers.cmd_confirm(msg)  # type: ignore[arg-type]
    assert msg.answers[-1]["text"].startswith("Usage: /confirm")


@pytest.mark.asyncio
async def test_cmd_confirm_complete_cancel_and_dealinfo(monkeypatch) -> None:
    pb = FakePocketBase()
    rep = ReputationService(pb=pb)
    deals = DealService(pb=pb, reputation=rep)
    monkeypatch.setattr(deal_handlers, "deal_service", deals)

    initiator = FakeUser(1, username="a", full_name="A")
    counterparty = FakeUser(2, username="b", full_name="B")
    replied = FakeMessage(text="hi", from_user=counterparty, chat=FakeChat(100, "group"))

    create = FakeMessage(
        text="/deal something",
        from_user=initiator,
        chat=FakeChat(100, "group"),
        reply_to_message=replied,
    )
    await deal_handlers.cmd_deal(create)  # type: ignore[arg-type]
    created = (await pb.list_records("deals", per_page=1)).get("items", [])[0]
    deal_id = created["id"]

    # Counterparty confirms.
    confirm = FakeMessage(text=f"/confirm {deal_id}", from_user=counterparty, chat=FakeChat(100, "group"))
    await deal_handlers.cmd_confirm(confirm)  # type: ignore[arg-type]
    assert "Deal confirmed" in confirm.answers[-1]["text"]

    # Initiator completes.
    complete = FakeMessage(text=f"/complete {deal_id}", from_user=initiator, chat=FakeChat(100, "group"))
    await deal_handlers.cmd_complete(complete)  # type: ignore[arg-type]
    assert "Deal completed" in complete.answers[-1]["text"]

    # Dealinfo should exist.
    info = FakeMessage(text=f"/dealinfo {deal_id}", from_user=initiator, chat=FakeChat(100, "group"))
    await deal_handlers.cmd_deal_info(info)  # type: ignore[arg-type]
    assert "Deal Information" in info.answers[-1]["text"]

    # Cancelling completed deal should fail.
    cancel = FakeMessage(text=f"/cancel {deal_id}", from_user=initiator, chat=FakeChat(100, "group"))
    await deal_handlers.cmd_cancel(cancel)  # type: ignore[arg-type]
    assert "Cannot cancel a completed deal" in cancel.answers[-1]["text"]


@pytest.mark.asyncio
async def test_cmd_review_usage(monkeypatch) -> None:
    pb = FakePocketBase()
    rep = ReputationService(pb=pb)
    deals = DealService(pb=pb, reputation=rep)
    monkeypatch.setattr(deal_handlers, "deal_service", deals)

    msg = FakeMessage(text="/review", from_user=FakeUser(1), chat=FakeChat(100, "group"))
    await deal_handlers.cmd_review(msg)  # type: ignore[arg-type]
    assert msg.answers[-1]["text"].startswith("Usage: /review")
