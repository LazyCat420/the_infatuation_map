"""
image_downloader.py — Download restaurant hero images as local thumbnails.

Downloads images from Cloudinary to local static files so they load instantly.
Saves as optimized JPEGs in app/public/images/ for fast static serving.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = Path("app/public/images")
# Request a 400px wide image from Cloudinary (auto quality)
CLOUDINARY_TRANSFORM = "c_fill,w_400,h_250,f_auto,q_auto"

USER_AGENT = (
    "InfatuationMapBot/1.0 "
    "(personal-project; downloading restaurant images for a map)"
)


def download_images(
    restaurants: list[dict[str, object]],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    rate_limit: float = 0.5,
) -> list[dict[str, object]]:
    """
    Download hero images for restaurants that have image_url set.
    Saves to output_dir/{restaurant_id}.jpg and updates the record
    with a local_image_path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    needs_download = [
        r for r in restaurants
        if r.get("image_url") and not (output_dir / f"{r['id']}.jpg").exists()
    ]

    logger.info(
        "Downloading %d images (of %d total restaurants)",
        len(needs_download),
        len(restaurants),
    )

    for i, restaurant in enumerate(needs_download, 1):
        image_url = str(restaurant["image_url"])
        rest_id = str(restaurant["id"])
        out_path = output_dir / f"{rest_id}.jpg"

        try:
            time.sleep(rate_limit)
            resp = session.get(image_url, timeout=15, stream=True)
            resp.raise_for_status()

            with open(out_path, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)

            logger.info(
                "  %d/%d: %s → %s",
                i, len(needs_download),
                restaurant.get("name"),
                out_path.name,
            )
        except requests.RequestException as exc:
            logger.warning(
                "  %d/%d: %s — download failed: %s",
                i, len(needs_download),
                restaurant.get("name"),
                exc,
            )

    # Update all restaurants with local image paths
    for restaurant in restaurants:
        rest_id = str(restaurant.get("id", ""))
        local_path = output_dir / f"{rest_id}.jpg"
        if local_path.exists():
            # Path relative to the app's public dir
            restaurant["image_url"] = f"/images/{rest_id}.jpg"

    downloaded = sum(1 for r in restaurants if str(r.get("image_url", "")).startswith("/images/"))
    logger.info("Images: %d/%d have local files", downloaded, len(restaurants))

    return restaurants
