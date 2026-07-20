from app.config import Config
from app.utils.url_fetcher import fetch_url_text


class _Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "success": True,
            "results": [{
                "success": True,
                "metadata": {"title": "Test article"},
                "markdown": {"raw_markdown": "x" * 120},
            }],
        }


def test_fetch_url_text_uses_shared_crawl4ai(monkeypatch):
    monkeypatch.setattr(Config, "CRAWL4AI_URL", "https://crawler.example")
    monkeypatch.setattr(Config, "CRAWL4AI_API_TOKEN", "token")
    seen = {}

    def fake_post(url, **kwargs):
        seen["url"] = url
        seen.update(kwargs)
        return _Response()

    monkeypatch.setattr("app.utils.url_fetcher.requests.post", fake_post)

    result = fetch_url_text("https://example.com/article")

    assert seen["url"] == "https://crawler.example/crawl"
    assert seen["headers"] == {"Authorization": "Bearer token"}
    assert seen["json"] == {"urls": ["https://example.com/article"]}
    assert result == {
        "title": "Test article",
        "text": "x" * 120,
        "url": "https://example.com/article",
        "char_count": 120,
    }
