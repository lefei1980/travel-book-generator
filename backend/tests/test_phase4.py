import os
from unittest.mock import patch, MagicMock
import httpx
from app.models import Trip, Day, Place
from app.services.maps import render_trip_html, _build_template_data
from app.services.pdf import generate_pdf, PDF_OUTPUT_DIR
from tests.conftest import SAMPLE_TRIP


# --- Sample enriched data (as produced by phases 2+3) ---

SAMPLE_ENRICHED_DATA = {
    "routes": {
        "1": {
            "total_distance_m": 12500.0,
            "total_duration_s": 1500.0,
            "geometry": {
                "type": "LineString",
                "coordinates": [[2.2945, 48.8584], [2.3376, 48.8606], [2.3325, 48.854]],
            },
            "segments": [
                {"from_index": 0, "to_index": 1, "distance_m": 5000.0, "duration_s": 600.0},
                {"from_index": 1, "to_index": 2, "distance_m": 7500.0, "duration_s": 900.0},
            ],
        },
    },
    "places": {
        "Eiffel Tower": {
            "description": "Iconic wrought-iron lattice tower on the Champ de Mars.",
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/eiffel.jpg/800px-eiffel.jpg",
            "image_attribution": "CC BY-SA 3.0, Wikimedia Commons",
            "wikipedia_url": "https://en.wikipedia.org/wiki/Eiffel_Tower",
        },
        "Louvre Museum": {
            "description": "The world's most-visited art museum.",
            "image_url": None,
            "image_attribution": None,
            "wikipedia_url": "https://en.wikipedia.org/wiki/Louvre",
        },
        "Café de Flore": {
            "description": "No description available.",
            "image_url": None,
            "image_attribution": None,
            "wikipedia_url": None,
        },
    },
}


def _create_trip_with_enriched_data(db):
    """Helper: create a trip in the DB with enriched_data populated."""
    trip = Trip(
        title="Paris Adventure",
        start_date="2025-06-01",
        end_date="2025-06-03",
        status="rendering",
        enriched_data=SAMPLE_ENRICHED_DATA,
    )
    db.add(trip)
    db.flush()

    day = Day(trip_id=trip.id, day_number=1, start_location="CDG Airport", end_location="Hotel Le Marais")
    db.add(day)
    db.flush()

    places = [
        Place(day_id=day.id, name="Eiffel Tower", place_type="attraction", order_index=0, latitude=48.8584, longitude=2.2945),
        Place(day_id=day.id, name="Louvre Museum", place_type="attraction", order_index=1, latitude=48.8606, longitude=2.3376),
        Place(day_id=day.id, name="Café de Flore", place_type="restaurant", order_index=2, latitude=48.854, longitude=2.3325),
    ]
    for p in places:
        db.add(p)
    db.commit()
    db.refresh(trip)
    return trip


# --- Template Tests ---


def test_template_renders_valid_html(db):
    """Jinja2 template produces valid HTML with map container and tile layer."""
    trip = _create_trip_with_enriched_data(db)
    html = render_trip_html(trip)

    assert "<!DOCTYPE html>" in html
    assert "map-day1" in html
    assert "tile.openstreetmap.org" in html
    assert "Paris Adventure" in html
    assert "Eiffel Tower" in html
    assert "Louvre Museum" in html
    assert "Café de Flore" in html


def test_template_includes_route_polyline(db):
    """Template includes OSRM route geometry as polyline."""
    trip = _create_trip_with_enriched_data(db)
    html = render_trip_html(trip)

    # Route coordinates should be embedded in the JS
    assert "2.2945" in html
    assert "48.8584" in html
    assert "L.polyline" in html


def test_template_includes_colored_markers(db):
    """Template renders different marker colors by place type."""
    trip = _create_trip_with_enriched_data(db)
    html = render_trip_html(trip)

    assert "poi-type-attraction" in html
    assert "poi-type-restaurant" in html
    assert "#d63031" in html  # attraction color
    assert "#e67e22" in html  # restaurant color


def test_template_includes_enrichment_data(db):
    """Template renders descriptions and images from enrichment."""
    trip = _create_trip_with_enriched_data(db)
    html = render_trip_html(trip)

    assert "wrought-iron lattice tower" in html
    assert "most-visited art museum" in html
    assert "No description available." in html
    assert "upload.wikimedia.org" in html


def test_template_includes_route_summary(db):
    """Template shows distance and duration in route summary."""
    trip = _create_trip_with_enriched_data(db)
    html = render_trip_html(trip)

    assert "12.5 km" in html
    assert "25 min" in html


def test_build_template_data_structure(db):
    """Verify _build_template_data returns correct structure."""
    trip = _create_trip_with_enriched_data(db)
    data = _build_template_data(trip)

    assert data["trip"]["title"] == "Paris Adventure"
    assert len(data["days"]) == 1
    day = data["days"][0]
    assert day["day_number"] == 1
    assert day["route"] is not None
    assert day["route"]["total_distance_m"] == 12500.0
    assert len(day["places"]) == 3
    assert day["places"][0]["enrichment"]["description"] == "Iconic wrought-iron lattice tower on the Champ de Mars."


def test_template_map_ready_signal(db):
    """Template includes mapReady signal for Playwright sync."""
    trip = _create_trip_with_enriched_data(db)
    html = render_trip_html(trip)

    assert "window.mapReady = true" in html
    assert "window.mapReady === true" not in html or "wait_for_function" not in html


# --- PDF Generation Tests ---


def test_pdf_generates_nonempty_file(db):
    """Playwright produces a non-empty PDF file."""
    trip = _create_trip_with_enriched_data(db)
    pdf_path = generate_pdf(trip)

    try:
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 0
        assert pdf_path.endswith(".pdf")
    finally:
        # Cleanup
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


# --- Pipeline Integration Tests ---


def test_pipeline_rendering_sets_complete(client, db):
    """Pipeline rendering stage sets status=complete and populates pdf_path."""
    mock_nominatim = MagicMock()
    mock_nominatim.json.return_value = [
        {"lat": "48.858", "lon": "2.294", "display_name": "Place"}
    ]
    mock_nominatim.raise_for_status = MagicMock()

    mock_osrm = MagicMock()
    mock_osrm.json.return_value = {
        "code": "Ok",
        "routes": [
            {
                "distance": 5000.0,
                "duration": 600.0,
                "geometry": {"type": "LineString", "coordinates": [[2.294, 48.858], [2.337, 48.861]]},
                "legs": [{"distance": 5000.0, "duration": 600.0}],
            }
        ],
    }
    mock_osrm.raise_for_status = MagicMock()

    mock_wiki = MagicMock()
    mock_wiki.json.return_value = {
        "query": {
            "pages": {
                "12345": {
                    "pageid": 12345,
                    "title": "Eiffel Tower",
                    "extract": "A famous tower in Paris.",
                }
            }
        }
    }
    mock_wiki.raise_for_status = MagicMock()

    mock_image = MagicMock()
    mock_image.json.return_value = {
        "query": {
            "pages": {
                "12345": {
                    "pageid": 12345,
                    "title": "Eiffel Tower",
                    "thumbnail": {
                        "source": "https://upload.wikimedia.org/eiffel.jpg",
                        "width": 800,
                        "height": 600,
                    },
                }
            }
        }
    }
    mock_image.raise_for_status = MagicMock()

    mock_http = MagicMock(spec=httpx.Client)

    def side_effect(url, **kwargs):
        url_str = str(url)
        if "nominatim" in url_str:
            return mock_nominatim
        if "router.project-osrm" in url_str:
            return mock_osrm
        params = kwargs.get("params", {})
        prop = params.get("prop", "")
        if "extracts" in prop:
            return mock_wiki
        return mock_image

    mock_http.get.side_effect = side_effect

    with patch("app.services.geocoding.httpx.Client", return_value=mock_http):
        with patch("app.services.routing.httpx.Client", return_value=mock_http):
            with patch("app.services.enrichment.httpx.Client", return_value=mock_http):
                resp = client.post("/api/trips", json=SAMPLE_TRIP)
                trip_id = resp.json()["id"]

    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    db.refresh(trip)

    assert trip.status == "complete"
    assert trip.pdf_path is not None
    assert os.path.exists(trip.pdf_path)
    assert os.path.getsize(trip.pdf_path) > 0

    # Cleanup
    if os.path.exists(trip.pdf_path):
        os.remove(trip.pdf_path)


def test_download_endpoint_returns_pdf(client, db):
    """GET /api/trips/{id}/download returns the PDF when status=complete."""
    mock_nominatim = MagicMock()
    mock_nominatim.json.return_value = [
        {"lat": "48.858", "lon": "2.294", "display_name": "Place"}
    ]
    mock_nominatim.raise_for_status = MagicMock()

    mock_osrm = MagicMock()
    mock_osrm.json.return_value = {
        "code": "Ok",
        "routes": [
            {
                "distance": 5000.0,
                "duration": 600.0,
                "geometry": {"type": "LineString", "coordinates": [[2.294, 48.858]]},
                "legs": [{"distance": 5000.0, "duration": 600.0}],
            }
        ],
    }
    mock_osrm.raise_for_status = MagicMock()

    mock_wiki = MagicMock()
    mock_wiki.json.return_value = {
        "query": {"pages": {"12345": {"pageid": 12345, "title": "Test", "extract": "A test place."}}}
    }
    mock_wiki.raise_for_status = MagicMock()

    mock_image = MagicMock()
    mock_image.json.return_value = {
        "query": {"pages": {"12345": {"pageid": 12345, "title": "Test"}}}
    }
    mock_image.raise_for_status = MagicMock()

    mock_http = MagicMock(spec=httpx.Client)

    def side_effect(url, **kwargs):
        url_str = str(url)
        if "nominatim" in url_str:
            return mock_nominatim
        if "router.project-osrm" in url_str:
            return mock_osrm
        params = kwargs.get("params", {})
        prop = params.get("prop", "")
        if "extracts" in prop:
            return mock_wiki
        return mock_image

    mock_http.get.side_effect = side_effect

    with patch("app.services.geocoding.httpx.Client", return_value=mock_http):
        with patch("app.services.routing.httpx.Client", return_value=mock_http):
            with patch("app.services.enrichment.httpx.Client", return_value=mock_http):
                resp = client.post("/api/trips", json=SAMPLE_TRIP)
                trip_id = resp.json()["id"]

    # Download the PDF
    resp = client.get(f"/api/trips/{trip_id}/download")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 0

    # Cleanup
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if trip and trip.pdf_path and os.path.exists(trip.pdf_path):
        os.remove(trip.pdf_path)
