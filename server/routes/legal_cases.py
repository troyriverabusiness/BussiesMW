from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from data_access.legal_case_repository import LegalCaseRepository
from database import get_db
from schemas.legal_case import LegalCaseDetailResponse, LegalCaseResponse
from services.legal_case_service import LegalCaseService


router = APIRouter()


def get_legal_case_service(db: Session = Depends(get_db)) -> LegalCaseService:
    repository = LegalCaseRepository(db=db)
    return LegalCaseService(repository=repository)


@router.get("/legal-cases", response_model=list[LegalCaseResponse])
def read_legal_cases(
    service: LegalCaseService = Depends(get_legal_case_service),
) -> list[LegalCaseResponse]:
    return service.list_cases()


@router.get("/legal-cases/{case_id}", response_model=LegalCaseDetailResponse)
def read_legal_case(
    case_id: UUID,
    service: LegalCaseService = Depends(get_legal_case_service),
) -> LegalCaseDetailResponse:
    legal_case = service.get_case(case_id)
    if legal_case is None:
        raise HTTPException(status_code=404, detail="Legal case not found")

    return legal_case
