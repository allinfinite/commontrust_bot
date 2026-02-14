def test_imports() -> None:
    # Smoke test: importing should not require secrets or a running PocketBase.
    import commontrust_bot.config  # noqa: F401
    import commontrust_bot.handlers  # noqa: F401
    import commontrust_bot.main  # noqa: F401
    import commontrust_bot.pocketbase_client  # noqa: F401
    import commontrust_bot.services.deal  # noqa: F401
    import commontrust_bot.services.mutual_credit  # noqa: F401
    import commontrust_bot.services.reputation  # noqa: F401

