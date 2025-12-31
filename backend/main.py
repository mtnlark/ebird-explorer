"""eBird Explorer - FastAPI application."""

from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse
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
        },
    )
