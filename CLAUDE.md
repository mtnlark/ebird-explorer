# eBird Data Explorer

## What We're Building

A web-based tool for exploring eBird data with better UX than eBird's native interface. The core insight: eBird has great data but makes common birding questions surprisingly hard to answer. We're fixing that.

**Primary user**: Birders who want to quickly answer questions like "what's been seen near me lately?" or "where was that interesting species reported?" without wrestling with eBird's county-centric, clunky interface.

**Design philosophy**: Keep it simple. No unnecessary dependencies. If vanilla JS does the job, don't add React. If a feature doesn't serve a real use case, don't build it.

## MVP Features

### 1. Location Search
The killer feature. Enter a town name, ZIP code, or address → get recent observations within a configurable radius.

- Geocode input using OpenStreetMap Nominatim (free, no API key)
- Default radius: 10 miles, user-adjustable
- Display results as a clean list, sorted by date (most recent first)

### 2. Notable Sightings Feed
Rare and unusual birds in the area—the stuff eBird marks as "notable."

- Uses the same location input as above
- Filterable by date range (last 7 days, 14 days, 30 days)
- Should make it obvious *why* something is notable (rare for region? out of season?)

### 3. Hotspot Explorer
Pick a hotspot, see what's been happening there.

- Search/browse hotspots near a location
- Recent species list for selected hotspot
- Basic stats: recent checklist count, species diversity

### 4. Species Lookup
"Where has [species] been seen near me recently?"

- Autocomplete species input (eBird has a taxonomy endpoint)
- Show recent observations on a map or as a list with locations
- Distance from search location

## Technical Architecture

### Backend: Python + FastAPI
- FastAPI for the API layer (async support, automatic OpenAPI docs)
- httpx for async HTTP requests to eBird API
- Keep it stateless—no database for MVP

### Frontend: HTML + CSS + Vanilla JS (or HTMX)
- Server-rendered HTML from FastAPI, enhanced with JS for interactivity
- No build step, no node_modules, no React
- HTMX is fine if it simplifies things; don't add it just to add it
- CSS: keep it clean and readable; a simple custom stylesheet is fine

### External APIs
- **eBird API**: https://documenter.getpostman.com/view/664302/S1ENwy59
  - Requires API key (free, get one at https://ebird.org/api/keygen)
  - Rate limit: ~200 requests/minute (generous for personal use)
  - Key endpoints:
    - `GET /v2/data/obs/geo/recent` — recent obs near lat/lng
    - `GET /v2/data/obs/geo/recent/notable` — notable obs near lat/lng
    - `GET /v2/ref/hotspot/geo` — hotspots near lat/lng
    - `GET /v2/data/obs/{locId}/recent` — recent obs at a hotspot
    - `GET /v2/data/nearest/geo/recent/{speciesCode}` — nearest sightings of a species
    - `GET /v2/ref/taxonomy/ebird` — species taxonomy for autocomplete

- **Nominatim (OpenStreetMap)**: https://nominatim.org/release-docs/latest/api/Search/
  - Free, no API key
  - Rate limit: 1 request/second (cache aggressively)
  - Be a good citizen: set a descriptive User-Agent header

## Project Structure

```
ebird-explorer/
├── api/
│   └── index.py             # Vercel serverless entrypoint
├── backend/
│   ├── main.py              # FastAPI app, routes
│   ├── ebird_client.py      # eBird API wrapper
│   ├── geocoding.py         # Nominatim geocoding
│   ├── templates/           # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── results.html
│   │   ├── hotspot.html
│   │   ├── hotspots.html
│   │   └── species.html
│   └── static/
│       ├── style.css
│       └── autocomplete.js  # Species name autocomplete
├── .env                     # EBIRD_API_KEY goes here (see .env.example)
├── .env.example             # Template for environment variables
├── geocode_cache.json       # Persistent geocoding cache (auto-generated)
├── vercel.json              # Vercel deployment config
└── requirements.txt
```

## Key Implementation Notes

### Geocoding
- Cache geocoding results to a JSON file (survives server restarts, trivial to implement)
- Coordinates don't change, so no cache invalidation needed—cache forever
- Nominatim returns lat/lng; eBird's geo endpoints want lat/lng + distance in km
- Handle ambiguous locations gracefully (e.g., "Springfield" exists in many states)

### eBird API Patterns
- All requests need header: `X-eBirdApiToken: {your_key}`
- Species codes are 6-letter codes (e.g., "baleag" for Bald Eagle)
- Region codes follow a hierarchy: country/state/county (e.g., "US-NY-119" for Westchester)
- The `back` parameter controls how many days back to search (default 14, max 30)

### Error Handling
- eBird API can be slow; use appropriate timeouts
- Geocoding can fail or return unexpected results; fail gracefully
- Show useful error messages, not stack traces

## Stretch Goals (Post-MVP)

Once the core features work well:

1. **Compare two locations** — side-by-side recent sightings
2. **"What's new" diff** — species seen this week that weren't seen last week
3. **Seasonal arrival tracking** — monitor when target species start appearing
4. **Map view** — plot sightings on an interactive map (Leaflet)
5. **Personal data import** — analyze your own eBird export CSV

## What NOT to Build (Yet)

- User accounts / authentication
- Database persistence
- Historical trend analysis (API doesn't support it well)
- Mobile app
- Sharing / social features

## Getting Started

1. Get an eBird API key: https://ebird.org/api/keygen
2. Copy `.env.example` to `.env` and add your API key
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `uvicorn backend.main:app --reload`
5. Open http://localhost:8000 in your browser
