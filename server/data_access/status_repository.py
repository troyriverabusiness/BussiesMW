class StatusRepository:
    """Repository responsible for reading raw status data."""

    def fetch_status_message(self) -> str:
        """Return the raw status message from the data source."""
        return "Server is running"
