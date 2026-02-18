from contextlib import asynccontextmanager
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routers import trips, geocode, chat

# Configure logging to show in Docker logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting TravelBook Generator API v0.2.0 (with preview feature)")
    init_db()
    yield


app = FastAPI(title="TravelBook Generator", version="0.2.0", lifespan=lifespan)

# Configure CORS - allow frontend origins
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trips.router)
app.include_router(geocode.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok"}
