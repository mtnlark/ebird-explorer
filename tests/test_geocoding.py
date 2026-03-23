"""Tests for backend/geocoding.py - Nominatim geocoding with caching."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestLooksLikeUsZip:
    """Tests for US ZIP code detection."""

    def test_five_digit_zip(self):
        """Test that 5-digit ZIP codes are detected."""
        from backend.geocoding import _looks_like_us_zip

        assert _looks_like_us_zip("10001") is True
        assert _looks_like_us_zip("90210") is True
        assert _looks_like_us_zip("00000") is True

    def test_zip_plus_four(self):
        """Test that ZIP+4 format is detected."""
        from backend.geocoding import _looks_like_us_zip

        assert _looks_like_us_zip("10001-1234") is True
        assert _looks_like_us_zip("90210-0001") is True

    def test_non_zip_strings(self):
        """Test that non-ZIP strings are not detected."""
        from backend.geocoding import _looks_like_us_zip

        assert _looks_like_us_zip("New York") is False
        assert _looks_like_us_zip("1234") is False  # Too short
        assert _looks_like_us_zip("123456") is False  # Too long
        assert _looks_like_us_zip("1234a") is False  # Contains letter
        assert _looks_like_us_zip("") is False

    def test_zip_with_spaces(self):
        """Test ZIP detection handles whitespace."""
        from backend.geocoding import _looks_like_us_zip

        assert _looks_like_us_zip(" 10001 ") is True
        assert _looks_like_us_zip("  90210  ") is True


class TestGeocode:
    """Tests for the geocode function."""

    @pytest.mark.asyncio
    async def test_returns_cached_result(self):
        """Test that cached results are returned without API call."""
        from backend.geocoding import geocode

        cached_data = {
            "lat": 40.7128,
            "lng": -74.0060,
            "display_name": "New York, NY, USA",
        }

        with patch("backend.geocoding._load_cache", return_value={"new york": cached_data}):
            result = await geocode("New York")

            assert result.lat == cached_data["lat"]
            assert result.lng == cached_data["lng"]
            assert result.display_name == cached_data["display_name"]

    @pytest.mark.asyncio
    async def test_fetches_from_api_on_cache_miss(self):
        """Test that API is called when location not in cache."""
        from backend.geocoding import geocode

        api_response = [
            {
                "lat": "40.7128",
                "lon": "-74.0060",
                "display_name": "New York, NY, USA",
            }
        ]

        with patch("backend.geocoding._load_cache", return_value={}), patch(
            "backend.geocoding._save_cache"
        ), patch("httpx.AsyncClient") as MockClient:
                    mock_response = MagicMock()
                    mock_response.json.return_value = api_response
                    mock_response.raise_for_status = MagicMock()

                    mock_client = AsyncMock()
                    mock_client.get = AsyncMock(return_value=mock_response)
                    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client.__aexit__ = AsyncMock()
                    MockClient.return_value = mock_client

                    result = await geocode("New York")

                    assert result.lat == 40.7128
                    assert result.lng == -74.0060

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        """Test that None is returned when location not found."""
        from backend.geocoding import GeocodingClient

        client = GeocodingClient()

        with patch("backend.geocoding._load_cache", return_value={}), patch.object(
            client, "_get_client"
        ) as mock_get_client:
            mock_response = MagicMock()
            mock_response.json.return_value = []  # Empty results
            mock_response.raise_for_status = MagicMock()

            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            result = await client.geocode("NonexistentPlace12345")

            assert result is None

    @pytest.mark.asyncio
    async def test_us_zip_appends_usa(self):
        """Test that US ZIP codes get USA appended to query."""
        from backend.geocoding import GeocodingClient

        client = GeocodingClient()

        api_response = [
            {
                "lat": "40.7484",
                "lon": "-73.9967",
                "display_name": "10001, New York, USA",
            }
        ]

        with patch("backend.geocoding._load_cache", return_value={}), patch(
            "backend.geocoding._save_cache"
        ), patch.object(client, "_get_client") as mock_get_client:
            mock_response = MagicMock()
            mock_response.json.return_value = api_response
            mock_response.raise_for_status = MagicMock()

            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            await client.geocode("10001")

            # Check that the query included ", USA"
            call_args = mock_http.get.call_args
            assert "10001, USA" in call_args[1]["params"]["q"]

    @pytest.mark.asyncio
    async def test_cache_key_is_lowercase(self):
        """Test that cache keys are normalized to lowercase."""
        from backend.geocoding import geocode

        cached_data = {
            "lat": 40.7128,
            "lng": -74.0060,
            "display_name": "New York, NY, USA",
        }

        with patch("backend.geocoding._load_cache", return_value={"new york": cached_data}):
            # Should hit cache even with different casing
            result1 = await geocode("New York")
            result2 = await geocode("NEW YORK")
            result3 = await geocode("new york")

            assert result1.lat == cached_data["lat"]
            assert result2.lat == cached_data["lat"]
            assert result3.lat == cached_data["lat"]


class TestCachePersistence:
    """Tests for cache loading and saving."""

    def test_load_cache_from_file(self, tmp_path):
        """Test that cache loads from file when it exists."""
        from backend.geocoding import _load_cache

        cache_data = {"test location": {"lat": 1.0, "lng": 2.0, "display_name": "Test"}}
        cache_file = tmp_path / "cache.json"
        cache_file.write_text(json.dumps(cache_data))

        with patch("backend.config.settings.cache_file", cache_file):
            result = _load_cache()
            assert result == cache_data

    def test_load_cache_returns_memory_on_file_error(self):
        """Test that memory cache is returned when file read fails."""
        from backend.geocoding import _load_cache

        with patch("backend.config.settings.cache_file") as mock_path:
            mock_path.exists.return_value = True
            mock_path.read_text.side_effect = OSError("Permission denied")

            # Should return memory cache (which starts empty)
            result = _load_cache()
            assert isinstance(result, dict)

    def test_save_cache_handles_readonly_filesystem(self):
        """Test that save_cache doesn't raise on read-only filesystem."""
        from backend.geocoding import _save_cache

        with patch("backend.config.settings.cache_file") as mock_path:
            mock_path.write_text.side_effect = OSError("Read-only filesystem")

            # Should not raise
            _save_cache({"test": "data"})


class TestGeocodingErrorHandling:
    """Tests for geocoding error handling."""

    @pytest.mark.asyncio
    async def test_timeout_raises_geocoding_timeout_error(self):
        """Test that httpx timeout raises GeocodingTimeoutError."""
        import httpx

        from backend.geocoding import GeocodingClient, GeocodingTimeoutError

        client = GeocodingClient()

        with patch("backend.geocoding._load_cache", return_value={}), patch.object(
            client, "_get_client"
        ) as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_get_client.return_value = mock_http

            with pytest.raises(GeocodingTimeoutError, match="timed out"):
                await client.geocode("New York")

    @pytest.mark.asyncio
    async def test_connect_error_raises_geocoding_network_error(self):
        """Test that httpx connect error raises GeocodingNetworkError."""
        import httpx

        from backend.geocoding import GeocodingClient, GeocodingNetworkError

        client = GeocodingClient()

        with patch("backend.geocoding._load_cache", return_value={}), patch.object(
            client, "_get_client"
        ) as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=httpx.ConnectError("failed"))
            mock_get_client.return_value = mock_http

            with pytest.raises(GeocodingNetworkError, match="Could not connect"):
                await client.geocode("New York")

    @pytest.mark.asyncio
    async def test_request_error_raises_geocoding_network_error(self):
        """Test that generic httpx request error raises GeocodingNetworkError."""
        import httpx

        from backend.geocoding import GeocodingClient, GeocodingNetworkError

        client = GeocodingClient()

        with patch("backend.geocoding._load_cache", return_value={}), patch.object(
            client, "_get_client"
        ) as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=httpx.RequestError("unknown"))
            mock_get_client.return_value = mock_http

            with pytest.raises(GeocodingNetworkError, match="network error"):
                await client.geocode("New York")


class TestGeocodingClientPooling:
    """Tests for GeocodingClient connection pooling."""

    @pytest.mark.asyncio
    async def test_client_reuses_http_client(self):
        """Test that the same HTTP client is reused across calls."""
        from backend.geocoding import GeocodingClient

        client = GeocodingClient()
        assert client._client is None

        with patch("httpx.AsyncClient") as MockAsyncClient:
            mock_http = AsyncMock()
            MockAsyncClient.return_value = mock_http

            # Get client twice
            client1 = await client._get_client()
            client2 = await client._get_client()

            # Should be the same instance
            assert client1 is client2
            # AsyncClient should only be instantiated once
            MockAsyncClient.assert_called_once()

    @pytest.mark.asyncio
    async def test_aclose_closes_client(self):
        """Test that aclose properly closes the HTTP client."""
        from backend.geocoding import GeocodingClient

        client = GeocodingClient()

        with patch("httpx.AsyncClient") as MockAsyncClient:
            mock_http = AsyncMock()
            mock_http.aclose = AsyncMock()
            MockAsyncClient.return_value = mock_http

            # Initialize the client
            await client._get_client()
            assert client._client is not None

            # Close it
            await client.aclose()

            mock_http.aclose.assert_called_once()
            assert client._client is None

    @pytest.mark.asyncio
    async def test_aclose_handles_uninitialized_client(self):
        """Test that aclose works even if client was never initialized."""
        from backend.geocoding import GeocodingClient

        client = GeocodingClient()
        # Should not raise
        await client.aclose()
        assert client._client is None
