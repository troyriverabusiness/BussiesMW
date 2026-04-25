from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from data_access.legal_case_repository import LegalCaseRepository, LegalCaseRepositoryError
from data_access.trace_repository import TraceRepository, TraceRepositoryError
from schemas.trace import TraceResponse
from services.trace_service import TraceService
from supabase_client import SupabaseConfigurationError


router = APIRouter()


def get_trace_service() -> TraceService:
    return TraceService(
        case_repository=LegalCaseRepository(),
        trace_repository=TraceRepository(),
    )


def _service_unavailable_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


@router.get("/cases/{case_id}/traces", response_model=list[TraceResponse])
@router.get("/legal-cases/{case_id}/traces", response_model=list[TraceResponse], include_in_schema=False)
def read_case_traces(
    case_id: UUID,
    service: TraceService = Depends(get_trace_service),
) -> list[TraceResponse]:
    try:
        traces = service.list_case_traces(case_id)
    except (SupabaseConfigurationError, LegalCaseRepositoryError, TraceRepositoryError) as exc:
        raise _service_unavailable_error(exc) from exc

    if traces is None:
        raise HTTPException(status_code=404, detail="Case not found")

    return traces
