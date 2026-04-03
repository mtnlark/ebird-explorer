"""Tests for the What's New feature - species diff between time periods."""

from unittest.mock import AsyncMock, patch

from backend.models import Observation


def _make_obs(species_code, com_name, obs_dt, loc_name="Central Park"):
    """Helper to create Observation instances for testing."""
    return Observation(
        speciesCode=species_code,
        comName=com_name,
        sciName=f"Sci {com_name}",
        locId="L123456",
        locName=loc_name,
        obsDt=obs_dt,
        howMany=1,
        lat=40.7829,
        lng=-73.9654,
        obsValid=True,
        obsReviewed=False,
        locationPrivate=False,
        subId="S12345678",
    )


class TestComputeWhatsNew:
    """Tests for the compute_whats_new diff logic."""

    def test_species_only_in_current_are_arrivals(self):
        """Species in current period but not extended-only are arrivals."""
        from backend.main import compute_whats_new

        current = [
            _make_obs("baleag", "Bald Eagle", "2024-12-30 10:00"),
            _make_obs("amecro", "American Crow", "2024-12-30 09:00"),
        ]
        extended = [
            _make_obs("baleag", "Bald Eagle", "2024-12-30 10:00"),
            _make_obs("amecro", "American Crow", "2024-12-30 09:00"),
            _make_obs("rewbla", "Red-winged Blackbird", "2024-12-22 08:00"),
        ]

        result = compute_whats_new(current, extended)

        arrival_codes = {o.species_code for o in result["arrivals"]}
        assert arrival_codes == {"baleag", "amecro"}

    def test_species_only_in_extended_are_departures(self):
        """Species in extended period but not current are departures."""
        from backend.main import compute_whats_new

        current = [
            _make_obs("baleag", "Bald Eagle", "2024-12-30 10:00"),
        ]
        extended = [
            _make_obs("baleag", "Bald Eagle", "2024-12-30 10:00"),
            _make_obs("rewbla", "Red-winged Blackbird", "2024-12-22 08:00"),
            _make_obs("amecro", "American Crow", "2024-12-23 11:00"),
        ]

        result = compute_whats_new(current, extended)

        departure_codes = {o.species_code for o in result["departures"]}
        assert departure_codes == {"rewbla", "amecro"}

    def test_empty_current_all_departures(self):
        """If nothing seen currently, all extended species are departures."""
        from backend.main import compute_whats_new

        current = []
        extended = [
            _make_obs("rewbla", "Red-winged Blackbird", "2024-12-22 08:00"),
        ]

        result = compute_whats_new(current, extended)

        assert len(result["arrivals"]) == 0
        assert len(result["departures"]) == 1
        assert result["departures"][0].species_code == "rewbla"

    def test_empty_extended_all_arrivals(self):
        """If extended is empty (shouldn't happen but handle it), current are arrivals."""
        from backend.main import compute_whats_new

        current = [
            _make_obs("baleag", "Bald Eagle", "2024-12-30 10:00"),
        ]
        extended = [
            _make_obs("baleag", "Bald Eagle", "2024-12-30 10:00"),
        ]

        result = compute_whats_new(current, extended)

        assert len(result["arrivals"]) == 1
        assert len(result["departures"]) == 0

    def test_both_empty(self):
        """If both periods are empty, result is empty."""
        from backend.main import compute_whats_new

        result = compute_whats_new([], [])

        assert result["arrivals"] == []
        assert result["departures"] == []

    def test_result_preserves_observation_objects(self):
        """The result should contain the actual Observation objects, not just codes."""
        from backend.main import compute_whats_new

        eagle = _make_obs("baleag", "Bald Eagle", "2024-12-30 10:00", "Central Park")
        blackbird = _make_obs("rewbla", "Red-winged Blackbird", "2024-12-22 08:00", "Prospect Park")

        current = [eagle]
        extended = [eagle, blackbird]

        result = compute_whats_new(current, extended)

        assert result["arrivals"][0].location_name == "Central Park"
        assert result["departures"][0].location_name == "Prospect Park"


class TestWhatsNewRoute:
    """Tests for the /whats-new endpoint."""

    def test_whats_new_success(self, client, mock_geocode, mock_ebird_client):
        """Test successful what's new search returns a page."""
        response = client.get("/whats-new?location=New+York&radius=10&period=7")

        assert response.status_code == 200
        assert "What" in response.text and "New" in response.text or "new" in response.text

    def test_whats_new_shows_arrivals_and_departures(self, client, mock_geocode):
        """Test that the page shows both arrivals and departures sections."""
        current_obs = [
            _make_obs("baleag", "Bald Eagle", "2024-12-30 10:00"),
        ]
        extended_obs = [
            _make_obs("baleag", "Bald Eagle", "2024-12-30 10:00"),
            _make_obs("rewbla", "Red-winged Blackbird", "2024-12-22 08:00"),
        ]

        with patch("backend.main.ebird") as mock:
            mock.get_recent_observations = AsyncMock(side_effect=[current_obs, extended_obs])

            response = client.get("/whats-new?location=New+York&radius=10&period=7")

        assert response.status_code == 200
        assert "Bald Eagle" in response.text
        assert "Red-winged Blackbird" in response.text

    def test_whats_new_location_not_found(self, client, mock_geocode_not_found):
        """Test what's new with unknown location shows error."""
        response = client.get("/whats-new?location=NonexistentPlace123&period=7")

        assert response.status_code == 200
        assert "Could not find location" in response.text

    def test_whats_new_missing_location(self, client):
        """Test what's new without location returns 422."""
        response = client.get("/whats-new")

        assert response.status_code == 422

    def test_whats_new_default_period(self, client, mock_geocode, mock_ebird_client):
        """Test that period defaults to 7 days."""
        response = client.get("/whats-new?location=New+York")

        assert response.status_code == 200
        # Verify the ebird client was called with back=7 and back=14
        calls = mock_ebird_client.get_recent_observations.call_args_list
        assert len(calls) == 2
        assert calls[0].kwargs["back"] == 7
        assert calls[1].kwargs["back"] == 14

    def test_whats_new_custom_period(self, client, mock_geocode, mock_ebird_client):
        """Test that custom period is passed correctly."""
        response = client.get("/whats-new?location=New+York&period=14")

        assert response.status_code == 200
        calls = mock_ebird_client.get_recent_observations.call_args_list
        assert len(calls) == 2
        assert calls[0].kwargs["back"] == 14
        assert calls[1].kwargs["back"] == 28

    def test_whats_new_period_clamped_to_max(self, client, mock_geocode, mock_ebird_client):
        """Test that extended period is clamped to 30 days max (eBird limit)."""
        response = client.get("/whats-new?location=New+York&period=20")

        assert response.status_code == 200
        calls = mock_ebird_client.get_recent_observations.call_args_list
        assert len(calls) == 2
        # Extended period would be 40, but should be clamped to 30
        assert calls[1].kwargs["back"] == 30

    def test_whats_new_has_tabs_with_other_views(self, client, mock_geocode, mock_ebird_client):
        """Test that the page includes navigation tabs."""
        response = client.get("/whats-new?location=New+York&radius=10&period=7")

        assert response.status_code == 200
        assert "/search?" in response.text
        assert "/notable?" in response.text
