import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.legal_cases import router as legal_cases_router
from routes.status import router as status_router
from routes.toto import router as toto_router


def create_application() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    application = FastAPI(
        title="BussiesMW API",
        version="0.1.0",
        description="Legal-tech case orchestration API backed by server-side Supabase calls.",
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
