"""Geocoding via OpenStreetMap Nominatim with hybrid cache.

Uses file-based cache locally (persists across restarts) and falls back
to in-memory cache on serverless platforms with read-only filesystems.
"""

import json
import logging
import httpx
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_FILE = Path(__file__).parent.parent / "geocode_cache.json"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "eBirdExplorer/1.0 (personal birding tool)"

# In-memory fallback cache
_memory_cache: dict = {}


def _load_cache() -> dict:
    """Load from file cache, fall back to memory cache."""
    try:
        if CACHE_FILE.exists():
            cache = json.loads(CACHE_FILE.read_text())
            logger.debug(f"Loaded geocode cache from file ({len(cache)} entries)")
            return cache
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"Could not load geocode cache file: {e}")
    return _memory_cache.copy()


def _save_cache(cache: dict) -> None:
    """Try to save to file, silently fall back to memory-only on failure."""
    global _memory_cache
    _memory_cache = cache
    try:
        CACHE_FILE.write_text(json.dumps(cache, indent=2))
        logger.debug(f"Saved geocode cache to file ({len(cache)} entries)")
    except OSError as e:
        logger.debug(f"Could not write geocode cache file (using memory): {e}")


def _looks_like_us_zip(location: str) -> bool:
    """Check if input looks like a US ZIP code (5 digits or 5+4 format)."""
    loc = location.strip()
    # 5 digits or 5 digits + hyphen + 4 digits
    if loc.isdigit() and len(loc) == 5:
        return True
    if len(loc) == 10 and loc[:5].isdigit() and loc[5] == '-' and loc[6:].isdigit():
        return True
    return False


async def geocode(location: str) -> dict | None:
    """
    Convert a location string to lat/lng coordinates.

    Returns dict with 'lat', 'lng', 'display_name' or None if not found.
    Results are cached (file-based locally, in-memory on serverless).
    """
    cache = _load_cache()
    cache_key = location.lower().strip()

    if cache_key in cache:
        logger.debug(f"Geocode cache hit for '{location}'")
        return cache[cache_key]

    # For US ZIP codes, append USA to avoid matching foreign postal codes
    query = location
    if _looks_like_us_zip(location):
        query = f"{location}, USA"

    logger.debug(f"Geocoding '{location}' via Nominatim API")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            NOMINATIM_URL,
            params={
                "q": query,
                "format": "json",
                "limit": 1,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=10.0,
        )
        response.raise_for_status()
        results = response.json()

    if not results:
        logger.info(f"Geocoding found no results for '{location}'")
        return None

    result = results[0]
    geocoded = {
        "lat": float(result["lat"]),
        "lng": float(result["lon"]),
        "display_name": result["display_name"],
    }

    logger.info(f"Geocoded '{location}' -> {geocoded['display_name']}")
    cache[cache_key] = geocoded
    _save_cache(cache)
    return geocoded
