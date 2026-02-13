import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.database import Base, get_db
from app.main import app
from app.services.pipeline import set_session_factory

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    set_session_factory(TestingSessionLocal)
    yield
    Base.metadata.drop_all(bind=engine)
    set_session_factory(None)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


SAMPLE_TRIP = {
    "title": "Paris Adventure",
    "start_date": "2025-06-01",
    "end_date": "2025-06-03",
    "days": [
        {
            "day_number": 1,
            "start_location": "CDG Airport",
            "end_location": "Hotel Le Marais",
            "places": [
                {"name": "Eiffel Tower", "place_type": "attraction"},
                {"name": "Louvre Museum", "place_type": "attraction"},
                {"name": "Café de Flore", "place_type": "restaurant"},
            ],
        },
        {
            "day_number": 2,
            "start_location": "Hotel Le Marais",
            "end_location": "Hotel Le Marais",
            "places": [
                {"name": "Notre-Dame Cathedral", "place_type": "attraction"},
                {"name": "Le Jules Verne", "place_type": "restaurant"},
            ],
        },
    ],
}
