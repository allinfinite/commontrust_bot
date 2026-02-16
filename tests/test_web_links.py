from commontrust_bot.web_links import deal_reviews_url, review_respond_url, review_url
from commontrust_bot.config import settings


def test_deal_reviews_url_none_when_unset(monkeypatch) -> None:
    monkeypatch.setattr(settings, "commontrust_web_url", "", raising=False)
    assert deal_reviews_url("abc") is None


def test_deal_reviews_url_builds(monkeypatch) -> None:
    monkeypatch.setattr(settings, "commontrust_web_url", "https://example.com/", raising=False)
    assert deal_reviews_url("abc") == "https://example.com/deals/abc"


def test_review_url_builds(monkeypatch) -> None:
    monkeypatch.setattr(settings, "commontrust_web_url", "https://example.com/", raising=False)
    assert review_url("r123") == "https://example.com/reviews/r123"


def test_review_respond_url_builds(monkeypatch) -> None:
    monkeypatch.setattr(settings, "commontrust_web_url", "https://example.com/", raising=False)
    assert review_respond_url("tok") == "https://example.com/respond/tok"
