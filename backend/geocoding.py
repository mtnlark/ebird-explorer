"""Geocoding via OpenStreetMap Nominatim with persistent JSON cache."""

import json
import httpx
from pathlib import Path

CACHE_FILE = Path(__file__).parent.parent / "geocode_cache.json"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "eBirdExplorer/1.0 (personal birding tool)"


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text())
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_FILE.write_text(json.dumps(cache, indent=2))


async def geocode(location: str) -> dict | None:
    """
    Convert a location string to lat/lng coordinates.

    Returns dict with 'lat', 'lng', 'display_name' or None if not found.
    Results are cached permanently (coordinates don't change).
    """
    cache = _load_cache()
    cache_key = location.lower().strip()

    if cache_key in cache:
        return cache[cache_key]

    async with httpx.AsyncClient() as client:
        response = await client.get(
            NOMINATIM_URL,
            params={
                "q": location,
                "format": "json",
                "limit": 1,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=10.0,
        )
        response.raise_for_status()
        results = response.json()

    if not results:
        return None

    result = results[0]
    geocoded = {
        "lat": float(result["lat"]),
        "lng": float(result["lon"]),
        "display_name": result["display_name"],
    }

    cache[cache_key] = geocoded
    _save_cache(cache)

    return geocoded
