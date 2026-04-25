from fastapi import FastAPI

from routes.status import router as status_router


def create_application() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    return FastAPI(
        title="BussiesMW API",
        version="0.1.0",
        description="Basic FastAPI skeleton with routes, services, and data access layers.",
    )


app = create_application()
app.include_router(status_router, prefix="/api/v1", tags=["status"])
