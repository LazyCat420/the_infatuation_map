# Pipeline — The Infatuation SF Restaurant Scraper

## What it does

Crawls The Infatuation's San Francisco section to extract restaurant data (name, address, cuisine, neighborhood, tags) and outputs a `restaurants.json` file for the map PWA.

## Quick Start

```bash
cd pipeline
python -m venv venv
.\venv\Scripts\activate       # Windows
pip install -r requirements.txt

# Run full pipeline (without geocoding)
python -m pipeline.run --refresh --skip-geocoding

# Run with geocoding (requires Google Maps API key)
set GOOGLE_MAPS_API_KEY=your-key-here
python -m pipeline.run --refresh

# Quick test with limited guides
python -m pipeline.run --refresh --max-guides 3 --skip-geocoding
```

## Output Files

- `data/restaurants.raw.json` — Raw extracted data (before dedup)
- `data/restaurants.normalized.json` — Deduplicated and normalized
- `data/restaurants.json` — Final output with coordinates (used by the app)

## Architecture

1. **Crawler** (`crawler.py`) — Discovers review/guide URLs from the SF hub
2. **Extractor** (`extractor.py`) — Parses each page for restaurant data (JSON-LD → HTML fallback)
3. **Normalizer** (`normalizer.py`) — Deduplicates and generates stable IDs
4. **Geocoder** (`geocoder.py`) — Fills in missing lat/lng via Google Geocoding API (cached)
