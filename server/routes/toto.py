from fastapi import APIRouter, Depends

from data_access.legal_case_repository import LegalCaseRepository, LegalCaseRepositoryError
from schemas.toto import TotoChatRequest, TotoChatResponse
from services.toto_service import TotoService
from supabase_client import SupabaseConfigurationError


router = APIRouter()


def get_toto_service() -> TotoService:
    repository = LegalCaseRepository()
    return TotoService(repository=repository)

# TODO: Implement correctly
@router.post("/toto/chat", response_model=TotoChatResponse)
def chat_with_toto(
    payload: TotoChatRequest,
    service: TotoService = Depends(get_toto_service),
) -> TotoChatResponse:
    try:
        return service.get_case_update(payload)
    except (SupabaseConfigurationError, LegalCaseRepositoryError) as exc:
        return TotoChatResponse(
            status="Supabase unavailable",
            lastCorrespondence=str(exc),
            waitingFor="Confirm the server Supabase configuration and retry.",
            summary="Toto could not fetch the latest case data from Supabase.",
        )
