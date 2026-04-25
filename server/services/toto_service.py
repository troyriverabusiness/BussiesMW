from data_access.legal_case_repository import LegalCaseRepository
from schemas.toto import TotoChatRequest, TotoChatResponse


class TotoService:
    def __init__(self, repository: LegalCaseRepository) -> None:
        self._repository = repository

    def get_case_update(self, payload: TotoChatRequest) -> TotoChatResponse:
        if payload.case_id:
            legal_case = self._repository.get_by_id(payload.case_id)
            if legal_case is None:
                return TotoChatResponse(
                    status="Case not found",
                    lastCorrespondence="No case record was available for the provided identifier.",
                    waitingFor="Verify the case link and try again.",
                    summary="I could not find that case in the legal case registry.",
                )

            return TotoChatResponse(
                status=legal_case.status.value,
                lastCorrespondence=legal_case.last_correspondence,
                waitingFor=legal_case.waiting_for,
                summary=(
                    f"{legal_case.case_number} is currently {legal_case.status.value.lower()} with "
                    f"{legal_case.assigned_attorney} assigned. The risk level is "
                    f"{legal_case.priority_risk_level.value.lower()}, the next due date is "
                    f"{legal_case.next_due_date:%B %-d, %Y}, and the current blocker is: "
                    f"{legal_case.waiting_for}"
                ),
            )

        return TotoChatResponse(
            status="Action Required",
            lastCorrespondence="Legal operations received a new intake note from the business owner.",
            waitingFor="Matter owner assignment and initial risk triage.",
            summary=(
                "Toto can prepare a concise update once a case is selected. "
                "For now, the request appears to need ownership, status confirmation, and next-step routing."
            ),
        )
