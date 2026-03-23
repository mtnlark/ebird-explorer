"""eBird Explorer - FastAPI application."""

import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .ebird_client import ebird
from .geocoding import GeocodingError, close_geocoding_client, geocode

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - cleanup on shutdown."""
    logger.info("Starting eBird Explorer application")
    yield
    # Cleanup: close HTTP connection pools
    logger.info("Shutting down - closing HTTP client pools")
    await ebird.aclose()
    await close_geocoding_client()


app = FastAPI(title="eBird Explorer", lifespan=lifespan)

# Setup templates and static files
BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def format_obs_date(obs_dt: str) -> str:
    """Format observation datetime to a friendly format.

    Examples: 'Today, 2:30 PM', 'Yesterday, 9:15 AM', 'Dec 28, 10:00 AM'
    """
    try:
        # eBird returns dates like "2024-12-30 14:30"
        dt = datetime.strptime(obs_dt[:16], "%Y-%m-%d %H:%M")
        today = date.today()
        obs_date = dt.date()

        # Use %I and strip leading zero for cross-platform compatibility
        time_str = dt.strftime("%I:%M %p").lstrip("0")

        if obs_date == today:
            return f"Today, {time_str}"
        elif obs_date == today - timedelta(days=1):
            return f"Yesterday, {time_str}"
        else:
            day_str = str(dt.day)  # Avoid platform-specific %-d
            return f"{dt.strftime('%b')} {day_str}, {time_str}"
    except (ValueError, IndexError):
        # Fallback if parsing fails
        return obs_dt


# Register custom filter
templates.env.filters["format_date"] = format_obs_date


def add_formatted_dates(observations: list[dict]) -> list[dict]:
    """Add pre-formatted date strings to observations for client-side rendering."""
    for obs in observations:
        if "obsDt" in obs:
            obs["formattedDate"] = format_obs_date(obs["obsDt"])
    return observations


def miles_to_km(miles: float) -> int:
    """Convert miles to kilometers, rounded."""
    return round(miles * 1.60934)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with location search form."""
    return templates.TemplateResponse(request, "index.html")


async def _search_observations(
    request: Request,
    location: str,
    radius: int,
    days: int,
    notable: bool,
) -> HTMLResponse:
    """Common handler for search and notable endpoints."""
    search_type = "notable" if notable else "recent"
    logger.info(
        f"Search request: {search_type} observations near '{location}' ({radius}mi, {days}d)"
    )

    try:
        geo = await geocode(location)
    except GeocodingError as e:
        logger.error(f"Geocoding error for '{location}': {e}")
        return templates.TemplateResponse(
            request,
            "results.html",
            {
                "error": str(e),
                "location": location,
                "notable": notable,
            },
        )

    if not geo:
        logger.warning(f"Geocoding failed for location: {location}")
        return templates.TemplateResponse(
            request,
            "results.html",
            {
                "error": f"Could not find location: {location}",
                "location": location,
                "notable": notable,
            },
        )

    try:
        fetch_func = ebird.get_notable_observations if notable else ebird.get_recent_observations
        observations = await fetch_func(
            lat=geo.lat,
            lng=geo.lng,
            dist_km=miles_to_km(radius),
            back=days,
        )
        add_formatted_dates(observations)
        logger.info(f"Found {len(observations)} {search_type} observations for '{location}'")
    except Exception as e:
        logger.error(f"eBird API error for '{location}': {e}")
        return templates.TemplateResponse(
            request,
            "results.html",
            {
                "error": f"eBird API error: {str(e)}",
                "location": location,
                "notable": notable,
            },
        )

    return templates.TemplateResponse(
        request,
        "results.html",
        {
            "location": location,
            "display_name": geo.display_name,
            "observations": [obs.model_dump(by_alias=True) for obs in observations],
            "radius": radius,
            "days": days,
            "count": len(observations),
            "notable": notable,
        },
    )


@app.get("/search", response_class=HTMLResponse)
async def search(
    request: Request,
    location: str = Query(..., min_length=1),
    radius: int = Query(default=10, ge=1, le=31),  # miles
    days: int = Query(default=14, ge=1, le=30),
):
    """Search for recent observations near a location."""
    return await _search_observations(request, location, radius, days, notable=False)


@app.get("/notable", response_class=HTMLResponse)
async def notable(
    request: Request,
    location: str = Query(..., min_length=1),
    radius: int = Query(default=10, ge=1, le=31),
    days: int = Query(default=14, ge=1, le=30),
):
    """Search for notable (rare/unusual) observations near a location."""
    return await _search_observations(request, location, radius, days, notable=True)


@app.get("/hotspots", response_class=HTMLResponse)
async def hotspots(
    request: Request,
    location: str = Query(..., min_length=1),
    radius: int = Query(default=10, ge=1, le=31),
):
    """Find birding hotspots near a location."""
    try:
        geo = await geocode(location)
    except GeocodingError as e:
        return templates.TemplateResponse(
            request,
            "hotspots.html",
            {
                "error": str(e),
                "location": location,
            },
        )

    if not geo:
        return templates.TemplateResponse(
            request,
            "hotspots.html",
            {
                "error": f"Could not find location: {location}",
                "location": location,
            },
        )

    try:
        hotspot_list = await ebird.get_nearby_hotspots(
            lat=geo.lat,
            lng=geo.lng,
            dist_km=miles_to_km(radius),
        )
    except Exception as e:
        return templates.TemplateResponse(
            request,
            "hotspots.html",
            {
                "error": f"eBird API error: {str(e)}",
                "location": location,
            },
        )

    return templates.TemplateResponse(
        request,
        "hotspots.html",
        {
            "location": location,
            "display_name": geo.display_name,
            "hotspots": [h.model_dump(by_alias=True) for h in hotspot_list],
            "radius": radius,
            "count": len(hotspot_list),
        },
    )


# eBird location IDs follow the pattern L followed by digits (e.g., L123456)
LOC_ID_PATTERN = re.compile(r"^L\d+$")

# eBird species codes are 4-6 lowercase letters (e.g., "baleag", "amecro")
SPECIES_CODE_PATTERN = re.compile(r"^[a-z]{4,6}[a-z0-9]{0,2}$")


@app.get("/hotspot/{loc_id}", response_class=HTMLResponse)
async def hotspot_detail(
    request: Request,
    loc_id: str,
    days: int = Query(default=14, ge=1, le=30),
):
    """View recent observations at a specific hotspot."""
    # Validate loc_id format to prevent potential API injection
    if not LOC_ID_PATTERN.match(loc_id):
        return templates.TemplateResponse(
            request,
            "hotspot.html",
            {
                "error": "Invalid hotspot ID format",
            },
        )

    try:
        # Fetch hotspot info and observations concurrently for better performance
        info, observations = await asyncio.gather(
            ebird.get_hotspot_info(loc_id),
            ebird.get_hotspot_observations(loc_id, back=days),
        )

        if not info:
            return templates.TemplateResponse(
                request,
                "hotspot.html",
                {
                    "error": f"Hotspot not found: {loc_id}",
                },
            )
    except Exception as e:
        return templates.TemplateResponse(
            request,
            "hotspot.html",
            {
                "error": f"eBird API error: {str(e)}",
            },
        )

    return templates.TemplateResponse(
        request,
        "hotspot.html",
        {
            "hotspot": info.model_dump(by_alias=True) if info else None,
            "observations": [obs.model_dump(by_alias=True) for obs in observations],
            "days": days,
            "count": len(observations),
        },
    )


# Cache taxonomy in memory (it's ~17k species, ~3MB, doesn't change often)
_taxonomy_cache: list[dict] | None = None


async def get_taxonomy_cached():
    """Get taxonomy from cache, fetching from eBird API if needed."""
    global _taxonomy_cache
    if _taxonomy_cache is None:
        _taxonomy_cache = await ebird.get_taxonomy()
    return _taxonomy_cache


@app.get("/api/taxonomy")
async def api_taxonomy():
    """API endpoint to get full species taxonomy for client-side fuzzy search."""
    taxonomy = await get_taxonomy_cached()

    # Return simplified list for client-side use
    return [
        {
            "code": species.species_code,
            "name": species.common_name,
            "sciName": species.scientific_name,
        }
        for species in taxonomy
    ]


@app.get("/api/species")
async def api_species(q: str = Query(default="", min_length=0)):
    """API endpoint for species autocomplete (legacy, prefer /api/taxonomy for fuzzy)."""
    if not q:
        return []

    taxonomy = await get_taxonomy_cached()
    q_lower = q.lower()
    matches = []
    for species in taxonomy:
        com_name = species.common_name.lower() if species.common_name else ""
        sci_name = species.scientific_name.lower() if species.scientific_name else ""
        if q_lower in com_name or q_lower in sci_name:
            matches.append(
                {
                    "code": species.species_code,
                    "name": species.common_name,
                    "sciName": species.scientific_name,
                }
            )
            if len(matches) >= 10:
                break
    return matches


@app.get("/species", response_class=HTMLResponse)
async def species_search(
    request: Request,
    species: str = Query(default=""),
    location: str = Query(default=""),
    radius: int = Query(default=25, ge=1, le=50),
    days: int = Query(default=14, ge=1, le=30),
):
    """Search for where a species has been seen near a location."""
    # If no species selected yet, show the search form
    if not species or not location:
        return templates.TemplateResponse(
            request,
            "species.html",
            {
                "species": species,
                "location": location,
            },
        )

    # Geocode the location
    try:
        geo = await geocode(location)
    except GeocodingError as e:
        return templates.TemplateResponse(
            request,
            "species.html",
            {
                "error": str(e),
                "species": species,
                "location": location,
            },
        )

    if not geo:
        return templates.TemplateResponse(
            request,
            "species.html",
            {
                "error": f"Could not find location: {location}",
                "species": species,
                "location": location,
            },
        )

    # Validate species code format to prevent API injection
    if not SPECIES_CODE_PATTERN.match(species):
        return templates.TemplateResponse(
            request,
            "species.html",
            {
                "error": "Invalid species code format",
                "location": location,
            },
        )

    # Get species info from taxonomy cache
    taxonomy = await get_taxonomy_cached()

    species_info = None
    for s in taxonomy:
        # taxonomy now returns Species models, access via attribute
        if s.species_code == species:
            species_info = s
            break

    if not species_info:
        return templates.TemplateResponse(
            request,
            "species.html",
            {
                "error": f"Species not found: {species}",
                "location": location,
            },
        )

    # Fetch observations
    try:
        observations = await ebird.get_nearest_species_observations(
            species_code=species,
            lat=geo.lat,
            lng=geo.lng,
            dist_km=miles_to_km(radius),
            back=days,
        )
    except Exception as e:
        return templates.TemplateResponse(
            request,
            "species.html",
            {
                "error": f"eBird API error: {str(e)}",
                "species": species,
                "location": location,
            },
        )

    return templates.TemplateResponse(
        request,
        "species.html",
        {
            "species_code": species,
            "species_name": species_info.common_name,
            "species_sci": species_info.scientific_name,
            "location": location,
            "display_name": geo.display_name,
            "observations": [obs.model_dump(by_alias=True) for obs in observations],
            "radius": radius,
            "days": days,
            "count": len(observations),
        },
    )
