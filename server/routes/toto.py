from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from data_access.legal_case_repository import LegalCaseRepository
from database import get_db
from schemas.toto import TotoChatRequest, TotoChatResponse
from services.toto_service import TotoService


router = APIRouter()


def get_toto_service(db: Session = Depends(get_db)) -> TotoService:
    repository = LegalCaseRepository(db=db)
    return TotoService(repository=repository)


@router.post("/toto/chat", response_model=TotoChatResponse)
def chat_with_toto(
    payload: TotoChatRequest,
    service: TotoService = Depends(get_toto_service),
) -> TotoChatResponse:
    return service.get_case_update(payload)
