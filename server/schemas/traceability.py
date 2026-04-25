from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TraceStepResponse(BaseModel):
    id: UUID
    trace_id: UUID = Field(alias="traceId")
    step: str
    input: dict[str, object]
    output: dict[str, object]
    reasoning: str
    confidence: float
    tool_calls: list[dict[str, object]] = Field(alias="toolCalls")
    human_in_loop_required: bool = Field(alias="humanInLoopRequired")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class HumanReviewResponse(BaseModel):
    id: UUID
    trace_id: UUID = Field(alias="traceId")
    trace_step_id: UUID | None = Field(alias="traceStepId")
    reviewer_name: str = Field(alias="reviewerName")
    decision: str
    comment: str
    reviewed_at: datetime = Field(alias="reviewedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TraceResponse(BaseModel):
    id: UUID
    status: str
    confidence: float
    human_in_loop_required: bool = Field(alias="humanInLoopRequired")
    created_at: datetime = Field(alias="createdAt")
    steps: list[TraceStepResponse]
    reviews: list[HumanReviewResponse]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CaseTraceabilityResponse(BaseModel):
    id: UUID
    case_id: UUID = Field(alias="caseId")
    case_number: str = Field(alias="caseNumber")
    issue_summary: str = Field(alias="issueSummary")
    email_subject: str = Field(alias="emailSubject")
    email_sender: str = Field(alias="emailSender")
    received_at: datetime = Field(alias="receivedAt")
    started_at: datetime = Field(alias="startedAt")
    completed_at: datetime = Field(alias="completedAt")
    status: str
    traces: list[TraceResponse]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class HumanReviewCreate(BaseModel):
    trace_id: UUID = Field(alias="traceId")
    trace_step_id: UUID | None = Field(default=None, alias="traceStepId")
    reviewer_name: str = Field(default="Legal reviewer", alias="reviewerName")
    decision: str
    comment: str

    model_config = ConfigDict(populate_by_name=True)
