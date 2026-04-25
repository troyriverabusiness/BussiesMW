from data_access.legal_case_repository import LegalCaseRepository
from models.legal_case import LegalCase
from uuid import UUID


class LegalCaseService:
    def __init__(self, repository: LegalCaseRepository) -> None:
        self._repository = repository

    def list_cases(self) -> list[LegalCase]:
        return self._repository.list_all()

    def get_case(self, case_id: UUID) -> LegalCase | None:
        return self._repository.get_by_id(case_id)
