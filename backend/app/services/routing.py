import logging
import httpx
from sqlalchemy.orm import Session
from app.models import Trip, GeocodingCache

logger = logging.getLogger(__name__)

OSRM_URL = "https://router.project-osrm.org/route/v1/driving"


def _get_coordinates(name: str, db: Session) -> tuple[float, float] | None:
    """Look up cached coordinates for a place name."""
    cached = db.query(GeocodingCache).filter(GeocodingCache.place_name == name).first()
    if cached:
        return (cached.longitude, cached.latitude)  # OSRM uses lon,lat order
    return None


def _build_waypoints(day, db: Session) -> list[tuple[float, float]]:
    """Build ordered waypoint list (lon, lat) for a day's itinerary."""
    waypoints = []

    # Start location
    if day.start_location:
        coords = _get_coordinates(day.start_location, db)
        if coords:
            waypoints.append(coords)

    # Places in order
    for place in day.places:
        if place.longitude is not None and place.latitude is not None:
            waypoints.append((place.longitude, place.latitude))

    # End location
    if day.end_location:
        coords = _get_coordinates(day.end_location, db)
        if coords:
            waypoints.append(coords)

    return waypoints


def get_route(waypoints: list[tuple[float, float]], client: httpx.Client | None = None) -> dict | None:
    """Call OSRM to get route between ordered waypoints.
    Returns dict with total_distance, total_duration, segments, and geometry."""
    if len(waypoints) < 2:
        return None

    coords_str = ";".join(f"{lon},{lat}" for lon, lat in waypoints)
    url = f"{OSRM_URL}/{coords_str}"

    should_close = False
    if client is None:
        client = httpx.Client(timeout=15.0)
        should_close = True

    try:
        response = client.get(
            url,
            params={
                "overview": "full",
                "geometries": "geojson",
                "steps": "false",
            },
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logger.error(f"OSRM request failed: {e}")
        return None
    finally:
        if should_close:
            client.close()

    if data.get("code") != "Ok" or not data.get("routes"):
        logger.warning(f"OSRM returned no routes: {data.get('code')}")
        return None

    route = data["routes"][0]
    legs = route.get("legs", [])

    segments = []
    for i, leg in enumerate(legs):
        segments.append({
            "from_index": i,
            "to_index": i + 1,
            "distance_m": leg["distance"],
            "duration_s": leg["duration"],
        })

    return {
        "total_distance_m": route["distance"],
        "total_duration_s": route["duration"],
        "geometry": route["geometry"],
        "segments": segments,
    }


def route_trip(db: Session, trip: Trip, client: httpx.Client | None = None) -> dict:
    """Compute routes for all days in a trip.
    Returns enriched route data keyed by day number."""
    should_close = False
    if client is None:
        client = httpx.Client(timeout=15.0)
        should_close = True

    route_data = {}
    try:
        for day in trip.days:
            waypoints = _build_waypoints(day, db)
            if len(waypoints) >= 2:
                route_result = get_route(waypoints, client)
                if route_result:
                    route_data[str(day.day_number)] = route_result
                    logger.info(
                        f"Day {day.day_number}: {route_result['total_distance_m']/1000:.1f}km, "
                        f"{route_result['total_duration_s']/60:.0f}min"
                    )
                else:
                    route_data[str(day.day_number)] = None
            else:
                route_data[str(day.day_number)] = None
    finally:
        if should_close:
            client.close()

    return route_data
