import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ChatSession, Trip, Day, Place
from app.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    FinalizeResponse,
    ChatSessionResponse,
    TripCreateRequest,
)
from app.services.llm import chat_with_llm, generate_itinerary_json
from app.services.pipeline import run_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatMessageResponse)
def send_message(request: ChatMessageRequest, db: Session = Depends(get_db)):
    """Send a chat message. Creates a new session if session_id is not provided."""
    # Load existing session or create a new one
    if request.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == request.session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        messages = list(session.messages or [])
    else:
        session = ChatSession(messages=[])
        db.add(session)
        db.flush()
        messages = []

    # Append user message
    messages.append({"role": "user", "content": request.message})

    # Call LLM
    try:
        reply = chat_with_llm(messages)
    except Exception as e:
        logger.exception("LLM chat call failed")
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")

    # Append assistant reply and persist
    messages.append({"role": "assistant", "content": reply})
    session.messages = messages
    db.commit()

    return ChatMessageResponse(session_id=session.id, reply=reply)


@router.post("/{session_id}/finalize", response_model=FinalizeResponse)
def finalize_itinerary(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Convert the conversation to a structured itinerary and launch the pipeline."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = list(session.messages or [])
    if not messages:
        raise HTTPException(status_code=400, detail="No conversation to finalize")

    # Generate structured JSON from conversation
    try:
        itinerary_data = generate_itinerary_json(messages)
    except Exception as e:
        logger.exception("LLM JSON generation failed")
        raise HTTPException(status_code=500, detail=f"Failed to generate itinerary structure: {str(e)}")

    # Validate against the trip schema
    try:
        trip_request = TripCreateRequest(**itinerary_data)
    except Exception as e:
        logger.error(f"Schema validation failed. Data: {itinerary_data}. Error: {e}")
        raise HTTPException(
            status_code=422,
            detail="The itinerary structure was invalid. Please add more details (hotels, dates, places) and try again.",
        )

    # Create Trip record
    trip = Trip(
        title=trip_request.title,
        start_date=trip_request.start_date,
        end_date=trip_request.end_date,
        status="pending",
    )
    db.add(trip)
    db.flush()

    # Build geocoding hints from city/country fields provided by LLM
    geocoding_hints: dict[str, dict] = {}

    # Create Day and Place records
    for day_input in trip_request.days:
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
            # Store city/country hint for geocoding if provided by LLM
            if place_input.city or place_input.country:
                hint_key = f"{day_input.day_number}:{place_input.name}"
                geocoding_hints[hint_key] = {
                    "city": place_input.city or "",
                    "country": place_input.country or "",
                }

    # Store geocoding hints in enriched_data so the pipeline can use them
    if geocoding_hints:
        trip.enriched_data = {"geocoding_hints": geocoding_hints}
        logger.info(f"Stored {len(geocoding_hints)} geocoding hints for trip {trip.id}")

    # Link session to trip and persist
    session.trip_id = trip.id
    db.commit()
    db.refresh(trip)

    # Launch background pipeline (same as manual entry flow)
    background_tasks.add_task(run_pipeline, trip.id)

    logger.info(f"Finalized chat session {session_id} → trip {trip.id} ({trip.title})")
    return FinalizeResponse(trip_id=trip.id, title=trip.title, status=trip.status)


@router.get("/{session_id}", response_model=ChatSessionResponse)
def get_session(session_id: str, db: Session = Depends(get_db)):
    """Return the full message history for a chat session."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return ChatSessionResponse(session_id=session.id, messages=session.messages or [])
