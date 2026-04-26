from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from data_access.legal_case_repository import LegalCaseRepository
from data_access.openai_chat_client import OpenAIChatClient
from data_access.trace_repository import TraceRepository
from schemas.chat import ChatRequest
from services.chat_service import ChatService
from services.chat_tool_registry import ChatToolRegistry
from services.legal_case_service import LegalCaseService
from services.trace_service import TraceService


router = APIRouter()


def get_chat_service() -> ChatService:
    case_repository = LegalCaseRepository()
    legal_case_service = LegalCaseService(repository=case_repository)
    trace_service = TraceService(
        case_repository=case_repository,
        trace_repository=TraceRepository(),
    )
    tool_registry = ChatToolRegistry(
        legal_case_service=legal_case_service,
        trace_service=trace_service,
    )
    return ChatService(
        openai_client=OpenAIChatClient(),
        tool_registry=tool_registry,
    )


@router.post("/chat")
def stream_chat(
    payload: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    return StreamingResponse(
        service.stream_chat(payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
