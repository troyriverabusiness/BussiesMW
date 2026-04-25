from datetime import datetime
from uuid import UUID
from uuid import uuid4

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime, Float, JSON, Uuid

from database import Base


class CaseTraceability(Base):
    __tablename__ = "case_traceability"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("legal_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email_subject: Mapped[str] = mapped_column(String(240), nullable=False)
    email_sender: Mapped[str] = mapped_column(String(160), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)


class Trace(Base):
    __tablename__ = "traces"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    case_traceability_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("case_traceability.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    human_in_loop_required: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TraceStep(Base):
    __tablename__ = "trace_steps"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    trace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("traces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step: Mapped[str] = mapped_column(String(160), nullable=False)
    input: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    output: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    tool_calls: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    human_in_loop_required: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HumanReview(Base):
    __tablename__ = "human_reviews"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    trace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("traces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trace_step_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("trace_steps.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
