from commontrust_bot.web_links import deal_reviews_url
from commontrust_bot.config import settings


def test_deal_reviews_url_none_when_unset(monkeypatch) -> None:
    monkeypatch.setattr(settings, "commontrust_web_url", "", raising=False)
    assert deal_reviews_url("abc") is None


def test_deal_reviews_url_builds(monkeypatch) -> None:
    monkeypatch.setattr(settings, "commontrust_web_url", "https://example.com/", raising=False)
    assert deal_reviews_url("abc") == "https://example.com/deals/abc"

