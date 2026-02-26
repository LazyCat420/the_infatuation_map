"""
geocoder.py — Geocode restaurant addresses using OpenStreetMap Nominatim.

Free, no API key required! Just needs to respect usage policy:
- Max 1 request per second
- Identify with a custom User-Agent

Features:
- File-based cache to avoid repeated lookups
- Only geocodes entries missing lat/lng
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

DEFAULT_CACHE_PATH = Path("data/.geocode_cache.json")
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

USER_AGENT = (
    "InfatuationMapBot/1.0 "
    "(personal-project; geocoding restaurant addresses for a map)"
)


class Geocoder:
    """OpenStreetMap Nominatim geocoder with file-based caching."""

    def __init__(
        self,
        cache_path: Path = DEFAULT_CACHE_PATH,
        rate_limit: float = 1.1,  # Nominatim requires >= 1s between requests
    ) -> None:
        self.cache_path = cache_path
        self.rate_limit = rate_limit
        self._cache: dict[str, dict[str, object]] = self._load_cache()
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})

    def _load_cache(self) -> dict[str, dict[str, object]]:
        """Load the geocode cache from disk."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, encoding="utf-8") as f:
                    data = json.load(f)
                logger.info("Loaded geocode cache: %d entries", len(data))
                return data  # type: ignore[no-any-return]
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load cache: %s", exc)
        return {}

    def _save_cache(self) -> None:
        """Persist the geocode cache to disk."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, indent=2, ensure_ascii=False)

    def geocode_address(self, address: str) -> dict[str, object] | None:
        """
        Geocode a single address via Nominatim.
        Returns dict with lat, lng, or None on failure.
        Uses cache when available.
        """
        cache_key = address.strip().lower()

        # Cache hit
        if cache_key in self._cache:
            logger.debug("Cache hit: %s", address)
            return self._cache[cache_key]

        # API call
        logger.info("Geocoding: %s", address)
        try:
            time.sleep(self.rate_limit)
            resp = self._session.get(
                NOMINATIM_URL,
                params={
                    "q": address,
                    "format": "json",
                    "limit": 1,
                    "countrycodes": "us",
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.warning("Geocoding request failed for '%s': %s", address, exc)
            return None

        if not data:
            logger.warning("No results for: %s", address)
            return None

        result = data[0]
        entry: dict[str, object] = {
            "lat": float(result["lat"]),
            "lng": float(result["lon"]),
            "display_name": result.get("display_name", ""),
            "osm_type": result.get("osm_type", ""),
            "importance": result.get("importance", 0),
        }

        # Cache it
        self._cache[cache_key] = entry
        self._save_cache()

        return entry

    def geocode_restaurants(
        self, restaurants: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        """
        Geocode all restaurants missing coordinates.
        Modifies in place and returns the list.
        """
        needs_geocoding = [
            r for r in restaurants if not r.get("lat") or not r.get("lng")
        ]
        logger.info(
            "Geocoding %d of %d restaurants (free via Nominatim, ~1 req/sec)",
            len(needs_geocoding),
            len(restaurants),
        )

        for i, restaurant in enumerate(needs_geocoding, 1):
            address = str(restaurant.get("address", ""))
            if not address:
                logger.warning(
                    "Skipping '%s' — no address", restaurant.get("name")
                )
                continue

            result = self.geocode_address(address)
            if result:
                restaurant["lat"] = result["lat"]
                restaurant["lng"] = result["lng"]
                restaurant["geocode_confidence"] = result.get(
                    "osm_type", ""
                )
                logger.info(
                    "  %d/%d: %s → (%.4f, %.4f)",
                    i,
                    len(needs_geocoding),
                    restaurant.get("name"),
                    result["lat"],
                    result["lng"],
                )
            else:
                logger.warning(
                    "  %d/%d: %s — geocoding failed",
                    i,
                    len(needs_geocoding),
                    restaurant.get("name"),
                )

        geocoded = sum(1 for r in restaurants if r.get("lat") and r.get("lng"))
        logger.info(
            "Geocoding complete: %d/%d have coordinates", geocoded, len(restaurants)
        )
        return restaurants
