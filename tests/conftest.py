"""Shared test fixtures for eBird Explorer."""

import os
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

# Set test environment variables before importing app
os.environ["EBIRD_API_KEY"] = "test_api_key_12345"


@pytest.fixture
def client():
    """FastAPI test client."""
    from backend.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_geocode():
    """Mock geocode function returning NYC coordinates."""
    with patch("backend.main.geocode") as mock:
        mock.return_value = {
            "lat": 40.7128,
            "lng": -74.0060,
            "display_name": "New York, NY, USA",
        }
        yield mock


@pytest.fixture
def mock_geocode_not_found():
    """Mock geocode function returning None (location not found)."""
    with patch("backend.main.geocode") as mock:
        mock.return_value = None
        yield mock


@pytest.fixture
def sample_observations():
    """Sample eBird observation data."""
    return [
        {
            "speciesCode": "baleag",
            "comName": "Bald Eagle",
            "sciName": "Haliaeetus leucocephalus",
            "locId": "L123456",
            "locName": "Central Park",
            "obsDt": "2024-12-30 14:30",
            "howMany": 2,
            "subId": "S12345678",
            "locationPrivate": False,
        },
        {
            "speciesCode": "rewbla",
            "comName": "Red-winged Blackbird",
            "sciName": "Agelaius phoeniceus",
            "locId": "L123456",
            "locName": "Central Park",
            "obsDt": "2024-12-29 09:15",
            "howMany": 15,
            "subId": "S12345679",
            "locationPrivate": False,
        },
    ]


@pytest.fixture
def sample_hotspots():
    """Sample eBird hotspot data."""
    return [
        {
            "locId": "L123456",
            "locName": "Central Park",
            "countryCode": "US",
            "subnational1Code": "US-NY",
            "lat": 40.7829,
            "lng": -73.9654,
            "numSpeciesAllTime": 250,
            "latestObsDt": "2024-12-30",
        },
        {
            "locId": "L789012",
            "locName": "Prospect Park",
            "countryCode": "US",
            "subnational1Code": "US-NY",
            "lat": 40.6602,
            "lng": -73.9690,
            "numSpeciesAllTime": 200,
            "latestObsDt": "2024-12-29",
        },
    ]


@pytest.fixture
def sample_hotspot_info():
    """Sample hotspot info response."""
    return {
        "locId": "L123456",
        "name": "Central Park",
        "latitude": 40.7829,
        "longitude": -73.9654,
        "countryCode": "US",
        "subnational1Code": "US-NY",
        "numSpeciesAllTime": 250,
    }


@pytest.fixture
def sample_taxonomy():
    """Sample taxonomy data for species autocomplete."""
    return [
        {
            "speciesCode": "baleag",
            "comName": "Bald Eagle",
            "sciName": "Haliaeetus leucocephalus",
        },
        {
            "speciesCode": "rewbla",
            "comName": "Red-winged Blackbird",
            "sciName": "Agelaius phoeniceus",
        },
        {
            "speciesCode": "amecro",
            "comName": "American Crow",
            "sciName": "Corvus brachyrhynchos",
        },
    ]


@pytest.fixture
def mock_ebird_client(sample_observations, sample_hotspots, sample_hotspot_info, sample_taxonomy):
    """Mock all eBird client methods."""
    with patch("backend.main.ebird") as mock:
        mock.get_recent_observations = AsyncMock(return_value=sample_observations)
        mock.get_notable_observations = AsyncMock(return_value=sample_observations)
        mock.get_nearby_hotspots = AsyncMock(return_value=sample_hotspots)
        mock.get_hotspot_observations = AsyncMock(return_value=sample_observations)
        mock.get_hotspot_info = AsyncMock(return_value=sample_hotspot_info)
        mock.get_taxonomy = AsyncMock(return_value=sample_taxonomy)
        mock.get_nearest_species_observations = AsyncMock(return_value=sample_observations)
        yield mock
