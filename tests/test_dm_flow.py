import pytest

from commontrust_bot.handlers import dm as dm_handlers
from aiogram.dispatcher.event.bases import SkipHandler
from commontrust_bot.services.deal import DealService
from commontrust_bot.services.reputation import ReputationService
from tests.fake_pocketbase import FakePocketBase
from tests.fake_telegram import FakeChat, FakeMessage, FakeUser


class _FakeBot:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def get_me(self):
        class _Me:
            username = "testbot"

        return _Me()

    async def send_message(self, chat_id: int, text: str, **kwargs):
        self.sent.append((chat_id, text))


@pytest.mark.asyncio
async def test_newdeal_creates_invite_link(monkeypatch) -> None:
    pb = FakePocketBase()
    rep = ReputationService(pb=pb)
    deals = DealService(pb=pb, reputation=rep)
    monkeypatch.setattr(dm_handlers, "deal_service", deals)

    msg = FakeMessage(
        text="/newdeal test",
        from_user=FakeUser(1, "u1", "U1"),
        chat=FakeChat(1, "private"),
    )
    msg.bot = _FakeBot()  # type: ignore[attr-defined]

    await dm_handlers.cmd_newdeal(msg)  # type: ignore[arg-type]
    assert "https://t.me/testbot?start=deal_" in msg.answers[-1]["text"]


@pytest.mark.asyncio
async def test_start_deal_claims_and_notifies_initiator(monkeypatch) -> None:
    pb = FakePocketBase()
    rep = ReputationService(pb=pb)
    deals = DealService(pb=pb, reputation=rep)
    monkeypatch.setattr(dm_handlers, "deal_service", deals)

    created = await deals.create_invite_deal(initiator_telegram_id=1, description="x")
    deal_id = created["deal"]["id"]

    msg = FakeMessage(
        text=f"/start deal_{deal_id}",
        from_user=FakeUser(2, "u2", "U2"),
        chat=FakeChat(2, "private"),
    )
    msg.bot = _FakeBot()  # type: ignore[attr-defined]

    await dm_handlers.cmd_start_deeplink(msg)  # type: ignore[arg-type]
    assert "Deal accepted and confirmed" in msg.answers[-1]["text"]
    # initiator was notified
    assert any(chat_id == 1 for chat_id, _ in msg.bot.sent)  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_start_without_payload_skips(monkeypatch) -> None:
    # DM router should not swallow /start without a payload.
    msg = FakeMessage(text="/start", from_user=FakeUser(1), chat=FakeChat(1, "private"))
    msg.bot = _FakeBot()  # type: ignore[attr-defined]
    with pytest.raises(SkipHandler):
        await dm_handlers.cmd_start_deeplink(msg)  # type: ignore[arg-type]
