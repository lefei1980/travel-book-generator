# TODO - Active Development Tasks

## 🎯 Current Status

**Deployment Status**: ✅ **Live in Production**
- Frontend: Vercel (HTTPS)
- Backend: Oracle Cloud VM (HTTP via public IP)
- CI/CD: Automated via GitHub Actions

**Recent Fixes Completed:**
- ✅ Mixed content blocking (Next.js API proxy)
- ✅ Geocoding normalization ("The Louvre Museum" → "Louvre")
- ✅ Wikipedia enrichment fallback strategy
- ✅ Overview map shows start/end locations

---

## ✅ Phase 7: UX Improvements (COMPLETED)

### Priority 1: Real-time Geocoding Preview ✅

**Problem:** Users can't verify geocoding accuracy before PDF generation
- "Mt. Britton Tower" → Queensland, Australia ✗ (should be Puerto Rico ✓)
- No feedback until PDF is downloaded (too late to fix)

**Solution:** Add live location preview as user types

**Backend Tasks:**
- [x] Create geocoding preview endpoint `GET /api/geocode/preview`
  - Accept query parameter `?q={query}&limit=10`
  - Return up to 10 Nominatim results
  - Include display_name, lat, lon, type, importance
  - Add response caching to prevent rate limiting
  - File: `backend/app/routers/geocode.py` ✅
  - File: `backend/app/services/geocoding.py` ✅

- [x] Register geocode router in main app
  - File: `backend/app/main.py` ✅

**Frontend Tasks:**
- [x] Create LocationPreview component
  - Debounced input (1 second delay)
  - Show loading spinner while fetching
  - Display up to 5 results at a time
  - "Show 5 more" button if >5 results
  - Click result to select (or dismiss)
  - Show "❌ No locations found" if empty
  - File: `frontend/src/components/LocationPreview.tsx` ✅

- [x] Integrate LocationPreview into forms
  - Start location input ✅
  - End location input ✅
  - All place name inputs ✅
  - File: `frontend/src/components/DaySection.tsx` ✅

- [x] Add geocodePreview API function
  - File: `frontend/src/lib/api.ts` ✅

- [x] Add proxy endpoint for geocoding preview
  - File: `frontend/src/app/api/geocode/preview/route.ts` ✅

**UI Design:**
```
[Input: mt. britton tower                    ]

📍 Preview locations:
┌─────────────────────────────────────────────┐
│ ✓ Mt Britton Tower, El Yunque, Puerto Rico │ [Select]
│   Mt Britton, Queensland, Australia        │ [Select]
├─────────────────────────────────────────────┤
│ Showing 2 of 2 results                      │
└─────────────────────────────────────────────┘
```

**Time Taken:** 2.5 hours ✅

---

### Priority 2: Improve Description Quality ✅

**Problem:** Keyword-based summaries are poor quality, hard to read

**Solution:** Revert to full sentence extraction with optimized word limit

**Implementation:**
- [x] Calculate optimal word count based on page layout
  - Page layout: Top 20% map, 73% for 5 POI cards
  - Per POI: ~39mm height, ~11mm for description
  - Font: 11px, line-height 1.4
  - Target: ~50 words (fits 2.5 lines) ✅

- [x] Replace `_summarize_to_keywords()` with `_extract_sentences()`
  - Extract first complete sentences ✅
  - Truncate at ~50 words ✅
  - Preserve sentence structure ✅
  - File: `backend/app/services/enrichment.py` ✅

- [x] Update template CSS if needed
  - File: `backend/app/templates/travelbook.html` ✅

**Time Taken:** 20 minutes ✅

---

### Priority 3: Remove POI Limit Per Day ✅

**Problem:** Artificial 5 POI limit prevents comprehensive itineraries

**Solution:** Allow unlimited POIs, let days span multiple pages

**Implementation:**
- [x] Update template CSS for multi-page days
  - Add `page-break-inside: avoid` to POI cards ✅
  - Allow natural page breaks between cards ✅
  - File: `backend/app/templates/travelbook.html` ✅

- [x] Remove frontend limit validation
  - Allow unlimited "Add Place" clicks ✅
  - Add soft warning at 10+ POIs: "⚠️ You have 12 places. This day may span 2-3 pages in the PDF." ✅
  - File: `frontend/src/components/DaySection.tsx` ✅

**Time Taken:** 15 minutes ✅

---

## 📊 Progress Tracker

| Phase | Status | Files Changed | Time |
|-------|--------|---------------|------|
| Geocoding Preview | ✅ Complete | 8 files (3 new, 5 modified) | 2.5h |
| Description Quality | ✅ Complete | 1 file | 20min |
| Remove POI Limit | ✅ Complete | 2 files | 15min |

**Total Time:** 3 hours ✅

---

## ✅ Implementation Complete

1. ✅ **Geocoding preview** - Most impactful UX improvement
2. ✅ **Description quality** - Quick win
3. ✅ **Remove POI limit** - Nice to have

**All phases deployed and live in production!**

---

## 📝 Session Notes

**Session 2026-02-15 (COMPLETED):**
- ✅ Fixed deployment issues (mixed content, geocoding, enrichment)
- ✅ User tested Paris itinerary - works perfectly
- ✅ User tested Puerto Rico - identified geocoding accuracy issue
- ✅ Implemented Phase 7 (all 3 priorities):
  - Real-time geocoding preview with location hints
  - Improved description quality (sentence extraction)
  - Removed POI limit, enabled multi-page days
- ✅ All features deployed and live in production

---

## 📖 Documentation

See `DEBUG_NOTES.md` for detailed troubleshooting history and solutions.
