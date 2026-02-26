"""Quick script to geocode existing normalized data without re-crawling."""
import json
import logging
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.geocoder import Geocoder

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
normalized_path = DATA_DIR / "restaurants.normalized.json"
output_path = DATA_DIR / "restaurants.json"

data = json.loads(normalized_path.read_text(encoding="utf-8"))
logging.info("Loaded %d restaurants", len(data))

geocoder = Geocoder(cache_path=DATA_DIR / ".geocode_cache.json")
result = geocoder.geocode_restaurants(data)

output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

geocoded = sum(1 for r in result if r.get("lat"))
logging.info("Done: %d of %d geocoded → %s", geocoded, len(result), output_path)
