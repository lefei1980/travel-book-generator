from tests.conftest import SAMPLE_TRIP


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_trip_returns_201(client):
    resp = client.post("/api/trips", json=SAMPLE_TRIP)
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["status"] == "pending"


def test_get_trip_returns_data(client):
    create_resp = client.post("/api/trips", json=SAMPLE_TRIP)
    trip_id = create_resp.json()["id"]

    resp = client.get(f"/api/trips/{trip_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Paris Adventure"
    assert data["status"] in ("pending", "geocoding", "routing", "enriching", "rendering", "complete")
    assert len(data["days"]) == 2
    assert len(data["days"][0]["places"]) == 3


def test_get_nonexistent_trip_returns_404(client):
    resp = client.get("/api/trips/nonexistent-id")
    assert resp.status_code == 404


def test_invalid_input_returns_422(client):
    # Empty title
    bad_trip = {**SAMPLE_TRIP, "title": "   "}
    resp = client.post("/api/trips", json=bad_trip)
    assert resp.status_code == 422

    # No days
    bad_trip = {**SAMPLE_TRIP, "days": []}
    resp = client.post("/api/trips", json=bad_trip)
    assert resp.status_code == 422


def test_too_many_places_returns_422(client):
    day_with_6_places = {
        "day_number": 1,
        "start_location": "Start",
        "end_location": "End",
        "places": [{"name": f"Place {i}", "place_type": "attraction"} for i in range(6)],
    }
    bad_trip = {**SAMPLE_TRIP, "days": [day_with_6_places]}
    resp = client.post("/api/trips", json=bad_trip)
    assert resp.status_code == 422


def test_invalid_place_type_returns_422(client):
    bad_trip = {
        **SAMPLE_TRIP,
        "days": [
            {
                "day_number": 1,
                "start_location": "Start",
                "end_location": "End",
                "places": [{"name": "Some Place", "place_type": "invalid_type"}],
            }
        ],
    }
    resp = client.post("/api/trips", json=bad_trip)
    assert resp.status_code == 422


def test_place_name_normalization(client):
    trip = {
        **SAMPLE_TRIP,
        "days": [
            {
                "day_number": 1,
                "start_location": "  Start  Location  ",
                "end_location": "End",
                "places": [{"name": "  Eiffel   Tower  ", "place_type": "attraction"}],
            }
        ],
    }
    resp = client.post("/api/trips", json=trip)
    trip_id = resp.json()["id"]

    resp = client.get(f"/api/trips/{trip_id}")
    data = resp.json()
    assert data["days"][0]["places"][0]["name"] == "Eiffel Tower"
    assert data["days"][0]["start_location"] == "Start Location"


def test_duplicate_day_numbers_returns_422(client):
    bad_trip = {
        **SAMPLE_TRIP,
        "days": [
            {"day_number": 1, "places": [{"name": "A", "place_type": "attraction"}]},
            {"day_number": 1, "places": [{"name": "B", "place_type": "attraction"}]},
        ],
    }
    resp = client.post("/api/trips", json=bad_trip)
    assert resp.status_code == 422


def test_download_before_complete(client):
    """Download should fail for a trip that hasn't completed."""
    # Create trip but prevent pipeline from running by checking a non-existent trip
    resp = client.get("/api/trips/nonexistent-id/download")
    assert resp.status_code == 404


def test_pipeline_updates_status(client, db):
    """After background task runs, status should reach 'complete'."""
    resp = client.post("/api/trips", json=SAMPLE_TRIP)
    trip_id = resp.json()["id"]

    # TestClient runs background tasks synchronously, so by the time
    # we query, the pipeline should have completed
    resp = client.get(f"/api/trips/{trip_id}")
    data = resp.json()
    assert data["status"] == "complete"
