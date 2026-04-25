from fastapi import APIRouter, Depends

from schemas.toto import TotoChatRequest, TotoChatResponse
from services.toto_service import TotoService


router = APIRouter()


def get_toto_service() -> TotoService:
    return TotoService()


@router.post("/toto/chat", response_model=TotoChatResponse)
def chat_with_toto(
    payload: TotoChatRequest,
    service: TotoService = Depends(get_toto_service),
) -> TotoChatResponse:
    return service.get_case_update(payload)
