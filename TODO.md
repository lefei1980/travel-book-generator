# Current Phase: Phase 3 — POI Enrichment

## Subtasks
- [ ] 3.1 Wikipedia service — query Wikipedia API, extract first paragraph, truncate to 150 words
- [ ] 3.2 Image service — fetch Wikimedia Commons thumbnail URL + license attribution
- [ ] 3.3 Pipeline integration — enrichment stage populates enriched_data JSON with descriptions + image URLs
- [ ] 3.4 Fallback handling — graceful degradation when Wikipedia has no result

## Tests to Pass
- [ ] Mock Wikipedia API → verify description extraction and word truncation
- [ ] Mock Wikimedia → verify thumbnail URL and attribution stored
- [ ] Test fallback: no Wikipedia result → place still included with "No description available"
- [ ] Verify enriched_data JSON structure after enrichment stage
