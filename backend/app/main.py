from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="eBird Explorer API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

EBIRD_API_KEY = os.getenv("EBIRD_API_KEY")
EBIRD_BASE_URL = "https://api.ebird.org/v2"

@app.get("/")
async def root():
    return {"message": "eBird Explorer API is running!"}

@app.get("/api/test-ebird")
async def test_ebird_connection():
    """Test that we can connect to eBird API"""
    headers = {"X-eBirdApiToken": EBIRD_API_KEY}

    # Get recent observations from Central Park, NYC
    url = f"{EBIRD_BASE_URL}/data/obs/geo/recent"
    params = {
        "lat": 40.7829,
        "lng": -73.9654,
        "dist": 5
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        return {
            "status": "Connected to eBird!",
            "observation_count": len(data),
            "sample": data[:3] if data else []
        }
    else:
        return {
            "status": "Connection failed",
            "error": response.status_code
        }

@app.get("/api/observations/by-location")
async def get_observations_by_location(
    location: str = Query(..., description="Town name, ZIP, or 'lat,lng'"),
    days_back: int = Query(7, description="Days to look back (max 30)")
):
    """Get bird observations for any location"""

    # For MVP, handle simple lat,lng format
    # We'll add geocoding in the next iteration
    try:
        lat, lng = location.split(",")
        lat, lng = float(lat.strip()), float(lng.strip())
    except:
        # For now, default to a known location if parsing fails
        # We'll add proper geocoding next
        return {
            "error": "Please use format: 'latitude,longitude' (e.g., '42.3601,-71.0589')",
            "hint": "Geocoding coming soon!"
        }

    headers = {"X-eBirdApiToken": EBIRD_API_KEY}
    url = f"{EBIRD_BASE_URL}/data/obs/geo/recent"
    params = {
        "lat": lat,
        "lng": lng,
        "dist": 25,  # 25km radius
        "back": min(days_back, 30)  # eBird limits to 30 days
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)

    if response.status_code == 200:
        observations = response.json()

        # Process and summarize the data
        species_list = {}
        total_bird_count = 0

        for obs in observations:
            species = obs.get("comName", "Unknown")
            # Get the number of individuals observed (howMany field)
            # If not specified, default to 1
            how_many = obs.get("howMany", 1)

            if species not in species_list:
                species_list[species] = {
                    "count": 0,
                    "scientific_name": obs.get("sciName", ""),
                    "last_seen": obs.get("obsDt", "")
                }

            species_list[species]["count"] += how_many
            total_bird_count += how_many

        return {
            "location": {"lat": lat, "lng": lng},
            "total_observations": total_bird_count,
            "unique_species": len(species_list),
            "species": species_list,
            "days_searched": days_back
        }
    else:
        return {
            "error": f"eBird API error: {response.status_code}",
            "message": "Check your API key and try again"
        }
