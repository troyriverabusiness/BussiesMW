from uuid import UUID

from httpx import HTTPError
from postgrest.exceptions import APIError
from supabase import Client

from supabase_client import get_supabase_client


class LegalCaseRepositoryError(RuntimeError):
    """Raised when Supabase cannot fulfill a cases query."""


class LegalCaseRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client

    def list_all(self) -> list[dict[str, object]]:
        try:
            response = (
                self._get_client()
                .table("cases")
                .select("*")
                .order("last_update_date", desc=True)
                .execute()
            )
        except (APIError, HTTPError) as exc:
            raise LegalCaseRepositoryError("Unable to fetch cases from Supabase.") from exc

        return list(response.data or [])

    def get_by_id(self, case_id: UUID) -> dict[str, object] | None:
        try:
            response = (
                self._get_client()
                .table("cases")
                .select("*")
                .eq("id", str(case_id))
                .limit(1)
                .execute()
            )
        except (APIError, HTTPError) as exc:
            raise LegalCaseRepositoryError("Unable to fetch case from Supabase.") from exc

        cases = response.data or []
        return cases[0] if cases else None

    def _get_client(self) -> Client:
        if self._client is None:
            self._client = get_supabase_client()

        return self._client
