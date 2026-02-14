import pytest

from commontrust_bot import main as main_mod


@pytest.mark.asyncio
async def test_main_exits_when_not_configured(monkeypatch) -> None:
    # Force unconfigured state.
    from commontrust_bot import config as config_mod

    monkeypatch.setattr(config_mod.settings, "telegram_bot_token", "", raising=False)
    monkeypatch.setattr(config_mod.settings, "pocketbase_admin_token", None, raising=False)
    monkeypatch.setattr(config_mod.settings, "pocketbase_admin_email", None, raising=False)
    monkeypatch.setattr(config_mod.settings, "pocketbase_admin_password", None, raising=False)

    with pytest.raises(SystemExit):
        await main_mod.main()

