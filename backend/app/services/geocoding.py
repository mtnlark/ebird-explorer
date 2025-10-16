import httpx
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta

class GeocodingService:
    def __init__(self):
        self.base_url = "https://nominatim.openstreetmap.org"
        self.headers = {"User-Agent": "eBird-Explorer/1.0 (Educational Project)"}
        # Simple in-memory cache to avoid redundant API calls
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.cache_duration = timedelta(hours=24)

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get data from cache if it exists and is not expired"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.cache_duration:
                return data
        return None

    def _add_to_cache(self, key: str, data: Any):
        """Add data to cache with current timestamp"""
        self.cache[key] = (data, datetime.now())

    async def geocode_address(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Convert address/town/ZIP to coordinates

        Returns:
            Dict with 'lat', 'lng', and 'display_name' if found, None otherwise
        """
        # Check cache first
        cache_key = f"geocode:{address.lower()}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        url = f"{self.base_url}/search"
        params = {
            "q": address,
            "format": "json",
            "limit": 1,
            "countrycodes": "us"  # Bias towards US results
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()

                    if data and len(data) > 0:
                        result = {
                            "lat": float(data[0]["lat"]),
                            "lng": float(data[0]["lon"]),
                            "display_name": data[0].get("display_name", address)
                        }
                        # Cache the result
                        self._add_to_cache(cache_key, result)
                        return result

        except httpx.HTTPError as e:
            print(f"Geocoding error: {e}")

        return None

    async def reverse_geocode(self, lat: float, lng: float) -> Optional[str]:
        """
        Convert coordinates to address/location name

        Returns:
            Human-readable location name if found, None otherwise
        """
        # Check cache first
        cache_key = f"reverse:{lat:.4f},{lng:.4f}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        url = f"{self.base_url}/reverse"
        params = {
            "lat": lat,
            "lon": lng,
            "format": "json"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()

                    if "display_name" in data:
                        display_name = data["display_name"]
                        # Cache the result
                        self._add_to_cache(cache_key, display_name)
                        return display_name

        except httpx.HTTPError as e:
            print(f"Reverse geocoding error: {e}")

        return None
