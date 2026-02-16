def test_imports() -> None:
    # Smoke test: importing should not require secrets or a running PocketBase.
    import commontrust_api.app  # noqa: F401
    import commontrust_credit_bot.main  # noqa: F401
