from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Trip, Day, Place
from app.schemas import TripCreateRequest, TripResponse, TripCreateResponse
from app.services.pipeline import run_pipeline

router = APIRouter(prefix="/api/trips", tags=["trips"])


@router.post("", response_model=TripCreateResponse, status_code=201)
def create_trip(
    request: TripCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    trip = Trip(title=request.title, start_date=request.start_date, end_date=request.end_date, status="pending")
    db.add(trip)
    db.flush()

    for day_input in request.days:
        day = Day(
            trip_id=trip.id,
            day_number=day_input.day_number,
            start_location=day_input.start_location,
            end_location=day_input.end_location,
        )
        db.add(day)
        db.flush()

        for idx, place_input in enumerate(day_input.places):
            place = Place(
                day_id=day.id,
                name=place_input.name,
                place_type=place_input.place_type,
                order_index=idx,
            )
            db.add(place)

    db.commit()
    db.refresh(trip)

    background_tasks.add_task(run_pipeline, trip.id)

    return TripCreateResponse(id=trip.id, status=trip.status)


@router.get("/{trip_id}", response_model=TripResponse)
def get_trip(trip_id: str, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Build response with route data from enriched_data
    enriched = trip.enriched_data or {}
    routes = enriched.get("routes", {})

    days_data = []
    for day in trip.days:
        day_route = routes.get(str(day.day_number))
        places_data = [
            {
                "name": p.name,
                "place_type": p.place_type,
                "latitude": p.latitude,
                "longitude": p.longitude,
            }
            for p in day.places
        ]
        days_data.append({
            "day_number": day.day_number,
            "start_location": day.start_location,
            "end_location": day.end_location,
            "places": places_data,
            "route": day_route,
        })

    return {
        "id": trip.id,
        "title": trip.title,
        "start_date": trip.start_date,
        "end_date": trip.end_date,
        "status": trip.status,
        "error_message": trip.error_message,
        "days": days_data,
    }


@router.get("/{trip_id}/download")
def download_trip(trip_id: str, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.status != "complete":
        raise HTTPException(status_code=400, detail=f"Trip is not ready. Current status: {trip.status}")
    if not trip.pdf_path:
        raise HTTPException(status_code=404, detail="PDF not generated yet")
    return FileResponse(trip.pdf_path, media_type="application/pdf", filename=f"{trip.title}.pdf")
