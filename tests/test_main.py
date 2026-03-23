"""Tests for backend/main.py - FastAPI routes and utilities."""

from datetime import date, timedelta
from unittest.mock import patch

from backend.geocoding import GeocodingNetworkError, GeocodingTimeoutError  # noqa: F401


class TestFormatObsDate:
    """Tests for the format_obs_date utility function."""

    def test_format_today(self):
        """Test that today's date formats as 'Today, HH:MM AM/PM'."""
        from backend.main import format_obs_date

        today = date.today()
        obs_dt = f"{today.isoformat()} 14:30"

        result = format_obs_date(obs_dt)

        assert result.startswith("Today, ")
        assert "2:30 PM" in result

    def test_format_yesterday(self):
        """Test that yesterday's date formats as 'Yesterday, HH:MM AM/PM'."""
        from backend.main import format_obs_date

        yesterday = date.today() - timedelta(days=1)
        obs_dt = f"{yesterday.isoformat()} 09:15"

        result = format_obs_date(obs_dt)

        assert result.startswith("Yesterday, ")
        assert "9:15 AM" in result

    def test_format_yesterday_across_month_boundary(self):
        """Test yesterday detection works across month boundaries."""
        from backend.main import format_obs_date

        # Mock today as the 1st of a month
        with patch("backend.main.date") as mock_date:
            mock_date.today.return_value = date(2024, 2, 1)
            # Yesterday would be Jan 31
            obs_dt = "2024-01-31 10:00"

            result = format_obs_date(obs_dt)

            assert result.startswith("Yesterday, ")

    def test_format_older_date(self):
        """Test that older dates format as 'Mon D, HH:MM AM/PM'."""
        from backend.main import format_obs_date

        # Use a fixed date that's definitely not today or yesterday
        obs_dt = "2024-12-25 16:45"

        # Mock today to ensure Dec 25 is "old"
        with patch("backend.main.date") as mock_date:
            mock_date.today.return_value = date(2024, 12, 30)

            result = format_obs_date(obs_dt)

            assert "Dec 25" in result
            assert "4:45 PM" in result

    def test_format_morning_time(self):
        """Test that morning times (AM) format correctly."""
        from backend.main import format_obs_date

        today = date.today()
        obs_dt = f"{today.isoformat()} 06:05"

        result = format_obs_date(obs_dt)

        assert "6:05 AM" in result

    def test_format_noon(self):
        """Test that noon formats correctly (12 PM not 0 PM)."""
        from backend.main import format_obs_date

        today = date.today()
        obs_dt = f"{today.isoformat()} 12:00"

        result = format_obs_date(obs_dt)

        assert "12:00 PM" in result

    def test_format_midnight(self):
        """Test that midnight formats correctly (12 AM)."""
        from backend.main import format_obs_date

        today = date.today()
        obs_dt = f"{today.isoformat()} 00:30"

        result = format_obs_date(obs_dt)

        assert "12:30 AM" in result

    def test_format_invalid_input_returns_original(self):
        """Test that invalid date strings return the original string."""
        from backend.main import format_obs_date

        result = format_obs_date("not a date")
        assert result == "not a date"

    def test_format_empty_string_returns_original(self):
        """Test that empty string returns empty string."""
        from backend.main import format_obs_date

        result = format_obs_date("")
        assert result == ""

    def test_format_truncated_date(self):
        """Test handling of date without time component."""
        from backend.main import format_obs_date

        # Should fall back to original
        result = format_obs_date("2024-12-30")
        assert result == "2024-12-30"


class TestMilesToKm:
    """Tests for the miles_to_km utility function."""

    def test_ten_miles(self):
        """Test 10 miles conversion."""
        from backend.main import miles_to_km

        assert miles_to_km(10) == 16

    def test_one_mile(self):
        """Test 1 mile conversion."""
        from backend.main import miles_to_km

        assert miles_to_km(1) == 2

    def test_twenty_five_miles(self):
        """Test 25 miles conversion."""
        from backend.main import miles_to_km

        assert miles_to_km(25) == 40

    def test_zero_miles(self):
        """Test 0 miles returns 0."""
        from backend.main import miles_to_km

        assert miles_to_km(0) == 0


class TestSearchRoute:
    """Tests for the /search endpoint."""

    def test_search_success(self, client, mock_geocode, mock_ebird_client):
        """Test successful search returns observations."""
        response = client.get("/search?location=New+York&radius=10&days=14")

        assert response.status_code == 200
        assert "Bald Eagle" in response.text
        assert "Red-winged Blackbird" in response.text

    def test_search_location_not_found(self, client, mock_geocode_not_found):
        """Test search with unknown location shows error."""
        response = client.get("/search?location=NonexistentPlace123")

        assert response.status_code == 200
        assert "Could not find location" in response.text

    def test_search_missing_location_param(self, client):
        """Test search without location parameter returns 422."""
        response = client.get("/search")

        assert response.status_code == 422


class TestNotableRoute:
    """Tests for the /notable endpoint."""

    def test_notable_success(self, client, mock_geocode, mock_ebird_client):
        """Test successful notable search."""
        response = client.get("/notable?location=New+York&radius=10&days=14")

        assert response.status_code == 200
        assert "Notable" in response.text or "notable" in response.text


class TestHotspotsRoute:
    """Tests for the /hotspots endpoint."""

    def test_hotspots_success(self, client, mock_geocode, mock_ebird_client):
        """Test successful hotspots search."""
        response = client.get("/hotspots?location=New+York&radius=10")

        assert response.status_code == 200
        assert "Central Park" in response.text
        assert "Prospect Park" in response.text


class TestHotspotDetailRoute:
    """Tests for the /hotspot/{loc_id} endpoint."""

    def test_hotspot_detail_success(self, client, mock_ebird_client):
        """Test successful hotspot detail view."""
        response = client.get("/hotspot/L123456")

        assert response.status_code == 200
        assert "Central Park" in response.text

    def test_hotspot_detail_valid_loc_id_formats(self, client, mock_ebird_client):
        """Test that various valid loc_id formats work."""
        # Standard eBird location ID format
        response = client.get("/hotspot/L123456")
        assert response.status_code == 200

        response = client.get("/hotspot/L1")
        assert response.status_code == 200

        response = client.get("/hotspot/L999999999")
        assert response.status_code == 200

    def test_hotspot_detail_invalid_loc_id_no_L_prefix(self, client):
        """Test that loc_id without L prefix is rejected."""
        response = client.get("/hotspot/123456")

        assert response.status_code == 200  # Returns error page, not 404
        assert "Invalid hotspot ID" in response.text

    def test_hotspot_detail_invalid_loc_id_letters(self, client):
        """Test that loc_id with letters after L is rejected."""
        response = client.get("/hotspot/LABC123")

        assert response.status_code == 200
        assert "Invalid hotspot ID" in response.text

    def test_hotspot_detail_invalid_loc_id_special_chars(self, client):
        """Test that loc_id with special characters is rejected."""
        response = client.get("/hotspot/L123-456")

        assert response.status_code == 200
        assert "Invalid hotspot ID" in response.text

    def test_hotspot_detail_invalid_loc_id_empty(self, client):
        """Test that empty loc_id is rejected (FastAPI handles this)."""
        # FastAPI will return 404 for /hotspot/ since it doesn't match the route
        response = client.get("/hotspot/")
        assert response.status_code == 404


class TestHomeRoute:
    """Tests for the home page."""

    def test_home_page_loads(self, client):
        """Test home page loads successfully."""
        response = client.get("/")

        assert response.status_code == 200
        assert "eBird Explorer" in response.text
        assert "Recent sightings" in response.text


class TestSpeciesCodeValidation:
    """Tests for species code validation pattern."""

    def test_valid_species_codes(self):
        """Test that valid species codes match the pattern."""
        from backend.main import SPECIES_CODE_PATTERN

        valid_codes = ["baleag", "amecro", "rewbla", "yerwar", "cangoo"]
        for code in valid_codes:
            assert SPECIES_CODE_PATTERN.match(code), f"{code} should be valid"

    def test_species_codes_with_numbers(self):
        """Test that species codes with trailing numbers are valid."""
        from backend.main import SPECIES_CODE_PATTERN

        # Some eBird codes include numbers for subspecies/hybrids
        assert SPECIES_CODE_PATTERN.match("yerwar1")
        assert SPECIES_CODE_PATTERN.match("mallar3")

    def test_invalid_species_codes(self):
        """Test that invalid species codes don't match."""
        from backend.main import SPECIES_CODE_PATTERN

        invalid_codes = [
            "BALEAG",  # Uppercase
            "bal",  # Too short
            "bald eagle",  # Contains space
            "bal-eag",  # Contains hyphen
            "123456",  # All numbers
            "",  # Empty
        ]
        for code in invalid_codes:
            assert not SPECIES_CODE_PATTERN.match(code), f"{code} should be invalid"


class TestSpeciesRoute:
    """Tests for the /species endpoint."""

    def test_species_search_success(self, client, mock_geocode, mock_ebird_client):
        """Test successful species search."""
        response = client.get("/species?species=baleag&location=New+York&radius=25&days=14")

        assert response.status_code == 200
        assert "Bald Eagle" in response.text

    def test_species_search_invalid_code(self, client, mock_geocode):
        """Test that invalid species code shows error."""
        response = client.get("/species?species=INVALID&location=New+York")

        assert response.status_code == 200
        assert "Invalid species code" in response.text

    def test_species_search_code_with_special_chars(self, client, mock_geocode):
        """Test that species code with special characters is rejected."""
        response = client.get("/species?species=bal-eag&location=New+York")

        assert response.status_code == 200
        assert "Invalid species code" in response.text

    def test_species_search_location_not_found(
        self, client, mock_geocode_not_found, mock_ebird_client
    ):
        """Test species search with unknown location shows error."""
        response = client.get(
            "/species?species=baleag&location=NonexistentPlace"
        )

        assert response.status_code == 200
        assert "Could not find location" in response.text

    def test_species_form_page(self, client):
        """Test species search form page loads."""
        response = client.get("/species")

        assert response.status_code == 200
        assert "Where has a species been seen" in response.text


class TestGeocodingErrorHandling:
    """Tests for geocoding error handling in routes."""

    def test_search_geocoding_timeout(self, client):
        """Test that geocoding timeout shows friendly error."""
        with patch("backend.main.geocode", side_effect=GeocodingTimeoutError("timeout")):
            response = client.get("/search?location=New+York")

            assert response.status_code == 200
            assert "timeout" in response.text.lower() or "timed out" in response.text.lower()

    def test_search_geocoding_network_error(self, client):
        """Test that geocoding network error shows friendly error."""
        with patch("backend.main.geocode", side_effect=GeocodingNetworkError("network error")):
            response = client.get("/search?location=New+York")

            assert response.status_code == 200
            assert "network" in response.text.lower() or "connect" in response.text.lower()

    def test_hotspots_geocoding_error(self, client):
        """Test that hotspots route handles geocoding errors."""
        with patch("backend.main.geocode", side_effect=GeocodingTimeoutError("timeout")):
            response = client.get("/hotspots?location=New+York")

            assert response.status_code == 200
            assert "timeout" in response.text.lower() or "timed out" in response.text.lower()

    def test_species_geocoding_error(self, client, mock_ebird_client):
        """Test that species route handles geocoding errors."""
        with patch("backend.main.geocode", side_effect=GeocodingNetworkError("cannot connect")):
            response = client.get("/species?species=baleag&location=New+York")

            assert response.status_code == 200
            assert "connect" in response.text.lower() or "network" in response.text.lower()
