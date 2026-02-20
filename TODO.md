# TODO - Active Development Tasks

## 🎯 Current Status

**Deployment Status**: ✅ **Live in Production**
- Frontend: Vercel (HTTPS)
- Backend: Oracle Cloud VM (HTTP via public IP)
- CI/CD: Automated via GitHub Actions

**Stable Revert Point (manual-entry-only baseline):**
- Commit: `709acbf4ae4d1f5f5c38872d84b2c85da24b3401` — "Add date and day of week to daily itineraries"

**Recent Fixes Completed:**
- ✅ Phase 7: Real-time geocoding preview, improved descriptions, unlimited POIs per day
- ✅ Mixed content blocking (Next.js API proxy)
- ✅ Geocoding normalization ("The Louvre Museum" → "Louvre")
- ✅ Wikipedia enrichment fallback strategy
- ✅ Overview map shows start/end locations

---

## ✅ Phase 8: Wikipedia Enrichment Accuracy (COMPLETED)

### Problem 1: Disambiguation Page Handling

**Issue:** When geocoding finds "Ponce" (disambiguation page), we extract content from the disambiguation page itself instead of the correct sublink.

**Example:**
- Input: "Ponce" at coordinates (18.01, -66.61) [Puerto Rico]
- Current: Shows "Administrative . Located in United States" (from disambiguation page)
- Expected: Shows description from "Ponce, Puerto Rico" article

### Problem 2: Missing Thumbnail Images

**Issue:** Places with Wikipedia articles don't get thumbnail images because image lookup uses the original input name, not the canonical Wikipedia title found.

**Example:**
- Input: "El yunque"
- Wikipedia finds: "El Yunque National Forest" (correct article)
- Image search uses: "El yunque" (original input) → ❌ No match
- Should use: "El Yunque National Forest" → ✓ Has thumbnail

### Solution: Coordinate-Based Article Matching

**Strategy:**
1. Run both geosearch (coordinate-based) AND opensearch (fuzzy text matching)
2. Fetch Wikipedia coordinates for opensearch results
3. Calculate distance from target coordinates
4. Choose the closest match (likely the most relevant article)
5. Use the canonical title for both description AND images

**Benefits:**
- Validates that opensearch found the right location (not "El Yunque, Guatemala")
- Solves image mismatch by using consistent canonical titles
- Handles name variations ("Louvre" vs "Musée du Louvre")
- Prevents false positives via distance threshold

### Implementation Tasks

**Backend (enrichment.py):**
- [x] Add `_fetch_wikipedia_coordinates(title, client)` function ✅
  - Use Wikipedia API `prop=coordinates`
  - Return (lat, lon) or None if no coordinates
  - File: `backend/app/services/enrichment.py`

- [x] Add `_calculate_distance(lat1, lon1, lat2, lon2)` function ✅
  - Use Haversine formula for accurate distance
  - Return distance in meters
  - File: `backend/app/services/enrichment.py`

- [x] Update `get_wikipedia_summary()` logic ✅
  - Always call both geosearch AND opensearch
  - Fetch coordinates for opensearch result
  - Compare distances and choose closest match
  - Return dict with `canonical_title` field
  - Add detailed logging for debugging
  - File: `backend/app/services/enrichment.py`

- [x] Update `enrich_trip()` to use canonical title ✅
  - Extract `canonical_title` from Wikipedia result
  - Pass canonical title to `get_wikimedia_image()` instead of `place.name`
  - File: `backend/app/services/enrichment.py`

**Distance Thresholds:**
- < 500m: Very likely the same place
- 500m - 2km: Probably related (use closer match)
- \> 2km: Different places (reject, might be false positive)

**Fallback Strategy:**
- If opensearch result has no coordinates: use geosearch result
- If both have no coordinates: use opensearch result (better text match)
- If geosearch finds nothing: use opensearch result only

### Performance Impact

**Current:** ~4-5 API calls per place
**Proposed:** ~6-7 API calls per place

**Added time:** ~6-10 seconds per trip (15 places)
**Total pipeline:** ~25-50 seconds (acceptable for background processing)

**Resource usage:** Low risk for Oracle Free Tier (1 OCPU, 1GB RAM)
- Network I/O bound, not CPU intensive
- Distance calculation is trivial (< 1ms)
- Background task (no user timeout)

---

## ✅ Phase 11: Geocoding Accuracy Upgrade (COMPLETED)

### Problem
AI chat interface was working but geocoding results were inaccurate — wrong places found or geocoding failures because:
1. LLM JSON only output `name` + `place_type` per place, no city/country context
2. Nominatim called with `limit=1` — first result blindly accepted even if wrong
3. No confidence scoring or fallback strategy

### Solution (4-file change, no DB migration)

**`backend/app/services/llm.py`**
- Updated `JSON_SYSTEM_PROMPT` to require `city` and `country` per place
- Added `generate_name_variants(place, city, country)` — LLM fallback that suggests alternative names when geocoding fails

**`backend/app/schemas.py`**
- Added `city: Optional[str] = None` and `country: Optional[str] = None` to `PlaceInput`

**`backend/app/routers/chat.py`**
- At finalize time, builds `geocoding_hints` dict: `{ "1:Eiffel Tower": {"city": "Paris", "country": "France"} }`
- Stored in `trip.enriched_data` before pipeline launches

**`backend/app/services/geocoding.py`**
- Added `_score_candidate(candidate, name, city, country)`: name match +50, city +20, country +20, importance bonus
- Added `geocode_place_smart(name, city, country, db, client)`:
  - Builds query `"Place, City, Country"`, fetches 5 candidates, scores them
  - If score ≥ 60: accept (high confidence)
  - If score ≥ 40: accept (medium confidence)
  - If score < 40: call LLM for variant names and retry
  - Accept best ≥ 20 (low confidence, with warning log)
- Updated `geocode_trip()` to read `geocoding_hints` from `enriched_data` and call `geocode_place_smart()`

## ✅ Phase 12: Geocoding Bug Fixes (COMPLETED)

### Problems Fixed

1. **Restaurants geocoded to wrong countries** — "El Mesón" → Tenerife Spain (score=52), "La Estación" → Colombia (score=52)
   - Fix: Country validation in `geocode_place_smart()` — reject any Nominatim result where expected country is absent from `display_name`

2. **Start/end flags missing for vague accommodation names** — "AirBnb near Loiza" returns 0 Nominatim candidates
   - Fix: `_extract_neighborhood()` extracts "Loiza" from "AirBnb near Loiza"; `geocode_trip()` tries neighborhood then day-level city as fallback; stores approx coords under original cache key

3. **OSRM 400 Bad Request errors** caused by wrong-hemisphere coordinates included as waypoints
   - Fix: Resolved by fixing restaurant geocoding (country validation prevents wrong-country results from ever being stored)

### Files Changed
- `backend/app/services/geocoding.py` — country validation, `_extract_neighborhood()`, city fallback in `geocode_trip()`

## ✅ Phase 13: Map Bug Fixes (COMPLETED 2026-02-19)

### Problems Fixed

1. **Start/end flags missing on daily itinerary** (pipeline.py)
   - Root cause: geocoding stage did not call `flag_modified(trip, "enriched_data")` before `db.commit()`, so SQLAlchemy did not detect the JSON mutation and `start_end_coords` was never persisted to SQLite. All other pipeline stages (routing, enriching, rendering) correctly call `flag_modified`.
   - Fix: Added `dict()` copy + `flag_modified(trip, "enriched_data")` in the geocoding stage, matching the pattern used by other stages.

2. **Restaurants included in route planning** (routing.py)
   - Root cause: `_build_waypoints()` included ALL places (including restaurants) as OSRM waypoints. Restaurant geocoding is unreliable, leading to cross-city detours.
   - Fix: Skip `place_type == 'restaurant'` in waypoint construction. Restaurants are still shown on the map with numbered markers but excluded from the driving route.

3. **Daily map zoom missing start/end** — auto-fixed by #1
   - The template already adds `start_coords`/`end_coords` to `bounds` when they exist. Once `start_end_coords` is correctly persisted (fix #1), the map automatically zooms to include start, all attractions, and end.

### Files Changed
- `backend/app/services/pipeline.py` — geocoding stage: `dict()` copy + `flag_modified`
- `backend/app/services/routing.py` — `_build_waypoints`: skip restaurants

---

## 📊 Progress Tracker

| Phase | Status | Files Changed | Time |
|-------|--------|---------------|------|
| Phase 7: UX Improvements | ✅ Complete | 10 files | 3h |
| Phase 8: Enrichment Accuracy | ✅ Complete | 1 file (backend) | 2h |
| Phase 9: UX Improvements | ✅ Complete | 2 files (frontend) | 45min |
| Phase 11: Geocoding Accuracy | ✅ Complete | 4 files (backend) | 1h |
| Phase 12: Geocoding Bug Fixes | ✅ Complete | 1 file (backend) | 1h |

---

## 📝 Session Notes

**Session 2026-02-16 (COMPLETED):**

### Phase 8: Wikipedia Enrichment Accuracy ✅
- 🔍 User reported enrichment issues:
  1. Disambiguation pages showing generic content (e.g., "Ponce")
  2. Missing thumbnail images for known attractions (e.g., "El Yunque")
  3. Wrong articles selected when multiple exist at same coordinates (e.g., "Castillo San Felipe del Morro" → "Fort Brooke")
  4. Cities rejected due to strict 2km distance threshold (e.g., "Ponce, Puerto Rico" at 6.2km)

- ✅ Fixes implemented:
  1. **Multi-result disambiguation handling**: Try up to 5 opensearch results, skip disambiguation pages
  2. **Canonical title for images**: Use Wikipedia article title (not user input) for image lookup
  3. **Coordinate-based filtering**: Only accept articles with Wikipedia coordinates (filters out people/concepts)
  4. **Adaptive distance threshold**: Accept closest match beyond 2km if no results within 2km (handles large cities)
  5. **Prefer text matches**: When distances are similar (≤100m), prefer opensearch (text match) over geosearch

- 📊 Results:
  - "Ponce" → Now finds "Ponce, Puerto Rico" city with thumbnail ✓
  - "El Yunque" → Now finds "El Yunque National Forest" with thumbnail ✓
  - "Castillo San Felipe del Morro" → Now finds correct fort (not Fort Brooke) ✓

### Phase 9: UX Improvements ✅
- 🔍 User reported UX issues:
  1. Drag-and-drop interferes with text selection (can't highlight text with mouse)
  2. Repetitive location input for same hotel/location

- ✅ Fixes implemented:
  1. **Drag handle only**: Move draggable attribute to handle (⋮⋮) only, not entire card
     - Text selection now works normally in all inputs ✓
  2. **Trip-level location shortcut**: "All days start and end at same location"
     - Single input auto-fills all days
     - Use case: Same hotel entire trip
  3. **Per-day location shortcut**: "End at same location as start" (default checked)
     - Auto-copies start → end
     - Use case: Multi-night stays at different hotels

- 📦 All changes deployed and live in production

**Session 2026-02-18 (COMPLETED):**

### Phase 11: Geocoding Accuracy Upgrade ✅
- Updated `llm.py` JSON prompt to require city/country per place
- Added `generate_name_variants()` LLM fallback
- Added `city/country` to `PlaceInput` schema
- `chat.py` stores `geocoding_hints` in `enriched_data` at finalize time
- `geocoding.py`: `_score_candidate()`, `geocode_place_smart()`, updated `geocode_trip()`
- `routing.py` + `pipeline.py`: prefer prefix-match cache entries

### Phase 12: Geocoding Bug Fixes ✅
- Country validation in `geocode_place_smart()` — prevents wrong-country results (score=52 no longer enough if country absent)
- `_extract_neighborhood()` — extracts geocodable neighborhood from vague descriptions
- City/neighborhood fallback in `geocode_trip()` for ungeocodable start/end locations

**Previous Session 2026-02-15:**
- ✅ Fixed deployment issues (mixed content, geocoding, enrichment)
- ✅ User tested Paris itinerary - works perfectly
- ✅ User tested Puerto Rico - identified geocoding accuracy issue
- ✅ Implemented Phase 7 (all 3 priorities)
- ✅ All features deployed and live in production

---

---

## ✅ Phase 10: Automation Upgrade — Chat UI + LLM + JSON Generation (COMPLETE)

### Overview
Add an AI chat interface so users can plan trips conversationally. Clicking "Finalize" converts
the conversation to structured JSON and feeds directly into the existing pipeline (geocoding →
enriching → rendering → PDF). The existing manual-entry form remains as a second tab.

### Backend Tasks

- [ ] Install `groq` Python package — add to `requirements.txt`
- [ ] Create `backend/app/services/llm.py`
  - Groq client wrapper (model: `llama-3.3-70b-versatile`)
  - `chat_with_llm(messages, temperature)` — returns assistant reply string
  - `generate_itinerary_json(messages)` — calls LLM at temp=0.1 with JSON schema prompt, returns parsed dict
  - `generate_name_variants(place, city, country)` — fallback helper (used in Phase 2)
  - System prompts: Stage 1 (conversational, no JSON), Stage 2 (JSON only, strict schema)
- [ ] Add `ChatSession` model to `backend/app/models.py`
  - Fields: `id` (UUID), `created_at`, `messages` (JSON column — list of {role, content}), `trip_id` (nullable FK to Trip)
- [ ] Add chat schemas to `backend/app/schemas.py`
  - `ChatMessageRequest` — `{ session_id: str | None, message: str }`
  - `ChatMessageResponse` — `{ session_id: str, reply: str }`
  - `FinalizeRequest` — `{ session_id: str }`
  - `FinalizeResponse` — `{ trip_id: str, status: str }`
- [ ] Create `backend/app/routers/chat.py`
  - `POST /api/chat` — create or continue session, call LLM Stage 1, return reply
  - `POST /api/chat/{session_id}/finalize` — call LLM Stage 2 → JSON → validate → save Trip → trigger existing pipeline → return trip_id
  - `GET /api/chat/{session_id}` — return full message history
- [ ] Register chat router in `backend/app/main.py`
- [ ] Run Alembic migration (or recreate DB) to add `chat_sessions` table

### Frontend Tasks

- [ ] Add Next.js API proxy routes for chat endpoints:
  - `src/app/api/chat/route.ts` — proxy `POST /api/chat`
  - `src/app/api/chat/[id]/finalize/route.ts` — proxy `POST /api/chat/{id}/finalize`
  - `src/app/api/chat/[id]/route.ts` — proxy `GET /api/chat/{id}`
- [ ] Create `src/components/ChatPlanner.tsx`
  - Scrollable message list (user bubbles right, assistant bubbles left)
  - Text input + Send button (Enter to send)
  - "Finalize Itinerary" button — appears after at least 2 exchanges
  - On finalize: calls finalize endpoint → receives `trip_id` → switches to progress bar view (reuse existing polling + download UI from `TripForm`)
  - Loading indicator while waiting for LLM reply
- [ ] Update `src/app/page.tsx` to show two tabs:
  - "AI Chat" tab → `<ChatPlanner />`
  - "Manual Entry" tab → existing `<TripForm />` (unchanged)
- [ ] Update `src/lib/api.ts` — add chat API functions

### What was built
- `backend/app/services/llm.py` — Groq client (llama-3.3-70b-versatile), chat + JSON generation
- `backend/app/models.py` — ChatSession model (id, created_at, messages JSON, trip_id FK)
- `backend/app/schemas.py` — ChatMessageRequest/Response, FinalizeResponse, ChatSessionResponse
- `backend/app/routers/chat.py` — POST /api/chat, POST /api/chat/{id}/finalize, GET /api/chat/{id}
- `frontend/src/app/api/chat/` — 3 Next.js proxy routes
- `frontend/src/components/ChatPlanner.tsx` — full chat UI with status/preview/download flow
- `frontend/src/app/page.tsx` — two-tab layout (AI Chat / Manual Entry)
- `frontend/src/lib/api.ts` — sendChatMessage, finalizeChat functions
- Groq API smoke tested and working ✅

### Deployment Steps (to apply to production)
1. Commit and push — GitHub Actions deploys frontend to Vercel automatically
2. On Oracle VM: `pip install groq==0.13.1` in the venv
3. On Oracle VM: add `GROQ_API_KEY=...` to `backend/.env`
4. Restart backend service (`systemctl restart travelbook` or equivalent)

---

## 📖 Documentation

See `DEBUG_NOTES.md` for detailed troubleshooting history and solutions.
