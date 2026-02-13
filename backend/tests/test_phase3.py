from unittest.mock import patch, MagicMock
import httpx
from app.models import Trip
from app.services.enrichment import (
    get_wikipedia_summary,
    get_wikimedia_image,
    enrich_trip,
    _truncate_to_words,
    _search_wikipedia_title,
)
from tests.conftest import SAMPLE_TRIP


# --- Mock Wikipedia API responses ---

WIKIPEDIA_RESPONSE = {
    "query": {
        "pages": {
            "12345": {
                "pageid": 12345,
                "title": "Eiffel Tower",
                "extract": (
                    "The Eiffel Tower is a wrought-iron lattice tower on the "
                    "Champ de Mars in Paris, France. It is named after the engineer "
                    "Gustave Eiffel, whose company designed and built the tower from "
                    "1887 to 1889 as the centerpiece of the 1889 World's Fair."
                ),
            }
        }
    }
}

WIKIPEDIA_NO_RESULT = {
    "query": {
        "pages": {
            "-1": {
                "ns": 0,
                "title": "NonexistentPlace12345",
                "missing": "",
            }
        }
    }
}

WIKIMEDIA_IMAGE_RESPONSE = {
    "query": {
        "pages": {
            "12345": {
                "pageid": 12345,
                "title": "Eiffel Tower",
                "thumbnail": {
                    "source": "https://upload.wikimedia.org/wikipedia/commons/thumb/eiffel.jpg/800px-eiffel.jpg",
                    "width": 800,
                    "height": 600,
                },
            }
        }
    }
}

WIKIMEDIA_NO_IMAGE = {
    "query": {
        "pages": {
            "12345": {
                "pageid": 12345,
                "title": "Eiffel Tower",
            }
        }
    }
}

# Long text for truncation testing (200+ words)
LONG_EXTRACT = " ".join([f"word{i}" for i in range(200)])


# --- Unit Tests: Wikipedia ---


def test_wikipedia_summary_extraction(db):
    """Mock Wikipedia API → verify description extraction."""
    mock_response = MagicMock()
    mock_response.json.return_value = WIKIPEDIA_RESPONSE
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    result = get_wikipedia_summary("Eiffel Tower", client=mock_client)

    assert result is not None
    assert "wrought-iron lattice tower" in result["description"]
    assert result["wikipedia_url"] == "https://en.wikipedia.org/wiki/Eiffel_Tower"


def test_wikipedia_truncation():
    """Verify description truncation to 150 words."""
    truncated = _truncate_to_words(LONG_EXTRACT, 150)
    words = truncated.rstrip("...").split()
    assert len(words) == 150
    assert truncated.endswith("...")


def test_wikipedia_short_text_not_truncated():
    """Short text should not be truncated."""
    short = "A short description of a place."
    result = _truncate_to_words(short, 150)
    assert result == short
    assert not result.endswith("...")


def test_wikipedia_no_result(db):
    """No Wikipedia page → returns None."""
    mock_response = MagicMock()
    mock_response.json.return_value = WIKIPEDIA_NO_RESULT
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    result = get_wikipedia_summary("NonexistentPlace12345", client=mock_client)
    assert result is None


def test_wikipedia_search_fallback_on_typo(db):
    """Typo in place name → search API finds correct article → returns summary."""
    # Exact match fails (page not found)
    mock_no_result = MagicMock()
    mock_no_result.json.return_value = WIKIPEDIA_NO_RESULT
    mock_no_result.raise_for_status = MagicMock()

    # Search returns the correct title
    mock_search = MagicMock()
    mock_search.json.return_value = [
        "Eifel Tower",  # typo query
        ["Eiffel Tower"],  # correct title found
        ["The Eiffel Tower is..."],
        ["https://en.wikipedia.org/wiki/Eiffel_Tower"],
    ]
    mock_search.raise_for_status = MagicMock()

    # Second extract call with correct title succeeds
    mock_extract = MagicMock()
    mock_extract.json.return_value = WIKIPEDIA_RESPONSE
    mock_extract.raise_for_status = MagicMock()

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = [mock_no_result, mock_search, mock_extract]

    result = get_wikipedia_summary("Eifel Tower", client=mock_client)

    assert result is not None
    assert "wrought-iron lattice tower" in result["description"]
    assert result["wikipedia_url"] == "https://en.wikipedia.org/wiki/Eiffel_Tower"


def test_wikipedia_api_error(db):
    """Wikipedia API error → returns None gracefully."""
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = httpx.HTTPError("Connection timeout")

    result = get_wikipedia_summary("Eiffel Tower", client=mock_client)
    assert result is None


# --- Unit Tests: Wikimedia Images ---


def test_wikimedia_image_url(db):
    """Mock Wikimedia → verify thumbnail URL and attribution."""
    mock_response = MagicMock()
    mock_response.json.return_value = WIKIMEDIA_IMAGE_RESPONSE
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    result = get_wikimedia_image("Eiffel Tower", client=mock_client)

    assert result is not None
    assert "upload.wikimedia.org" in result["image_url"]
    assert "800px" in result["image_url"]
    assert result["image_attribution"] is not None
    assert "CC" in result["image_attribution"]


def test_wikimedia_no_image(db):
    """Page exists but no image → returns None."""
    mock_response = MagicMock()
    mock_response.json.return_value = WIKIMEDIA_NO_IMAGE
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    result = get_wikimedia_image("Eiffel Tower", client=mock_client)
    assert result is None


def test_wikimedia_api_error(db):
    """Wikimedia API error → returns None gracefully."""
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = httpx.HTTPError("Connection timeout")

    result = get_wikimedia_image("Eiffel Tower", client=mock_client)
    assert result is None


# --- Unit Tests: Fallback Handling ---


def test_fallback_no_wikipedia_no_image(db):
    """Place with no Wikipedia result → still included with fallback description."""
    mock_no_result = MagicMock()
    mock_no_result.json.return_value = WIKIPEDIA_NO_RESULT
    mock_no_result.raise_for_status = MagicMock()

    mock_no_image = MagicMock()
    mock_no_image.json.return_value = WIKIMEDIA_NO_IMAGE
    mock_no_image.raise_for_status = MagicMock()

    # opensearch returns empty results
    mock_search_empty = MagicMock()
    mock_search_empty.json.return_value = ["Unknown Café", [], [], []]
    mock_search_empty.raise_for_status = MagicMock()

    mock_client = MagicMock(spec=httpx.Client)
    # get_wikipedia_summary: _fetch_extract (no result) → _search_wikipedia_title (empty)
    # get_wikimedia_image: _fetch_page_image (no image) → _search_wikipedia_title (empty)
    mock_client.get.side_effect = [
        mock_no_result, mock_search_empty,  # wikipedia summary
        mock_no_image, mock_search_empty,   # wikimedia image
    ]

    result_wiki = get_wikipedia_summary("Unknown Café", client=mock_client)
    result_img = get_wikimedia_image("Unknown Café", client=mock_client)

    assert result_wiki is None
    assert result_img is None


# --- Integration Tests: enrich_trip ---


def test_enrich_trip_populates_places(client, db):
    """Enrichment stage populates enriched_data with place descriptions + images."""
    # Create trip via API first
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
    mock_wiki.json.return_value = WIKIPEDIA_RESPONSE
    mock_wiki.raise_for_status = MagicMock()

    mock_image = MagicMock()
    mock_image.json.return_value = WIKIMEDIA_IMAGE_RESPONSE
    mock_image.raise_for_status = MagicMock()

    mock_http = MagicMock(spec=httpx.Client)

    def route_side_effect(url, **kwargs):
        url_str = str(url)
        if "nominatim" in url_str:
            return mock_nominatim
        if "router.project-osrm" in url_str:
            return mock_osrm
        # Wikipedia/Wikimedia calls — alternate between wiki and image
        params = kwargs.get("params", {})
        prop = params.get("prop", "")
        if "extracts" in prop:
            return mock_wiki
        return mock_image

    mock_http.get.side_effect = route_side_effect

    with patch("app.services.geocoding.httpx.Client", return_value=mock_http):
        with patch("app.services.routing.httpx.Client", return_value=mock_http):
            with patch("app.services.enrichment.httpx.Client", return_value=mock_http):
                resp = client.post("/api/trips", json=SAMPLE_TRIP)
                trip_id = resp.json()["id"]

    # Check enriched_data
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    db.refresh(trip)

    assert trip.status == "complete"
    assert trip.enriched_data is not None
    assert "places" in trip.enriched_data
    assert "routes" in trip.enriched_data

    places = trip.enriched_data["places"]
    assert "Eiffel Tower" in places
    assert "wrought-iron" in places["Eiffel Tower"]["description"]
    assert places["Eiffel Tower"]["image_url"] is not None
    assert places["Eiffel Tower"]["wikipedia_url"] is not None


def test_enrich_trip_fallback_description(client, db):
    """Places with no Wikipedia data get fallback 'No description available.'."""
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

    # Wikipedia returns no results for all places
    mock_wiki_no_result = MagicMock()
    mock_wiki_no_result.json.return_value = WIKIPEDIA_NO_RESULT
    mock_wiki_no_result.raise_for_status = MagicMock()

    mock_no_image = MagicMock()
    mock_no_image.json.return_value = WIKIMEDIA_NO_IMAGE
    mock_no_image.raise_for_status = MagicMock()

    mock_http = MagicMock(spec=httpx.Client)

    # opensearch returns empty results
    mock_search_empty = MagicMock()
    mock_search_empty.json.return_value = ["query", [], [], []]
    mock_search_empty.raise_for_status = MagicMock()

    def route_side_effect(url, **kwargs):
        url_str = str(url)
        if "nominatim" in url_str:
            return mock_nominatim
        if "router.project-osrm" in url_str:
            return mock_osrm
        params = kwargs.get("params", {})
        action = params.get("action", "")
        if action == "opensearch":
            return mock_search_empty
        prop = params.get("prop", "")
        if "extracts" in prop:
            return mock_wiki_no_result
        return mock_no_image

    mock_http.get.side_effect = route_side_effect

    with patch("app.services.geocoding.httpx.Client", return_value=mock_http):
        with patch("app.services.routing.httpx.Client", return_value=mock_http):
            with patch("app.services.enrichment.httpx.Client", return_value=mock_http):
                resp = client.post("/api/trips", json=SAMPLE_TRIP)
                trip_id = resp.json()["id"]

    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    db.refresh(trip)

    assert trip.status == "complete"
    places = trip.enriched_data["places"]

    # All places should have fallback description
    for place_name, info in places.items():
        assert info["description"] == "No description available."
        assert info["image_url"] is None


def test_enriched_data_json_structure(client, db):
    """Verify the complete enriched_data JSON structure after enrichment."""
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
    mock_wiki.json.return_value = WIKIPEDIA_RESPONSE
    mock_wiki.raise_for_status = MagicMock()

    mock_image = MagicMock()
    mock_image.json.return_value = WIKIMEDIA_IMAGE_RESPONSE
    mock_image.raise_for_status = MagicMock()

    mock_http = MagicMock(spec=httpx.Client)

    def route_side_effect(url, **kwargs):
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

    mock_http.get.side_effect = route_side_effect

    with patch("app.services.geocoding.httpx.Client", return_value=mock_http):
        with patch("app.services.routing.httpx.Client", return_value=mock_http):
            with patch("app.services.enrichment.httpx.Client", return_value=mock_http):
                resp = client.post("/api/trips", json=SAMPLE_TRIP)
                trip_id = resp.json()["id"]

    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    db.refresh(trip)

    enriched = trip.enriched_data
    assert isinstance(enriched, dict)

    # Must have both routes and places
    assert "routes" in enriched
    assert "places" in enriched

    # Each place must have required keys
    for place_name, info in enriched["places"].items():
        assert "description" in info
        assert "image_url" in info
        assert "image_attribution" in info
        assert "wikipedia_url" in info
