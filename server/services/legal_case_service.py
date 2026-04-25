from uuid import UUID

from data_access.legal_case_repository import LegalCaseRepository
from schemas.legal_case import LegalCaseDetailResponse, LegalCaseResponse


class LegalCaseService:
    def __init__(self, repository: LegalCaseRepository) -> None:
        self._repository = repository

    def list_cases(self) -> list[LegalCaseResponse]:
        return [LegalCaseResponse.model_validate(case) for case in self._repository.list_all()]

    def get_case(self, case_id: UUID) -> LegalCaseDetailResponse | None:
        legal_case = self._repository.get_by_id(case_id)
        if legal_case is None:
            return None

        return LegalCaseDetailResponse.model_validate(legal_case)
