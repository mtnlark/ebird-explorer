"""eBird API client with async support."""

import logging

import httpx

from .config import settings
from .models import Hotspot, HotspotInfo, Observation, Species

logger = logging.getLogger(__name__)

EBIRD_BASE_URL = "https://api.ebird.org/v2"


class EBirdAPIError(Exception):
    """Base exception for eBird API errors."""

    pass


class EBirdAuthError(EBirdAPIError):
    """Invalid or missing API key."""

    pass


class EBirdRateLimitError(EBirdAPIError):
    """API rate limit exceeded."""

    pass


class EBirdTimeoutError(EBirdAPIError):
    """Request timed out."""

    pass


class EBirdNetworkError(EBirdAPIError):
    """Network connectivity error."""

    pass


class EBirdClient:
    def __init__(self):
        self.api_key = settings.ebird_api_key
        # Shared HTTP client for connection pooling
        self._client: httpx.AsyncClient | None = None

    def _headers(self) -> dict:
        return {"X-eBirdApiToken": self.api_key}

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the shared HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=EBIRD_BASE_URL,
                headers=self._headers(),
                timeout=settings.ebird_timeout,
            )
        return self._client

    async def aclose(self) -> None:
        """Close the HTTP client. Call this on application shutdown."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _handle_response(self, response: httpx.Response) -> None:
        """Check response status and raise appropriate exceptions."""
        if response.status_code == 401:
            raise EBirdAuthError("Invalid eBird API key")
        if response.status_code == 403:
            raise EBirdAuthError("eBird API access forbidden - check your API key")
        if response.status_code == 429:
            raise EBirdRateLimitError("eBird API rate limit exceeded - please wait and try again")
        if response.status_code >= 500:
            raise EBirdAPIError(f"eBird server error ({response.status_code}) - try again later")
        response.raise_for_status()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Make an API request with proper error handling."""
        client = await self._get_client()
        logger.debug(f"eBird API request: {method} {endpoint}")
        try:
            response = await client.request(
                method,
                endpoint,
                params=params,
                timeout=timeout,
            )
            self._handle_response(response)
            logger.debug(f"eBird API response: {response.status_code}")
            return response
        except httpx.TimeoutException as e:
            logger.warning(f"eBird API timeout: {endpoint}")
            raise EBirdTimeoutError("eBird API request timed out - the server may be slow") from e
        except httpx.ConnectError as e:
            logger.error(f"eBird API connection error: {endpoint}")
            raise EBirdNetworkError(
                "Could not connect to eBird API - check your internet connection"
            ) from e
        except httpx.RequestError as e:
            logger.error(f"eBird API request error: {endpoint} - {e}")
            raise EBirdNetworkError(f"Network error: {e}") from e

    async def get_recent_observations(
        self,
        lat: float,
        lng: float,
        dist_km: int = 16,  # ~10 miles
        back: int = 14,  # days
    ) -> list[Observation]:
        """
        Get recent observations near a location.

        Args:
            lat: Latitude
            lng: Longitude
            dist_km: Search radius in kilometers (max 50)
            back: Days back to search (max 30)

        Returns:
            List of observation dicts sorted by date (most recent first)
        """
        response = await self._request(
            "GET",
            "/data/obs/geo/recent",
            params={
                "lat": lat,
                "lng": lng,
                "dist": min(dist_km, 50),
                "back": min(back, 30),
                "sort": "date",
            },
        )
        return [Observation.model_validate(obs) for obs in response.json()]

    async def get_notable_observations(
        self,
        lat: float,
        lng: float,
        dist_km: int = 16,
        back: int = 14,
    ) -> list[Observation]:
        """Get notable (rare/unusual) observations near a location."""
        response = await self._request(
            "GET",
            "/data/obs/geo/recent/notable",
            params={
                "lat": lat,
                "lng": lng,
                "dist": min(dist_km, 50),
                "back": min(back, 30),
            },
        )
        return [Observation.model_validate(obs) for obs in response.json()]

    async def get_nearby_hotspots(
        self,
        lat: float,
        lng: float,
        dist_km: int = 16,
    ) -> list[Hotspot]:
        """Get birding hotspots near a location."""
        response = await self._request(
            "GET",
            "/ref/hotspot/geo",
            params={
                "lat": lat,
                "lng": lng,
                "dist": min(dist_km, 50),
                "fmt": "json",
            },
        )
        return [Hotspot.model_validate(h) for h in response.json()]

    async def get_hotspot_observations(
        self,
        loc_id: str,
        back: int = 14,
    ) -> list[Observation]:
        """Get recent observations at a specific hotspot."""
        response = await self._request(
            "GET",
            f"/data/obs/{loc_id}/recent",
            params={"back": min(back, 30)},
        )
        return [Observation.model_validate(obs) for obs in response.json()]

    async def get_hotspot_info(self, loc_id: str) -> HotspotInfo | None:
        """Get info about a specific hotspot. Returns None if not found."""
        client = await self._get_client()
        try:
            response = await client.request(
                "GET",
                f"/ref/hotspot/info/{loc_id}",
            )
            # Handle 404 specially - return None instead of raising
            if response.status_code == 404:
                return None
            self._handle_response(response)
            return HotspotInfo.model_validate(response.json())
        except httpx.TimeoutException as e:
            raise EBirdTimeoutError("eBird API request timed out - the server may be slow") from e
        except httpx.ConnectError as e:
            raise EBirdNetworkError(
                "Could not connect to eBird API - check your internet connection"
            ) from e
        except httpx.RequestError as e:
            raise EBirdNetworkError(f"Network error: {e}") from e

    async def get_taxonomy(self) -> list[Species]:
        """Get eBird taxonomy (species list) for autocomplete."""
        response = await self._request(
            "GET",
            "/ref/taxonomy/ebird",
            params={"fmt": "json", "cat": "species"},
            timeout=settings.ebird_taxonomy_timeout,
        )
        return [Species.model_validate(s) for s in response.json()]

    async def get_nearest_species_observations(
        self,
        species_code: str,
        lat: float,
        lng: float,
        dist_km: int = 50,
        back: int = 14,
    ) -> list[Observation]:
        """Get nearest recent observations of a specific species."""
        response = await self._request(
            "GET",
            f"/data/nearest/geo/recent/{species_code}",
            params={
                "lat": lat,
                "lng": lng,
                "dist": min(dist_km, 50),
                "back": min(back, 30),
            },
        )
        return [Observation.model_validate(obs) for obs in response.json()]


# Singleton instance
ebird = EBirdClient()
