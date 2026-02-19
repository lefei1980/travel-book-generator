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


def geocode_preview(name: str, db: Session, limit: int = 10, client: httpx.Client | None = None) -> list[dict]:
    """Preview geocoding results for a location query.
    Returns multiple results (up to limit) to help users verify accuracy.

    Returns list of dicts with:
    - display_name: Human-readable location name
    - lat: Latitude
    - lon: Longitude
    - type: Location type (e.g., 'city', 'tourism', 'peak')
    - importance: Nominatim importance score (0-1)
    """
    # Mock mode for testing
    if MOCK_GEOCODING:
        logger.info(f"MOCK_GEOCODING enabled: returning mock preview for '{name}'")
        coords = _get_mock_coords(name)
        return [{
            "display_name": coords[2],
            "lat": coords[0],
            "lon": coords[1],
            "type": "mock",
            "importance": 1.0
        }]

    # Call Nominatim with multiple results
    should_close = False
    if client is None:
        client = httpx.Client(timeout=15.0)
        should_close = True

    results = []
    try:
        _rate_limit()
        try:
            response = client.get(
                NOMINATIM_URL,
                params={"q": name, "format": "json", "limit": limit},
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
            data = response.json()

            for item in data:
                results.append({
                    "display_name": item.get("display_name", name),
                    "lat": float(item["lat"]),
                    "lon": float(item["lon"]),
                    "type": item.get("type", "unknown"),
                    "importance": float(item.get("importance", 0)),
                })

        except Exception as e:
            logger.error(f"Nominatim preview request failed for '{name}': {e}")

    finally:
        if should_close:
            client.close()

    return results


def get_place_metadata(name: str, client: httpx.Client | None = None) -> dict | None:
    """Fetch detailed metadata from Nominatim for enrichment fallback.

    Returns dict with:
    - type: Place type (restaurant, tourism, etc.)
    - category: Category (fast_food, museum, etc.)
    - address: Structured address components
    - display_name: Full address string

    Used when Wikipedia enrichment fails to provide basic place info.
    """
    if MOCK_GEOCODING:
        return None

    should_close = False
    if client is None:
        client = httpx.Client(timeout=15.0)
        should_close = True

    try:
        _rate_limit()
        response = client.get(
            NOMINATIM_URL,
            params={
                "q": name,
                "format": "json",
                "limit": 1,
                "addressdetails": 1,  # Get structured address
                "extratags": 1,  # Get extra tags (cuisine, etc.)
            },
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        results = response.json()

        if not results:
            return None

        result = results[0]
        address = result.get("address", {})
        extratags = result.get("extratags", {})

        # Build metadata
        metadata = {
            "type": result.get("type", "place"),
            "category": result.get("class", ""),
            "display_name": result.get("display_name", name),
            "address": {
                "road": address.get("road", ""),
                "suburb": address.get("suburb", ""),
                "city": address.get("city") or address.get("town") or address.get("village", ""),
                "country": address.get("country", ""),
                "postcode": address.get("postcode", ""),
            },
            "cuisine": extratags.get("cuisine", ""),
            "opening_hours": extratags.get("opening_hours", ""),
        }

        return metadata

    except Exception as e:
        logger.error(f"Failed to fetch metadata for '{name}': {e}")
        return None
    finally:
        if should_close:
            client.close()


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


def _extract_neighborhood(name: str) -> str | None:
    """Extract a geocodable neighborhood/place from a vague accommodation description.
    E.g., 'AirBnb near Loiza' -> 'Loiza'
          'Hotel near Old Town'  -> 'Old Town'
          'Hostel in Miraflores' -> 'Miraflores'
    Returns None if no clear neighborhood can be extracted."""
    import re
    # Patterns like "near X", "in X", "at X", "by X" where X is the geocodable part
    match = re.search(r'\b(?:near|in|at|by|close to)\s+(.+)$', name, re.IGNORECASE)
    if match:
        extracted = match.group(1).strip()
        # Only return if it looks like a real place (not too short or too generic)
        if len(extracted) >= 3 and extracted.lower() not in {"the", "a", "an", "downtown", "center"}:
            return extracted
    return None


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


def _score_candidate(candidate: dict, name: str, city: str, country: str) -> float:
    """Score a Nominatim candidate result for relevance.

    Scoring:
    - Name found in display_name: +50
    - City found in display_name: +20
    - Country found in display_name: +20
    - Penalty for very short names (avoid wrong matches): -10 if name < 4 chars
    """
    display = candidate.get("display_name", "").lower()
    score = 0.0

    if name.lower() in display:
        score += 50
    elif any(word in display for word in name.lower().split() if len(word) > 3):
        # Partial word match (e.g., "Eiffel" matched in "Tour Eiffel")
        score += 25

    if city and city.lower() in display:
        score += 20

    if country and country.lower() in display:
        score += 20

    # Boost by Nominatim importance score (0-1 scale → up to +10 bonus)
    score += float(candidate.get("importance", 0)) * 10

    return score


def geocode_place_smart(
    name: str,
    city: str,
    country: str,
    db: Session,
    client: httpx.Client | None = None,
) -> tuple[float, float, str] | None:
    """Geocode a place using city/country context and multi-candidate scoring.

    Strategy:
    1. Build query: "Place Name, City, Country"
    2. Fetch up to 5 candidates from Nominatim
    3. Score each candidate (name match + city match + country match)
    4. Accept best if score >= 60
    5. If best score < 40: ask LLM for variant names and retry
    6. Always return best result above a minimum threshold (>= 20) or None
    """
    # Build cache key using the full context query
    context_parts = [p for p in [name, city, country] if p]
    cache_key = ", ".join(context_parts)

    # Check cache first
    cached = db.query(GeocodingCache).filter(GeocodingCache.place_name == cache_key).first()
    if cached:
        logger.debug(f"Cache hit for '{cache_key}'")
        return (cached.latitude, cached.longitude, cached.display_name or cache_key)

    # Also check cache for plain name, but only if BOTH city AND country match the cached result
    # (city alone is insufficient — e.g., "Keystone" exists in both Florida and South Dakota)
    cached = db.query(GeocodingCache).filter(GeocodingCache.place_name == name).first()
    if cached:
        display = (cached.display_name or "").lower()
        city_match = not city or city.lower() in display
        country_match = not country or country.lower() in display
        if city_match and country_match and (city or country):
            logger.debug(f"Cache hit (name only, city+country validated) for '{name}'")
            return (cached.latitude, cached.longitude, cached.display_name or name)

    if MOCK_GEOCODING:
        return geocode_place(name, db, client)

    should_close = False
    if client is None:
        client = httpx.Client(timeout=15.0)
        should_close = True

    def _fetch_candidates(query: str) -> list[dict]:
        """Fetch up to 5 candidates from Nominatim for a query."""
        _rate_limit()
        try:
            response = client.get(
                NOMINATIM_URL,
                params={"q": query, "format": "json", "limit": 5},
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Nominatim fetch failed for '{query}': {e}")
            return []

    def _best_candidate(candidates: list[dict]) -> tuple[dict | None, float]:
        """Return the best scored candidate and its score."""
        if not candidates:
            return None, 0.0
        scored = [(c, _score_candidate(c, name, city, country)) for c in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0]

    def _save_and_return(candidate: dict, key: str) -> tuple[float, float, str]:
        lat = float(candidate["lat"])
        lon = float(candidate["lon"])
        display = candidate.get("display_name", key)
        cache_entry = GeocodingCache(place_name=key, latitude=lat, longitude=lon, display_name=display)
        db.add(cache_entry)
        db.commit()
        return (lat, lon, display)

    try:
        # Build primary query with full context
        primary_query = cache_key
        candidates = _fetch_candidates(primary_query)
        best, score = _best_candidate(candidates)

        logger.info(f"Geocoding '{name}' (city={city}, country={country}): {len(candidates)} candidates, best score={score:.0f}")

        if best and score >= 60:
            # For high-confidence results, still validate country if specified
            if country and country.lower() not in best.get("display_name", "").lower():
                logger.warning(f"✗ Rejected high-score result for '{name}' — country '{country}' not in: {best.get('display_name', '')[:60]}")
                best = None
                score = 0
            else:
                logger.info(f"✓ High-confidence match for '{name}': {best.get('display_name', '')[:80]} (score={score:.0f})")
                return _save_and_return(best, cache_key)

        # Score too low — try plain name alone if we haven't already
        if city or country:
            plain_candidates = _fetch_candidates(name)
            plain_best, plain_score = _best_candidate(plain_candidates)
            if plain_best and plain_score > score:
                candidates = plain_candidates
                best = plain_best
                score = plain_score
                logger.info(f"Plain name search improved score to {score:.0f}")

        # Country validation: reject any result that doesn't match the expected country
        # This prevents "El Mesón" (Puerto Rico) → Spain, or "La Estación" (Puerto Rico) → Colombia
        if best and country:
            display_lower = best.get("display_name", "").lower()
            if country.lower() not in display_lower:
                logger.warning(f"✗ Country mismatch for '{name}': expected '{country}', got: {display_lower[:60]}")
                best = None
                score = 0

        if best and score >= 40:
            logger.info(f"✓ Medium-confidence match for '{name}': {best.get('display_name', '')[:80]} (score={score:.0f})")
            return _save_and_return(best, cache_key)

        # Low confidence — try LLM variant names as fallback
        if city or country:
            try:
                from app.services.llm import generate_name_variants
                variants = generate_name_variants(name, city or "", country or "")
                logger.info(f"LLM suggested variants for '{name}': {variants}")
                for variant in variants[:3]:
                    variant_query = f"{variant}, {city}, {country}" if city and country else variant
                    var_candidates = _fetch_candidates(variant_query)
                    var_best, var_score = _best_candidate(var_candidates)
                    if var_best and var_score > score:
                        best = var_best
                        score = var_score
                        logger.info(f"Variant '{variant}' improved score to {var_score:.0f}")
                    if var_best and var_score >= 60:
                        logger.info(f"✓ Variant match for '{name}' via '{variant}': score={var_score:.0f}")
                        return _save_and_return(var_best, cache_key)
            except Exception as e:
                logger.warning(f"LLM variant generation failed for '{name}': {e}")

        # Accept best available result even if below ideal threshold
        if best and score >= 20:
            logger.warning(f"⚠ Low-confidence match for '{name}': {best.get('display_name', '')[:80]} (score={score:.0f})")
            return _save_and_return(best, cache_key)

        logger.warning(f"✗ No usable geocoding result for '{name}'")
        return None

    finally:
        if should_close:
            client.close()


def geocode_trip(db: Session, trip, client: httpx.Client | None = None) -> None:
    """Geocode all places in a trip, updating coordinates in the DB.
    Also geocodes start/end locations for each day."""
    should_close = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        should_close = True

    # Load geocoding hints stored by the chat finalize endpoint (city/country per place)
    hints: dict[str, dict] = {}
    if trip.enriched_data:
        hints = trip.enriched_data.get("geocoding_hints", {})
    if hints:
        logger.info(f"Using {len(hints)} geocoding hints for trip {trip.id}")

    try:
        for day in trip.days:
            # Derive city/country context from this day's place hints
            # e.g. Day 2 has hints for "Mount Rushmore" (city=Keystone) → use that to geocode "Keystone RV Park"
            day_hints = {k: v for k, v in hints.items() if k.startswith(f"{day.day_number}:")}
            day_country = next((h.get("country", "") for h in day_hints.values() if h.get("country")), "")
            day_city = next((h.get("city", "") for h in day_hints.values() if h.get("city")), "")

            # Geocode start/end locations using smart scorer with day-level city/country context
            # This prevents "Keystone RV Park" → Florida instead of South Dakota
            seen_start_end: set[str] = set()
            for location_name in [day.start_location, day.end_location]:
                if not location_name or location_name in seen_start_end:
                    continue
                seen_start_end.add(location_name)

                logger.info(f"Geocoding start/end '{location_name}' (city='{day_city}', country='{day_country}')")
                result = geocode_place_smart(location_name, day_city, day_country, db, client)

                if not result:
                    # Try extracting neighborhood from vague descriptions like "AirBnb near Loiza"
                    neighborhood = _extract_neighborhood(location_name)
                    fallback = neighborhood or day_city
                    if fallback and fallback.lower() != location_name.lower():
                        logger.info(f"Start/end fallback: trying '{fallback}' for ungeocodable '{location_name}'")
                        fallback_result = geocode_place_smart(fallback, "", day_country, db, client)
                        if fallback_result:
                            # Store under the original context key so pipeline lookup finds it
                            ctx_key = ", ".join(p for p in [location_name, day_city, day_country] if p)
                            existing = db.query(GeocodingCache).filter(
                                GeocodingCache.place_name == ctx_key
                            ).first()
                            if not existing:
                                entry = GeocodingCache(
                                    place_name=ctx_key,
                                    latitude=fallback_result[0],
                                    longitude=fallback_result[1],
                                    display_name=f"{location_name} (approx. {fallback})",
                                )
                                db.add(entry)
                                db.commit()
                                logger.info(f"⚠ Stored approx. coords for '{location_name}' using '{fallback}'")

            # Geocode each place using smart scoring with city/country context
            for place in day.places:
                hint_key = f"{day.day_number}:{place.name}"
                hint = hints.get(hint_key, {})
                city = hint.get("city", "") or day_city or ""
                country = hint.get("country", "") or day_country or ""

                logger.info(f"Geocoding '{place.name}' (city='{city}', country='{country}')")
                result = geocode_place_smart(place.name, city, country, db, client)

                if result:
                    place.latitude, place.longitude = result[0], result[1]
                    logger.info(f"✓ Geocoded '{place.name}' → ({result[0]:.4f}, {result[1]:.4f})")
                else:
                    logger.warning(f"✗ Failed to geocode '{place.name}'")

            db.commit()
    finally:
        if should_close:
            client.close()
