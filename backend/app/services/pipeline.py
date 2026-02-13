import logging
from sqlalchemy.orm import Session
from app.models import Trip

logger = logging.getLogger(__name__)

PIPELINE_STAGES = ["geocoding", "routing", "enriching", "rendering", "complete"]

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
    """Background pipeline that processes a trip through all stages.
    Each stage updates the trip status in the database.
    Actual logic will be added in later phases."""
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

    except Exception as e:
        logger.exception(f"Pipeline error for trip {trip_id}")
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        if trip:
            trip.status = "error"
            trip.error_message = str(e)
            db.commit()
    finally:
        db.close()
