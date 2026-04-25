from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from data_access.traceability_repository import TraceabilityRepository
from database import get_db
from schemas.traceability import CaseTraceabilityResponse, HumanReviewCreate, HumanReviewResponse
from services.traceability_service import TraceabilityService


router = APIRouter()


def get_traceability_service(db: Session = Depends(get_db)) -> TraceabilityService:
    repository = TraceabilityRepository(db=db)
    return TraceabilityService(repository=repository)


@router.get("/legal-cases/{case_id}/traceability", response_model=CaseTraceabilityResponse)
def read_case_traceability(
    case_id: UUID,
    service: TraceabilityService = Depends(get_traceability_service),
) -> CaseTraceabilityResponse:
    traceability = service.get_case_traceability(case_id)
    if traceability is None:
        raise HTTPException(status_code=404, detail="Case traceability not found")

    return traceability


@router.post("/reviews", response_model=HumanReviewResponse)
def create_human_review(
    payload: HumanReviewCreate,
    service: TraceabilityService = Depends(get_traceability_service),
) -> HumanReviewResponse:
    return service.create_review(payload)
