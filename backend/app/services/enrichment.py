import logging
import re
import math
import time
import httpx
from sqlalchemy.orm import Session
from app.models import Trip
from app.services.geocoding import get_place_metadata

logger = logging.getLogger(__name__)

# Wikipedia API rate limiting
WIKIPEDIA_REQUEST_DELAY = 0.4  # seconds between requests to avoid 429 errors
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # exponential backoff delays in seconds


def _wikipedia_api_call(client: httpx.Client, url: str, params: dict, headers: dict) -> httpx.Response:
    """Make a Wikipedia API call with rate limiting and retry logic for 429 errors."""
    for attempt in range(MAX_RETRIES):
        try:
            response = client.get(url, params=params, headers=headers)

            # Check for rate limiting
            if response.status_code == 429:
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    logger.warning(f"Wikipedia rate limit hit (429), retrying in {delay}s (attempt {attempt + 1}/{MAX_RETRIES})")
                    print(f"⚠️  [WIKIPEDIA] Rate limit, waiting {delay}s before retry...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Wikipedia rate limit hit (429), max retries exceeded")
                    response.raise_for_status()

            # Add delay after successful request to avoid rate limits
            time.sleep(WIKIPEDIA_REQUEST_DELAY)
            return response

        except httpx.HTTPStatusError as e:
            if e.response.status_code != 429 or attempt >= MAX_RETRIES - 1:
                raise

    # Should never reach here, but just in case
    raise Exception("Wikipedia API call failed after retries")


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


def _calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates using Haversine formula.
    Returns distance in meters."""
    # Earth's radius in meters
    R = 6371000

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Haversine formula
    a = math.sin(delta_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * \
        math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def _fetch_wikipedia_coordinates(title: str, client: httpx.Client) -> tuple[float, float] | None:
    """Fetch coordinates for a Wikipedia article.
    Returns (lat, lon) or None if article has no coordinates."""
    try:
        response = _wikipedia_api_call(
            client,
            WIKIPEDIA_API_URL,
            params={
                "action": "query",
                "titles": title,
                "prop": "coordinates",
                "format": "json",
            },
            headers={"User-Agent": USER_AGENT},
        )
        data = response.json()

        pages = data.get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            if page_id == "-1":
                return None
            coords = page.get("coordinates")
            if coords and len(coords) > 0:
                lat = coords[0].get("lat")
                lon = coords[0].get("lon")
                if lat is not None and lon is not None:
                    return (lat, lon)
        return None
    except Exception as e:
        logger.error(f"Failed to fetch coordinates for '{title}': {e}")
        return None


def _search_wikipedia_by_coordinates(lat: float, lon: float, client: httpx.Client) -> str | None:
    """Use Wikipedia's geosearch API to find articles near specific coordinates.
    This helps avoid disambiguation pages by finding the most relevant local article."""
    try:
        response = _wikipedia_api_call(
            client,
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
        response = _wikipedia_api_call(
            client,
            WIKIPEDIA_API_URL,
            params={
                "action": "opensearch",
                "search": place_name,
                "limit": 1,
                "format": "json",
            },
            headers={"User-Agent": USER_AGENT},
        )
        data = response.json()
        # opensearch returns [query, [titles], [descriptions], [urls]]
        if len(data) >= 2 and len(data[1]) > 0:
            return data[1][0]
    except Exception as e:
        logger.error(f"Wikipedia search failed for '{place_name}': {e}")
    return None


def _search_wikipedia_titles(place_name: str, limit: int, client: httpx.Client) -> list[str]:
    """Use Wikipedia's search API to find multiple matching article titles.
    Returns up to 'limit' results for disambiguation handling."""
    try:
        response = _wikipedia_api_call(
            client,
            WIKIPEDIA_API_URL,
            params={
                "action": "opensearch",
                "search": place_name,
                "limit": limit,
                "format": "json",
            },
            headers={"User-Agent": USER_AGENT},
        )
        data = response.json()
        # opensearch returns [query, [titles], [descriptions], [urls]]
        if len(data) >= 2 and len(data[1]) > 0:
            return data[1]
        return []
    except Exception as e:
        logger.error(f"Wikipedia search failed for '{place_name}': {e}")
        return []


def _fetch_extract(title: str, client: httpx.Client) -> dict | None:
    """Fetch the intro extract for an exact Wikipedia title."""
    try:
        response = _wikipedia_api_call(
            client,
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
            "canonical_title": canon_title,
        }
    return None


def get_wikipedia_summary(place_name: str, lat: float | None = None, lon: float | None = None, client: httpx.Client | None = None) -> dict | None:
    """Query Wikipedia API for a place summary.
    Uses coordinate-based matching to find the most relevant article.
    Compares geosearch (coordinate-based) and opensearch (fuzzy text) results,
    choosing the one closest to the target coordinates.
    Returns dict with 'description', 'wikipedia_url', and 'canonical_title', or None if not found."""
    print(f"🔍 [WIKIPEDIA] Looking up '{place_name}' with coords ({lat}, {lon})")
    should_close = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        should_close = True

    try:
        normalized_name = _normalize_place_name(place_name)
        queries = [place_name]  # Original first
        if normalized_name != place_name:
            queries.append(normalized_name)  # Normalized second

        # Use coordinate-based matching if we have coordinates
        if lat is not None and lon is not None:
            logger.info(f"Using coordinate-based matching for '{place_name}' at ({lat}, {lon})")
            print(f"📍 [COORDINATE MATCHING] Target location: ({lat}, {lon})")

            best_result = None
            best_distance = float('inf')
            best_source = None

            # Track closest match even if >2km (for cities/large areas)
            closest_result = None
            closest_distance = float('inf')
            closest_source = None

            # Try geosearch (finds articles with coordinates near the target)
            geo_title = _search_wikipedia_by_coordinates(lat, lon, client)
            if geo_title:
                logger.info(f"Geosearch found: '{geo_title}'")
                print(f"✓ [GEOSEARCH] Found article: '{geo_title}'")
                geo_result = _fetch_extract(geo_title, client)
                if geo_result and not _is_disambiguation_page(geo_result["description"]):
                    # Geosearch already found something near our coordinates
                    # Distance is implicitly small (within 1km radius)
                    geo_coords = _fetch_wikipedia_coordinates(geo_title, client)
                    if geo_coords:
                        geo_distance = _calculate_distance(lat, lon, geo_coords[0], geo_coords[1])
                        logger.info(f"Geosearch result '{geo_title}' is {geo_distance:.0f}m away")
                        print(f"📏 [GEOSEARCH] Distance: {geo_distance:.0f}m")

                        # Track as closest
                        closest_result = geo_result
                        closest_distance = geo_distance
                        closest_source = "geosearch"

                        # Also set as best if within 2km
                        if geo_distance <= 2000:
                            best_result = geo_result
                            best_distance = geo_distance
                            best_source = "geosearch"
                        else:
                            logger.info(f"Geosearch result beyond strict threshold ({geo_distance:.0f}m > 2000m)")
                            print(f"⚠️  [GEOSEARCH] Beyond 2km, tracking as fallback")
                    else:
                        # No coordinates - skip (likely not a geographic location)
                        logger.info(f"Geosearch result '{geo_title}' has no coordinates, skipping")
                        print(f"⚠️  [GEOSEARCH] No coordinates (not a place), skipping")
                else:
                    if geo_result:
                        logger.warning(f"Geosearch returned disambiguation page: '{geo_title}'")
                        print(f"⚠️  [GEOSEARCH] Disambiguation page detected")

            # Try opensearch (fuzzy text matching) - get multiple results to handle disambiguation
            for query in queries:
                search_titles = _search_wikipedia_titles(query, limit=5, client=client)
                if search_titles:
                    logger.info(f"Opensearch found {len(search_titles)} results for query '{query}': {search_titles}")
                    print(f"✓ [OPENSEARCH] Found {len(search_titles)} articles for '{query}'")

                    # Try each search result until we find a good match
                    for search_title in search_titles:
                        logger.info(f"Trying opensearch result: '{search_title}'")
                        print(f"  🔍 [OPENSEARCH] Checking: '{search_title}'")
                        search_result = _fetch_extract(search_title, client)

                        if search_result:
                            # Check if it's a disambiguation page
                            if _is_disambiguation_page(search_result["description"]):
                                logger.info(f"Skipping disambiguation page: '{search_title}'")
                                print(f"  ⚠️  [OPENSEARCH] Disambiguation page, skipping")
                                continue

                            # Get coordinates for opensearch result
                            search_coords = _fetch_wikipedia_coordinates(search_title, client)
                            if search_coords:
                                search_distance = _calculate_distance(lat, lon, search_coords[0], search_coords[1])
                                logger.info(f"Opensearch result '{search_title}' is {search_distance:.0f}m away")
                                print(f"  📏 [OPENSEARCH] Distance: {search_distance:.0f}m")

                                # Track closest match overall (even if >2km)
                                if search_distance < closest_distance:
                                    closest_result = search_result
                                    closest_distance = search_distance
                                    closest_source = "opensearch"

                                # Prefer matches within 2km (strict threshold for high confidence)
                                if search_distance <= 2000:
                                    # Prefer opensearch (text match) over geosearch when distances are very close
                                    # This handles cases where multiple articles exist at the same location
                                    distance_difference = search_distance - best_distance
                                    if search_distance < best_distance or distance_difference <= 100:
                                        if search_distance < best_distance:
                                            logger.info(f"Opensearch result is closer ({search_distance:.0f}m < {best_distance:.0f}m)")
                                            print(f"  ✨ [OPENSEARCH] Better match! ({search_distance:.0f}m)")
                                        else:
                                            logger.info(f"Opensearch result at similar distance ({search_distance:.0f}m vs {best_distance:.0f}m), preferring text match")
                                            print(f"  ✨ [OPENSEARCH] Similar distance, preferring text match ({search_distance:.0f}m vs {best_distance:.0f}m)")
                                        best_result = search_result
                                        best_distance = search_distance
                                        best_source = "opensearch"
                                else:
                                    logger.info(f"Opensearch result beyond strict threshold ({search_distance:.0f}m > 2000m), tracking as fallback")
                                    print(f"  ⚠️  [OPENSEARCH] Beyond 2km ({search_distance:.0f}m), tracking as fallback")
                            else:
                                # No coordinates - skip (likely person/concept, not a place)
                                logger.info(f"Opensearch result '{search_title}' has no coordinates, skipping")
                                print(f"  ⚠️  [OPENSEARCH] No coordinates (not a place), skipping")
                                continue

                    # Break after first query if we found a good result
                    if best_result and best_source and "opensearch" in best_source:
                        break

            # Return the best match found
            if best_result:
                logger.info(f"✓ Using {best_source} result (distance: {best_distance:.0f}m)")
                print(f"✅ [WIKIPEDIA] Selected: '{best_result['canonical_title']}' via {best_source} ({best_distance:.0f}m)")
                return best_result
            elif closest_result:
                # No match within 2km, but we found the closest geographic article
                # Accept it (likely a large city or area where 2km threshold is too strict)
                logger.info(f"✓ Using closest match beyond 2km threshold: {closest_source} result (distance: {closest_distance:.0f}m)")
                print(f"✅ [WIKIPEDIA] Selected closest match: '{closest_result['canonical_title']}' via {closest_source} ({closest_distance:.0f}m)")
                print(f"⚠️  [NOTE] Distance >{2000}m - likely a large city/area")
                return closest_result

        # Fallback: No coordinates, or coordinate-based matching found nothing
        # Use simple text-based search
        logger.info(f"Falling back to text-based search for '{place_name}'")
        print(f"🔄 [FALLBACK] Using text-based search")

        for query in queries:
            # Try exact title match
            result = _fetch_extract(query, client)
            if result and not _is_disambiguation_page(result["description"]):
                logger.info(f"✓ Wikipedia found for '{place_name}' using exact match '{query}'")
                print(f"✅ [WIKIPEDIA] Found via exact match: '{query}'")
                return result

            # Fallback: search for best matching title
            search_title = _search_wikipedia_title(query, client)
            if search_title and search_title != query:
                result = _fetch_extract(search_title, client)
                if result and not _is_disambiguation_page(result["description"]):
                    logger.info(f"✓ Wikipedia found for '{place_name}' via search '{query}' → '{search_title}'")
                    print(f"✅ [WIKIPEDIA] Found via opensearch: '{search_title}'")
                    return result

        logger.warning(f"✗ No Wikipedia page for '{place_name}' after trying {len(queries)} queries")
        print(f"❌ [WIKIPEDIA] No suitable article found for '{place_name}'")
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

                    # Get Wikimedia image using canonical Wikipedia title
                    # This ensures we search for images using the exact article title we found,
                    # not the user's original input (which may not match)
                    canonical_title = wiki.get("canonical_title", place.name)
                    logger.info(f"Fetching image for '{place.name}' using canonical title '{canonical_title}'")
                    image = get_wikimedia_image(canonical_title, client)
                    if image:
                        place_info["image_url"] = image["image_url"]
                        place_info["image_attribution"] = image["image_attribution"]
                        logger.info(f"✓ Found image for '{place.name}'")
                    else:
                        logger.warning(f"✗ No image found for '{place.name}' (canonical: '{canonical_title}')")
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
