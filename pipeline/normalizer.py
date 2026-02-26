"""
normalizer.py — Deduplicate and normalize extracted restaurant data.

Merges duplicate entries (same restaurant URL or same name+address),
generates stable IDs, and produces a clean output.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import asdict
from datetime import datetime, timezone

from pipeline.extractor import RawRestaurant

logger = logging.getLogger(__name__)


def _normalize_text(text: str) -> str:
    """Lowercase, strip whitespace, collapse multiple spaces."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _make_id(name: str, address: str) -> str:
    """Generate a stable, deterministic ID from name + address."""
    key = f"{_normalize_text(name)}|{_normalize_text(address)}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _make_slug(name: str) -> str:
    """Generate a URL-friendly slug from a name."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    return slug.strip("-")


def _dedup_key(r: RawRestaurant) -> str:
    """Create a deduplication key: canonical URL or normalized name+address."""
    if r.restaurant_url and "/reviews/" in r.restaurant_url:
        # Canonical review URL is the best dedup key
        return r.restaurant_url.rstrip("/").lower()
    # Fall back to name + address
    return f"{_normalize_text(r.name)}|{_normalize_text(r.address)}"


def _merge_restaurants(
    existing: dict[str, object], new: RawRestaurant
) -> dict[str, object]:
    """Merge a new extraction into an existing record, keeping richer data."""
    # Prefer non-empty values
    if not existing.get("address") and new.address:
        existing["address"] = new.address
    if not existing.get("neighborhood") and new.neighborhood:
        existing["neighborhood"] = new.neighborhood
    if not existing.get("cuisine") and new.cuisine:
        existing["cuisine"] = new.cuisine
    if not existing.get("restaurant_url") and new.restaurant_url:
        existing["restaurant_url"] = new.restaurant_url
    if not existing.get("image_url") and new.image_url:
        existing["image_url"] = new.image_url

    # Merge tags (deduplicated)
    existing_tags: list[str] = list(existing.get("tags", []))  # type: ignore[arg-type]
    for tag in new.tags:
        if tag not in existing_tags:
            existing_tags.append(tag)
    existing["tags"] = existing_tags

    # Track all source URLs
    source_urls: list[str] = list(existing.get("source_urls", []))  # type: ignore[arg-type]
    if new.source_url and new.source_url not in source_urls:
        source_urls.append(new.source_url)
    existing["source_urls"] = source_urls

    # Prefer coordinates if available
    if new.lat and new.lng:
        existing["lat"] = new.lat
        existing["lng"] = new.lng

    return existing


def normalize(raw_restaurants: list[RawRestaurant]) -> list[dict[str, object]]:
    """
    Normalize and deduplicate a list of raw restaurant extractions.

    Returns a sorted list of restaurant dicts ready for geocoding and output.
    """
    now = datetime.now(timezone.utc).isoformat()
    deduped: dict[str, dict[str, object]] = {}

    for raw in raw_restaurants:
        if not raw.name or not raw.name.strip():
            continue

        key = _dedup_key(raw)

        if key in deduped:
            deduped[key] = _merge_restaurants(deduped[key], raw)
        else:
            record: dict[str, object] = {
                "name": raw.name.strip(),
                "address": raw.address.strip(),
                "neighborhood": raw.neighborhood.strip(),
                "cuisine": raw.cuisine.strip(),
                "restaurant_url": raw.restaurant_url,
                "image_url": raw.image_url,
                "source_url": raw.source_url,
                "source_urls": [raw.source_url] if raw.source_url else [],
                "lat": raw.lat,
                "lng": raw.lng,
                "tags": list(raw.tags),
                "last_seen_at": now,
                "source": "theinfatuation",
            }
            deduped[key] = record

    # Generate stable IDs and sort
    results: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for record in deduped.values():
        name = str(record.get("name", ""))
        address = str(record.get("address", ""))
        rid = _make_id(name, address)
        if rid in seen_ids:
            logger.debug("Skipping duplicate ID %s (%s)", rid, name)
            continue
        seen_ids.add(rid)
        record["id"] = rid
        record["slug"] = _make_slug(name)
        results.append(record)

    # Stable sort by name for deterministic output
    results.sort(key=lambda r: str(r.get("name", "")).lower())

    logger.info(
        "Normalized: %d raw -> %d unique restaurants",
        len(raw_restaurants),
        len(results),
    )
    return results
