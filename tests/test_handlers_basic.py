import pytest

from commontrust_bot.config import settings
from commontrust_bot.handlers import basic as basic_handlers
from tests.fake_telegram import FakeChat, FakeMessage, FakeUser


@pytest.mark.asyncio
async def test_cmd_start_prioritizes_newdeal(monkeypatch) -> None:
    monkeypatch.setattr(settings, "commontrust_web_url", "", raising=False)
    msg = FakeMessage(text="/start", from_user=FakeUser(1), chat=FakeChat(1, "private"))

    await basic_handlers.cmd_start(msg)  # type: ignore[arg-type]
    text = msg.answers[-1]["text"]
    assert "First step (required)" in text
    assert "/newdeal your deal description" in text
    assert "send the invite link I generate" in text


@pytest.mark.asyncio
async def test_cmd_start_includes_how_to_link_when_configured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "commontrust_web_url", "https://example.com", raising=False)
    msg = FakeMessage(text="/start", from_user=FakeUser(1), chat=FakeChat(1, "private"))

    await basic_handlers.cmd_start(msg)  # type: ignore[arg-type]
    assert "https://example.com/how-to" in msg.answers[-1]["text"]
