import logging
import os
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session
from app.models import Trip

logger = logging.getLogger(__name__)

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")


def _build_template_data(trip: Trip) -> dict:
    """Build the template context from a Trip model and its enriched_data."""
    enriched = trip.enriched_data or {}
    routes = enriched.get("routes", {})
    places_enrichment = enriched.get("places", {})
    start_end_coords = enriched.get("start_end_coords", {})

    days = []
    for day in trip.days:
        day_number = str(day.day_number)
        route = routes.get(day_number)
        coords = start_end_coords.get(day_number, {})

        places = []
        for place in day.places:
            enrichment = places_enrichment.get(place.name)
            places.append({
                "name": place.name,
                "place_type": place.place_type,
                "latitude": place.latitude,
                "longitude": place.longitude,
                "enrichment": enrichment,
            })

        days.append({
            "day_number": day.day_number,
            "start_location": day.start_location,
            "end_location": day.end_location,
            "start_coords": coords.get("start"),
            "end_coords": coords.get("end"),
            "route": route,
            "places": places,
        })

    return {
        "trip": {
            "title": trip.title,
            "start_date": trip.start_date,
            "end_date": trip.end_date,
        },
        "days": days,
    }


def render_trip_html(trip: Trip) -> str:
    """Render a complete HTML document for a trip using the Jinja2 template."""
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template("travelbook.html")
    context = _build_template_data(trip)
    return template.render(**context)
