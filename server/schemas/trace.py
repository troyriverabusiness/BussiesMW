from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TraceStepResponse(BaseModel):
    id: UUID
    trace_id: UUID = Field(alias="traceId")
    step: str
    input: Any
    output: Any
    reasoning: str
    confidence: float
    tool_calls: Any = Field(alias="toolCalls")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)


class TraceResponse(BaseModel):
    id: UUID
    case_id: UUID | None = Field(default=None, alias="caseId")
    started_at: datetime | None = Field(default=None, alias="startedAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")
    trace_steps: list[TraceStepResponse] = Field(default_factory=list, alias="traceSteps")

    model_config = ConfigDict(populate_by_name=True)
