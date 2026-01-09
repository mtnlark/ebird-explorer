"""eBird Explorer - FastAPI application."""

from datetime import datetime, date
from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from .geocoding import geocode
from .ebird_client import ebird

app = FastAPI(title="eBird Explorer")

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

        time_str = dt.strftime("%-I:%M %p").lstrip("0")

        if obs_date == today:
            return f"Today, {time_str}"
        elif obs_date == today.replace(day=today.day - 1) if today.day > 1 else None:
            return f"Yesterday, {time_str}"
        else:
            # Check if it's yesterday (handle month boundaries)
            from datetime import timedelta
            if obs_date == today - timedelta(days=1):
                return f"Yesterday, {time_str}"
            return f"{dt.strftime('%b %-d')}, {time_str}"
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
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/search", response_class=HTMLResponse)
async def search(
    request: Request,
    location: str = Query(..., min_length=1),
    radius: int = Query(default=10, ge=1, le=31),  # miles
    days: int = Query(default=14, ge=1, le=30),
):
    """Search for recent observations near a location."""
    # Geocode the location
    geo = await geocode(location)
    if not geo:
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "error": f"Could not find location: {location}",
                "location": location,
            },
        )

    # Fetch observations from eBird
    try:
        observations = await ebird.get_recent_observations(
            lat=geo["lat"],
            lng=geo["lng"],
            dist_km=miles_to_km(radius),
            back=days,
        )
        add_formatted_dates(observations)
    except Exception as e:
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "error": f"eBird API error: {str(e)}",
                "location": location,
            },
        )

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "location": location,
            "display_name": geo["display_name"],
            "observations": observations,
            "radius": radius,
            "days": days,
            "count": len(observations),
            "notable": False,
        },
    )


@app.get("/notable", response_class=HTMLResponse)
async def notable(
    request: Request,
    location: str = Query(..., min_length=1),
    radius: int = Query(default=10, ge=1, le=31),
    days: int = Query(default=14, ge=1, le=30),
):
    """Search for notable (rare/unusual) observations near a location."""
    geo = await geocode(location)
    if not geo:
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "error": f"Could not find location: {location}",
                "location": location,
                "notable": True,
            },
        )

    try:
        observations = await ebird.get_notable_observations(
            lat=geo["lat"],
            lng=geo["lng"],
            dist_km=miles_to_km(radius),
            back=days,
        )
        add_formatted_dates(observations)
    except Exception as e:
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "error": f"eBird API error: {str(e)}",
                "location": location,
                "notable": True,
            },
        )

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "location": location,
            "display_name": geo["display_name"],
            "observations": observations,
            "radius": radius,
            "days": days,
            "count": len(observations),
            "notable": True,
        },
    )


@app.get("/hotspots", response_class=HTMLResponse)
async def hotspots(
    request: Request,
    location: str = Query(..., min_length=1),
    radius: int = Query(default=10, ge=1, le=31),
):
    """Find birding hotspots near a location."""
    geo = await geocode(location)
    if not geo:
        return templates.TemplateResponse(
            "hotspots.html",
            {
                "request": request,
                "error": f"Could not find location: {location}",
                "location": location,
            },
        )

    try:
        hotspot_list = await ebird.get_nearby_hotspots(
            lat=geo["lat"],
            lng=geo["lng"],
            dist_km=miles_to_km(radius),
        )
    except Exception as e:
        return templates.TemplateResponse(
            "hotspots.html",
            {
                "request": request,
                "error": f"eBird API error: {str(e)}",
                "location": location,
            },
        )

    return templates.TemplateResponse(
        "hotspots.html",
        {
            "request": request,
            "location": location,
            "display_name": geo["display_name"],
            "hotspots": hotspot_list,
            "radius": radius,
            "count": len(hotspot_list),
        },
    )


@app.get("/hotspot/{loc_id}", response_class=HTMLResponse)
async def hotspot_detail(
    request: Request,
    loc_id: str,
    days: int = Query(default=14, ge=1, le=30),
):
    """View recent observations at a specific hotspot."""
    try:
        info = await ebird.get_hotspot_info(loc_id)
        if not info:
            return templates.TemplateResponse(
                "hotspot.html",
                {
                    "request": request,
                    "error": f"Hotspot not found: {loc_id}",
                },
            )

        observations = await ebird.get_hotspot_observations(loc_id, back=days)
    except Exception as e:
        return templates.TemplateResponse(
            "hotspot.html",
            {
                "request": request,
                "error": f"eBird API error: {str(e)}",
            },
        )

    return templates.TemplateResponse(
        "hotspot.html",
        {
            "request": request,
            "hotspot": info,
            "observations": observations,
            "days": days,
            "count": len(observations),
        },
    )


# Cache taxonomy in memory (it's ~17k species, ~3MB, doesn't change often)
_taxonomy_cache: list[dict] | None = None


async def get_taxonomy_cached() -> list[dict]:
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
            "code": species["speciesCode"],
            "name": species["comName"],
            "sciName": species["sciName"],
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
        com_name = species.get("comName", "").lower()
        sci_name = species.get("sciName", "").lower()
        if q_lower in com_name or q_lower in sci_name:
            matches.append({
                "code": species["speciesCode"],
                "name": species["comName"],
                "sciName": species["sciName"],
            })
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
            "species.html",
            {
                "request": request,
                "species": species,
                "location": location,
            },
        )

    # Geocode the location
    geo = await geocode(location)
    if not geo:
        return templates.TemplateResponse(
            "species.html",
            {
                "request": request,
                "error": f"Could not find location: {location}",
                "species": species,
                "location": location,
            },
        )

    # Get species info from taxonomy cache
    taxonomy = await get_taxonomy_cached()

    species_info = None
    for s in taxonomy:
        if s["speciesCode"] == species:
            species_info = s
            break

    if not species_info:
        return templates.TemplateResponse(
            "species.html",
            {
                "request": request,
                "error": f"Species not found: {species}",
                "location": location,
            },
        )

    # Fetch observations
    try:
        observations = await ebird.get_nearest_species_observations(
            species_code=species,
            lat=geo["lat"],
            lng=geo["lng"],
            dist_km=miles_to_km(radius),
            back=days,
        )
    except Exception as e:
        return templates.TemplateResponse(
            "species.html",
            {
                "request": request,
                "error": f"eBird API error: {str(e)}",
                "species": species,
                "location": location,
            },
        )

    return templates.TemplateResponse(
        "species.html",
        {
            "request": request,
            "species_code": species,
            "species_name": species_info["comName"],
            "species_sci": species_info["sciName"],
            "location": location,
            "display_name": geo["display_name"],
            "observations": observations,
            "radius": radius,
            "days": days,
            "count": len(observations),
        },
    )
