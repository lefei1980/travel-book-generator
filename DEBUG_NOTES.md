# Phase 4 Complete — End-to-End Demo Results

## Test Results (2026-02-13)

### What Worked
- Frontend and backend servers started successfully
- Trip creation via web form worked (POST /api/trips returned 201)
- Status polling worked correctly (frontend polling every second)
- Pipeline progression through stages: pending → geocoding → routing → enriching → rendering
- PDF generation completed successfully
- Download endpoint served generated PDF

### Issues Found & Fixed
1. **Nominatim 403 Forbidden**: FIXED by using real email address
   - Root cause: `example.com` email in User-Agent was blocked by Nominatim
   - Solution: Use real email (lefei1980@hotmail.com) via environment variable
   - Result: Geocoding now works correctly

2. **Incomplete pipeline handling**: When geocoding fails, the pipeline may stall or error handling could be improved

### Fixes Applied
- [x] Update Nominatim User-Agent with a valid contact email (replace `example.com`)
  - Created `.env` file with `CONTACT_EMAIL` setting
  - Using real email: lefei1980@hotmail.com
  - `geocoding.py` now loads email from environment variable
- [x] Add geocoding mock/test mode for demo/testing without external API
  - Added `MOCK_GEOCODING=true` option in `.env`
  - Returns mock coordinates for common cities (Paris, London, Tokyo, New York)
- [x] Improve error handling: show meaningful errors when geocoding fails
  - Added specific 403 error message with instructions
- [ ] Add fallback geocoding provider or graceful degradation

### Demo Results (with real Nominatim)
- Trip: "Paris Adventure" with Eiffel Tower, Louvre Museum, Cafe de Flore
- Pipeline completed in ~7 seconds
- Generated PDF: 2.6MB with maps and content
- All geocoding requests successful with real email

## Completed Phases
- [x] Phase 1: Core infrastructure — FastAPI + Next.js + SQLite + trip CRUD
- [x] Phase 2: Geospatial engine — Nominatim geocoding + OSRM routing
- [x] Phase 3: POI enrichment — Wikipedia summaries + Wikimedia Commons images + fuzzy search fallback
- [x] Phase 4: Map + PDF rendering — Jinja2 templates, Leaflet maps, Playwright PDF generation

## Map Rendering Enhancements (2026-02-13 Evening)

### User Feedback on Initial PDF
After reviewing `paris_route_test.pdf`, the following issues were identified:
1. Background map looked vague with low contrast
2. Starting and ending locations not clearly marked
3. POIs on map not numbered - confusing which pin is which location
4. Front page map should use day-colored pins (no route) matching Day X titles

### Enhancements Implemented
- [x] **Enhanced map contrast & resolution**
  - Switched from OpenStreetMap to CartoDB Voyager tiles (`rastertiles/voyager`)
  - Much better readability and contrast in PDF output
  - Higher quality rendering at all zoom levels

- [x] **Unique start/end markers**
  - Green "START" flag marker for first location on each day's route
  - Red "END" flag marker for last location on each day's route
  - Clear visual differentiation from regular POI markers

- [x] **Numbered POI markers**
  - Each POI now has a numbered marker (1, 2, 3...) on the map
  - Matching number badges on POI description cards below the map
  - Easy to correlate map pins with text descriptions
  - Middle POIs use color-coded numbered markers (attraction=red, restaurant=orange, hotel=dark)

- [x] **Color-coded front page map**
  - Summary map now uses day-colored markers (Day 1=red, Day 2=blue, Day 3=green, etc.)
  - Colors match the "Day X" titles in the trip overview section
  - No route lines on summary map - just location markers
  - 7 distinct day colors defined for multi-day trips

### Test Results
- Generated `paris_map_enhanced.pdf` with 2-day Paris itinerary
- File size: 6.8MB (larger due to higher quality tiles)
- All 4 enhancements verified working
- Maps render correctly with proper marker icons and numbering

### Critical Geocoding Bug Found & Fixed (2026-02-13 Evening)

**Problem**: Maps showed incorrect locations - Day 1 ending in USA, Day 2 ending in Portugal
- Root cause: Geocoding queries lacked city context
- Example: "Hotel des Arts" returned San Francisco location instead of Paris
- "Notre-Dame Cathedral" returned Luxembourg location instead of Paris Notre-Dame

**Fix Implemented**:
- Modified `geocode_trip()` in `geocoding.py` to extract city context from start/end locations
- Added `_extract_city_context()` function to parse city/country from location strings
- Now queries "Notre-Dame Cathedral, France" instead of just "Notre-Dame Cathedral"
- Ensures disambiguous geocoding results for common place names

**Verification**:
- All test locations now correctly geocoded to Paris (lat: 48.8-48.9, lon: 2.2-2.4)
- Generated `paris_corrected_geocoding.pdf` (7.0MB) with accurate maps
- Notre-Dame: 48.8529, 2.3501 ✓
- All 7 POIs verified within Paris bounds ✓

### Additional Map & Content Fixes (2026-02-13 Late Evening)

**Problem**: Map markers and descriptions issues
1. START/END markers were replacing first/last POIs instead of being separate
2. Descriptions too verbose with full sentences
3. French/native names mixed into description body

**Fixes Implemented**:

**Map Marker Fix**:
- Modified `pipeline.py` to store start/end location coordinates in `enriched_data.start_end_coords`
- Updated `maps.py` to include `start_coords` and `end_coords` in template data
- Changed template to render START/END as separate markers (not replacing POIs)
- Now all POIs get numbered 1-N, with separate START/END flags for start_location/end_location

**Description Improvements**:
- Reduced `MAX_DESCRIPTION_WORDS` from 75 to 30
- Added `_extract_native_name()` to pull out French/native language text
- Added `_summarize_to_keywords()` to convert sentences to keyword-based summaries
- Removes filler words ("is", "are", "the", "a", etc.)
- Native names now shown in title line as "(French: xxx)" instead of in description body

**Test Results**:
- Generated `paris_final_test.pdf` (7.0MB)
- Day 1: 4 numbered POIs + START (CDG Airport) + END (Montmartre)
- Day 2: 3 numbered POIs + START (Montmartre) + END (Latin Quarter)
- All markers correctly positioned with proper numbering

### Map Zoom & Route Fix (2026-02-13 Final)

**User Feedback**:
1. Route polyline not visible on maps
2. Day 2 map too zoomed out - POIs cramped together
3. Want close-up zoom on POIs, start/end can be outside map bounds
4. Route should still show even if start/end markers are outside

**Fix Implemented**:
- Modified map bounds calculation to focus on POIs only (not start/end)
- Route polyline always renders (full OSRM geometry)
- START/END markers only show if within 50% padding of POI area
- If start/end outside map, route still visible leading to/from them
- Increased padding to 0.15 (from 0.12) for better POI visibility

**Test Results**:
- Generated `paris_route_zoom_fixed.pdf` (3.7MB)
- Day 1: Route visible, 3 POIs clearly shown, appropriate zoom
- Day 2: Close-up on 2 POIs, route visible connecting them
- START/END markers conditional based on proximity to POIs

### Final Fixes (2026-02-13 Night)

**Issues Found**:
1. Map zoom too aggressive - only showing POIs, route circling outside
2. Descriptions shortened but not truly keyword-based
3. Pipeline not saving route data (routes missing from enriched_data)

**Fixes Applied**:
- **Map zoom**: Changed bounds to include start, end, AND POIs (pad 0.1)
- **Route persistence**: Added `flag_modified()` to pipeline routing stage
- **Keyword descriptions**: Much more aggressive summarization:
  - Only first 1-2 sentences
  - Remove ALL filler words (is, are, the, a, of, for, etc.)
  - Remove parenthetical and pronunciation info
  - Convert commas/semicolons to bullets (•)

**Final Test**:
- Generated `paris_ALL_FIXED.pdf` (3.7MB)
- Routes present for both days ✓
- Map shows start, POIs, end ✓
- Descriptions: "Louvre • national art museum Paris • France • former royal palace..." (185 chars)

## Phase 5: Complete ✅

All core functionality implemented and tested:
- [x] Map rendering with high-contrast tiles
- [x] START/END markers with numbered POIs
- [x] Route polylines visible and correct
- [x] Geocoding with city context
- [x] Keyword-based descriptions
- [x] PDF generation with Playwright

---

## Phase 6: Deployment Issues (2026-02-14/15)

### Issue 1: Backend Deployment Failed ❌

**Error Message** (from GitHub Actions):
```
2026/02/14 19:45:15 Error: missing server host
```

**Root Cause**:
GitHub Secrets are **NOT configured** in the repository. The workflow files (`.github/workflows/deploy-backend.yml` and `deploy-frontend.yml`) are correct, but they reference secrets that don't exist yet.

**Required Secrets** (6 total):

#### Backend Deployment (3 secrets)
- `ORACLE_VM_HOST` - Oracle Cloud VM public IP address (e.g., `123.45.67.89`)
- `ORACLE_VM_USER` - SSH username (usually `ubuntu`)
- `ORACLE_VM_SSH_KEY` - SSH private key for GitHub Actions authentication

#### Frontend Deployment (3 secrets)
- `VERCEL_TOKEN` - Vercel API token (from https://vercel.com/account/tokens)
- `VERCEL_ORG_ID` - Vercel organization ID (from `.vercel/project.json`)
- `VERCEL_PROJECT_ID` - Vercel project ID (from `.vercel/project.json`)

**Current Status**: None of these secrets are configured yet.

---

### Solution Steps

#### Prerequisites (Must Do First)

1. **Set Up Oracle Cloud VM**
   - Create VM at https://cloud.oracle.com (Always Free tier)
   - Configure security list: open ports 22 (SSH) and 8000 (HTTP)
   - Note your VM's public IP address

2. **Deploy Backend Manually to VM First**
   ```bash
   # SSH into VM
   ssh ubuntu@YOUR_VM_IP

   # Install Docker + Docker Compose
   sudo apt update
   sudo apt install -y docker.io docker-compose git
   sudo usermod -aG docker ubuntu
   exit && ssh ubuntu@YOUR_VM_IP  # Reconnect

   # Clone repo
   cd ~
   git clone https://github.com/lefei1980/travel-book-generator.git

   # Set up backend
   cd travel-book-generator/backend
   cp .env.example .env
   nano .env  # Edit CONTACT_EMAIL

   # Deploy
   chmod +x deploy.sh
   ./deploy.sh

   # Verify
   curl http://localhost:8000/health
   # Should return: {"status":"ok"}
   ```

3. **Create SSH Key for GitHub Actions**
   ```bash
   # On your LOCAL machine
   ssh-keygen -t ed25519 -f ~/.ssh/github_actions_oracle -N ""

   # Copy public key to VM
   ssh-copy-id -i ~/.ssh/github_actions_oracle.pub ubuntu@YOUR_VM_IP

   # Test connection
   ssh -i ~/.ssh/github_actions_oracle ubuntu@YOUR_VM_IP
   # Should work without password
   exit

   # Get private key content (for GitHub Secret)
   cat ~/.ssh/github_actions_oracle
   # Copy the ENTIRE output
   ```

#### Add Secrets to GitHub

1. Go to https://github.com/lefei1980/travel-book-generator
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add all 6 secrets (see above for values)

#### Test Backend Deployment

After adding the 3 backend secrets:
```bash
# Make a small change
cd backend/app
echo "# Test" >> main.py

git add .
git commit -m "Test backend deployment"
git push origin main
```

Watch at: https://github.com/lefei1980/travel-book-generator/actions

#### Set Up Vercel (Frontend)

```bash
cd frontend

# Install Vercel CLI
npm install -g vercel

# Login and link project
vercel login
vercel link

# Get org and project IDs
cat .vercel/project.json
# Copy orgId and projectId values
```

Add the 3 frontend secrets to GitHub, then test with a frontend change.

---

### Troubleshooting Guide

**"missing server host"** → `ORACLE_VM_HOST` secret not set
**"Permission denied"** → SSH key not in VM's `~/.ssh/authorized_keys`
**"git pull fails"** → Run `git reset --hard origin/main` on VM
**"Health check fails"** → Check `docker-compose logs -f` on VM
**"Vercel deployment fails"** → Verify token is valid, re-run `vercel link`

---

### Current Deployment Status

- [ ] Oracle Cloud VM created and configured
- [ ] Backend deployed manually to VM (working at http://localhost:8000)
- [ ] SSH key created and added to VM
- [ ] GitHub Secrets configured (0/6 done)
  - [ ] ORACLE_VM_HOST
  - [ ] ORACLE_VM_USER
  - [ ] ORACLE_VM_SSH_KEY
  - [ ] VERCEL_TOKEN
  - [ ] VERCEL_ORG_ID
  - [ ] VERCEL_PROJECT_ID
- [ ] Backend auto-deployment tested
- [ ] Frontend auto-deployment tested
- [ ] End-to-end app working in production

**Next Step**: Follow the prerequisite steps above before attempting deployment again.