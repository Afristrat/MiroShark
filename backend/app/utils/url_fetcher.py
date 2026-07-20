"""Safe URL ingestion through the shared Crawl4AI service."""

import ipaddress
import socket
from urllib.parse import urlparse

import requests

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger("miroshark.url_fetcher")


def _check_ip(ip_str: str) -> None:
    """Raise when a URL resolves to an address that must not be crawled."""
    address = ipaddress.ip_address(ip_str)
    if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
        raise ValueError(f"Requests to private or internal addresses are not allowed ({ip_str})")


def _validate_url(url: str) -> str:
    """Validate the user-controlled URL before it reaches the crawler."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Only http and https URLs are supported (got '{parsed.scheme}')")
    if not parsed.netloc:
        raise ValueError("Invalid URL: missing host")
    host = parsed.hostname
    if not host:
        raise ValueError("Invalid URL: missing host")
    try:
        _check_ip(socket.gethostbyname(host))
    except socket.gaierror:
        pass
    return host


def _crawl_result_text(result: dict) -> str:
    """Return the best text field from Crawl4AI's stable result envelope."""
    markdown = result.get("markdown")
    if isinstance(markdown, dict):
        return str(markdown.get("fit_markdown") or markdown.get("raw_markdown") or "").strip()
    return str(markdown or result.get("extracted_content") or "").strip()


def fetch_url_text(url: str, timeout: int = 60) -> dict:
    """Fetch one public URL with Crawl4AI and normalize it for simulation ingestion."""
    _validate_url(url)
    if not Config.CRAWL4AI_URL or not Config.CRAWL4AI_API_TOKEN:
        raise ValueError("Crawl4AI is not configured")

    try:
        response = requests.post(
            f"{Config.CRAWL4AI_URL}/crawl",
            headers={"Authorization": f"Bearer {Config.CRAWL4AI_API_TOKEN}"},
            json={"urls": [url]},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        logger.error("Crawl4AI URL fetch failed: %s", exc)
        raise ValueError("Crawl4AI could not fetch this URL") from exc
    except ValueError as exc:
        raise ValueError("Crawl4AI returned an invalid response") from exc

    results = payload.get("results") if isinstance(payload, dict) else None
    result = results[0] if isinstance(results, list) and results else None
    if not isinstance(result, dict) or not result.get("success"):
        detail = result.get("error_message") if isinstance(result, dict) else "empty result"
        raise ValueError(f"Crawl4AI could not fetch this URL: {detail}")

    text = _crawl_result_text(result)
    if len(text) < 100:
        raise ValueError("Could not extract meaningful text from the page")

    metadata = result.get("metadata")
    title = ""
    if isinstance(metadata, dict):
        title = str(metadata.get("title") or metadata.get("og:title") or "").strip()
    title = title or urlparse(url).netloc
    return {"title": title[:120], "text": text, "url": url, "char_count": len(text)}
