from fastapi import APIRouter, Depends

from data_access.status_repository import StatusRepository
from schemas.status import StatusResponse
from services.status_service import StatusService


router = APIRouter()


def get_status_repository() -> StatusRepository:
    """Create the data access dependency for the request lifecycle."""
    return StatusRepository()


def get_status_service() -> StatusService:
    """Create the service dependency for the request lifecycle."""
    repository = get_status_repository()
    return StatusService(repository=repository)


@router.get("/status", response_model=StatusResponse)
def read_status(service: StatusService = Depends(get_status_service)) -> StatusResponse:
    """Return a simple status payload from the service layer."""
    return service.get_status()
