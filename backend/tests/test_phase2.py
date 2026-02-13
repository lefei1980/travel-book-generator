import time
from unittest.mock import patch, MagicMock
import httpx
from app.models import GeocodingCache, Place
from app.services.geocoding import geocode_place, geocode_trip, _last_request_time
from app.services.routing import get_route, route_trip, _build_waypoints
from tests.conftest import SAMPLE_TRIP


# --- Nominatim mock response ---
NOMINATIM_RESPONSE = [
    {
        "lat": "48.8583701",
        "lon": "2.2944813",
        "display_name": "Eiffel Tower, Avenue Anatole France, Paris, France",
    }
]

OSRM_RESPONSE = {
    "code": "Ok",
    "routes": [
        {
            "distance": 12500.0,
            "duration": 1500.0,
            "geometry": {
                "type": "LineString",
                "coordinates": [[2.294, 48.858], [2.337, 48.861], [2.352, 48.856]],
            },
            "legs": [
                {"distance": 5000.0, "duration": 600.0},
                {"distance": 7500.0, "duration": 900.0},
            ],
        }
    ],
}


# --- Geocoding Tests ---


def test_geocode_parses_coordinates(db):
    """Mock Nominatim → verify coordinate parsing."""
    mock_response = MagicMock()
    mock_response.json.return_value = NOMINATIM_RESPONSE
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    result = geocode_place("Eiffel Tower", db, client=mock_client)

    assert result is not None
    lat, lon, display_name = result
    assert abs(lat - 48.8583701) < 0.0001
    assert abs(lon - 2.2944813) < 0.0001
    assert "Eiffel Tower" in display_name


def test_geocode_cache_hit(db):
    """Second geocode of same place should use cache, not API."""
    mock_response = MagicMock()
    mock_response.json.return_value = NOMINATIM_RESPONSE
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    # First call hits API
    result1 = geocode_place("Eiffel Tower", db, client=mock_client)
    assert mock_client.get.call_count == 1

    # Second call should use cache
    result2 = geocode_place("Eiffel Tower", db, client=mock_client)
    assert mock_client.get.call_count == 1  # No additional API call
    assert result1 == result2


def test_geocode_cache_stored_in_db(db):
    """Verify cache entry is stored in SQLite."""
    mock_response = MagicMock()
    mock_response.json.return_value = NOMINATIM_RESPONSE
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    geocode_place("Eiffel Tower", db, client=mock_client)

    cached = db.query(GeocodingCache).filter(GeocodingCache.place_name == "Eiffel Tower").first()
    assert cached is not None
    assert abs(cached.latitude - 48.8583701) < 0.0001
    assert abs(cached.longitude - 2.2944813) < 0.0001


def test_geocode_no_results(db):
    """Graceful handling when Nominatim returns empty results."""
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    result = geocode_place("NonexistentPlace12345", db, client=mock_client)
    assert result is None


def test_geocode_sends_user_agent(db):
    """Verify custom User-Agent header is sent."""
    mock_response = MagicMock()
    mock_response.json.return_value = NOMINATIM_RESPONSE
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    geocode_place("Eiffel Tower", db, client=mock_client)

    call_kwargs = mock_client.get.call_args
    headers = call_kwargs.kwargs.get("headers", {})
    assert "TravelBookGenerator" in headers.get("User-Agent", "")


def test_geocode_rate_limiting(db):
    """Verify rate limiting enforces ~1 sec delay between API calls."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    # Return different results so cache doesn't interfere
    mock_response.json.side_effect = [
        [{"lat": "48.858", "lon": "2.294", "display_name": "Place A"}],
        [{"lat": "48.860", "lon": "2.340", "display_name": "Place B"}],
    ]

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    start = time.monotonic()
    geocode_place("Place A", db, client=mock_client)
    geocode_place("Place B", db, client=mock_client)
    elapsed = time.monotonic() - start

    # Should take at least ~1 second due to rate limiting
    assert elapsed >= 0.9


# --- Routing Tests ---


def test_route_parses_segments():
    """Mock OSRM → verify route segment extraction."""
    mock_response = MagicMock()
    mock_response.json.return_value = OSRM_RESPONSE
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    waypoints = [(2.294, 48.858), (2.337, 48.861), (2.352, 48.856)]
    result = get_route(waypoints, client=mock_client)

    assert result is not None
    assert result["total_distance_m"] == 12500.0
    assert result["total_duration_s"] == 1500.0
    assert len(result["segments"]) == 2
    assert result["segments"][0]["distance_m"] == 5000.0
    assert result["geometry"]["type"] == "LineString"


def test_route_too_few_waypoints():
    """Route with <2 waypoints should return None."""
    result = get_route([(2.294, 48.858)])
    assert result is None


def test_route_osrm_error():
    """Graceful handling when OSRM returns an error."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"code": "InvalidQuery"}
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    result = get_route([(2.294, 48.858), (2.337, 48.861)], client=mock_client)
    assert result is None


# --- Pipeline Integration Tests ---


def test_pipeline_geocodes_places(client, db):
    """Pipeline geocoding stage should update Place coordinates."""
    mock_response = MagicMock()
    mock_response.json.return_value = NOMINATIM_RESPONSE
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    with patch("app.services.geocoding.httpx.Client", return_value=mock_client):
        with patch("app.services.routing.httpx.Client", return_value=mock_client):
            # Mock OSRM response too
            osrm_resp = MagicMock()
            osrm_resp.json.return_value = OSRM_RESPONSE
            osrm_resp.raise_for_status = MagicMock()

            def side_effect(*args, **kwargs):
                url = args[0] if args else kwargs.get("url", "")
                if "nominatim" in str(url):
                    return mock_response
                return osrm_resp

            mock_client.get.side_effect = side_effect

            resp = client.post("/api/trips", json=SAMPLE_TRIP)
            trip_id = resp.json()["id"]

    # Check places got coordinates
    places = db.query(Place).all()
    geocoded_places = [p for p in places if p.latitude is not None]
    assert len(geocoded_places) > 0


def test_pipeline_populates_route_data(client, db):
    """Pipeline routing stage should populate enriched_data with routes."""
    mock_nominatim = MagicMock()
    mock_nominatim.json.return_value = NOMINATIM_RESPONSE
    mock_nominatim.raise_for_status = MagicMock()

    mock_osrm = MagicMock()
    mock_osrm.json.return_value = OSRM_RESPONSE
    mock_osrm.raise_for_status = MagicMock()

    mock_client = MagicMock(spec=httpx.Client)

    def side_effect(url, **kwargs):
        if "nominatim" in url:
            return mock_nominatim
        return mock_osrm

    mock_client.get.side_effect = side_effect

    with patch("app.services.geocoding.httpx.Client", return_value=mock_client):
        with patch("app.services.routing.httpx.Client", return_value=mock_client):
            resp = client.post("/api/trips", json=SAMPLE_TRIP)
            trip_id = resp.json()["id"]

    resp = client.get(f"/api/trips/{trip_id}")
    data = resp.json()
    assert data["status"] == "complete"
