# TODO - Active Development Tasks

## 🎯 Current Status

**Deployment Status**: ✅ **Live in Production**
- Frontend: Vercel (HTTPS)
- Backend: Oracle Cloud VM (HTTP via public IP)
- CI/CD: Automated via GitHub Actions

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

## 📊 Progress Tracker

| Phase | Status | Files Changed | Time |
|-------|--------|---------------|------|
| Phase 7: UX Improvements | ✅ Complete | 10 files | 3h |
| Phase 8: Enrichment Accuracy | ✅ Complete | 1 file | 1h |

---

## 📝 Session Notes

**Session 2026-02-16 (COMPLETED):**
- 🔍 User reported two enrichment issues:
  1. Disambiguation pages showing generic content
  2. Missing thumbnail images for known attractions
- 💡 Identified root causes:
  1. Extracting from disambiguation page instead of specific article
  2. Image lookup using original input instead of canonical Wikipedia title
- 🎯 Solution: Coordinate-based article matching
  - Validate opensearch results with distance calculation
  - Use canonical titles consistently for descriptions and images
- ✅ Implementation completed:
  - Added `_fetch_wikipedia_coordinates()` for getting article coordinates
  - Added `_calculate_distance()` using Haversine formula
  - Rewrote `get_wikipedia_summary()` with coordinate-based matching logic
  - Updated `enrich_trip()` to use canonical titles for image lookup
  - Added comprehensive logging for debugging
- 📦 Ready for deployment and testing

**Previous Session 2026-02-15:**
- ✅ Fixed deployment issues (mixed content, geocoding, enrichment)
- ✅ User tested Paris itinerary - works perfectly
- ✅ User tested Puerto Rico - identified geocoding accuracy issue
- ✅ Implemented Phase 7 (all 3 priorities)
- ✅ All features deployed and live in production

---

## 📖 Documentation

See `DEBUG_NOTES.md` for detailed troubleshooting history and solutions.
