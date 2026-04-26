import json
from collections.abc import Iterator
from typing import Any
from uuid import UUID

from data_access.chat_repository import ChatRepository
from data_access.legal_case_repository import LegalCaseRepository
from data_access.openai_chat_client import OpenAIChatClient
from schemas.chat import ApprovedToolCall, ChatPersistedMessageResponse, ChatRequest, ChatSessionResponse
from services.chat_tool_registry import ChatToolRegistry


MAX_TOOL_ITERATIONS = 6


def _sse_event(payload: dict[str, Any] | str) -> str:
    if isinstance(payload, str):
        return f"data: {payload}\n\n"

    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


class ChatService:
    def __init__(
        self,
        openai_client: OpenAIChatClient,
        tool_registry: ChatToolRegistry,
        chat_repository: ChatRepository,
        case_repository: LegalCaseRepository,
    ) -> None:
        self._openai_client = openai_client
        self._tool_registry = tool_registry
        self._chat_repository = chat_repository
        self._case_repository = case_repository

    def list_case_sessions(self, case_id: UUID) -> list[ChatSessionResponse] | None:
        if self._case_repository.get_by_id(case_id) is None:
            return None

        sessions = self._chat_repository.list_sessions_by_case_id(case_id)
        return [ChatSessionResponse.model_validate(session) for session in sessions]

    def create_case_session(self, case_id: UUID, title: str | None = None) -> ChatSessionResponse | None:
        if self._case_repository.get_by_id(case_id) is None:
            return None

        session = self._chat_repository.create_session(
            case_id=case_id,
            title=self._session_title(title or "New chat"),
        )
        return ChatSessionResponse.model_validate(session)

    def list_session_messages(self, session_id: UUID) -> list[ChatPersistedMessageResponse] | None:
        if self._chat_repository.get_session(session_id) is None:
            return None

        messages = self._chat_repository.list_messages_by_session_id(session_id)
        return [ChatPersistedMessageResponse.model_validate(message) for message in messages]

    def stream_chat(self, payload: ChatRequest) -> Iterator[str]:
        try:
            session = self._prepare_session(payload)
            persisted_messages = None
            if session:
                yield _sse_event({"session": {"id": str(session["id"])}})
                persisted_messages = self._chat_repository.list_messages_by_session_id(UUID(str(session["id"])))

            messages = self._build_messages(payload, persisted_messages)
            assistant_content_parts: list[str] = []
            tool_calls_log: list[dict[str, object]] = []
            tool_results_log: list[dict[str, object]] = []

            if payload.approved_tool_call:
                yield from self._stream_approved_tool_call(
                    payload.approved_tool_call,
                    assistant_content_parts,
                    tool_calls_log,
                    tool_results_log,
                )
            else:
                yield from self._stream_model_loop(messages, assistant_content_parts, tool_calls_log, tool_results_log)
            if session:
                assistant_content = "".join(assistant_content_parts).strip()
                if assistant_content:
                    self._chat_repository.add_message(
                        session_id=UUID(str(session["id"])),
                        role="assistant",
                        content=assistant_content,
                        tool_calls=tool_calls_log or None,
                        tool_results=tool_results_log or None,
                    )
                    self._chat_repository.update_session_after_message(UUID(str(session["id"])))
        except Exception as exc:
            yield _sse_event({"error": str(exc)})
        finally:
            yield _sse_event("[DONE]")

    def _stream_model_loop(
        self,
        messages: list[dict[str, Any]],
        assistant_content_parts: list[str],
        tool_calls_log: list[dict[str, object]],
        tool_results_log: list[dict[str, object]],
    ) -> Iterator[str]:
        for iteration in range(MAX_TOOL_ITERATIONS):
            content_parts: list[str] = []
            tool_calls = yield from self._stream_completion(messages, content_parts)
            assistant_content_parts.extend(content_parts)

            if not tool_calls:
                return

            assistant_message = {
                "role": "assistant",
                "content": "".join(content_parts) or None,
                "tool_calls": list(tool_calls.values()),
            }
            messages.append(assistant_message)

            for tool_call in tool_calls.values():
                tool_name = str(tool_call["function"]["name"])
                tool_args = self._parse_tool_args(str(tool_call["function"]["arguments"]))
                tool_calls_log.append({"name": tool_name, "args": tool_args})
                yield _sse_event({"tool_call": {"name": tool_name, "args": tool_args}})

                if self._tool_registry.requires_approval(tool_name):
                    approval_message = "Approval required before contacting the external person."
                    assistant_content_parts.append(approval_message)
                    yield _sse_event({"approval_required": {"name": tool_name, "args": tool_args}})
                    yield _sse_event({"content": approval_message})
                    return

                tool_result = self._dispatch_tool(tool_name, tool_args)
                parsed_tool_result = self._parse_tool_result(tool_result)
                artifact = parsed_tool_result.get("artifact")
                if isinstance(artifact, dict):
                    tool_results_log.append({"name": tool_name, "artifact": artifact})
                else:
                    tool_results_log.append({"name": tool_name})
                yield _sse_event({"tool_result": {"name": tool_name}})
                if isinstance(artifact, dict):
                    yield _sse_event({"download": artifact})

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": tool_name,
                        "content": tool_result,
                    }
                )

            if iteration == MAX_TOOL_ITERATIONS - 1:
                yield _sse_event({"error": "Tool loop exceeded maximum iterations."})

    def _stream_completion(
        self,
        messages: list[dict[str, Any]],
        content_parts: list[str],
    ) -> Iterator[str]:
        tool_calls: dict[int, dict[str, Any]] = {}
        stream = self._openai_client.create_completion_stream(
            messages=messages,
            tools=self._tool_registry.tools,
        )

        for chunk in stream:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            if delta.content:
                content_parts.append(delta.content)
                yield _sse_event({"content": delta.content})

            for delta_tool_call in delta.tool_calls or []:
                index = delta_tool_call.index
                tool_call = tool_calls.setdefault(
                    index,
                    {
                        "id": "",
                        "type": "function",
                        "function": {"name": "", "arguments": ""},
                    },
                )
                if delta_tool_call.id:
                    tool_call["id"] = delta_tool_call.id
                if delta_tool_call.function:
                    if delta_tool_call.function.name:
                        tool_call["function"]["name"] += delta_tool_call.function.name
                    if delta_tool_call.function.arguments:
                        tool_call["function"]["arguments"] += delta_tool_call.function.arguments

        return tool_calls

    def _stream_approved_tool_call(
        self,
        approved_tool_call: ApprovedToolCall,
        assistant_content_parts: list[str],
        tool_calls_log: list[dict[str, object]],
        tool_results_log: list[dict[str, object]],
    ) -> Iterator[str]:
        tool_name = approved_tool_call.name
        tool_args = approved_tool_call.args
        if not self._tool_registry.requires_approval(tool_name):
            yield _sse_event({"error": f"Tool does not require approval: {tool_name}"})
            return

        tool_calls_log.append({"name": tool_name, "args": tool_args})
        yield _sse_event({"tool_call": {"name": tool_name, "args": tool_args}})

        raw_result = self._dispatch_tool(tool_name, tool_args)
        tool_results_log.append({"name": tool_name})
        yield _sse_event({"tool_result": {"name": tool_name}})

        result = self._parse_tool_result(raw_result)
        if result.get("sent") is True:
            response_text = "External contact message sent."
        else:
            error = str(result.get("error") or "Unknown error.")
            response_text = f"External contact message was not sent: {error}"

        assistant_content_parts.append(response_text)
        yield _sse_event({"content": response_text})

    def _build_messages(
        self,
        payload: ChatRequest,
        persisted_messages: list[dict[str, object]] | None = None,
    ) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are Veritas, a legal operations assistant. Use local tools when case "
                    "or traceability data is needed. Use the contact_internal_employee tool "
                    "when the user asks you to notify, message, escalate to, or contact an "
                    "internal employee. Use the contact_external_person tool when the user "
                    "asks you to contact an external person; that tool will be paused for "
                    "explicit user approval before it sends anything. Use the "
                    "generate_legal_document_pdf tool when the user asks you to draft, create, "
                    "generate, download, prepare, or produce a legal document such as a court "
                    "order, contract, agreement, notice, letter, or filing. Draft complete, "
                    "formal sections for the tool arguments; include the current case ID when "
                    "available. Keep answers concise and grounded in the tool results."
                ),
            }
        ]
        if payload.case_id:
            messages.append({"role": "system", "content": f"Current case ID: {payload.case_id}"})

        if persisted_messages is not None:
            for message in persisted_messages:
                messages.append({"role": message["role"], "content": message["content"]})
            return messages

        for message in payload.messages:
            messages.append({"role": message.role, "content": message.content})

        user_content = payload.message
        if payload.case_id:
            user_content = f"{payload.message}\n\nCurrent case ID: {payload.case_id}"
        messages.append({"role": "user", "content": user_content})
        return messages

    def _prepare_session(self, payload: ChatRequest) -> dict[str, object] | None:
        if payload.session_id:
            session = self._chat_repository.get_session(payload.session_id)
            if session is None:
                raise ValueError("Chat session not found.")
            if payload.case_id and str(session["case_id"]) != str(payload.case_id):
                raise ValueError("Chat session does not belong to the current case.")

            self._chat_repository.add_message(
                session_id=payload.session_id,
                role="user",
                content=payload.message,
            )
            title = self._title_for_existing_session(session, payload.message)
            self._chat_repository.update_session_after_message(payload.session_id, title=title)
            if title:
                session["title"] = title
            return session

        if not payload.case_id:
            return None

        session = self._chat_repository.create_session(
            case_id=payload.case_id,
            title=self._session_title(payload.message),
        )
        session_id = UUID(str(session["id"]))
        self._chat_repository.add_message(
            session_id=session_id,
            role="user",
            content=payload.message,
        )
        self._chat_repository.update_session_after_message(session_id)
        return session

    def _title_for_existing_session(self, session: dict[str, object], message: str) -> str | None:
        current_title = str(session.get("title") or "")
        if current_title and current_title != "New chat":
            return None
        return self._session_title(message)

    def _session_title(self, value: str) -> str:
        title = " ".join(value.split())
        if not title:
            return "New chat"
        return title[:60]

    def _parse_tool_args(self, raw_args: str) -> dict[str, Any]:
        if not raw_args:
            return {}

        args = json.loads(raw_args)
        return args if isinstance(args, dict) else {"value": args}

    def _dispatch_tool(self, name: str, args: dict[str, Any]) -> str:
        try:
            return self._tool_registry.dispatch_json(name, args)
        except Exception as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)

    def _parse_tool_result(self, raw_result: str) -> dict[str, Any]:
        try:
            result = json.loads(raw_result)
        except json.JSONDecodeError:
            return {}
        return result if isinstance(result, dict) else {}
