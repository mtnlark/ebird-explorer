"""eBird API client with async support."""

import httpx
import os
from dotenv import load_dotenv

load_dotenv()

EBIRD_API_KEY = os.getenv("EBIRD_API_KEY")
EBIRD_BASE_URL = "https://api.ebird.org/v2"


class EBirdClient:
    def __init__(self):
        self.api_key = EBIRD_API_KEY
        if not self.api_key:
            raise ValueError("EBIRD_API_KEY not found in environment")

    def _headers(self) -> dict:
        return {"X-eBirdApiToken": self.api_key}

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
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{EBIRD_BASE_URL}/data/obs/geo/recent",
                params={
                    "lat": lat,
                    "lng": lng,
                    "dist": min(dist_km, 50),
                    "back": min(back, 30),
                    "sort": "date",
                },
                headers=self._headers(),
                timeout=15.0,
            )
            response.raise_for_status()
            return response.json()

    async def get_notable_observations(
        self,
        lat: float,
        lng: float,
        dist_km: int = 16,
        back: int = 14,
    ) -> list[dict]:
        """Get notable (rare/unusual) observations near a location."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{EBIRD_BASE_URL}/data/obs/geo/recent/notable",
                params={
                    "lat": lat,
                    "lng": lng,
                    "dist": min(dist_km, 50),
                    "back": min(back, 30),
                },
                headers=self._headers(),
                timeout=15.0,
            )
            response.raise_for_status()
            return response.json()

    async def get_nearby_hotspots(
        self,
        lat: float,
        lng: float,
        dist_km: int = 16,
    ) -> list[dict]:
        """Get birding hotspots near a location."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{EBIRD_BASE_URL}/ref/hotspot/geo",
                params={
                    "lat": lat,
                    "lng": lng,
                    "dist": min(dist_km, 50),
                    "fmt": "json",
                },
                headers=self._headers(),
                timeout=15.0,
            )
            response.raise_for_status()
            return response.json()

    async def get_hotspot_observations(
        self,
        loc_id: str,
        back: int = 14,
    ) -> list[dict]:
        """Get recent observations at a specific hotspot."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{EBIRD_BASE_URL}/data/obs/{loc_id}/recent",
                params={"back": min(back, 30)},
                headers=self._headers(),
                timeout=15.0,
            )
            response.raise_for_status()
            return response.json()

    async def get_hotspot_info(self, loc_id: str) -> dict | None:
        """Get info about a specific hotspot."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{EBIRD_BASE_URL}/ref/hotspot/info/{loc_id}",
                headers=self._headers(),
                timeout=15.0,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()


# Singleton instance
ebird = EBirdClient()
