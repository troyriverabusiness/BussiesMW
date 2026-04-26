from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ApprovedToolCall(BaseModel):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    message: str
    case_id: UUID | None = Field(default=None, alias="caseId")
    session_id: UUID | None = Field(default=None, alias="sessionId")
    messages: list[ChatMessage] = Field(default_factory=list)
    approved_tool_call: ApprovedToolCall | None = Field(default=None, alias="approvedToolCall")

    model_config = ConfigDict(populate_by_name=True)


class ChatSessionCreateRequest(BaseModel):
    title: str | None = None


class ChatSessionResponse(BaseModel):
    id: UUID
    case_id: UUID = Field(alias="caseId")
    user_id: UUID | None = Field(default=None, alias="userId")
    title: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class ChatPersistedMessageResponse(BaseModel):
    id: UUID
    session_id: UUID = Field(alias="sessionId")
    role: Literal["user", "assistant"]
    content: str
    tool_calls: object | None = Field(default=None, alias="toolCalls")
    tool_results: object | None = Field(default=None, alias="toolResults")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)
