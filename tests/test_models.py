"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError


class TestObservationModel:
    """Tests for the Observation model."""

    def test_valid_observation_parses(self):
        """Test that a valid observation with camelCase keys parses correctly."""
        from backend.models import Observation

        data = {
            "speciesCode": "baleag",
            "comName": "Bald Eagle",
            "sciName": "Haliaeetus leucocephalus",
            "locId": "L123456",
            "locName": "Central Park",
            "obsDt": "2024-03-15 10:30",
            "howMany": 2,
            "lat": 40.7829,
            "lng": -73.9654,
            "obsValid": True,
            "obsReviewed": False,
            "locationPrivate": False,
            "subId": "S123456789",
        }

        obs = Observation(**data)
        assert obs.species_code == "baleag"
        assert obs.common_name == "Bald Eagle"
        assert obs.scientific_name == "Haliaeetus leucocephalus"
        assert obs.location_id == "L123456"
        assert obs.location_name == "Central Park"
        assert obs.observation_date == "2024-03-15 10:30"
        assert obs.count == 2
        assert obs.lat == 40.7829
        assert obs.lng == -73.9654
        assert obs.obs_valid is True
        assert obs.obs_reviewed is False
        assert obs.location_private is False
        assert obs.sub_id == "S123456789"

    def test_missing_required_field_raises_error(self):
        """Test that missing required fields raise ValidationError."""
        from backend.models import Observation

        data = {
            "speciesCode": "baleag",
            "comName": "Bald Eagle",
            # Missing sciName and other required fields
        }

        with pytest.raises(ValidationError):
            Observation(**data)

    def test_extra_fields_ignored(self):
        """Test that extra fields from the API are ignored."""
        from backend.models import Observation

        data = {
            "speciesCode": "baleag",
            "comName": "Bald Eagle",
            "sciName": "Haliaeetus leucocephalus",
            "locId": "L123456",
            "locName": "Central Park",
            "obsDt": "2024-03-15 10:30",
            "lat": 40.7829,
            "lng": -73.9654,
            "obsValid": True,
            "obsReviewed": False,
            "locationPrivate": False,
            "subId": "S123456789",
            "unexpectedField": "should be ignored",
            "anotherExtra": 12345,
        }

        obs = Observation(**data)
        assert obs.species_code == "baleag"
        assert not hasattr(obs, "unexpectedField")
        assert not hasattr(obs, "anotherExtra")

    def test_optional_count_defaults_to_none(self):
        """Test that count (howMany) is optional and defaults to None."""
        from backend.models import Observation

        data = {
            "speciesCode": "baleag",
            "comName": "Bald Eagle",
            "sciName": "Haliaeetus leucocephalus",
            "locId": "L123456",
            "locName": "Central Park",
            "obsDt": "2024-03-15 10:30",
            # howMany is omitted
            "lat": 40.7829,
            "lng": -73.9654,
            "obsValid": True,
            "obsReviewed": False,
            "locationPrivate": False,
            "subId": "S123456789",
        }

        obs = Observation(**data)
        assert obs.count is None


class TestHotspotModel:
    """Tests for the Hotspot model."""

    def test_valid_hotspot_parses(self):
        """Test that a valid hotspot with camelCase keys parses correctly."""
        from backend.models import Hotspot

        data = {
            "locId": "L123456",
            "locName": "Central Park",
            "countryCode": "US",
            "subnational1Code": "US-NY",
            "lat": 40.7829,
            "lng": -73.9654,
            "latestObsDt": "2024-03-15",
            "numSpeciesAllTime": 234,
        }

        hotspot = Hotspot(**data)
        assert hotspot.location_id == "L123456"
        assert hotspot.name == "Central Park"
        assert hotspot.country_code == "US"
        assert hotspot.subnational1_code == "US-NY"
        assert hotspot.lat == 40.7829
        assert hotspot.lng == -73.9654
        assert hotspot.latest_observation_date == "2024-03-15"
        assert hotspot.species_count == 234


class TestHotspotInfoModel:
    """Tests for the HotspotInfo model."""

    def test_valid_hotspot_info_parses(self):
        """Test that detailed hotspot info with camelCase keys parses correctly."""
        from backend.models import HotspotInfo

        data = {
            "locId": "L123456",
            "name": "Central Park",
            "latitude": 40.7829,
            "longitude": -73.9654,
            "countryCode": "US",
            "countryName": "United States",
            "subnational1Code": "US-NY",
            "subnational1Name": "New York",
            "subnational2Code": "US-NY-061",
            "subnational2Name": "New York County",
            "isHotspot": True,
            "hierarchicalName": "United States > New York > New York County > Central Park",
            "numSpeciesAllTime": 234,
        }

        info = HotspotInfo(**data)
        assert info.location_id == "L123456"
        assert info.name == "Central Park"
        assert info.latitude == 40.7829
        assert info.longitude == -73.9654
        assert info.country_code == "US"
        assert info.country_name == "United States"
        assert info.subnational1_code == "US-NY"
        assert info.subnational1_name == "New York"
        assert info.subnational2_code == "US-NY-061"
        assert info.subnational2_name == "New York County"
        assert info.is_hotspot is True
        assert info.hierarchical_name == "United States > New York > New York County > Central Park"
        assert info.species_count == 234


class TestSpeciesModel:
    """Tests for the Species model."""

    def test_valid_species_parses(self):
        """Test that a valid species from taxonomy with camelCase keys parses correctly."""
        from backend.models import Species

        data = {
            "speciesCode": "baleag",
            "comName": "Bald Eagle",
            "sciName": "Haliaeetus leucocephalus",
            "category": "species",
            "order": "Accipitriformes",
            "familyCode": "accipa1",
            "familyComName": "Hawks, Eagles, and Kites",
        }

        species = Species(**data)
        assert species.species_code == "baleag"
        assert species.common_name == "Bald Eagle"
        assert species.scientific_name == "Haliaeetus leucocephalus"
        assert species.category == "species"
        assert species.order == "Accipitriformes"
        assert species.family_code == "accipa1"
        assert species.family_common_name == "Hawks, Eagles, and Kites"


class TestGeocodedLocationModel:
    """Tests for the GeocodedLocation model."""

    def test_nominatim_lon_mapped_to_lng(self):
        """Test that Nominatim's 'lon' field is correctly mapped to 'lng'."""
        from backend.models import GeocodedLocation

        data = {
            "lat": "40.7829",
            "lon": "-73.9654",  # Nominatim returns "lon"
            "display_name": "Central Park, Manhattan, New York, NY, USA",
        }

        location = GeocodedLocation(**data)
        assert location.lat == 40.7829
        assert location.lng == -73.9654
        assert location.display_name == "Central Park, Manhattan, New York, NY, USA"

    def test_accepts_lon_alias(self):
        """Test that both 'lon' and 'lng' are accepted as field names."""
        from backend.models import GeocodedLocation

        # Test with 'lng' directly
        data1 = {
            "lat": "40.7829",
            "lng": "-73.9654",
            "display_name": "Central Park, Manhattan, New York, NY, USA",
        }
        location1 = GeocodedLocation(**data1)
        assert location1.lng == -73.9654

        # Test with 'lon' (alias)
        data2 = {
            "lat": "40.7829",
            "lon": "-73.9654",
            "display_name": "Central Park, Manhattan, New York, NY, USA",
        }
        location2 = GeocodedLocation(**data2)
        assert location2.lng == -73.9654
