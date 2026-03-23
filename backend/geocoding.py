"""Geocoding via OpenStreetMap Nominatim with hybrid cache.

Uses file-based cache locally (persists across restarts) and falls back
to in-memory cache on serverless platforms with read-only filesystems.
"""

import json
import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# Configuration constants
CACHE_FILE = Path(__file__).parent.parent / "geocode_cache.json"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "eBirdExplorer/1.0 (personal birding tool)"
NOMINATIM_TIMEOUT = 10.0

# In-memory fallback cache
_memory_cache: dict = {}


class GeocodingError(Exception):
    """Base exception for geocoding errors."""

    pass


class GeocodingNetworkError(GeocodingError):
    """Network connectivity error during geocoding."""

    pass


class GeocodingTimeoutError(GeocodingError):
    """Request timed out during geocoding."""

    pass


class GeocodingClient:
    """Nominatim geocoding client with connection pooling."""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the shared HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={"User-Agent": USER_AGENT},
                timeout=NOMINATIM_TIMEOUT,
            )
        return self._client

    async def aclose(self) -> None:
        """Close the HTTP client. Call this on application shutdown."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def geocode(self, location: str) -> dict | None:
        """
        Convert a location string to lat/lng coordinates.

        Returns dict with 'lat', 'lng', 'display_name' or None if not found.
        Results are cached (file-based locally, in-memory on serverless).

        Raises:
            GeocodingNetworkError: If unable to connect to Nominatim
            GeocodingTimeoutError: If the request times out
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

        try:
            client = await self._get_client()
            response = await client.get(
                NOMINATIM_URL,
                params={
                    "q": query,
                    "format": "json",
                    "limit": 1,
                },
            )
            response.raise_for_status()
            results = response.json()
        except httpx.TimeoutException as e:
            logger.warning(f"Geocoding timeout for '{location}'")
            raise GeocodingTimeoutError(
                "Geocoding request timed out - the server may be slow"
            ) from e
        except httpx.ConnectError as e:
            logger.error(f"Geocoding connection error for '{location}'")
            raise GeocodingNetworkError(
                "Could not connect to geocoding service - check your internet connection"
            ) from e
        except httpx.RequestError as e:
            logger.error(f"Geocoding request error for '{location}': {e}")
            raise GeocodingNetworkError(f"Geocoding network error: {e}") from e

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
    return (loc.isdigit() and len(loc) == 5) or (
        len(loc) == 10
        and loc[:5].isdigit()
        and loc[5] == "-"
        and loc[6:].isdigit()
    )


# Singleton instance
_geocoding_client = GeocodingClient()


async def geocode(location: str) -> dict | None:
    """
    Convert a location string to lat/lng coordinates.

    This is a convenience function that uses the singleton client.
    Returns dict with 'lat', 'lng', 'display_name' or None if not found.
    """
    return await _geocoding_client.geocode(location)


async def close_geocoding_client() -> None:
    """Close the geocoding client. Call this on application shutdown."""
    await _geocoding_client.aclose()
