# TravelBook Generator

## GitHub Repository
**Repo URL**: https://github.com/lefei1980/travel-book-generator

## Project Goal
Convert structured itinerary input into a downloadable, professionally formatted, map-rich PDF travel guide.

## Architecture
```
Frontend (Next.js)
  → POST /api/trips (returns trip ID immediately)
  → Polls GET /api/trips/{id} for status updates
  → Downloads PDF when status=complete

Backend (FastAPI)
  → Saves trip (status=pending)
  → Launches BackgroundTask pipeline:
      geocoding → routing → enriching → rendering → complete
  → Stores enriched_data as JSON column
  → Renders HTML+Leaflet → Playwright → PDF (no intermediate PNG)
```

## Tech Stack
- **Frontend**: Next.js (React), TypeScript
- **Backend**: FastAPI (Python 3.11+)
- **PDF/Map Rendering**: Playwright (HTML with embedded Leaflet maps → direct PDF)
- **Database**: SQLite (caching geocoding, trip storage, enriched_data JSON)
- **External APIs (MVP)**: Nominatim (geocoding), OSRM (routing), Wikipedia + Wikimedia Commons

## Project Structure
```
travel-book-generator/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app, CORS, lifespan
│   │   ├── models.py        # SQLAlchemy models (Trip has enriched_data JSON col)
│   │   ├── schemas.py       # Pydantic request/response schemas
│   │   ├── database.py      # SQLite engine/session
│   │   ├── routers/
│   │   │   └── trips.py     # Trip endpoints
│   │   ├── services/
│   │   │   ├── geocoding.py  # Nominatim + cache (1 req/sec, custom User-Agent)
│   │   │   ├── routing.py    # OSRM integration
│   │   │   ├── enrichment.py # Wikipedia summary + Wikimedia image
│   │   │   ├── maps.py       # Leaflet HTML template rendering
│   │   │   ├── pdf.py        # HTML → Playwright → PDF pipeline
│   │   │   └── pipeline.py   # Orchestrates full background pipeline
│   │   └── templates/        # Jinja2 HTML templates for PDF
│   ├── tests/
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   └── lib/
│   ├── package.json
│   └── tsconfig.json
├── CLAUDE.md
├── PLAN.md
└── TODO.md
```

## Data Model
- **Trip**: title, dates, status (pending|geocoding|routing|enriching|rendering|complete|error), enriched_data (JSON), days[]
- **Day**: day_number, start_location, attractions[], restaurants[], end_location
- **Place**: name, type (hotel|attraction|restaurant), coordinates, metadata, image_url

## Trip Status Lifecycle
`pending → geocoding → routing → enriching → rendering → complete` (or `error` at any stage)

## API Endpoints
- `POST /api/trips` — save trip, launch background pipeline, return trip ID immediately
- `GET /api/trips/{id}` — get trip status + data (frontend polls this)
- `GET /api/trips/{id}/download` — download generated PDF (only when status=complete)

## Key Constraints
- **No intermediate PNG**: HTML+Leaflet maps render directly to PDF via Playwright
- **Map sync**: Use `window.mapReady` flag + `page.wait_for_function("window.mapReady === true")`
- **Layout**: Max 4-5 POIs per day, max 150 words per description, fixed image size
- **Nominatim**: 1 req/sec rate limit, custom User-Agent `TravelBookGenerator/1.0 (email)`
- **MVP enrichment**: Wikipedia + Wikimedia only (no OpenTripMap)
- **Images**: Only CC/public domain with attribution

## Configuration

### Backend Environment Variables (backend/.env)
- `CONTACT_EMAIL` — Email for Nominatim User-Agent (must be valid, not example.com)
- `MOCK_GEOCODING` — Set to `true` to bypass Nominatim and use mock coordinates (useful for testing)

Copy `backend/.env.example` to `backend/.env` and configure:
```bash
cp backend/.env.example backend/.env
# Edit CONTACT_EMAIL with your real email
```

## Deployment
- **Frontend**: Vercel (free tier, HTTPS automatic)
- **Backend**: Oracle Cloud Always Free VM (HTTP via public IP)
- **CI/CD**: GitHub Actions (automated deployment)
- See `DEPLOYMENT.md` for complete deployment guide

## Session Startup
Read `CLAUDE.md` and `TODO.md` to resume work.

## IMPORTANT: After completing each phase, update `TODO.md` with the next phase's tasks, and remove completed tasks, before ending the session.
## IMPORTANT: Write debugging and diagnostic notes to `DEBUG_NOTES.md`.
## IMPORTANT: Never commit sensitive files (SSH keys, .env files, public IP addresses) to the repository.
## IMPORTANT: Before implementing complex changes, present a concise plan in plain English and wait for user approval before coding.
