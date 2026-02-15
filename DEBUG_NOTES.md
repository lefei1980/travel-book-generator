# Debug Notes

## 2026-02-15: Fixed "Failed to fetch" Error

### Problem
After successful deployment to Vercel (frontend) and Oracle Cloud (backend), the frontend immediately showed "Failed to fetch" error when clicking "Generate Travel Guide" button.

### Root Cause
**Mixed Content Blocking** - Modern browsers block HTTP requests from HTTPS pages for security:
- Frontend: `https://travel-book-generator.vercel.app` (HTTPS ✓)
- Backend: `http://129.213.164.97:8000` (HTTP ✗)
- Browser blocks: HTTPS → HTTP requests

### Diagnosis Steps
1. ✓ Verified backend is running and accessible: `curl http://129.213.164.97:8000/health`
2. ✓ Verified backend API works: `curl -X POST http://129.213.164.97:8000/api/trips`
3. ✓ Verified Vercel environment variable is set: `NEXT_PUBLIC_API_URL=http://129.213.164.97:8000`
4. ✗ Identified mixed content blocking as the issue

### Solution
Created Next.js API routes that proxy requests to the backend:
- `frontend/src/app/api/trips/route.ts` - POST /api/trips (create trip)
- `frontend/src/app/api/trips/[id]/route.ts` - GET /api/trips/{id} (get trip status)
- `frontend/src/app/api/trips/[id]/download/route.ts` - GET /api/trips/{id}/download (download PDF)

**How it works:**
1. Browser → HTTPS request to Vercel API routes (e.g., `https://your-app.vercel.app/api/trips`)
2. Vercel API route → HTTP request to backend (e.g., `http://129.213.164.97:8000/api/trips`)
3. Server-to-server HTTP requests are allowed (no browser security blocking)
4. Vercel API route → HTTPS response back to browser

**Code changes:**
- Updated `frontend/src/lib/api.ts` to use relative URLs (`/api/trips` instead of `${API_BASE}/api/trips`)
- Set `API_BASE = ""` to use relative URLs

### Alternative Solutions (Not Chosen)
1. **Add HTTPS to backend** - Would require reverse proxy (Caddy/nginx) or Let's Encrypt SSL certificate
   - More complex setup
   - Not necessary for this use case
2. **Ask users to disable mixed content blocking** - Bad UX and security practice

### Testing
- ✓ Frontend build successful with new API routes
- ✓ Changes committed and pushed to trigger auto-deployment
- Deployment in progress via GitHub Actions

### Next Steps
1. Wait for Vercel deployment to complete (~2-3 minutes)
2. Test the application by creating a trip
3. Verify PDF generation and download works end-to-end

### Notes
- This is a common pattern for Next.js apps that need to connect to HTTP backends
- No changes needed to backend code
- No changes needed to Vercel environment variables
- The proxy is transparent to the user

---

## 2026-02-15: Fixed Geocoding, Enrichment, and Map Rendering Issues

### Problems Reported
After deploying the mixed content fix, user tested the app with:
- Start/End: "CDG airport"
- Attraction 1: "Louvre museum Paris France"
- Attraction 2: "The Eiffel Tower Paris France"

Issues found:
1. **Overview map shows only 1 pin** instead of 3 (should show CDG + 2 attractions)
2. **Day 1 map missing Eiffel Tower** pin (but description shows)
3. **"The Louvre Museum" input** yields no description/image

### Root Causes (from backend logs)
```
No geocoding results for 'the louvre museum, paris, france'
No Wikipedia page for 'the louvre museum, paris, france'
```

**Analysis:**
1. **Geocoding failures**: Nominatim can't find overly formal queries
   - ✗ "The Louvre Museum, Paris, France" (too formal, includes "The" and full location)
   - ✓ "Louvre, Paris" (simple, works)

2. **Wikipedia search failures**: Similar issue with formal queries
   - ✗ "The Louvre Museum" (doesn't match article title "Louvre")
   - ✓ "Louvre" (matches article)

3. **Overview map design**: Only showed POI markers, not start/end locations
   - By design, only `day.places` were shown (attractions/restaurants/hotels)
   - Start/end locations were never rendered on overview map

### Solutions Implemented

#### 1. Place Name Normalization
Added `_normalize_place_name()` function in both geocoding.py and enrichment.py:
- Strips leading "the" (case insensitive)
- Removes common suffixes: " museum", " tower"
- Examples:
  - "The Louvre Museum" → "Louvre"
  - "The Eiffel Tower" → "Eiffel"

#### 2. Geocoding Fallback Strategy
Updated `geocode_trip()` to try multiple query variations:
1. Normalized name + city context: "Louvre, Paris, France"
2. Normalized name alone: "Louvre"
3. Original name + city context: "The Louvre Museum, Paris, France"

Adds detailed logging with ✓/✗ indicators to track which queries succeed.

#### 3. Wikipedia/Wikimedia Fallback Strategy
Updated `get_wikipedia_summary()` and `get_wikimedia_image()`:
- Try original name first
- Try normalized name second
- Use search API as fallback for both
- Improved logging to show which query variation succeeded

#### 4. Overview Map Enhancement
Updated `travelbook.html` template:
- Now collects start/end locations in addition to POIs
- Renders START/END flag icons on overview map
- Shows all trip locations (not just attractions)
- Prevents duplicate markers with coordinate deduplication

### Code Changes
- `backend/app/services/geocoding.py`: +normalization, +fallback logic
- `backend/app/services/enrichment.py`: +normalization, +fallback logic
- `backend/app/templates/travelbook.html`: +start/end on overview map

### Expected Results After Fix
With input:
- Start: "CDG airport"
- Attraction 1: "The Louvre Museum"
- Attraction 2: "The Eiffel Tower"
- End: "CDG airport"

**Overview map** should show:
- 1 START flag (CDG)
- 1 pin (Louvre)
- 1 pin (Eiffel Tower)
- 1 END flag (CDG, same location as START, so might overlap)
- **Total: 3-4 markers** (4 if start/end are different locations)

**Day 1 map** should show:
- START flag (CDG)
- Numbered pin 1 (Louvre)
- Numbered pin 2 (Eiffel Tower)
- END flag (CDG)
- Blue route line connecting all points

**Descriptions** should show:
- Louvre: Wikipedia description + Wikimedia image
- Eiffel Tower: Wikipedia description + Wikimedia image

### Testing
- ✓ Normalization tested locally:
  - "The Louvre Museum" → "Louvre"
  - "The Eiffel Tower" → "Eiffel"
- ✓ Code committed and pushed
- Deployment in progress via GitHub Actions

### Deployment Status
- Backend auto-deployment triggered (Oracle Cloud VM)
- Wait ~3-5 minutes for deployment to complete
- Check deployment: `ssh ubuntu@YOUR_VM "cd ~/travel-book-generator && docker compose logs backend --tail=50"`
