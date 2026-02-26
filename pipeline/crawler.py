"""
crawler.py — Discover restaurant-related URLs from The Infatuation SF hub.

Crawls the San Francisco hub page and linked guide/review pages to build a
complete list of restaurant review URLs and guide URLs that mention restaurants.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.theinfatuation.com"
SF_HUB = f"{BASE_URL}/san-francisco"

# Patterns we care about
REVIEW_PATTERN = re.compile(r"^/san-francisco/reviews/[\w-]+$")
GUIDE_PATTERN = re.compile(r"^/san-francisco/guides/[\w-]+$")

# Respect the site: identify ourselves and throttle
USER_AGENT = (
    "InfatuationMapBot/1.0 "
    "(personal-project; collects restaurant metadata for a map)"
)
REQUEST_DELAY_SECONDS = 1.5  # polite delay between requests


@dataclass
class CrawlResult:
    """Container for discovered URLs."""

    review_urls: list[str] = field(default_factory=list)
    guide_urls: list[str] = field(default_factory=list)
    failed_urls: list[str] = field(default_factory=list)


def _get_session() -> requests.Session:
    """Create a requests session with proper headers."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    return session


def _fetch_page(session: requests.Session, url: str) -> BeautifulSoup | None:
    """Fetch a page and return parsed HTML, or None on failure."""
    try:
        logger.info("Fetching: %s", url)
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except requests.RequestException as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None


def _extract_sf_links(soup: BeautifulSoup) -> tuple[set[str], set[str]]:
    """Extract review and guide links from a parsed page."""
    reviews: set[str] = set()
    guides: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        # Normalize: strip query/fragment, handle relative URLs
        parsed = urlparse(href)
        path = parsed.path.rstrip("/")

        if REVIEW_PATTERN.match(path):
            reviews.add(urljoin(BASE_URL, path))
        elif GUIDE_PATTERN.match(path):
            guides.add(urljoin(BASE_URL, path))

    return reviews, guides


def crawl(
    max_guides: int | None = None,
    request_delay: float = REQUEST_DELAY_SECONDS,
) -> CrawlResult:
    """
    Crawl The Infatuation SF section and discover restaurant URLs.

    1. Fetch the SF hub page
    2. Extract all guide and review links from the hub
    3. Follow each guide link to discover more review links
    4. Return deduplicated sets of review and guide URLs

    Args:
        max_guides: Optional limit on how many guide pages to follow.
        request_delay: Seconds to wait between requests.

    Returns:
        CrawlResult with all discovered URLs.
    """
    session = _get_session()
    result = CrawlResult()

    # --- Step 1: Fetch SF hub page ---
    logger.info("=== Starting crawl from %s ===", SF_HUB)
    hub_soup = _fetch_page(session, SF_HUB)
    if hub_soup is None:
        logger.error("Could not fetch hub page. Aborting.")
        result.failed_urls.append(SF_HUB)
        return result

    hub_reviews, hub_guides = _extract_sf_links(hub_soup)
    all_reviews = set(hub_reviews)
    all_guides = set(hub_guides)
    logger.info(
        "Hub page: found %d review links, %d guide links",
        len(hub_reviews),
        len(hub_guides),
    )

    # --- Step 2: Follow guide pages to discover more reviews ---
    guides_to_crawl = sorted(all_guides)
    if max_guides is not None:
        guides_to_crawl = guides_to_crawl[:max_guides]

    for i, guide_url in enumerate(guides_to_crawl, 1):
        logger.info("Guide %d/%d: %s", i, len(guides_to_crawl), guide_url)
        time.sleep(request_delay)

        guide_soup = _fetch_page(session, guide_url)
        if guide_soup is None:
            result.failed_urls.append(guide_url)
            continue

        guide_reviews, more_guides = _extract_sf_links(guide_soup)
        new_reviews = guide_reviews - all_reviews
        if new_reviews:
            logger.info("  → found %d new review links", len(new_reviews))
            all_reviews.update(new_reviews)

        # Don't recursively follow guides found within guides (avoid explosion)
        new_guides = more_guides - all_guides
        if new_guides:
            logger.debug(
                "  → found %d additional guide links (not following)",
                len(new_guides),
            )

    result.review_urls = sorted(all_reviews)
    result.guide_urls = sorted(all_guides)

    logger.info(
        "=== Crawl complete: %d reviews, %d guides, %d failures ===",
        len(result.review_urls),
        len(result.guide_urls),
        len(result.failed_urls),
    )
    return result
