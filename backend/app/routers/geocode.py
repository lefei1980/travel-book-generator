"""Geocoding preview endpoints for real-time location verification."""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.geocoding import geocode_preview

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/geocode", tags=["geocoding"])


@router.get("/preview")
def get_geocode_preview(
    q: str = Query(..., description="Location query string"),
    limit: int = Query(10, ge=1, le=20, description="Maximum number of results"),
    db: Session = Depends(get_db),
):
    """
    Preview geocoding results for a location query.

    Returns multiple matching locations to help users verify accuracy
    before submitting the full trip form.

    - **q**: Location query (e.g., "mt. britton tower")
    - **limit**: Max results to return (1-20, default 10)

    Returns:
    - **results**: List of location matches with display_name, coordinates, type
    - **total**: Total number of results
    - **query**: Original query string
    """
    if not q or not q.strip():
        return {
            "query": q,
            "results": [],
            "total": 0,
            "message": "Query cannot be empty"
        }

    results = geocode_preview(q.strip(), db, limit=limit)

    return {
        "query": q,
        "results": results,
        "total": len(results),
    }
