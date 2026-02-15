from commontrust_bot.config import settings
from commontrust_bot.web_links import deal_reviews_url, user_reviews_url, user_reviews_url_by_telegram_id


def test_deal_reviews_url_none_when_unset(monkeypatch) -> None:
    monkeypatch.setattr(settings, "commontrust_web_url", "", raising=False)
    assert deal_reviews_url("abc") is None


def test_deal_reviews_url_builds(monkeypatch) -> None:
    monkeypatch.setattr(settings, "commontrust_web_url", "https://example.com/", raising=False)
    assert deal_reviews_url("abc") == "https://example.com/deals/abc"


def test_deal_reviews_url_adds_https_when_missing(monkeypatch) -> None:
    monkeypatch.setattr(settings, "commontrust_web_url", "trust.bigislandbulletin.com", raising=False)
    assert deal_reviews_url("abc") == "https://trust.bigislandbulletin.com/deals/abc"


def test_user_reviews_url_builds(monkeypatch) -> None:
    monkeypatch.setattr(settings, "commontrust_web_url", "example.com", raising=False)
    assert user_reviews_url("@alice") == "https://example.com/user/alice"


def test_user_reviews_url_by_telegram_id_builds(monkeypatch) -> None:
    monkeypatch.setattr(settings, "commontrust_web_url", "https://example.com", raising=False)
    assert user_reviews_url_by_telegram_id(1234) == "https://example.com/user/1234"
