from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging
from app.api.routes import router as api_router
import structlog

setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting_up")
    await init_db()
    logger.info("database_initialized")
    yield
    logger.info("shutting_down")


app = FastAPI(
    title="InPlant Learning Path Recommender",
    description="AI-powered personalized learning path recommendation system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "inplant-backend"}


@app.get("/")
async def root():
    return {
        "name": "InPlant Learning Path Recommender",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }