from fastapi import APIRouter, Depends

from data_access.legal_case_repository import LegalCaseRepository, LegalCaseRepositoryError
from schemas.veritas import VeritasChatRequest, VeritasChatResponse
from services.veritas_service import VeritasService
from supabase_client import SupabaseConfigurationError


router = APIRouter()


def get_veritas_service() -> VeritasService:
    repository = LegalCaseRepository()
    return VeritasService(repository=repository)

# TODO: Implement correctly
@router.post("/veritas/chat", response_model=VeritasChatResponse)
def chat_with_veritas(
    payload: VeritasChatRequest,
    service: VeritasService = Depends(get_veritas_service),
) -> VeritasChatResponse:
    try:
        return service.get_case_update(payload)
    except (SupabaseConfigurationError, LegalCaseRepositoryError) as exc:
        return VeritasChatResponse(
            status="Supabase unavailable",
            lastCorrespondence=str(exc),
            waitingFor="Confirm the server Supabase configuration and retry.",
            summary="Veritas could not fetch the latest case data from Supabase.",
        )
