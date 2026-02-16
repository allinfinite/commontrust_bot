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
        self._message_id_counter = 1000

    async def get_me(self):
        class _Me:
            username = "testbot"

        return _Me()

    async def send_message(self, chat_id: int, text: str, **kwargs):
        self.sent.append((chat_id, text))
        # Return a fake message object with message_id
        msg = FakeMessage(text=text, from_user=FakeUser(0), chat=FakeChat(chat_id, "private"))
        msg.message_id = self._message_id_counter
        self._message_id_counter += 1
        return msg


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
    assert msg.answers[-1].get("reply_markup") is not None


@pytest.mark.asyncio
async def test_start_without_payload_skips(monkeypatch) -> None:
    # DM router should not swallow /start without a payload.
    msg = FakeMessage(text="/start", from_user=FakeUser(1), chat=FakeChat(1, "private"))
    msg.bot = _FakeBot()  # type: ignore[attr-defined]
    with pytest.raises(SkipHandler):
        await dm_handlers.cmd_start_deeplink(msg)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_next_message_after_review_notification_submits_response(monkeypatch) -> None:
    """Test that the next message a user sends after receiving a review notification becomes their public response."""
    from commontrust_bot import review_notify

    pb = FakePocketBase()
    rep = ReputationService(pb=pb)
    deals = DealService(pb=pb, reputation=rep)
    monkeypatch.setattr(dm_handlers, "deal_service", deals)
    monkeypatch.setattr(dm_handlers, "pb_client", pb)

    # Create members and a deal
    reviewer = await pb.member_get_or_create(1, "reviewer", "Reviewer")
    reviewee = await pb.member_get_or_create(2, "reviewee", "Reviewee")
    deal = await pb.deal_create(
        initiator_id=reviewer["id"],
        counterparty_id=reviewee["id"],
        group_id="test_group",
        description="Test deal",
    )

    # Create a review
    review = await pb.review_create(
        deal_id=deal["id"],
        reviewer_id=reviewer["id"],
        reviewee_id=reviewee["id"],
        rating=5,
        comment="Great work!",
        reviewer_username="reviewer",
        reviewee_username="reviewee",
    )

    # Simulate the user receiving a review notification (sets pending state)
    review_notify._PENDING_REVIEW_RESPONSE[2] = review["id"]

    # User sends a message (any message in the chat)
    response_msg = FakeMessage(
        text="Thank you for the feedback!",
        from_user=FakeUser(2, "reviewee", "Reviewee"),
        chat=FakeChat(2, "private"),
    )

    # Submit the response
    await dm_handlers.maybe_capture_review_response(response_msg)  # type: ignore[arg-type]

    # Verify the response was saved
    updated_review = await pb.get_record("reviews", review["id"])
    assert updated_review["response"] == "Thank you for the feedback!"
    assert updated_review["response_at"] is not None
    assert "published on the ledger" in response_msg.answers[-1]["text"]

    # Verify pending state was cleared
    assert 2 not in review_notify._PENDING_REVIEW_RESPONSE
