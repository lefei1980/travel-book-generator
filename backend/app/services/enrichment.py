import logging
import httpx
from sqlalchemy.orm import Session
from app.models import Trip

logger = logging.getLogger(__name__)

WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
WIKIMEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "TravelBookGenerator/1.0 (travelbook@example.com)"
MAX_DESCRIPTION_WORDS = 150


def _truncate_to_words(text: str, max_words: int) -> str:
    """Truncate text to max_words, appending '...' if truncated."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."


def _search_wikipedia_title(place_name: str, client: httpx.Client) -> str | None:
    """Use Wikipedia's search API to find the best matching article title.
    Handles typos, vague names, and alternate spellings."""
    try:
        response = client.get(
            WIKIPEDIA_API_URL,
            params={
                "action": "opensearch",
                "search": place_name,
                "limit": 1,
                "format": "json",
            },
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        data = response.json()
        # opensearch returns [query, [titles], [descriptions], [urls]]
        if len(data) >= 2 and len(data[1]) > 0:
            return data[1][0]
    except Exception as e:
        logger.error(f"Wikipedia search failed for '{place_name}': {e}")
    return None


def _fetch_extract(title: str, client: httpx.Client) -> dict | None:
    """Fetch the intro extract for an exact Wikipedia title."""
    try:
        response = client.get(
            WIKIPEDIA_API_URL,
            params={
                "action": "query",
                "titles": title,
                "prop": "extracts",
                "exintro": True,
                "explaintext": True,
                "format": "json",
                "redirects": 1,
            },
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logger.error(f"Wikipedia extract failed for '{title}': {e}")
        return None

    pages = data.get("query", {}).get("pages", {})
    for page_id, page in pages.items():
        if page_id == "-1":
            return None
        extract = page.get("extract", "")
        if not extract:
            return None
        canon_title = page.get("title", title)
        return {
            "description": _truncate_to_words(extract, MAX_DESCRIPTION_WORDS),
            "wikipedia_url": f"https://en.wikipedia.org/wiki/{canon_title.replace(' ', '_')}",
        }
    return None


def get_wikipedia_summary(place_name: str, client: httpx.Client | None = None) -> dict | None:
    """Query Wikipedia API for a place summary.
    First tries exact title match (with redirects). If that fails, falls back
    to Wikipedia's search API to handle typos and vague names.
    Returns dict with 'description' and 'wikipedia_url', or None if not found."""
    should_close = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        should_close = True

    try:
        # Try exact title match first
        result = _fetch_extract(place_name, client)
        if result:
            return result

        # Fallback: search for best matching title
        logger.info(f"Exact match failed for '{place_name}', trying search fallback")
        search_title = _search_wikipedia_title(place_name, client)
        if search_title and search_title != place_name:
            result = _fetch_extract(search_title, client)
            if result:
                return result

        logger.warning(f"No Wikipedia page for '{place_name}'")
        return None
    finally:
        if should_close:
            client.close()


def _fetch_page_image(title: str, client: httpx.Client) -> dict | None:
    """Fetch a Wikimedia Commons thumbnail for an exact Wikipedia title."""
    try:
        response = client.get(
            WIKIMEDIA_API_URL,
            params={
                "action": "query",
                "titles": title,
                "prop": "pageimages|imageinfo",
                "piprop": "thumbnail",
                "pithumbsize": 800,
                "iiprop": "extmetadata",
                "format": "json",
                "redirects": 1,
            },
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logger.error(f"Wikimedia API failed for '{title}': {e}")
        return None

    pages = data.get("query", {}).get("pages", {})
    for page_id, page in pages.items():
        if page_id == "-1":
            return None
        thumbnail = page.get("thumbnail", {})
        image_url = thumbnail.get("source")
        if not image_url:
            return None
        return {
            "image_url": image_url,
            "image_attribution": "CC BY-SA 3.0, Wikimedia Commons",
        }
    return None


def get_wikimedia_image(place_name: str, client: httpx.Client | None = None) -> dict | None:
    """Fetch a Wikimedia Commons thumbnail URL + license for a place.
    Tries exact title first, then falls back to search API.
    Returns dict with 'image_url' and 'image_attribution', or None."""
    should_close = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        should_close = True

    try:
        result = _fetch_page_image(place_name, client)
        if result:
            return result

        # Fallback: search for best matching title
        search_title = _search_wikipedia_title(place_name, client)
        if search_title and search_title != place_name:
            return _fetch_page_image(search_title, client)

        return None
    finally:
        if should_close:
            client.close()


def enrich_trip(db: Session, trip: Trip, client: httpx.Client | None = None) -> dict:
    """Enrich all places in a trip with Wikipedia descriptions and Wikimedia images.
    Returns a dict keyed by place name with description, image, and URLs."""
    should_close = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        should_close = True

    places_data = {}
    try:
        for day in trip.days:
            for place in day.places:
                place_info = {
                    "description": "No description available.",
                    "image_url": None,
                    "image_attribution": None,
                    "wikipedia_url": None,
                }

                # Get Wikipedia summary
                wiki = get_wikipedia_summary(place.name, client)
                if wiki:
                    place_info["description"] = wiki["description"]
                    place_info["wikipedia_url"] = wiki["wikipedia_url"]

                # Get Wikimedia image
                image = get_wikimedia_image(place.name, client)
                if image:
                    place_info["image_url"] = image["image_url"]
                    place_info["image_attribution"] = image["image_attribution"]

                places_data[place.name] = place_info
    finally:
        if should_close:
            client.close()

    return places_data
