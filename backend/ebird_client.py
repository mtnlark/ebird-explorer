"""eBird API client with async support."""

import httpx
import os
from dotenv import load_dotenv

load_dotenv()

EBIRD_API_KEY = os.getenv("EBIRD_API_KEY")
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
        self.api_key = EBIRD_API_KEY
        if not self.api_key:
            raise ValueError("EBIRD_API_KEY not found in environment")

    def _headers(self) -> dict:
        return {"X-eBirdApiToken": self.api_key}

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
        timeout: float = 15.0,
    ) -> httpx.Response:
        """Make an API request with proper error handling."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method,
                    f"{EBIRD_BASE_URL}{endpoint}",
                    params=params,
                    headers=self._headers(),
                    timeout=timeout,
                )
                self._handle_response(response)
                return response
        except httpx.TimeoutException:
            raise EBirdTimeoutError("eBird API request timed out - the server may be slow")
        except httpx.ConnectError:
            raise EBirdNetworkError("Could not connect to eBird API - check your internet connection")
        except httpx.RequestError as e:
            raise EBirdNetworkError(f"Network error: {e}")

    async def get_recent_observations(
        self,
        lat: float,
        lng: float,
        dist_km: int = 16,  # ~10 miles
        back: int = 14,  # days
    ) -> list[dict]:
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
        return response.json()

    async def get_notable_observations(
        self,
        lat: float,
        lng: float,
        dist_km: int = 16,
        back: int = 14,
    ) -> list[dict]:
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
        return response.json()

    async def get_nearby_hotspots(
        self,
        lat: float,
        lng: float,
        dist_km: int = 16,
    ) -> list[dict]:
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
        return response.json()

    async def get_hotspot_observations(
        self,
        loc_id: str,
        back: int = 14,
    ) -> list[dict]:
        """Get recent observations at a specific hotspot."""
        response = await self._request(
            "GET",
            f"/data/obs/{loc_id}/recent",
            params={"back": min(back, 30)},
        )
        return response.json()

    async def get_hotspot_info(self, loc_id: str) -> dict | None:
        """Get info about a specific hotspot."""
        try:
            response = await self._request(
                "GET",
                f"/ref/hotspot/info/{loc_id}",
            )
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def get_taxonomy(self) -> list[dict]:
        """Get eBird taxonomy (species list) for autocomplete."""
        response = await self._request(
            "GET",
            "/ref/taxonomy/ebird",
            params={"fmt": "json", "cat": "species"},
            timeout=30.0,
        )
        return response.json()

    async def get_nearest_species_observations(
        self,
        species_code: str,
        lat: float,
        lng: float,
        dist_km: int = 50,
        back: int = 14,
    ) -> list[dict]:
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
        return response.json()


# Singleton instance
ebird = EBirdClient()
