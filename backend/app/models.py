import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    messages: Mapped[list | None] = mapped_column(JSON, nullable=True)  # list of {role, content}
    trip_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("trips.id"), nullable=True)


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[str | None] = mapped_column(String(10))
    end_date: Mapped[str | None] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    enriched_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    days: Mapped[list["Day"]] = relationship("Day", back_populates="trip", cascade="all, delete-orphan", order_by="Day.day_number")


class Day(Base):
    __tablename__ = "days"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trip_id: Mapped[str] = mapped_column(String(36), ForeignKey("trips.id"), nullable=False)
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_location: Mapped[str | None] = mapped_column(String(200))
    end_location: Mapped[str | None] = mapped_column(String(200))

    trip: Mapped["Trip"] = relationship("Trip", back_populates="days")
    places: Mapped[list["Place"]] = relationship("Place", back_populates="day", cascade="all, delete-orphan", order_by="Place.order_index")


class Place(Base):
    __tablename__ = "places"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    day_id: Mapped[int] = mapped_column(Integer, ForeignKey("days.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    place_type: Mapped[str] = mapped_column(String(20), nullable=False)  # hotel, attraction, restaurant
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    day: Mapped["Day"] = relationship("Day", back_populates="places")


class GeocodingCache(Base):
    __tablename__ = "geocoding_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    place_name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cached_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
