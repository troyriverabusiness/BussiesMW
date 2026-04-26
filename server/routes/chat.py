from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from data_access.chat_repository import ChatRepository, ChatRepositoryError
from data_access.legal_case_repository import LegalCaseRepository, LegalCaseRepositoryError
from data_access.openai_chat_client import OpenAIChatClient
from data_access.trace_repository import TraceRepository
from schemas.chat import ChatPersistedMessageResponse, ChatRequest, ChatSessionCreateRequest, ChatSessionResponse
from services.chat_service import ChatService
from services.chat_tool_registry import ChatToolRegistry
from services.internal_contact_service import InternalContactService
from services.legal_case_service import LegalCaseService
from services.trace_service import TraceService
from supabase_client import SupabaseConfigurationError


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
        internal_contact_service=InternalContactService(),
        external_contact_service=InternalContactService(chat_id_environment_key="TELEGRAM_EXTERNAL_CHAT_ID"),
    )
    return ChatService(
        openai_client=OpenAIChatClient(),
        tool_registry=tool_registry,
        chat_repository=ChatRepository(),
        case_repository=case_repository,
    )


def _service_unavailable_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


@router.get("/cases/{case_id}/chat-sessions", response_model=list[ChatSessionResponse])
def read_case_chat_sessions(
    case_id: UUID,
    service: ChatService = Depends(get_chat_service),
) -> list[ChatSessionResponse]:
    try:
        sessions = service.list_case_sessions(case_id)
    except (SupabaseConfigurationError, ChatRepositoryError, LegalCaseRepositoryError) as exc:
        raise _service_unavailable_error(exc) from exc

    if sessions is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return sessions


@router.post("/cases/{case_id}/chat-sessions", response_model=ChatSessionResponse)
def create_case_chat_session(
    case_id: UUID,
    payload: ChatSessionCreateRequest | None = None,
    service: ChatService = Depends(get_chat_service),
) -> ChatSessionResponse:
    try:
        session = service.create_case_session(case_id, title=payload.title if payload else None)
    except (SupabaseConfigurationError, ChatRepositoryError, LegalCaseRepositoryError) as exc:
        raise _service_unavailable_error(exc) from exc

    if session is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return session


@router.get("/chat-sessions/{session_id}/messages", response_model=list[ChatPersistedMessageResponse])
def read_chat_session_messages(
    session_id: UUID,
    service: ChatService = Depends(get_chat_service),
) -> list[ChatPersistedMessageResponse]:
    try:
        messages = service.list_session_messages(session_id)
    except (SupabaseConfigurationError, ChatRepositoryError) as exc:
        raise _service_unavailable_error(exc) from exc

    if messages is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return messages


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
