import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.bookings import router as bookings_router
from app.api.centres import router as centres_router
from app.api.payments import router as payments_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.session import engine

logger = logging.getLogger("eve.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    Base.metadata.create_all(bind=engine)
    yield


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Diagnostic booking and simulated payment service for EVE Healthcare.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    logger.info(
        f"{request.method} {request.url.path} status={response.status_code} latency={duration_ms}ms"
    )
    return response


app.include_router(auth_router)
app.include_router(centres_router)
app.include_router(bookings_router)
app.include_router(payments_router)


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok"}
