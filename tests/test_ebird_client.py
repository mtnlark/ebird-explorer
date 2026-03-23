"""Tests for backend/ebird_client.py - eBird API client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.ebird_client import (
    EBirdAPIError,
    EBirdAuthError,
    EBirdClient,
    EBirdNetworkError,
    EBirdRateLimitError,
    EBirdTimeoutError,
)


class TestEBirdClientInitialization:
    """Tests for EBirdClient initialization."""

    def test_client_requires_api_key(self):
        """Test that client raises error without API key."""
        with patch("backend.ebird_client.EBIRD_API_KEY", None), pytest.raises(
            ValueError, match="EBIRD_API_KEY"
        ):
            EBirdClient()

    def test_client_initializes_with_api_key(self):
        """Test that client initializes when API key is present."""
        with patch("backend.ebird_client.EBIRD_API_KEY", "test_key"):
            client = EBirdClient()
            assert client.api_key == "test_key"
            assert client._client is None  # Lazy initialization


class TestEBirdClientConnectionPooling:
    """Tests for HTTP connection pooling."""

    @pytest.mark.asyncio
    async def test_client_creates_http_client_lazily(self):
        """Test that AsyncClient is created on first request."""
        with patch("backend.ebird_client.EBIRD_API_KEY", "test_key"):
            client = EBirdClient()
            assert client._client is None

            # Mock httpx.AsyncClient
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []

            with patch("httpx.AsyncClient") as MockAsyncClient:
                mock_http_client = AsyncMock()
                mock_http_client.request = AsyncMock(return_value=mock_response)
                MockAsyncClient.return_value = mock_http_client

                await client.get_recent_observations(lat=40.0, lng=-74.0)

                # Client should now be initialized
                assert client._client is not None
                MockAsyncClient.assert_called_once()

    @pytest.mark.asyncio
    async def test_client_reuses_http_client(self):
        """Test that the same AsyncClient is reused across requests."""
        with patch("backend.ebird_client.EBIRD_API_KEY", "test_key"):
            client = EBirdClient()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []

            with patch("httpx.AsyncClient") as MockAsyncClient:
                mock_http_client = AsyncMock()
                mock_http_client.request = AsyncMock(return_value=mock_response)
                MockAsyncClient.return_value = mock_http_client

                # Make two requests
                await client.get_recent_observations(lat=40.0, lng=-74.0)
                await client.get_notable_observations(lat=40.0, lng=-74.0)

                # AsyncClient should only be instantiated once
                MockAsyncClient.assert_called_once()
                # But request should be called twice
                assert mock_http_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_aclose_closes_client(self):
        """Test that aclose properly closes the HTTP client."""
        with patch("backend.ebird_client.EBIRD_API_KEY", "test_key"):
            client = EBirdClient()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []

            with patch("httpx.AsyncClient") as MockAsyncClient:
                mock_http_client = AsyncMock()
                mock_http_client.request = AsyncMock(return_value=mock_response)
                mock_http_client.aclose = AsyncMock()
                MockAsyncClient.return_value = mock_http_client

                # Initialize the client
                await client.get_recent_observations(lat=40.0, lng=-74.0)
                assert client._client is not None

                # Close it
                await client.aclose()

                mock_http_client.aclose.assert_called_once()
                assert client._client is None

    @pytest.mark.asyncio
    async def test_aclose_handles_uninitialized_client(self):
        """Test that aclose works even if client was never initialized."""
        with patch("backend.ebird_client.EBIRD_API_KEY", "test_key"):
            client = EBirdClient()
            # Should not raise
            await client.aclose()
            assert client._client is None


class TestEBirdClientErrorHandling:
    """Tests for error handling in eBird API calls."""

    @pytest.fixture
    def client_with_mock(self):
        """Create a client with mocked HTTP client."""
        with patch("backend.ebird_client.EBIRD_API_KEY", "test_key"):
            client = EBirdClient()
            mock_http_client = AsyncMock()
            client._client = mock_http_client
            yield client, mock_http_client

    @pytest.mark.asyncio
    async def test_auth_error_on_401(self, client_with_mock):
        """Test that 401 response raises EBirdAuthError."""
        client, mock_http = client_with_mock
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_http.request = AsyncMock(return_value=mock_response)

        with pytest.raises(EBirdAuthError, match="Invalid eBird API key"):
            await client.get_recent_observations(lat=40.0, lng=-74.0)

    @pytest.mark.asyncio
    async def test_auth_error_on_403(self, client_with_mock):
        """Test that 403 response raises EBirdAuthError."""
        client, mock_http = client_with_mock
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_http.request = AsyncMock(return_value=mock_response)

        with pytest.raises(EBirdAuthError, match="forbidden"):
            await client.get_recent_observations(lat=40.0, lng=-74.0)

    @pytest.mark.asyncio
    async def test_rate_limit_error_on_429(self, client_with_mock):
        """Test that 429 response raises EBirdRateLimitError."""
        client, mock_http = client_with_mock
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_http.request = AsyncMock(return_value=mock_response)

        with pytest.raises(EBirdRateLimitError, match="rate limit"):
            await client.get_recent_observations(lat=40.0, lng=-74.0)

    @pytest.mark.asyncio
    async def test_server_error_on_500(self, client_with_mock):
        """Test that 500+ response raises EBirdAPIError."""
        client, mock_http = client_with_mock
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_http.request = AsyncMock(return_value=mock_response)

        with pytest.raises(EBirdAPIError, match="server error"):
            await client.get_recent_observations(lat=40.0, lng=-74.0)

    @pytest.mark.asyncio
    async def test_server_error_on_503(self, client_with_mock):
        """Test that 503 response raises EBirdAPIError."""
        client, mock_http = client_with_mock
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_http.request = AsyncMock(return_value=mock_response)

        with pytest.raises(EBirdAPIError, match="server error"):
            await client.get_recent_observations(lat=40.0, lng=-74.0)

    @pytest.mark.asyncio
    async def test_timeout_error(self, client_with_mock):
        """Test that timeout raises EBirdTimeoutError."""
        client, mock_http = client_with_mock
        mock_http.request = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with pytest.raises(EBirdTimeoutError, match="timed out"):
            await client.get_recent_observations(lat=40.0, lng=-74.0)

    @pytest.mark.asyncio
    async def test_connect_error(self, client_with_mock):
        """Test that connection error raises EBirdNetworkError."""
        client, mock_http = client_with_mock
        mock_http.request = AsyncMock(side_effect=httpx.ConnectError("failed"))

        with pytest.raises(EBirdNetworkError, match="Could not connect"):
            await client.get_recent_observations(lat=40.0, lng=-74.0)

    @pytest.mark.asyncio
    async def test_generic_request_error(self, client_with_mock):
        """Test that generic request errors raise EBirdNetworkError."""
        client, mock_http = client_with_mock
        mock_http.request = AsyncMock(side_effect=httpx.RequestError("unknown error"))

        with pytest.raises(EBirdNetworkError, match="Network error"):
            await client.get_recent_observations(lat=40.0, lng=-74.0)


class TestEBirdClientMethods:
    """Tests for individual API methods."""

    @pytest.fixture
    def client_with_mock(self):
        """Create a client with mocked HTTP client."""
        with patch("backend.ebird_client.EBIRD_API_KEY", "test_key"):
            client = EBirdClient()
            mock_http_client = AsyncMock()
            client._client = mock_http_client
            yield client, mock_http_client

    @pytest.mark.asyncio
    async def test_get_recent_observations_params(self, client_with_mock):
        """Test that get_recent_observations passes correct parameters."""
        client, mock_http = client_with_mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_http.request = AsyncMock(return_value=mock_response)

        await client.get_recent_observations(lat=40.7, lng=-74.0, dist_km=25, back=7)

        call_args = mock_http.request.call_args
        assert call_args[1]["params"]["lat"] == 40.7
        assert call_args[1]["params"]["lng"] == -74.0
        assert call_args[1]["params"]["dist"] == 25
        assert call_args[1]["params"]["back"] == 7
        assert call_args[1]["params"]["sort"] == "date"

    @pytest.mark.asyncio
    async def test_distance_capped_at_50(self, client_with_mock):
        """Test that distance is capped at 50km max."""
        client, mock_http = client_with_mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_http.request = AsyncMock(return_value=mock_response)

        await client.get_recent_observations(lat=40.7, lng=-74.0, dist_km=100)

        call_args = mock_http.request.call_args
        assert call_args[1]["params"]["dist"] == 50  # Should be capped

    @pytest.mark.asyncio
    async def test_days_capped_at_30(self, client_with_mock):
        """Test that back days is capped at 30."""
        client, mock_http = client_with_mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_http.request = AsyncMock(return_value=mock_response)

        await client.get_recent_observations(lat=40.7, lng=-74.0, back=60)

        call_args = mock_http.request.call_args
        assert call_args[1]["params"]["back"] == 30  # Should be capped

    @pytest.mark.asyncio
    async def test_get_taxonomy_longer_timeout(self, client_with_mock):
        """Test that get_taxonomy uses a longer timeout."""
        client, mock_http = client_with_mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_http.request = AsyncMock(return_value=mock_response)

        await client.get_taxonomy()

        call_args = mock_http.request.call_args
        assert call_args[1]["timeout"] == 30.0


class TestGetHotspotInfo:
    """Tests for get_hotspot_info method."""

    @pytest.fixture
    def client_with_mock(self):
        """Create a client with mocked HTTP client."""
        with patch("backend.ebird_client.EBIRD_API_KEY", "test_key"):
            client = EBirdClient()
            mock_http_client = AsyncMock()
            client._client = mock_http_client
            yield client, mock_http_client

    @pytest.mark.asyncio
    async def test_returns_none_on_404(self, client_with_mock):
        """Test that 404 response returns None instead of raising."""
        client, mock_http = client_with_mock
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_http.request = AsyncMock(return_value=mock_response)

        result = await client.get_hotspot_info("L999999")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_info_on_success(self, client_with_mock):
        """Test that successful response returns hotspot info."""
        client, mock_http = client_with_mock
        hotspot_data = {"locId": "L123456", "name": "Central Park"}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = hotspot_data
        mock_response.raise_for_status = MagicMock()
        mock_http.request = AsyncMock(return_value=mock_response)

        result = await client.get_hotspot_info("L123456")

        assert result == hotspot_data

    @pytest.mark.asyncio
    async def test_raises_on_other_errors(self, client_with_mock):
        """Test that non-404 errors still raise."""
        client, mock_http = client_with_mock
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_http.request = AsyncMock(return_value=mock_response)

        with pytest.raises(EBirdAPIError, match="server error"):
            await client.get_hotspot_info("L123456")
