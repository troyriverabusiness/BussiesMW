import json
from collections.abc import Iterator
from typing import Any

from data_access.openai_chat_client import OpenAIChatClient
from schemas.chat import ChatRequest
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
    ) -> None:
        self._openai_client = openai_client
        self._tool_registry = tool_registry

    def stream_chat(self, payload: ChatRequest) -> Iterator[str]:
        messages = self._build_messages(payload)

        try:
            yield from self._stream_model_loop(messages)
        except Exception as exc:
            yield _sse_event({"error": str(exc)})
        finally:
            yield _sse_event("[DONE]")

    def _stream_model_loop(self, messages: list[dict[str, Any]]) -> Iterator[str]:
        for iteration in range(MAX_TOOL_ITERATIONS):
            content_parts: list[str] = []
            tool_calls = yield from self._stream_completion(messages, content_parts)

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
                yield _sse_event({"tool_call": {"name": tool_name, "args": tool_args}})

                tool_result = self._dispatch_tool(tool_name, tool_args)
                yield _sse_event({"tool_result": {"name": tool_name}})

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

    def _build_messages(self, payload: ChatRequest) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are Toto, a legal operations assistant. Use local tools when case "
                    "or traceability data is needed. Keep answers concise and grounded in "
                    "the tool results."
                ),
            }
        ]

        for message in payload.messages:
            messages.append({"role": message.role, "content": message.content})

        user_content = payload.message
        if payload.case_id:
            user_content = f"{payload.message}\n\nCurrent case ID: {payload.case_id}"
        messages.append({"role": "user", "content": user_content})
        return messages

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
