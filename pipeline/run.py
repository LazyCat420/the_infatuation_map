"""
run.py — Main entry point for the data pipeline.

Usage (run from project root OR from pipeline/):
    python pipeline/run.py --refresh
    python run.py --refresh               (if you're already in pipeline/)
    python run.py --refresh --max-guides 5  (quick test)
    python run.py --refresh --skip-images   (skip image download)
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path

# Resolve project root (works whether run from root or pipeline/)
_THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _THIS_DIR.parent if _THIS_DIR.name == "pipeline" else _THIS_DIR
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.crawler import crawl
from pipeline.extractor import extract_all
from pipeline.normalizer import normalize
from pipeline.geocoder import Geocoder
from pipeline.image_downloader import download_images

DATA_DIR = PROJECT_ROOT / "data"
RAW_PATH = DATA_DIR / "restaurants.raw.json"
NORMALIZED_PATH = DATA_DIR / "restaurants.normalized.json"
FINAL_PATH = DATA_DIR / "restaurants.json"
APP_PUBLIC = PROJECT_ROOT / "app" / "public"


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _save_json(data: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    logging.info("Wrote %s", path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="The Infatuation SF — Restaurant Data Pipeline"
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Run full pipeline: crawl -> extract -> normalize -> geocode",
    )
    parser.add_argument(
        "--max-guides",
        type=int,
        default=None,
        help="Limit number of guide pages to crawl (for testing)",
    )
    parser.add_argument(
        "--skip-geocoding",
        action="store_true",
        help="Skip geocoding step",
    )
    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="Skip image download step",
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=1.5,
        help="Delay between requests in seconds (default: 1.5)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable debug logging"
    )
    args = parser.parse_args()

    _setup_logging(args.verbose)

    if not args.refresh:
        parser.print_help()
        sys.exit(0)

    # --- Step 1: Crawl ---
    logging.info("=" * 60)
    logging.info("STEP 1: Crawling The Infatuation SF")
    logging.info("=" * 60)
    crawl_result = crawl(
        max_guides=args.max_guides,
        request_delay=args.request_delay,
    )
    logging.info(
        "Discovered %d review URLs, %d guide URLs",
        len(crawl_result.review_urls),
        len(crawl_result.guide_urls),
    )

    # --- Step 2: Extract ---
    logging.info("=" * 60)
    logging.info("STEP 2: Extracting restaurant data")
    logging.info("=" * 60)
    raw_restaurants = extract_all(
        review_urls=crawl_result.review_urls,
        guide_urls=crawl_result.guide_urls,
        request_delay=args.request_delay,
    )
    # Save raw
    raw_data = [
        {
            "name": r.name,
            "address": r.address,
            "neighborhood": r.neighborhood,
            "cuisine": r.cuisine,
            "source_url": r.source_url,
            "restaurant_url": r.restaurant_url,
            "image_url": r.image_url,
            "lat": r.lat,
            "lng": r.lng,
            "tags": r.tags,
        }
        for r in raw_restaurants
    ]
    _save_json(raw_data, RAW_PATH)

    # --- Step 3: Normalize ---
    logging.info("=" * 60)
    logging.info("STEP 3: Normalizing and deduplicating")
    logging.info("=" * 60)
    normalized = normalize(raw_restaurants)
    _save_json(normalized, NORMALIZED_PATH)

    # --- Step 4: Geocode (free via OpenStreetMap Nominatim) ---
    if args.skip_geocoding:
        logging.info("Skipping geocoding (--skip-geocoding flag)")
        final = normalized
    else:
        logging.info("=" * 60)
        logging.info("STEP 4: Geocoding (free via Nominatim, cached)")
        logging.info("=" * 60)
        geocoder = Geocoder(
            cache_path=DATA_DIR / ".geocode_cache.json",
        )
        final = geocoder.geocode_restaurants(normalized)

    # --- Step 5: Download images ---
    if args.skip_images:
        logging.info("Skipping image download (--skip-images flag)")
    else:
        logging.info("=" * 60)
        logging.info("STEP 5: Downloading hero images")
        logging.info("=" * 60)
        final = download_images(
            final,
            output_dir=APP_PUBLIC / "images",
        )

    # --- Save final output + copy to app ---
    _save_json(final, FINAL_PATH)

    # Auto-copy to app/public/ so the dev server picks it up
    app_json = APP_PUBLIC / "restaurants.json"
    shutil.copy2(FINAL_PATH, app_json)
    logging.info("Copied to %s", app_json)

    # --- Summary ---
    logging.info("=" * 60)
    logging.info("PIPELINE COMPLETE")
    logging.info("  Total restaurants: %d", len(final))
    geocoded = sum(1 for r in final if r.get("lat") and r.get("lng"))
    with_images = sum(1 for r in final if r.get("image_url"))
    logging.info("  With coordinates: %d", geocoded)
    logging.info("  With images: %d", with_images)
    logging.info("  Output: %s", FINAL_PATH)
    logging.info("=" * 60)


if __name__ == "__main__":
    main()
