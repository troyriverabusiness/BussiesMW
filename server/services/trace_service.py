from uuid import UUID

from data_access.legal_case_repository import LegalCaseRepository
from data_access.trace_repository import TraceRepository
from schemas.trace import TraceResponse


class TraceService:
    def __init__(
        self,
        case_repository: LegalCaseRepository,
        trace_repository: TraceRepository,
    ) -> None:
        self._case_repository = case_repository
        self._trace_repository = trace_repository

    def list_case_traces(self, case_id: UUID) -> list[TraceResponse] | None:
        legal_case = self._case_repository.get_by_id(case_id)
        if legal_case is None:
            return None

        traces = self._trace_repository.list_by_case_id(case_id)
        return [TraceResponse.model_validate(trace) for trace in traces]
