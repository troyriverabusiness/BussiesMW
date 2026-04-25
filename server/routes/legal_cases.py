from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from data_access.legal_case_repository import LegalCaseRepository
from database import get_db
from schemas.legal_case import LegalCaseResponse
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
