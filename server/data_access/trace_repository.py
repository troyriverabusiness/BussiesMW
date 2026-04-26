from datetime import UTC, datetime
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

    def create_trace_step(
        self,
        case_id: UUID,
        step: str,
        input_payload: dict[str, object],
        output_payload: dict[str, object],
        reasoning: str,
        confidence: float,
        tool_calls: list[dict[str, object]],
    ) -> dict[str, object]:
        now = datetime.now(UTC).isoformat()
        try:
            trace_response = (
                self._get_client()
                .table("traces")
                .insert(
                    {
                        "case_id": str(case_id),
                        "started_at": now,
                        "completed_at": now,
                    }
                )
                .execute()
            )
            traces = trace_response.data or []
            if not traces:
                raise TraceRepositoryError("Supabase did not return the created trace.")

            trace_id = str(traces[0]["id"])
            step_response = (
                self._get_client()
                .table("trace_steps")
                .insert(
                    {
                        "trace_id": trace_id,
                        "step": step,
                        "input": input_payload,
                        "output": output_payload,
                        "reasoning": reasoning,
                        "confidence": confidence,
                        "tool_calls": tool_calls,
                        "created_at": now,
                    }
                )
                .execute()
            )
        except (APIError, HTTPError) as exc:
            raise TraceRepositoryError("Unable to save trace step in Supabase.") from exc

        trace_steps = step_response.data or []
        if not trace_steps:
            raise TraceRepositoryError("Supabase did not return the created trace step.")
        return dict(trace_steps[0])

    def _get_client(self) -> Client:
        if self._client is None:
            self._client = get_supabase_client()

        return self._client
