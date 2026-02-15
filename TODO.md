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

## 🚀 Phase 7: UX Improvements (In Progress)

### Priority 1: Real-time Geocoding Preview (In Progress)

**Problem:** Users can't verify geocoding accuracy before PDF generation
- "Mt. Britton Tower" → Queensland, Australia ✗ (should be Puerto Rico ✓)
- No feedback until PDF is downloaded (too late to fix)

**Solution:** Add live location preview as user types

**Backend Tasks:**
- [ ] Create geocoding preview endpoint `GET /api/geocode/preview`
  - Accept query parameter `?q={query}&limit=10`
  - Return up to 10 Nominatim results
  - Include display_name, lat, lon, type, importance
  - Add response caching to prevent rate limiting
  - File: `backend/app/routers/geocode.py` (new)
  - File: `backend/app/services/geocoding.py` (add `geocode_preview()`)

- [ ] Register geocode router in main app
  - File: `backend/app/main.py`

**Frontend Tasks:**
- [ ] Create LocationPreview component
  - Debounced input (1 second delay)
  - Show loading spinner while fetching
  - Display up to 5 results at a time
  - "Show 5 more" button if >5 results
  - Click result to select (or dismiss)
  - Show "❌ No locations found" if empty
  - File: `frontend/src/components/LocationPreview.tsx` (new)

- [ ] Integrate LocationPreview into forms
  - Start location input
  - End location input
  - All place name inputs
  - File: `frontend/src/components/DaySection.tsx`

- [ ] Add geocodePreview API function
  - File: `frontend/src/lib/api.ts`

- [ ] Add proxy endpoint for geocoding preview
  - File: `frontend/src/app/api/geocode/preview/route.ts` (new)

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

**Estimated Time:** 2-3 hours

---

### Priority 2: Improve Description Quality

**Problem:** Keyword-based summaries are poor quality, hard to read

**Solution:** Revert to full sentence extraction with optimized word limit

**Implementation:**
- [ ] Calculate optimal word count based on page layout
  - Page layout: Top 20% map, 73% for 5 POI cards
  - Per POI: ~39mm height, ~11mm for description
  - Font: 11px, line-height 1.4
  - Target: ~50 words (fits 2.5 lines)

- [ ] Replace `_summarize_to_keywords()` with `_extract_sentences()`
  - Extract first complete sentences
  - Truncate at ~50 words
  - Preserve sentence structure
  - File: `backend/app/services/enrichment.py`

- [ ] Update template CSS if needed
  - File: `backend/app/templates/travelbook.html`

**Estimated Time:** 30 minutes

---

### Priority 3: Remove POI Limit Per Day

**Problem:** Artificial 5 POI limit prevents comprehensive itineraries

**Solution:** Allow unlimited POIs, let days span multiple pages

**Implementation:**
- [ ] Update template CSS for multi-page days
  - Add `page-break-inside: avoid` to POI cards
  - Allow natural page breaks between cards
  - File: `backend/app/templates/travelbook.html`

- [ ] Remove frontend limit validation
  - Allow unlimited "Add Place" clicks
  - Add soft warning at 10+ POIs: "⚠️ You have 12 places. This day may span 2-3 pages in the PDF."
  - File: `frontend/src/components/DaySection.tsx`

**Estimated Time:** 30 minutes

---

## 📊 Progress Tracker

| Phase | Status | Files Changed | Time |
|-------|--------|---------------|------|
| Geocoding Preview | 🔄 In Progress | 6 files (3 new, 3 modified) | 2-3h |
| Description Quality | ⏳ Pending | 2 files | 30min |
| Remove POI Limit | ⏳ Pending | 2 files | 30min |

**Total Estimated Time:** 3-4 hours

---

## 🔄 Implementation Order

1. **Start**: Geocoding preview (most impactful UX improvement)
2. **Then**: Description quality (quick win)
3. **Finally**: Remove POI limit (nice to have)

---

## 📝 Session Notes

**Current Session (2026-02-15):**
- Completed deployment fixes (mixed content, geocoding, enrichment)
- User tested with Paris itinerary - works ✅
- User tested with Puerto Rico - geocoding accuracy issue identified
- Plan approved for 3 UX improvements
- Starting Phase 7: Geocoding Preview

---

## 📖 Documentation

See `DEBUG_NOTES.md` for detailed troubleshooting history and solutions.
