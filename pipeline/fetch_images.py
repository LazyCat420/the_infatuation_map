"""
fetch_images.py — Re-fetch hero images for existing restaurant data.

Uses the existing restaurants.json to visit each restaurant_url and
extract the hero image, then downloads it locally.
Run from anywhere: python pipeline/fetch_images.py
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Resolve paths
_THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _THIS_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
APP_PUBLIC = PROJECT_ROOT / "app" / "public"
IMAGES_DIR = APP_PUBLIC / "images"

USER_AGENT = (
    "InfatuationMapBot/1.0 "
    "(personal-project; downloading restaurant images for a map)"
)


def _extract_hero_image(html: str) -> str:
    """Extract the first large Cloudinary image URL from HTML."""
    soup = BeautifulSoup(html, "lxml")
    for img in soup.find_all("img"):
        src = str(img.get("src", "") or img.get("data-src", ""))
        if "res.cloudinary.com/the-infatuation" not in src:
            continue
        # Skip tiny thumbnails (author avatars)
        if any(f"w_{s}" in src for s in ("96", "128", "256")):
            continue
        return src
    return ""


def main() -> None:
    input_path = DATA_DIR / "restaurants.json"
    data: list[dict] = json.loads(input_path.read_text(encoding="utf-8"))
    logger.info("Loaded %d restaurants", len(data))

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    # Only process restaurants with a review URL and no local image yet
    to_process = [
        r for r in data
        if r.get("restaurant_url", "").startswith("http")
        and "/reviews/" in r.get("restaurant_url", "")
        and not (IMAGES_DIR / f"{r['id']}.jpg").exists()
    ]
    logger.info("Need images for %d restaurants", len(to_process))

    for i, restaurant in enumerate(to_process, 1):
        url = restaurant["restaurant_url"]
        rid = restaurant["id"]
        name = restaurant.get("name", "")

        try:
            # Fetch the review page
            time.sleep(1.2)
            resp = session.get(url, timeout=20)
            resp.raise_for_status()

            # Extract hero image URL
            image_url = _extract_hero_image(resp.text)
            if not image_url:
                logger.warning("  %d/%d: %s — no image found", i, len(to_process), name)
                continue

            # Download the image
            time.sleep(0.3)
            img_resp = session.get(image_url, timeout=15, stream=True)
            img_resp.raise_for_status()

            out_path = IMAGES_DIR / f"{rid}.jpg"
            with open(out_path, "wb") as f:
                for chunk in img_resp.iter_content(8192):
                    f.write(chunk)

            # Update the restaurant's image_url to local path
            restaurant["image_url"] = f"/images/{rid}.jpg"
            logger.info("  %d/%d: %s -> %s", i, len(to_process), name, out_path.name)

        except requests.RequestException as exc:
            logger.warning("  %d/%d: %s — failed: %s", i, len(to_process), name, exc)

    # Update all existing local images too
    for r in data:
        local_path = IMAGES_DIR / f"{r['id']}.jpg"
        if local_path.exists():
            r["image_url"] = f"/images/{r['id']}.jpg"

    # Save updated data
    output = DATA_DIR / "restaurants.json"
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    logger.info("Updated %s", output)

    # Copy to app/public
    import shutil
    app_json = APP_PUBLIC / "restaurants.json"
    shutil.copy2(output, app_json)
    logger.info("Copied to %s", app_json)

    with_images = sum(1 for r in data if str(r.get("image_url", "")).startswith("/images/"))
    logger.info("Done: %d/%d have local images", with_images, len(data))


if __name__ == "__main__":
    main()
