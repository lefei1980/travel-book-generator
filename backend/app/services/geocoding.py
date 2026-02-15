import asyncio
import logging
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.models import GeocodingCache

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "travelbook@localhost.local")
USER_AGENT = f"TravelBookGenerator/1.0 ({CONTACT_EMAIL})"
MOCK_GEOCODING = os.getenv("MOCK_GEOCODING", "false").lower() == "true"
MAX_RETRIES = 3

# Log configuration on module load (use print for visibility)
print(f"[GEOCODING CONFIG] Loaded from: {env_path}")
print(f"[GEOCODING CONFIG] CONTACT_EMAIL={CONTACT_EMAIL}")
print(f"[GEOCODING CONFIG] MOCK_GEOCODING={MOCK_GEOCODING}")
print(f"[GEOCODING CONFIG] Raw env value: {os.getenv('MOCK_GEOCODING', 'NOT_SET')}")

# Mock coordinates for testing when API is unavailable
MOCK_COORDS = {
    "paris": (48.8566, 2.3522, "Paris, France"),
    "london": (51.5074, -0.1278, "London, UK"),
    "tokyo": (35.6762, 139.6503, "Tokyo, Japan"),
    "new york": (40.7128, -74.0060, "New York, USA"),
    "default": (0.0, 0.0, "Unknown Location"),
}

# Module-level timestamp for rate limiting across calls
_last_request_time: float = 0.0


def _rate_limit(min_delay: float = 1.5):
    """Enforce minimum delay between Nominatim requests for policy compliance."""
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < min_delay:
        time.sleep(min_delay - elapsed)
    _last_request_time = time.monotonic()


def _get_mock_coords(name: str) -> tuple[float, float, str]:
    """Return mock coordinates for testing without external API."""
    name_lower = name.lower()
    for key, coords in MOCK_COORDS.items():
        if key in name_lower:
            return coords
    return MOCK_COORDS["default"]


def geocode_place(name: str, db: Session, client: httpx.Client | None = None) -> tuple[float, float, str] | None:
    """Geocode a place name to (lat, lon, display_name).
    Checks SQLite cache first, then calls Nominatim API.
    Returns None if no results found.
    If MOCK_GEOCODING is enabled, returns mock coordinates."""

    # Check cache
    cached = db.query(GeocodingCache).filter(GeocodingCache.place_name == name).first()
    if cached:
        logger.debug(f"Cache hit for '{name}'")
        return (cached.latitude, cached.longitude, cached.display_name or name)

    # Mock mode for testing
    if MOCK_GEOCODING:
        logger.info(f"MOCK_GEOCODING enabled: returning mock coordinates for '{name}'")
        coords = _get_mock_coords(name)
        cache_entry = GeocodingCache(
            place_name=name,
            latitude=coords[0],
            longitude=coords[1],
            display_name=coords[2],
        )
        db.add(cache_entry)
        db.commit()
        return coords

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
            except httpx.HTTPStatusError as e:
                wait = 2 ** (attempt + 1)
                if e.response.status_code == 403:
                    logger.error(
                        f"Nominatim returned 403 Forbidden for '{name}'. "
                        f"This is likely because the CONTACT_EMAIL in .env is invalid or blocked. "
                        f"Current User-Agent: {USER_AGENT}. "
                        f"Please update backend/.env with a valid email, or set MOCK_GEOCODING=true for testing."
                    )
                else:
                    logger.warning(f"Nominatim attempt {attempt + 1}/{MAX_RETRIES} failed for '{name}': {e}. Retrying in {wait}s...")
                time.sleep(wait)
            except (httpx.TimeoutException, httpx.ConnectError) as e:
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


def _normalize_place_name(name: str) -> str:
    """Normalize place name for better geocoding results.
    Strips common prefixes/suffixes that might confuse geocoding."""
    normalized = name.strip()

    # Remove leading "the" (case insensitive)
    if normalized.lower().startswith("the "):
        normalized = normalized[4:]

    # Common word replacements for better matching
    # Keep these minimal to avoid over-normalization
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


def _extract_city_context(location: str | None) -> str | None:
    """Extract city/country context from a location string.
    E.g., 'Charles de Gaulle Airport, Paris' -> 'Paris'
    E.g., 'Hotel des Arts, Paris' -> 'Paris'"""
    if not location:
        return None

    # Split by comma and take the last meaningful part
    parts = [p.strip() for p in location.split(',')]
    # Return the last 1-2 parts (e.g., "Paris" or "Paris, France")
    if len(parts) >= 2:
        return ', '.join(parts[-2:]) if len(parts) > 2 else parts[-1]
    return None


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

            # Extract city context from start or end location
            city_context = (
                _extract_city_context(day.start_location) or
                _extract_city_context(day.end_location)
            )

            # Geocode each place with city context
            for place in day.places:
                # Try multiple query variations for better success rate
                normalized_name = _normalize_place_name(place.name)

                queries = []
                # Try normalized name with city context first
                if city_context and city_context.lower() not in normalized_name.lower():
                    queries.append(f"{normalized_name}, {city_context}")
                # Fallback to normalized name alone
                queries.append(normalized_name)
                # Last resort: original name with city context
                if city_context and city_context.lower() not in place.name.lower():
                    queries.append(f"{place.name}, {city_context}")

                result = None
                for query in queries:
                    logger.info(f"Geocoding place '{place.name}' with query: '{query}'")
                    result = geocode_place(query, db, client)
                    if result:
                        place.latitude, place.longitude = result[0], result[1]
                        logger.info(f"✓ Successfully geocoded '{place.name}' using query '{query}'")
                        break

                if not result:
                    logger.warning(f"✗ Failed to geocode '{place.name}' after trying {len(queries)} queries")

            db.commit()
    finally:
        if should_close:
            client.close()
