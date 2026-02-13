import asyncio
import logging
import time
import httpx
from sqlalchemy.orm import Session
from app.models import GeocodingCache

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "TravelBookGenerator/1.0 (travelbook@example.com)"
MAX_RETRIES = 3

# Module-level timestamp for rate limiting across calls
_last_request_time: float = 0.0


def _rate_limit(min_delay: float = 1.5):
    """Enforce minimum delay between Nominatim requests for policy compliance."""
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < min_delay:
        time.sleep(min_delay - elapsed)
    _last_request_time = time.monotonic()


def geocode_place(name: str, db: Session, client: httpx.Client | None = None) -> tuple[float, float, str] | None:
    """Geocode a place name to (lat, lon, display_name).
    Checks SQLite cache first, then calls Nominatim API.
    Returns None if no results found."""

    # Check cache
    cached = db.query(GeocodingCache).filter(GeocodingCache.place_name == name).first()
    if cached:
        logger.debug(f"Cache hit for '{name}'")
        return (cached.latitude, cached.longitude, cached.display_name or name)

    # Call Nominatim with retry logic
    should_close = False
    if client is None:
        client = httpx.Client(timeout=15.0)
        should_close = True

    results = None
    try:
        for attempt in range(MAX_RETRIES):
            _rate_limit()
            try:
                response = client.get(
                    NOMINATIM_URL,
                    params={"q": name, "format": "json", "limit": 1},
                    headers={"User-Agent": USER_AGENT},
                )
                response.raise_for_status()
                results = response.json()
                break
            except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError) as e:
                wait = 2 ** (attempt + 1)
                logger.warning(f"Nominatim attempt {attempt + 1}/{MAX_RETRIES} failed for '{name}': {e}. Retrying in {wait}s...")
                time.sleep(wait)
            except Exception as e:
                logger.error(f"Nominatim request failed for '{name}': {e}")
                return None
    finally:
        if should_close:
            client.close()

    if results is None:
        logger.error(f"Nominatim failed after {MAX_RETRIES} retries for '{name}'")
        return None

    if not results:
        logger.warning(f"No geocoding results for '{name}'")
        return None

    result = results[0]
    lat = float(result["lat"])
    lon = float(result["lon"])
    display_name = result.get("display_name", name)

    # Store in cache
    cache_entry = GeocodingCache(
        place_name=name,
        latitude=lat,
        longitude=lon,
        display_name=display_name,
    )
    db.add(cache_entry)
    db.commit()

    logger.info(f"Geocoded '{name}' → ({lat}, {lon})")
    return (lat, lon, display_name)


def geocode_trip(db: Session, trip, client: httpx.Client | None = None) -> None:
    """Geocode all places in a trip, updating coordinates in the DB.
    Also geocodes start/end locations for each day."""
    should_close = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        should_close = True

    try:
        for day in trip.days:
            # Geocode start/end locations (for routing)
            for location_name in [day.start_location, day.end_location]:
                if location_name:
                    geocode_place(location_name, db, client)

            # Geocode each place
            for place in day.places:
                result = geocode_place(place.name, db, client)
                if result:
                    place.latitude, place.longitude = result[0], result[1]

            db.commit()
    finally:
        if should_close:
            client.close()
