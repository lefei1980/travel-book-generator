import logging
from sqlalchemy.orm import Session
from app.models import Trip
from app.services.geocoding import geocode_trip
from app.services.routing import route_trip
from app.services.enrichment import enrich_trip
from app.services.pdf import generate_pdf

logger = logging.getLogger(__name__)

PIPELINE_STAGES = ["geocoding", "routing", "enriching", "rendering", "preview_ready"]

# Overridable session factory for testing
_session_factory = None


def set_session_factory(factory):
    global _session_factory
    _session_factory = factory


def _get_session() -> Session:
    if _session_factory:
        return _session_factory()
    from app.database import SessionLocal
    return SessionLocal()


def run_pipeline(trip_id: str) -> None:
    """Background pipeline that processes a trip through all stages."""
    db: Session = _get_session()
    try:
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        if not trip:
            logger.error(f"Trip {trip_id} not found")
            return

        for stage in PIPELINE_STAGES:
            trip = db.query(Trip).filter(Trip.id == trip_id).first()
            if trip.status == "error":
                return

            trip.status = stage
            db.commit()
            logger.info(f"Trip {trip_id}: stage={stage}")

            if stage == "geocoding":
                geocode_trip(db, trip)
                # Store start/end coordinates for map rendering
                start_end_coords = {}
                for day in trip.days:
                    from app.models import GeocodingCache
                    coords = {}
                    if day.start_location:
                        cached = db.query(GeocodingCache).filter(
                            GeocodingCache.place_name.like(f"%{day.start_location}%")
                        ).first()
                        if cached:
                            coords["start"] = {"lat": cached.latitude, "lng": cached.longitude, "name": day.start_location}
                    if day.end_location:
                        cached = db.query(GeocodingCache).filter(
                            GeocodingCache.place_name.like(f"%{day.end_location}%")
                        ).first()
                        if cached:
                            coords["end"] = {"lat": cached.latitude, "lng": cached.longitude, "name": day.end_location}
                    start_end_coords[str(day.day_number)] = coords

                enriched = trip.enriched_data or {}
                enriched["start_end_coords"] = start_end_coords
                trip.enriched_data = enriched
                db.commit()

            elif stage == "routing":
                route_data = route_trip(db, trip)
                enriched = dict(trip.enriched_data or {})
                enriched["routes"] = route_data
                trip.enriched_data = enriched
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(trip, "enriched_data")
                db.commit()

            elif stage == "enriching":
                places_data = enrich_trip(db, trip)
                enriched = dict(trip.enriched_data or {})
                enriched["places"] = places_data
                trip.enriched_data = enriched
                db.commit()

            elif stage == "rendering":
                # Generate HTML preview but don't create PDF yet
                from app.services.maps import render_trip_html
                html_content = render_trip_html(trip)

                # Store HTML in enriched_data for preview
                enriched = dict(trip.enriched_data or {})
                enriched["html_preview"] = html_content
                trip.enriched_data = enriched
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(trip, "enriched_data")
                db.commit()

                logger.info(f"Trip {trip_id}: HTML preview generated, ready for user review")

    except Exception as e:
        logger.exception(f"Pipeline error for trip {trip_id}")
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        if trip:
            trip.status = "error"
            trip.error_message = str(e)
            db.commit()
    finally:
        db.close()
