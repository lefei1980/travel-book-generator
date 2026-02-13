# Current Phase: Phase 1 — Core Infrastructure

## Subtasks
- [ ] 1.1 Backend project setup (FastAPI, folder structure, requirements.txt)
- [ ] 1.2 SQLite database setup (SQLAlchemy models: Trip with status + enriched_data JSON, Day, Place)
- [ ] 1.3 Pydantic schemas (request/response, validation: max 5 POIs/day, required fields)
- [ ] 1.4 API endpoints (POST /api/trips, GET /api/trips/{id}, GET /api/trips/{id}/download stub)
- [ ] 1.5 Background pipeline skeleton (status lifecycle: pending→geocoding→...→complete)
- [ ] 1.6 Frontend setup (create-next-app with TypeScript)
- [ ] 1.7 Trip form (structured day-by-day input)
- [ ] 1.8 API integration (frontend submits trip, polls status, shows stage)

## Tests to Pass
- [ ] POST /api/trips returns 201 + trip ID
- [ ] GET /api/trips/{id} returns trip with status
- [ ] Invalid input returns 422
- [ ] Background task updates status through stages
- [ ] Place count validation rejects >5 POIs per day
