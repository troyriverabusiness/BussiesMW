from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    case_id: UUID | None = Field(default=None, alias="caseId")
    messages: list[ChatMessage] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)
