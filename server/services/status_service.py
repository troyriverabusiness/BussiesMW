from data_access.status_repository import StatusRepository
from schemas.status import StatusResponse


class StatusService:
    """Service responsible for status-related business logic."""

    def __init__(self, repository: StatusRepository) -> None:
        self._repository = repository

    def get_status(self) -> StatusResponse:
        """Build the API response using repository data."""
        message = self._repository.fetch_status_message()
        return StatusResponse(message=message)
