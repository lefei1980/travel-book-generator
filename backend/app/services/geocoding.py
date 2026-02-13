import asyncio
import logging
import time
import httpx
from sqlalchemy.orm import Session
from app.models import GeocodingCache

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "TravelBookGenerator/1.0 (travelbook@example.com)"

# Module-level timestamp for rate limiting across calls
_last_request_time: float = 0.0


def _rate_limit():
    """Enforce 1 request/sec for Nominatim policy compliance."""
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
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

    # Rate limit before API call
    _rate_limit()

    # Call Nominatim
    should_close = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        should_close = True

    try:
        response = client.get(
            NOMINATIM_URL,
            params={"q": name, "format": "json", "limit": 1},
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        results = response.json()
    except Exception as e:
        logger.error(f"Nominatim request failed for '{name}': {e}")
        return None
    finally:
        if should_close:
            client.close()

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
