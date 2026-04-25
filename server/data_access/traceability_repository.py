from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.legal_case import LegalCase
from models.traceability import CaseTraceability, HumanReview, Trace, TraceStep
from schemas.traceability import HumanReviewCreate


class TraceabilityRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_case(self, case_id: UUID) -> LegalCase | None:
        return self._db.get(LegalCase, case_id)

    def get_case_traceability(self, case_id: UUID) -> CaseTraceability | None:
        statement = (
            select(CaseTraceability)
            .where(CaseTraceability.case_id == case_id)
            .order_by(CaseTraceability.received_at.desc())
            .limit(1)
        )
        return self._db.scalar(statement)

    def list_traces(self, traceability_id: UUID) -> list[Trace]:
        statement = select(Trace).where(Trace.case_traceability_id == traceability_id).order_by(Trace.created_at)
        return list(self._db.scalars(statement).all())

    def list_steps(self, trace_id: UUID) -> list[TraceStep]:
        statement = select(TraceStep).where(TraceStep.trace_id == trace_id).order_by(TraceStep.created_at)
        return list(self._db.scalars(statement).all())

    def list_reviews(self, trace_id: UUID) -> list[HumanReview]:
        statement = select(HumanReview).where(HumanReview.trace_id == trace_id).order_by(HumanReview.reviewed_at)
        return list(self._db.scalars(statement).all())

    def create_review(self, payload: HumanReviewCreate) -> HumanReview:
        review = HumanReview(
            trace_id=payload.trace_id,
            trace_step_id=payload.trace_step_id,
            reviewer_name=payload.reviewer_name,
            decision=payload.decision,
            comment=payload.comment,
            reviewed_at=datetime.now(UTC),
        )
        self._db.add(review)
        self._db.commit()
        self._db.refresh(review)
        return review
