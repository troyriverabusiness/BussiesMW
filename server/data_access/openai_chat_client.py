import os
from typing import Any

from openai import OpenAI


DEFAULT_OPENAI_CHAT_MODEL = "gpt-5.5"


class OpenAIChatConfigurationError(RuntimeError):
    """Raised when the OpenAI chat client cannot be configured."""


class OpenAIChatClient:
    def __init__(self, client: OpenAI | None = None) -> None:
        self._client = client

    def create_completion_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> Any:
        return self._get_client().chat.completions.create(
            model=self._chat_model,
            messages=messages,
            stream=True,
            tools=tools,
            tool_choice="auto",
        )

    @property
    def _chat_model(self) -> str:
        return os.getenv("OPENAI_CHAT_MODEL", DEFAULT_OPENAI_CHAT_MODEL).strip() or DEFAULT_OPENAI_CHAT_MODEL

    def _get_client(self) -> OpenAI:
        if self._client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise OpenAIChatConfigurationError("OPENAI_API_KEY is not configured.")

            self._client = OpenAI(api_key=api_key)

        return self._client
