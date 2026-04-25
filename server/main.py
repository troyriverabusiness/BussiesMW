import os
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import SessionLocal, create_database_schema
from routes.legal_cases import router as legal_cases_router
from routes.status import router as status_router
from routes.toto import router as toto_router
from seed import seed_legal_cases


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    create_database_schema()
    with SessionLocal() as db:
        seed_legal_cases(db)
    yield


def create_application() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    application = FastAPI(
        title="BussiesMW API",
        version="0.1.0",
        description="Legal-tech case orchestration API with PostgreSQL-backed case data.",
        lifespan=lifespan,
    )

    allowed_origins = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:4200,http://127.0.0.1:4200",
    ).split(",")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in allowed_origins if origin.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return application


app = create_application()
app.include_router(status_router, prefix="/api/v1", tags=["status"])
app.include_router(legal_cases_router, prefix="/api/v1", tags=["legal cases"])
app.include_router(toto_router, prefix="/api/v1", tags=["toto"])
