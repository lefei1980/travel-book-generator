from pydantic import BaseModel, field_validator
from typing import Optional


class PlaceInput(BaseModel):
    name: str
    place_type: str  # hotel, attraction, restaurant

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        return " ".join(v.strip().split())

    @field_validator("place_type")
    @classmethod
    def validate_place_type(cls, v: str) -> str:
        allowed = {"hotel", "attraction", "restaurant"}
        v = v.strip().lower()
        if v not in allowed:
            raise ValueError(f"place_type must be one of: {', '.join(allowed)}")
        return v


class DayInput(BaseModel):
    day_number: int
    start_location: Optional[str] = None
    end_location: Optional[str] = None
    places: list[PlaceInput]

    @field_validator("places")
    @classmethod
    def validate_place_count(cls, v: list[PlaceInput]) -> list[PlaceInput]:
        if len(v) > 5:
            raise ValueError("Maximum 5 places per day")
        return v

    @field_validator("start_location", "end_location", mode="before")
    @classmethod
    def normalize_location(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return " ".join(v.strip().split())


class TripCreateRequest(BaseModel):
    title: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    days: list[DayInput]

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty")
        return v

    @field_validator("days")
    @classmethod
    def validate_days(cls, v: list[DayInput]) -> list[DayInput]:
        if not v:
            raise ValueError("At least one day is required")
        numbers = [d.day_number for d in v]
        if len(numbers) != len(set(numbers)):
            raise ValueError("Day numbers must be unique")
        return sorted(v, key=lambda d: d.day_number)


class PlaceResponse(BaseModel):
    name: str
    place_type: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    model_config = {"from_attributes": True}


class RouteResponse(BaseModel):
    total_distance_m: float
    total_duration_s: float
    geometry: dict
    segments: Optional[list[dict]] = None

class DayResponse(BaseModel):
    day_number: int
    start_location: Optional[str] = None
    end_location: Optional[str] = None
    places: list[PlaceResponse]
    route: Optional[RouteResponse] = None

    model_config = {"from_attributes": True}


class TripResponse(BaseModel):
    id: str
    title: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    days: list[DayResponse]

    model_config = {"from_attributes": True}


class TripCreateResponse(BaseModel):
    id: str
    status: str
