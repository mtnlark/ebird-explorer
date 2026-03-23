# eBird Explorer

I'm a birder who wanted a way to quickly answer common questions like "what's been seen near me lately?" or "where was that interesting species reported?" This is a simple web tool for exploring eBird data, including at a more granular ZIP code or town level (vs. county).

![eBird Explorer homepage](assets/homepage.png)

## Features

- **Location Search**: Enter a town, ZIP code, or address to see recent bird observations within a configurable radius
- **Notable Sightings**: Find rare and unusual birds in your area, filterable by date range
- **Hotspot Explorer**: Browse hotspots near a location and see recent activity
- **Species Lookup**: Search for where a specific species has been seen recently, with autocomplete

## Setup

1. Get a free eBird API key at https://ebird.org/api/keygen

2. Clone the repo and set up your environment:
   ```bash
   git clone https://github.com/mtnlark/ebird-explorer.git
   cd ebird-explorer
   cp .env.example .env
   # Edit .env and add your API key
   ```

3. Install dependencies and run:
   ```bash
   pip install -r requirements.txt
   uvicorn backend.main:app --reload
   ```

4. Open http://localhost:8000

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, httpx (async HTTP)
- **Frontend**: Server-rendered HTML (Jinja2) with vanilla JavaScript
- **Validation**: Pydantic v2 for API response parsing and configuration
- **APIs**: eBird API, OpenStreetMap Nominatim (geocoding)
- **Tooling**: ruff (linting/formatting), pytest (testing)

## Architecture

```
backend/
├── main.py           # FastAPI routes, request handling
├── config.py         # Centralized settings (pydantic-settings)
├── models.py         # Pydantic models for API responses
├── ebird_client.py   # Async eBird API client
├── geocoding.py      # Nominatim geocoding with caching
├── templates/        # Jinja2 HTML templates
└── static/           # CSS and JavaScript

tests/                # pytest test suite (90+ tests)
api/index.py          # Vercel serverless entrypoint
```

**Key patterns:**

- **Pydantic models** validate and transform external API responses at the boundary, converting camelCase fields to snake_case with type safety
- **Centralized configuration** via `pydantic-settings` loads from environment variables with validation at startup
- **Async HTTP clients** (`httpx.AsyncClient`) with connection pooling for efficient API calls
- **Geocoding cache** persists to JSON file to respect Nominatim rate limits

## Deployment

The app is configured for deployment on Vercel. Push to your repo and connect it to Vercel, making sure to set the `EBIRD_API_KEY` environment variable.

## Development

Install dev dependencies:
```bash
pip install -e ".[dev]"
```

Run tests:
```bash
pytest tests/ -v
```

Run tests with coverage:
```bash
pytest tests/ --cov=backend --cov-report=html
```

Lint and format:
```bash
ruff check backend/ tests/
ruff format backend/ tests/
```

### Screenshots

Recent sightings in Charleston, SC:
![Recent sightings](assets/recent.png)

Notable sightings near Interlochen, MI:
![Notable sightings](assets/notable.png)

Hotspots near Catskill, NY:
![Hotspots](assets/hotspots.png)

## License

MIT
