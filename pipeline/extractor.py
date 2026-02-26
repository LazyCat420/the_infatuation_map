"""
extractor.py — Extract restaurant data from Infatuation review and guide pages.

Supports three extraction strategies (tried in order):
1. JSON-LD structured data
2. Embedded app state (__NEXT_DATA__)
3. HTML parsing (fallback)
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

USER_AGENT = (
    "InfatuationMapBot/1.0 "
    "(personal-project; collects restaurant metadata for a map)"
)


@dataclass
class RawRestaurant:
    """A restaurant entity as extracted from a page (before normalization)."""

    name: str
    address: str = ""
    neighborhood: str = ""
    cuisine: str = ""
    source_url: str = ""
    restaurant_url: str = ""
    image_url: str = ""
    lat: float | None = None
    lng: float | None = None
    tags: list[str] = field(default_factory=list)
    perfect_for: list[str] = field(default_factory=list)
    rating_text: str = ""


def _get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    return session


def _fetch(session: requests.Session, url: str) -> BeautifulSoup | None:
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except requests.RequestException as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Strategy 1: JSON-LD extraction
# ---------------------------------------------------------------------------

def _extract_jsonld(soup: BeautifulSoup) -> list[dict[str, object]]:
    """Extract JSON-LD blocks from the page."""
    results: list[dict[str, object]] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                results.extend(data)
            elif isinstance(data, dict):
                results.append(data)
        except (json.JSONDecodeError, TypeError):
            continue
    return results


def _restaurant_from_jsonld(
    ld: dict[str, object], source_url: str
) -> RawRestaurant | None:
    """Try to build a RawRestaurant from a JSON-LD Restaurant object."""
    ld_type = ld.get("@type", "")
    if isinstance(ld_type, list):
        type_strs = [str(t) for t in ld_type]
    else:
        type_strs = [str(ld_type)]

    if not any(t in ("Restaurant", "FoodEstablishment", "LocalBusiness") for t in type_strs):
        return None

    name = str(ld.get("name", "")).strip()
    if not name:
        return None

    address_obj = ld.get("address", {})
    address = ""
    if isinstance(address_obj, dict):
        parts = [
            str(address_obj.get("streetAddress", "")),
            str(address_obj.get("addressLocality", "")),
            str(address_obj.get("addressRegion", "")),
            str(address_obj.get("postalCode", "")),
        ]
        address = ", ".join(p for p in parts if p)
    elif isinstance(address_obj, str):
        address = address_obj

    lat, lng = None, None
    geo = ld.get("geo", {})
    if isinstance(geo, dict):
        try:
            lat = float(geo.get("latitude", 0)) or None
            lng = float(geo.get("longitude", 0)) or None
        except (ValueError, TypeError):
            pass

    cuisine_raw = ld.get("servesCuisine", "")
    if isinstance(cuisine_raw, list):
        cuisine = ", ".join(str(c) for c in cuisine_raw)
    else:
        cuisine = str(cuisine_raw)

    return RawRestaurant(
        name=name,
        address=address,
        cuisine=cuisine,
        lat=lat,
        lng=lng,
        source_url=source_url,
        restaurant_url=source_url,
    )


# ---------------------------------------------------------------------------
# Strategy 2: __NEXT_DATA__ extraction
# ---------------------------------------------------------------------------

def _extract_next_data(soup: BeautifulSoup) -> dict[str, object] | None:
    """Extract __NEXT_DATA__ JSON blob if present."""
    script = soup.find("script", id="__NEXT_DATA__")
    if script and script.string:
        try:
            return json.loads(script.string)  # type: ignore[return-value]
        except json.JSONDecodeError:
            pass
    return None


# ---------------------------------------------------------------------------
# Strategy 3: HTML parsing (most reliable for this site)
# ---------------------------------------------------------------------------

# Pattern: address appears in google maps links
_GMAPS_PATTERN = re.compile(
    r"google\.com/maps/search/\?api=1&query=(.+)", re.IGNORECASE
)

# Pattern: cuisine links
_CUISINE_PATTERN = re.compile(r"/san-francisco/cuisines/([\w-]+)")

# Pattern: neighborhood links
_NEIGHBORHOOD_PATTERN = re.compile(r"/san-francisco/neighborhoods/([\w-]+)")

# Pattern: perfect-for links
_PERFECT_FOR_PATTERN = re.compile(r"/san-francisco/perfect-for/([\w-]+)")

# Pattern: review links
_REVIEW_PATTERN = re.compile(r"^/san-francisco/reviews/([\w-]+)$")


def _slug_to_name(slug: str) -> str:
    """Convert a URL slug to a readable name: 'thai-food' → 'Thai Food'."""
    return slug.replace("-", " ").title()


def _extract_review_html(
    soup: BeautifulSoup, url: str
) -> RawRestaurant | None:
    """Extract a single restaurant from a review page via HTML parsing."""
    # Name: first H1
    h1 = soup.find("h1")
    if not h1:
        return None
    name = h1.get_text(strip=True)
    if not name or name.lower() in ("san francisco", ""):
        return None

    # Address: from Google Maps link
    address = ""
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        match = _GMAPS_PATTERN.search(href)
        if match:
            raw_query = unquote(match.group(1))
            # The query is usually "Name+Address", extract the address part
            # Format: "Burma%20Superstar+309 Clement St., ..."
            if "+" in raw_query:
                address = raw_query.split("+", 1)[1].strip()
            else:
                address = raw_query
            break

    # Cuisine
    cuisine = ""
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        cm = _CUISINE_PATTERN.search(href)
        if cm:
            cuisine = _slug_to_name(cm.group(1))
            break

    # Neighborhood
    neighborhood = ""
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        nm = _NEIGHBORHOOD_PATTERN.search(href)
        if nm:
            neighborhood = _slug_to_name(nm.group(1))
            break

    # Perfect for tags
    perfect_for: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        pm = _PERFECT_FOR_PATTERN.search(href)
        if pm:
            tag_name = _slug_to_name(pm.group(1))
            if tag_name not in perfect_for:
                perfect_for.append(tag_name)

    tags: list[str] = []
    if cuisine:
        tags.append(cuisine)
    tags.extend(perfect_for)

    # Hero image: find the first large Cloudinary image via src attribute
    image_url = ""
    for img in soup.find_all("img"):
        src = str(img.get("src", "") or img.get("data-src", ""))
        if "res.cloudinary.com/the-infatuation" not in src:
            continue
        # Skip tiny thumbnails (author avatars: w_96, w_128, w_256)
        if any(f"w_{s}" in src for s in ("96", "128", "256")):
            continue
        # Use the src directly — Cloudinary auto-serves optimized format
        image_url = src
        break

    return RawRestaurant(
        name=name,
        address=address,
        neighborhood=neighborhood,
        cuisine=cuisine,
        source_url=url,
        restaurant_url=url,
        image_url=image_url,
        tags=tags,
        perfect_for=perfect_for,
    )


def _extract_guide_html(
    soup: BeautifulSoup, guide_url: str
) -> list[RawRestaurant]:
    """Extract multiple restaurants mentioned in a guide page."""
    restaurants: list[RawRestaurant] = []

    # In guide pages, each restaurant appears as a section with:
    # - An H2 header with the restaurant name
    # - A google maps link with the address
    # - Cuisine and neighborhood links
    # We look for google maps links and then search nearby context

    # Collect all review links mentioned in the guide
    review_links: dict[str, str] = {}  # slug → full url
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        parsed = urlparse(href)
        path = parsed.path.rstrip("/")
        rm = _REVIEW_PATTERN.match(path)
        if rm:
            slug = rm.group(1)
            review_links[slug] = f"https://www.theinfatuation.com{path}"

    # Find all google maps links — each one is a restaurant mention
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        match = _GMAPS_PATTERN.search(href)
        if not match:
            continue

        raw_query = unquote(match.group(1))
        # Parse "RestaurantName+Address"
        if "+" in raw_query:
            parts = raw_query.split("+", 1)
            r_name = parts[0].strip()
            r_address = parts[1].strip()
        else:
            r_name = raw_query
            r_address = ""

        if not r_name:
            continue

        # Search for context around this anchor for cuisine/neighborhood
        parent: Tag | None = anchor
        cuisine = ""
        neighborhood = ""
        tags: list[str] = []

        # Walk up to find the containing section
        for _ in range(10):
            if parent is None:
                break
            parent = parent.parent    # type: ignore[assignment]
            if parent is None or not isinstance(parent, Tag):
                break
            # Look for cuisine/neighborhood links in this container
            for sub_anchor in parent.find_all("a", href=True):
                sub_href = str(sub_anchor["href"])
                cm = _CUISINE_PATTERN.search(sub_href)
                if cm and not cuisine:
                    cuisine = _slug_to_name(cm.group(1))
                nm = _NEIGHBORHOOD_PATTERN.search(sub_href)
                if nm and not neighborhood:
                    neighborhood = _slug_to_name(nm.group(1))
            if cuisine or neighborhood:
                break

        if cuisine:
            tags.append(cuisine)

        # Try to match to a review URL
        restaurant_url = ""
        name_slug = r_name.lower().replace(" ", "-")
        # Fuzzy match: check if any review slug is a substring or match
        for slug, full_url in review_links.items():
            if slug == name_slug or slug in name_slug or name_slug in slug:
                restaurant_url = full_url
                break

        restaurants.append(
            RawRestaurant(
                name=r_name,
                address=r_address,
                neighborhood=neighborhood,
                cuisine=cuisine,
                source_url=guide_url,
                restaurant_url=restaurant_url or guide_url,
                tags=tags,
            )
        )

    return restaurants


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_from_review(
    session: requests.Session, url: str
) -> RawRestaurant | None:
    """Extract a restaurant from a review page URL."""
    soup = _fetch(session, url)
    if soup is None:
        return None

    # Strategy 1: JSON-LD
    for ld in _extract_jsonld(soup):
        result = _restaurant_from_jsonld(ld, url)
        if result:
            logger.info("Extracted via JSON-LD: %s", result.name)
            return result

    # Strategy 3: HTML parsing (most common)
    result = _extract_review_html(soup, url)
    if result:
        logger.info("Extracted via HTML: %s", result.name)
        return result

    logger.warning("Could not extract restaurant from %s", url)
    return None


def extract_from_guide(
    session: requests.Session, url: str
) -> list[RawRestaurant]:
    """Extract restaurants mentioned in a guide page URL."""
    soup = _fetch(session, url)
    if soup is None:
        return []

    results = _extract_guide_html(soup, url)
    logger.info("Extracted %d restaurants from guide: %s", len(results), url)
    return results


def extract_all(
    review_urls: list[str],
    guide_urls: list[str],
    request_delay: float = 1.5,
) -> list[RawRestaurant]:
    """
    Extract restaurants from all discovered URLs.

    Reviews are the primary source (full detail per restaurant).
    Guides provide additional mentions and act as source attribution.
    """
    session = _get_session()
    all_restaurants: list[RawRestaurant] = []

    # Extract from review pages (one restaurant per page)
    logger.info("--- Extracting from %d review pages ---", len(review_urls))
    for i, url in enumerate(review_urls, 1):
        logger.info("Review %d/%d", i, len(review_urls))
        result = extract_from_review(session, url)
        if result:
            all_restaurants.append(result)
        time.sleep(request_delay)

    # Extract from guide pages (multiple restaurants per page)
    logger.info("--- Extracting from %d guide pages ---", len(guide_urls))
    for i, url in enumerate(guide_urls, 1):
        logger.info("Guide %d/%d", i, len(guide_urls))
        results = extract_from_guide(session, url)
        all_restaurants.extend(results)
        time.sleep(request_delay)

    logger.info("Total extracted: %d restaurants", len(all_restaurants))
    return all_restaurants
