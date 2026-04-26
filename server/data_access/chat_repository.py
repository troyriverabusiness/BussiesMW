from datetime import UTC, datetime
from uuid import UUID

from httpx import HTTPError
from postgrest.exceptions import APIError
from supabase import Client

from supabase_client import get_supabase_client


class ChatRepositoryError(RuntimeError):
    """Raised when Supabase cannot fulfill a chat history query."""


class ChatRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client

    def list_sessions_by_case_id(self, case_id: UUID) -> list[dict[str, object]]:
        try:
            response = (
                self._get_client()
                .table("chat_sessions")
                .select("*")
                .eq("case_id", str(case_id))
                .order("updated_at", desc=True)
                .execute()
            )
        except (APIError, HTTPError) as exc:
            raise ChatRepositoryError("Unable to fetch chat sessions from Supabase.") from exc

        return list(response.data or [])

    def create_session(self, case_id: UUID, title: str = "New chat") -> dict[str, object]:
        try:
            response = (
                self._get_client()
                .table("chat_sessions")
                .insert({"case_id": str(case_id), "title": title})
                .execute()
            )
        except (APIError, HTTPError) as exc:
            raise ChatRepositoryError("Unable to create chat session in Supabase.") from exc

        sessions = response.data or []
        if not sessions:
            raise ChatRepositoryError("Supabase did not return the created chat session.")
        return dict(sessions[0])

    def get_session(self, session_id: UUID) -> dict[str, object] | None:
        try:
            response = (
                self._get_client()
                .table("chat_sessions")
                .select("*")
                .eq("id", str(session_id))
                .limit(1)
                .execute()
            )
        except (APIError, HTTPError) as exc:
            raise ChatRepositoryError("Unable to fetch chat session from Supabase.") from exc

        sessions = response.data or []
        return dict(sessions[0]) if sessions else None

    def list_messages_by_session_id(self, session_id: UUID) -> list[dict[str, object]]:
        try:
            response = (
                self._get_client()
                .table("chat_messages")
                .select("*")
                .eq("session_id", str(session_id))
                .order("created_at")
                .execute()
            )
        except (APIError, HTTPError) as exc:
            raise ChatRepositoryError("Unable to fetch chat messages from Supabase.") from exc

        return list(response.data or [])

    def add_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        tool_calls: list[dict[str, object]] | None = None,
        tool_results: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "session_id": str(session_id),
            "role": role,
            "content": content,
        }
        if tool_calls is not None:
            payload["tool_calls"] = tool_calls
        if tool_results is not None:
            payload["tool_results"] = tool_results

        try:
            response = self._get_client().table("chat_messages").insert(payload).execute()
        except (APIError, HTTPError) as exc:
            raise ChatRepositoryError("Unable to save chat message in Supabase.") from exc

        messages = response.data or []
        if not messages:
            raise ChatRepositoryError("Supabase did not return the created chat message.")
        return dict(messages[0])

    def update_session_after_message(self, session_id: UUID, title: str | None = None) -> None:
        payload: dict[str, object] = {"updated_at": datetime.now(UTC).isoformat()}
        if title:
            payload["title"] = title

        try:
            (
                self._get_client()
                .table("chat_sessions")
                .update(payload)
                .eq("id", str(session_id))
                .execute()
            )
        except (APIError, HTTPError) as exc:
            raise ChatRepositoryError("Unable to update chat session in Supabase.") from exc

    def _get_client(self) -> Client:
        if self._client is None:
            self._client = get_supabase_client()

        return self._client
