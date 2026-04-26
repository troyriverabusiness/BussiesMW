from schemas.status import StatusResponse


class StatusService:
    """Service responsible for status-related business logic."""

    def get_status(self) -> StatusResponse:
        """Build the API health response."""
        return StatusResponse(message="Veritas API is running")
