"""Tests for backend/geocoding.py - Nominatim geocoding with caching."""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path


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
        from backend.geocoding import geocode, _memory_cache

        cached_data = {
            "lat": 40.7128,
            "lng": -74.0060,
            "display_name": "New York, NY, USA",
        }

        with patch("backend.geocoding._load_cache", return_value={"new york": cached_data}):
            result = await geocode("New York")

            assert result == cached_data

    @pytest.mark.asyncio
    async def test_fetches_from_api_on_cache_miss(self):
        """Test that API is called when location not in cache."""
        from backend.geocoding import geocode

        api_response = [{
            "lat": "40.7128",
            "lon": "-74.0060",
            "display_name": "New York, NY, USA",
        }]

        with patch("backend.geocoding._load_cache", return_value={}):
            with patch("backend.geocoding._save_cache"):
                with patch("httpx.AsyncClient") as MockClient:
                    mock_response = MagicMock()
                    mock_response.json.return_value = api_response
                    mock_response.raise_for_status = MagicMock()

                    mock_client = AsyncMock()
                    mock_client.get = AsyncMock(return_value=mock_response)
                    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client.__aexit__ = AsyncMock()
                    MockClient.return_value = mock_client

                    result = await geocode("New York")

                    assert result["lat"] == 40.7128
                    assert result["lng"] == -74.0060

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        """Test that None is returned when location not found."""
        from backend.geocoding import geocode

        with patch("backend.geocoding._load_cache", return_value={}):
            with patch("httpx.AsyncClient") as MockClient:
                mock_response = MagicMock()
                mock_response.json.return_value = []  # Empty results
                mock_response.raise_for_status = MagicMock()

                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock()
                MockClient.return_value = mock_client

                result = await geocode("NonexistentPlace12345")

                assert result is None

    @pytest.mark.asyncio
    async def test_us_zip_appends_usa(self):
        """Test that US ZIP codes get USA appended to query."""
        from backend.geocoding import geocode

        api_response = [{
            "lat": "40.7484",
            "lon": "-73.9967",
            "display_name": "10001, New York, USA",
        }]

        with patch("backend.geocoding._load_cache", return_value={}):
            with patch("backend.geocoding._save_cache"):
                with patch("httpx.AsyncClient") as MockClient:
                    mock_response = MagicMock()
                    mock_response.json.return_value = api_response
                    mock_response.raise_for_status = MagicMock()

                    mock_client = AsyncMock()
                    mock_client.get = AsyncMock(return_value=mock_response)
                    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client.__aexit__ = AsyncMock()
                    MockClient.return_value = mock_client

                    await geocode("10001")

                    # Check that the query included ", USA"
                    call_args = mock_client.get.call_args
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

            assert result1 == cached_data
            assert result2 == cached_data
            assert result3 == cached_data


class TestCachePersistence:
    """Tests for cache loading and saving."""

    def test_load_cache_from_file(self, tmp_path):
        """Test that cache loads from file when it exists."""
        from backend.geocoding import _load_cache, CACHE_FILE

        cache_data = {"test location": {"lat": 1.0, "lng": 2.0, "display_name": "Test"}}

        with patch("backend.geocoding.CACHE_FILE", tmp_path / "cache.json"):
            (tmp_path / "cache.json").write_text(json.dumps(cache_data))

            from backend import geocoding
            geocoding.CACHE_FILE = tmp_path / "cache.json"

            result = geocoding._load_cache()
            assert result == cache_data

    def test_load_cache_returns_memory_on_file_error(self):
        """Test that memory cache is returned when file read fails."""
        from backend.geocoding import _load_cache, _memory_cache

        with patch("backend.geocoding.CACHE_FILE") as mock_path:
            mock_path.exists.return_value = True
            mock_path.read_text.side_effect = OSError("Permission denied")

            # Should return memory cache (which starts empty)
            result = _load_cache()
            assert isinstance(result, dict)

    def test_save_cache_handles_readonly_filesystem(self):
        """Test that save_cache doesn't raise on read-only filesystem."""
        from backend.geocoding import _save_cache

        with patch("backend.geocoding.CACHE_FILE") as mock_path:
            mock_path.write_text.side_effect = OSError("Read-only filesystem")

            # Should not raise
            _save_cache({"test": "data"})
