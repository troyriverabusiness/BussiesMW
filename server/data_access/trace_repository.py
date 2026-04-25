from uuid import UUID

from httpx import HTTPError
from postgrest.exceptions import APIError
from supabase import Client

from supabase_client import get_supabase_client


class TraceRepositoryError(RuntimeError):
    """Raised when Supabase cannot fulfill a traces query."""


class TraceRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client

    def list_by_case_id(self, case_id: UUID) -> list[dict[str, object]]:
        try:
            response = (
                self._get_client()
                .table("traces")
                .select("*, trace_steps(*)")
                .eq("case_id", str(case_id))
                .order("started_at", desc=True)
                .execute()
            )
        except (APIError, HTTPError) as exc:
            raise TraceRepositoryError("Unable to fetch traces from Supabase.") from exc

        traces = list(response.data or [])
        for trace in traces:
            trace_steps = trace.get("trace_steps")
            if isinstance(trace_steps, list):
                trace_steps.sort(key=lambda step: str(step.get("created_at") or ""))

        return traces

    def _get_client(self) -> Client:
        if self._client is None:
            self._client = get_supabase_client()

        return self._client
