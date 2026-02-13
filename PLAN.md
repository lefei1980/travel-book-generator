# TravelBook Generator — Implementation Plan

## Phase 1: Core Infrastructure
**Goal**: Backend + frontend running, trip CRUD with background processing skeleton.

### Subtasks
1.1. Backend project setup — FastAPI, folder structure, `requirements.txt`
1.2. SQLite database setup — SQLAlchemy models: Trip (with `status`, `enriched_data` JSON column), Day, Place
1.3. Pydantic schemas — request/response models with validation (max 4-5 POIs/day, required fields)
1.4. API endpoints:
  - `POST /api/trips` — validate, save, launch `BackgroundTasks`, return trip ID
  - `GET /api/trips/{id}` — return trip data + current status stage
  - `GET /api/trips/{id}/download` — stub (returns 404 until Phase 6)
1.5. Background pipeline skeleton — updates status through lifecycle stages (pending→geocoding→...→complete), no actual logic yet
1.6. Frontend setup — `create-next-app` with TypeScript
1.7. Trip form — structured day-by-day form (title, dates, days with places)
1.8. API integration — frontend submits trip, polls status, displays stage updates

### Tests
- `POST /api/trips` returns 201 + trip ID
- `GET /api/trips/{id}` returns trip with status
- Invalid input returns 422 with clear errors
- Background task updates status through stages
- Place count validation (reject >5 POIs per day)

---

## Phase 2: Geospatial Engine
**Goal**: Geocode places and compute driving routes with proper caching.

### Subtasks
2.1. Geocoding service — Nominatim API with:
  - SQLite cache (check cache before API call)
  - 1 req/sec rate limit (asyncio.sleep)
  - Custom User-Agent: `TravelBookGenerator/1.0 (contact_email)`
2.2. Routing service — OSRM API:
  - Build ordered waypoint list per day
  - Parse: total distance, segment durations, polyline geometry
2.3. Pipeline integration — geocoding + routing stages update `enriched_data` JSON

### Tests
- **Unit**: Mock Nominatim → verify coordinate parsing, caching, rate limiting
- **Unit**: Mock OSRM → verify route segment extraction, polyline parsing
- **Integration** (optional/slow): Geocode "Eiffel Tower" → verify real coordinates
- Cache hit test: second geocode of same place skips API call

---

## Phase 3: POI Enrichment
**Goal**: Fetch Wikipedia descriptions and Wikimedia images for each place.

### Subtasks
3.1. Wikipedia service — query Wikipedia API, extract first paragraph, truncate to 150 words
3.2. Image service — fetch Wikimedia Commons thumbnail URL + license attribution
3.3. Pipeline integration — enrichment stage populates `enriched_data` JSON with descriptions + image URLs
3.4. Fallback handling — graceful degradation when Wikipedia has no result

### Tests
- Mock Wikipedia API → verify description extraction and word truncation
- Mock Wikimedia → verify thumbnail URL and attribution stored
- Test fallback: no Wikipedia result → place still included with "No description available"
- Verify enriched_data JSON structure after enrichment stage

---

## Phase 4: Map Rendering
**Goal**: Leaflet HTML templates for overview and daily maps, rendered directly in PDF.

### Subtasks
4.1. Leaflet HTML template — OpenStreetMap tiles, markers, polylines, `window.mapReady` signal
4.2. Overview map template — all trip markers with color coding (red=hotels, green=attractions, blue=restaurants)
4.3. Daily route map template — numbered markers in visit order, route polyline, distance labels
4.4. Map readiness sync — `map.whenReady(() => { window.mapReady = true; })`

### Tests
- Render map template with hardcoded data → verify HTML is valid
- Verify `window.mapReady` flag is set in template JS
- Template renders with 0 attractions (edge case)
- Template renders with max POIs

---

## Phase 5: PDF Engine
**Goal**: Assemble everything into formatted PDF via Playwright.

### Subtasks
5.1. Jinja2 page templates:
  - Overview page: map (60%) + condensed schedule (40%)
  - Daily page: route map + POI cards (thumbnail, title, description, tips)
5.2. Template rendering — populate Jinja2 with enriched_data JSON
5.3. Playwright PDF generation:
  - Render full HTML
  - `await page.wait_for_function("window.mapReady === true")`
  - Generate PDF with page breaks (`page-break-after: always`)
5.4. Download endpoint — serve generated PDF file
5.5. Full pipeline wiring — trip submission → all stages → PDF file

### Tests
- Generate PDF from hardcoded enriched data → verify valid PDF file
- Verify PDF page count = 1 (overview) + N (days)
- End-to-end with mocked external APIs: submit trip → download PDF
- Verify `wait_for_function` is called before PDF render

---

## Phase 6: Frontend Polish & Mobile
**Goal**: Polished UX with status feedback, error handling, responsive design.

### Subtasks
6.1. Status polling UI — display current pipeline stage ("Geocoding locations...", "Rendering PDF...")
6.2. Error handling — show API errors in form, handle network failures
6.3. Responsive design — mobile-friendly form, collapsible day sections
6.4. Download UX — download button appears when status=complete
6.5. Auto-save draft — persist form state to localStorage

### Tests
- Manual: verify status messages update correctly
- Manual: test on mobile viewport
- Manual: test error states
- Manual: verify localStorage persistence

---

## Phase 7: Integration Testing & Hardening
**Goal**: End-to-end tests, edge cases, performance.

### Subtasks
7.1. End-to-end test suite — full pipeline with mocked APIs
7.2. Edge cases — empty days, single-day trips, special characters in place names
7.3. Error recovery — API failures mid-pipeline, timeout handling
7.4. Rate limit compliance verification

### Tests
- Full E2E test with mock data
- Edge case tests pass
- Error recovery tests pass
