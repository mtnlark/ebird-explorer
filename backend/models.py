"""Pydantic models for API responses."""

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    """Base model for external API responses."""

    model_config = ConfigDict(
        populate_by_name=True,  # Accept both alias and field name
        extra="ignore",  # Ignore unexpected fields from API
    )


class Observation(APIModel):
    """An eBird observation record."""

    species_code: str = Field(alias="speciesCode")
    common_name: str = Field(alias="comName")
    scientific_name: str = Field(alias="sciName")
    location_id: str = Field(alias="locId")
    location_name: str = Field(alias="locName")
    observation_date: str = Field(alias="obsDt")
    count: int | None = Field(default=None, alias="howMany")
    lat: float
    lng: float
    obs_valid: bool = Field(alias="obsValid")
    obs_reviewed: bool = Field(alias="obsReviewed")
    location_private: bool = Field(alias="locationPrivate")
    sub_id: str = Field(alias="subId")


class Hotspot(APIModel):
    """An eBird hotspot location."""

    location_id: str = Field(alias="locId")
    name: str = Field(alias="locName")
    country_code: str = Field(alias="countryCode")
    subnational1_code: str = Field(alias="subnational1Code")
    lat: float
    lng: float
    latest_observation_date: str | None = Field(default=None, alias="latestObsDt")
    species_count: int | None = Field(default=None, alias="numSpeciesAllTime")


class HotspotInfo(APIModel):
    """Detailed hotspot information."""

    location_id: str = Field(alias="locId")
    name: str
    latitude: float
    longitude: float
    country_code: str = Field(alias="countryCode")
    country_name: str = Field(alias="countryName")
    subnational1_code: str = Field(alias="subnational1Code")
    subnational1_name: str = Field(alias="subnational1Name")
    subnational2_code: str | None = Field(default=None, alias="subnational2Code")
    subnational2_name: str | None = Field(default=None, alias="subnational2Name")
    is_hotspot: bool = Field(alias="isHotspot")
    hierarchical_name: str = Field(alias="hierarchicalName")
    species_count: int | None = Field(default=None, alias="numSpeciesAllTime")


class Species(APIModel):
    """An eBird species from the taxonomy."""

    species_code: str = Field(alias="speciesCode")
    common_name: str = Field(alias="comName")
    scientific_name: str = Field(alias="sciName")
    category: str | None = Field(default=None)
    order: str | None = Field(default=None)
    family_code: str | None = Field(default=None, alias="familyCode")
    family_common_name: str | None = Field(default=None, alias="familyComName")


class GeocodedLocation(BaseModel):
    """A geocoded location from Nominatim."""

    lat: float
    lng: float = Field(alias="lon")  # Nominatim returns "lon"
    display_name: str

    model_config = ConfigDict(populate_by_name=True)
