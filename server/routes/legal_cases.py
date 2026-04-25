from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from data_access.legal_case_repository import LegalCaseRepository, LegalCaseRepositoryError
from schemas.legal_case import LegalCaseDetailResponse, LegalCaseResponse
from services.legal_case_service import LegalCaseService
from supabase_client import SupabaseConfigurationError


router = APIRouter()


def get_legal_case_service() -> LegalCaseService:
    repository = LegalCaseRepository()
    return LegalCaseService(repository=repository)


def _service_unavailable_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


@router.get("/cases", response_model=list[LegalCaseResponse])
@router.get("/legal-cases", response_model=list[LegalCaseResponse], include_in_schema=False)
def read_legal_cases(
    service: LegalCaseService = Depends(get_legal_case_service),
) -> list[LegalCaseResponse]:
    try:
        return service.list_cases()
    except (SupabaseConfigurationError, LegalCaseRepositoryError) as exc:
        raise _service_unavailable_error(exc) from exc


@router.get("/cases/{case_id}", response_model=LegalCaseDetailResponse)
@router.get("/legal-cases/{case_id}", response_model=LegalCaseDetailResponse, include_in_schema=False)
def read_legal_case(
    case_id: UUID,
    service: LegalCaseService = Depends(get_legal_case_service),
) -> LegalCaseDetailResponse:
    try:
        legal_case = service.get_case(case_id)
    except (SupabaseConfigurationError, LegalCaseRepositoryError) as exc:
        raise _service_unavailable_error(exc) from exc

    if legal_case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    return legal_case
