import logging
import re
import httpx
from sqlalchemy.orm import Session
from app.models import Trip
from app.services.geocoding import get_place_metadata

logger = logging.getLogger(__name__)


def _normalize_place_name(name: str) -> str:
    """Normalize place name for better Wikipedia search results.
    Strips common prefixes/suffixes that might confuse search."""
    normalized = name.strip()

    # Remove leading "the" (case insensitive)
    if normalized.lower().startswith("the "):
        normalized = normalized[4:]

    # Common word replacements for better matching
    replacements = {
        " museum": "",  # "Louvre Museum" -> "Louvre"
        " tower": "",   # "Eiffel Tower" -> "Eiffel"
    }

    normalized_lower = normalized.lower()
    for old, new in replacements.items():
        if normalized_lower.endswith(old):
            normalized = normalized[:len(normalized) - len(old)] + new
            break

    return normalized.strip()

WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
WIKIMEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "TravelBookGenerator/1.0 (travelbook@example.com)"
MAX_DESCRIPTION_WORDS = 50  # Optimized for 2.5 lines at 11px font


def _extract_native_name(text: str) -> tuple[str | None, str]:
    """Extract native name/pronunciation from Wikipedia text.
    Returns (native_name, cleaned_text)."""
    # Match patterns like "French: [ʁwajal]" or "(French: Palais Royal)"
    patterns = [
        r'\([^)]*?:\s*([^\)]+)\)',  # (French: xxx)
        r'[,;]\s+([^,;]+?:\s*[^\.,;]+)',  # , French: xxx
    ]

    for pattern in patterns:
        match = re.search(pattern, text[:200])  # Only check first 200 chars
        if match:
            native = match.group(1).strip()
            # Remove from text
            text = re.sub(pattern, '', text, count=1).strip()
            return (native, text)

    return (None, text)


def _extract_sentences(text: str, max_words: int = 50) -> str:
    """Extract first complete sentences up to max_words for readable descriptions.

    Preserves sentence structure for better readability compared to keyword extraction.
    Optimized for PDF layout: ~50 words fits 2.5 lines at 11px font.
    """
    # Remove citations and parentheticals
    text = re.sub(r'\[[^\]]+\]', '', text)
    text = re.sub(r'\([^)]+\)', '', text)
    text = text.strip()

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)

    result = []
    word_count = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        words = sentence.split()
        sentence_word_count = len(words)

        # If adding this sentence keeps us under or at the limit, add it
        if word_count + sentence_word_count <= max_words:
            result.append(sentence)
            word_count += sentence_word_count
        else:
            # If we have less than 70% of target words, add partial sentence
            if word_count < max_words * 0.7:
                remaining_words = max_words - word_count
                partial = ' '.join(words[:remaining_words]) + '...'
                result.append(partial)
            break

    return ' '.join(result) if result else text[:max_words * 6] + '...'


def _truncate_to_words(text: str, max_words: int) -> str:
    """Truncate text to max_words, appending '...' if truncated."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."


def _is_disambiguation_page(text: str) -> bool:
    """Check if Wikipedia extract is from a disambiguation page."""
    disambiguation_indicators = [
        "may refer to:",
        "may also refer to:",
        "can refer to:",
        "may stand for:",
    ]
    text_lower = text.lower()[:200]  # Check first 200 chars
    return any(indicator in text_lower for indicator in disambiguation_indicators)


def _search_wikipedia_by_coordinates(lat: float, lon: float, client: httpx.Client) -> str | None:
    """Use Wikipedia's geosearch API to find articles near specific coordinates.
    This helps avoid disambiguation pages by finding the most relevant local article."""
    try:
        response = client.get(
            WIKIPEDIA_API_URL,
            params={
                "action": "query",
                "list": "geosearch",
                "gscoord": f"{lat}|{lon}",
                "gsradius": 1000,  # Search within 1km radius
                "gslimit": 1,
                "format": "json",
            },
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("query", {}).get("geosearch", [])
        if results:
            return results[0].get("title")
    except Exception as e:
        logger.error(f"Wikipedia geosearch failed for ({lat}, {lon}): {e}")
    return None


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

        # Extract native name and clean text
        native_name, cleaned_extract = _extract_native_name(extract)

        # Extract complete sentences for readable descriptions
        summary = _extract_sentences(cleaned_extract, MAX_DESCRIPTION_WORDS)

        return {
            "description": summary,
            "native_name": native_name,
            "wikipedia_url": f"https://en.wikipedia.org/wiki/{canon_title.replace(' ', '_')}",
        }
    return None


def get_wikipedia_summary(place_name: str, lat: float | None = None, lon: float | None = None, client: httpx.Client | None = None) -> dict | None:
    """Query Wikipedia API for a place summary.
    Tries multiple query variations for better success rate.
    Uses coordinates (if provided) to avoid disambiguation pages.
    Returns dict with 'description' and 'wikipedia_url', or None if not found."""
    should_close = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        should_close = True

    try:
        # Try geosearch first if we have coordinates
        if lat is not None and lon is not None:
            logger.info(f"Trying geosearch for '{place_name}' at coordinates ({lat}, {lon})")
            geo_title = _search_wikipedia_by_coordinates(lat, lon, client)
            if geo_title:
                logger.info(f"Geosearch found title: '{geo_title}'")
                result = _fetch_extract(geo_title, client)
                if result:
                    is_disambig = _is_disambiguation_page(result["description"])
                    logger.info(f"Geosearch result is_disambiguation: {is_disambig}")
                    if not is_disambig:
                        logger.info(f"✓ Wikipedia found for '{place_name}' via geosearch → '{geo_title}'")
                        return result
                    else:
                        logger.warning(f"✗ Geosearch returned disambiguation page for '{geo_title}', trying other methods")

        # Try multiple query variations
        normalized_name = _normalize_place_name(place_name)
        queries = [place_name]  # Original first
        if normalized_name != place_name:
            queries.append(normalized_name)  # Normalized second

        for query in queries:
            # Try exact title match
            result = _fetch_extract(query, client)
            if result and not _is_disambiguation_page(result["description"]):
                logger.info(f"✓ Wikipedia found for '{place_name}' using query '{query}'")
                return result

            # Fallback: search for best matching title
            search_title = _search_wikipedia_title(query, client)
            if search_title and search_title != query:
                result = _fetch_extract(search_title, client)
                if result and not _is_disambiguation_page(result["description"]):
                    logger.info(f"✓ Wikipedia found for '{place_name}' via search '{query}' → '{search_title}'")
                    return result

        logger.warning(f"✗ No Wikipedia page for '{place_name}' after trying {len(queries)} queries")
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
    Tries multiple query variations for better success rate.
    Returns dict with 'image_url' and 'image_attribution', or None."""
    should_close = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        should_close = True

    try:
        # Try multiple query variations
        normalized_name = _normalize_place_name(place_name)
        queries = [place_name]  # Original first
        if normalized_name != place_name:
            queries.append(normalized_name)  # Normalized second

        for query in queries:
            # Try exact title
            result = _fetch_page_image(query, client)
            if result:
                return result

            # Fallback: search for best matching title
            search_title = _search_wikipedia_title(query, client)
            if search_title and search_title != query:
                result = _fetch_page_image(search_title, client)
                if result:
                    return result

        return None
    finally:
        if should_close:
            client.close()


def _create_fallback_description(metadata: dict, place_type: str) -> str:
    """Create a basic description from Nominatim metadata when Wikipedia is not available."""
    parts = []

    # Type/category
    place_category = metadata.get("type", "").replace("_", " ").title()
    if place_category:
        parts.append(place_category)

    # Cuisine for restaurants
    cuisine = metadata.get("cuisine", "")
    if cuisine:
        parts.append(f"{cuisine.replace('_', ' ').title()} cuisine")

    # Address components
    address = metadata.get("address", {})
    city = address.get("city", "")
    country = address.get("country", "")

    if city or country:
        location = f"{city}, {country}" if city and country else city or country
        parts.append(f"Located in {location}")

    # Build description
    if parts:
        # First part as type, rest as additional info
        description = parts[0]
        if len(parts) > 1:
            description += " • " + " • ".join(parts[1:])
        return description

    return f"{place_type.title()} - No additional information available"


def enrich_trip(db: Session, trip: Trip, client: httpx.Client | None = None) -> dict:
    """Enrich all places in a trip with Wikipedia descriptions and Wikimedia images.
    Falls back to Nominatim metadata for places without Wikipedia articles.
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
                    "native_name": None,
                    "image_url": None,
                    "image_attribution": None,
                    "wikipedia_url": None,
                    "source": "none",  # Track data source: wikipedia, nominatim, or none
                }

                # Try Wikipedia first (best quality)
                # Pass coordinates to avoid disambiguation pages
                wiki = get_wikipedia_summary(
                    place.name,
                    lat=place.latitude,
                    lon=place.longitude,
                    client=client
                )
                if wiki:
                    place_info["description"] = wiki["description"]
                    place_info["native_name"] = wiki.get("native_name")
                    place_info["wikipedia_url"] = wiki["wikipedia_url"]
                    place_info["source"] = "wikipedia"

                    # Get Wikimedia image
                    image = get_wikimedia_image(place.name, client)
                    if image:
                        place_info["image_url"] = image["image_url"]
                        place_info["image_attribution"] = image["image_attribution"]
                else:
                    # Fallback to Nominatim metadata
                    logger.info(f"Wikipedia not available for '{place.name}', using Nominatim metadata")
                    metadata = get_place_metadata(place.name, client)
                    if metadata:
                        place_info["description"] = _create_fallback_description(metadata, place.place_type)
                        place_info["source"] = "nominatim"
                        # No image for Nominatim fallback
                        logger.info(f"✓ Using Nominatim fallback for '{place.name}': {place_info['description']}")
                    else:
                        logger.warning(f"✗ No enrichment data available for '{place.name}'")

                places_data[place.name] = place_info
    finally:
        if should_close:
            client.close()

    return places_data
