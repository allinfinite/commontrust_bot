import pytest

from commontrust_credit_bot import config as credit_config
from commontrust_credit_bot.handlers import admin as credit_admin_handlers
from commontrust_credit_bot.handlers import credit as credit_handlers
from tests.fake_commontrust_api import FakeCommonTrustApiClient
from tests.fake_pocketbase import FakePocketBase
from tests.fake_telegram import FakeChat, FakeMessage, FakeUser


@pytest.mark.asyncio
async def test_enable_credit_requires_admin(monkeypatch) -> None:
    pb = FakePocketBase()
    api = FakeCommonTrustApiClient(pb)
    monkeypatch.setattr(credit_admin_handlers, "api_client", api)
    monkeypatch.setattr(credit_config.credit_settings, "super_admin_user_ids", [999], raising=False)

    msg = FakeMessage(text="/enable_credit", from_user=FakeUser(1), chat=FakeChat(100, "group", "G"))
    await credit_admin_handlers.cmd_enable_credit(msg)  # type: ignore[arg-type]
    assert "Only group admins" in msg.answers[-1]["text"]


@pytest.mark.asyncio
async def test_enable_credit_and_pay_flow(monkeypatch) -> None:
    pb = FakePocketBase()
    api = FakeCommonTrustApiClient(pb)
    monkeypatch.setattr(credit_admin_handlers, "api_client", api)
    monkeypatch.setattr(credit_handlers, "api_client", api)
    monkeypatch.setattr(credit_config.credit_settings, "super_admin_user_ids", [1], raising=False)

    enable = FakeMessage(
        text="/enable_credit Hours h",
        from_user=FakeUser(1, username="admin", full_name="Admin"),
        chat=FakeChat(100, "group", "G"),
    )
    await credit_admin_handlers.cmd_enable_credit(enable)  # type: ignore[arg-type]
    assert "Mutual credit enabled" in enable.answers[-1]["text"]

    payer = FakeUser(1, username="payer", full_name="Payer")
    payee = FakeUser(2, username="payee", full_name="Payee")
    replied = FakeMessage(text="hello", from_user=payee, chat=FakeChat(100, "group"))
    pay = FakeMessage(text="/pay 10 lunch", from_user=payer, chat=FakeChat(100, "group"), reply_to_message=replied)
    await credit_handlers.cmd_pay(pay)  # type: ignore[arg-type]
    assert "Payment successful" in pay.answers[-1]["text"]
    assert "10 h" in pay.answers[-1]["text"]

    bal = FakeMessage(text="/balance", from_user=payer, chat=FakeChat(100, "group"))
    await credit_handlers.cmd_balance(bal)  # type: ignore[arg-type]
    assert "Balance" in bal.answers[-1]["text"]


@pytest.mark.asyncio
async def test_pay_by_username_and_unknown(monkeypatch) -> None:
    pb = FakePocketBase()
    api = FakeCommonTrustApiClient(pb)
    monkeypatch.setattr(credit_admin_handlers, "api_client", api)
    monkeypatch.setattr(credit_handlers, "api_client", api)
    monkeypatch.setattr(credit_config.credit_settings, "super_admin_user_ids", [1], raising=False)

    enable = FakeMessage(text="/enable_credit", from_user=FakeUser(1), chat=FakeChat(100, "group", "G"))
    await credit_admin_handlers.cmd_enable_credit(enable)  # type: ignore[arg-type]

    msg1 = FakeMessage(text="/pay @unknown 10", from_user=FakeUser(1, "payer", "Payer"), chat=FakeChat(100, "group"))
    await credit_handlers.cmd_pay(msg1)  # type: ignore[arg-type]
    assert "was not found" in msg1.answers[-1]["text"]

    await api.upsert_member(2, username="payee", display_name="Payee")
    msg2 = FakeMessage(text="/pay @payee 10", from_user=FakeUser(1, "payer", "Payer"), chat=FakeChat(100, "group"))
    await credit_handlers.cmd_pay(msg2)  # type: ignore[arg-type]
    assert "Payment successful" in msg2.answers[-1]["text"]

