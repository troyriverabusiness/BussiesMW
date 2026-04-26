import json
import os
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


UrlOpen = Callable[..., Any]


class InternalContactService:
    def __init__(
        self,
        bot_token: str | None = None,
        chat_id: str | None = None,
        chat_id_environment_key: str = "TELEGRAM_INTERNAL_CHAT_ID",
        request_timeout_seconds: float = 10.0,
        urlopen_handler: UrlOpen = urlopen,
    ) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._chat_id_environment_key = chat_id_environment_key
        self._request_timeout_seconds = request_timeout_seconds
        self._urlopen = urlopen_handler

    def send_message(self, message: str) -> dict[str, Any]:
        cleaned_message = " ".join(message.split())
        if not cleaned_message:
            return {
                "sent": False,
                "channel": "telegram",
                "error": "message is required",
            }
        if len(cleaned_message) > 4096:
            return {
                "sent": False,
                "channel": "telegram",
                "error": "message must be 4096 characters or fewer",
            }

        bot_token = self._configured_value(self._bot_token, "TELEGRAM_BOT_TOKEN")
        chat_id = self._configured_value(self._chat_id, self._chat_id_environment_key)
        if not bot_token or not chat_id:
            return {
                "sent": False,
                "channel": "telegram",
                "error": "Telegram contact is not configured.",
            }

        payload = {"chat_id": chat_id, "text": cleaned_message}
        request = Request(
            url=f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            response = self._urlopen(request, timeout=self._request_timeout_seconds)
            status_code = getattr(response, "status", None) or getattr(response, "code", None)
            response_body = self._read_json(response)
        except HTTPError as exc:
            return {
                "sent": False,
                "channel": "telegram",
                "error": "Telegram API rejected the message.",
                "statusCode": exc.code,
            }
        except URLError:
            return {
                "sent": False,
                "channel": "telegram",
                "error": "Telegram API could not be reached.",
            }

        if status_code and status_code >= 400:
            return {
                "sent": False,
                "channel": "telegram",
                "error": "Telegram API rejected the message.",
                "statusCode": status_code,
            }
        if response_body and response_body.get("ok") is False:
            return {
                "sent": False,
                "channel": "telegram",
                "error": "Telegram API rejected the message.",
            }

        return {"sent": True, "channel": "telegram"}

    def _configured_value(self, provided_value: str | None, environment_key: str) -> str:
        return (provided_value if provided_value is not None else os.getenv(environment_key, "")).strip()

    def _read_json(self, response: Any) -> dict[str, Any] | None:
        raw_body = response.read()
        if not raw_body:
            return None
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return body if isinstance(body, dict) else None
